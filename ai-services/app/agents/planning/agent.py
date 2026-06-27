import logging
import re
import time

from app.agents.planning.fallbacks import (
    fallback_assignment_brief,
    fallback_evaluation_brief,
    fallback_interview_brief,
    prepend_assignment_directive,
)
from app.agents.planning.grounding import (
    ANALYST_SYSTEM,
    merge_analyst_overlay,
    run_keyword_grounding,
    _parse_analyst_json,
)
from app.agents.planning.llm import PlanningLLM
from app.agents.planning.prompts import (
    ASSIGNMENT_BRIEF_SYSTEM,
    EVALUATION_BRIEF_SYSTEM,
    INTERVIEW_BRIEF_SYSTEM,
)
from app.infra.tracing import set_span_attributes, span_ok, trace_span
from app.schemas.plan import GroundingFacts, InterviewPlan, PlanRequest
from app.skills.interview_planning.scripts.planning_tools import duration_for_seniority

logger = logging.getLogger(__name__)


def _build_shared_context(request: PlanRequest, facts: GroundingFacts) -> str:
    comp_lines = "\n".join(f"- {c.name}: {c.weight}%" for c in facts.competencies)
    evidence_lines = "\n".join(
        f"- {e.name}: \"{e.evidence}\"" for e in facts.skills_evidence[:6]
    ) or "- (none extracted)"
    problem = facts.suggested_problem
    problem_line = (
        f"{problem.title} ({problem.difficulty}) — {problem.statement[:200]}"
        if problem
        else "N/A"
    )
    directive = facts.assignment

    return f"""POSITION: {facts.position}
JD:
{request.jd_text[:3500]}

CV:
{request.cv_markdown[:3500]}

HR NOTES: {request.special_requirements or 'none'}

GROUNDING FACTS BLOCK:
seniority_level: {facts.seniority_level}
domain: {facts.domain}
required_skills: {', '.join(facts.required_skills) or 'n/a'}
must_have_skills: {', '.join(facts.mandatory_skills) or 'n/a'}
evidenced_in_cv:
{evidence_lines}
skill_gaps: {', '.join(facts.skill_gaps) or 'none'}
assignment_hint: type={directive.type}, mode={directive.mode}, ai_assistant={directive.ai_assistant}, difficulty={directive.difficulty}
suggested_coding_problem: {problem_line}
COMPETENCIES (exact names + weights):
{comp_lines}"""


def _strip_code_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _competency_coverage(brief: str, facts: GroundingFacts) -> float:
    if not facts.competencies:
        return 1.0
    hits = sum(1 for c in facts.competencies if c.name.lower() in brief.lower())
    return hits / len(facts.competencies)


def _verify_competency_consistency(interview_brief: str, evaluation_brief: str, facts: GroundingFacts) -> None:
    iv_cov = _competency_coverage(interview_brief, facts)
    ev_cov = _competency_coverage(evaluation_brief, facts)
    if iv_cov < 0.5:
        logger.warning(
            "interview_brief mentions only %.0f%% competencies (expected >50%%)",
            iv_cov * 100,
        )
    if ev_cov < 0.5:
        logger.warning(
            "evaluation_brief mentions only %.0f%% competencies (expected >50%%)",
            ev_cov * 100,
        )


async def _semantic_grounding(
    llm: PlanningLLM,
    request: PlanRequest,
    base_facts: GroundingFacts,
) -> GroundingFacts:
    if not llm.enabled:
        base_facts.analyst_degraded = True
        return base_facts

    user = _build_shared_context(request, base_facts)
    raw = await llm.run_agent(
        name="planning_analyst",
        instructions=ANALYST_SYSTEM,
        user_message=user,
        model=None,
        max_tokens=None,
    )
    if not raw:
        base_facts.analyst_degraded = True
        return base_facts

    parsed = _parse_analyst_json(raw)
    if not parsed:
        logger.warning("Analyst JSON parse failed — keeping keyword base")
        base_facts.analyst_degraded = True
        return base_facts

    return merge_analyst_overlay(base_facts, parsed)


async def _generate_brief(
    llm: PlanningLLM,
    *,
    name: str,
    system: str,
    context: str,
    fallback_fn,
    degraded_counter: list[int],
) -> str:
    with trace_span(f"planning.brief.{name}", kind="CHAIN", step=name):
        started = time.perf_counter()
        raw = await llm.run_agent(name=name, instructions=system, user_message=context)
        if raw:
            text = _strip_code_fences(raw)
            elapsed = time.perf_counter() - started
            set_span_attributes(
                degraded=False,
                output_chars=len(text),
                latency_ms=round(elapsed * 1000, 1),
            )
            logger.info("brief %s generated in %.2fs (%d chars)", name, elapsed, len(text))
            return text

        degraded_counter[0] += 1
        set_span_attributes(degraded=True)
        logger.info("brief %s degraded to fallback", name)
        return fallback_fn()


async def run_planning_agent(request: PlanRequest) -> tuple[InterviewPlan, dict]:
    """Main orchestrator: keyword grounding → analyst LLM → 3 sequential brief LLMs."""
    with trace_span(
        "planning.run",
        kind="AGENT",
        agent="planning",
        position=request.position,
        candidate_name=request.candidate_name,
        language=request.language,
    ):
        return await _run_planning_agent(request)


async def _run_planning_agent(request: PlanRequest) -> tuple[InterviewPlan, dict]:
    llm = PlanningLLM()
    degraded_briefs = [0]

    with trace_span("planning.keyword_grounding", kind="CHAIN", step="keyword_grounding"):
        _, _, keyword_facts = run_keyword_grounding(request)
        set_span_attributes(
            match_score=keyword_facts.match_score,
            seniority=keyword_facts.seniority_level,
            domain=keyword_facts.domain,
        )

    with trace_span("planning.semantic_grounding", kind="CHAIN", step="planning_analyst"):
        facts = await _semantic_grounding(llm, request, keyword_facts)
        set_span_attributes(
            analyst_degraded=facts.analyst_degraded,
            skill_gaps=len(facts.skill_gaps),
        )

    context = _build_shared_context(request, facts)

    interview_brief = await _generate_brief(
        llm,
        name="interview_brief",
        system=INTERVIEW_BRIEF_SYSTEM,
        context=context,
        fallback_fn=lambda: fallback_interview_brief(facts, request.cv_markdown),
        degraded_counter=degraded_briefs,
    )

    evaluation_brief = await _generate_brief(
        llm,
        name="evaluation_brief",
        system=EVALUATION_BRIEF_SYSTEM,
        context=context,
        fallback_fn=lambda: fallback_evaluation_brief(facts),
        degraded_counter=degraded_briefs,
    )

    assignment_body = await _generate_brief(
        llm,
        name="assignment_brief",
        system=ASSIGNMENT_BRIEF_SYSTEM,
        context=context,
        fallback_fn=lambda: fallback_assignment_brief(facts),
        degraded_counter=degraded_briefs,
    )
    assignment_brief = prepend_assignment_directive(assignment_body, facts)

    _verify_competency_consistency(interview_brief, evaluation_brief, facts)

    if degraded_briefs[0] > 0 or facts.analyst_degraded or not llm.enabled:
        source = "planning-agent+fallback"
    else:
        source = "planning-agent"

    plan = InterviewPlan(
        interview_brief=interview_brief,
        evaluation_brief=evaluation_brief,
        assignment_brief=assignment_brief,
        duration_minutes=duration_for_seniority(facts.seniority_level),
        source=source,
        grounding=facts,
    )

    meta = {
        "agent": "planning",
        "llm_enabled": llm.enabled,
        "degraded_briefs": degraded_briefs[0],
        "analyst_degraded": facts.analyst_degraded,
        "match_score": facts.match_score,
        "skill_gaps": facts.skill_gaps,
    }
    set_span_attributes(
        source=source,
        degraded_briefs=degraded_briefs[0],
        analyst_degraded=facts.analyst_degraded,
        match_score=facts.match_score,
    )
    span_ok(f"plan source={source}")
    return plan, meta


# Backward-compatible class wrapper
class PlanningAgent:
    async def run(self, request: PlanRequest):
        return await run_planning_agent(request)