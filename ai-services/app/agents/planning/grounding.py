import json
import logging
import re
from typing import Any

from app.schemas.plan import (
    AssignmentDirective,
    Competency,
    GroundingFacts,
    PlanRequest,
    RequirementsResult,
    SeniorityLevel,
    SkillEvidence,
    SkillMatchResult,
)
from app.skills.interview_planning.scripts.planning_tools import (
    build_assignment_directive,
    build_competencies,
    extract_evidence_quotes,
    match_skills,
    renormalize_competencies,
    search_problem_bank,
)
from app.skills.jd_analysis.scripts.jd_tools import extract_requirements, has_tech_skills

logger = logging.getLogger(__name__)

_VALID_SENIORITY = frozenset({"junior", "mid", "senior", "manager"})
_VALID_DOMAIN = frozenset({"backend", "frontend", "data", "devops", "ai"})


def run_keyword_grounding(request: PlanRequest) -> tuple[RequirementsResult, SkillMatchResult, GroundingFacts]:
    position = (request.position or "Engineer").strip()
    requirements = extract_requirements(request.jd_text, request.position)
    skill_match = match_skills(request.cv_markdown, requirements.required_skills)
    assignment = build_assignment_directive(
        required_skills=requirements.required_skills,
        seniority_level=requirements.seniority_level,
    )
    competencies = build_competencies(requirements=requirements, match=skill_match)
    suggested = search_problem_bank(requirements.domain, requirements.seniority_level)

    evidence_quotes = extract_evidence_quotes(request.cv_markdown, skill_match.matched_skills)
    skills_evidence = [
        SkillEvidence(name=skill, evidence=quote) for skill, quote in evidence_quotes
    ]

    facts = GroundingFacts(
        position=position,
        seniority_level=requirements.seniority_level,
        seniority_reason=f"Keyword scan of JD/position ({requirements.seniority_level})",
        domain=requirements.domain,
        required_skills=requirements.required_skills,
        mandatory_skills=requirements.required_skills[:6],
        evidenced_skills=skill_match.matched_skills,
        skills_evidence=skills_evidence,
        skill_gaps=skill_match.skill_gaps,
        nice_to_have=requirements.nice_to_have,
        match_score=skill_match.match_score,
        competencies=competencies,
        assignment=assignment,
        suggested_problem=suggested,
        special_requirements=request.special_requirements or "",
        analyst_degraded=False,
    )
    return requirements, skill_match, facts


def _strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _parse_analyst_json(raw: str) -> dict[str, Any] | None:
    try:
        return json.loads(_strip_json_fences(raw))
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def merge_analyst_overlay(base: GroundingFacts, analyst: dict[str, Any]) -> GroundingFacts:
    data = base.model_dump()
    degraded = False

    level = analyst.get("seniority_level")
    if isinstance(level, str) and level in _VALID_SENIORITY:
        data["seniority_level"] = level
        if analyst.get("seniority_reason"):
            data["seniority_reason"] = str(analyst["seniority_reason"])[:300]

    domain = analyst.get("domain")
    if isinstance(domain, str) and domain in _VALID_DOMAIN:
        data["domain"] = domain

    for key in ("required_skills", "mandatory_skills", "evidenced_skills", "skill_gaps"):
        val = analyst.get(key if key != "evidenced_skills" else "evidenced_skills")
        if isinstance(val, list) and all(isinstance(x, str) for x in val):
            data[key] = val[:12]

    if isinstance(analyst.get("skills_evidence"), list):
        parsed: list[SkillEvidence] = []
        for row in analyst["skills_evidence"]:
            if isinstance(row, dict) and row.get("name"):
                parsed.append(
                    SkillEvidence(
                        name=str(row["name"]),
                        years=float(row["years"]) if row.get("years") is not None else None,
                        evidence=str(row.get("evidence", ""))[:200],
                    )
                )
        if parsed:
            data["skills_evidence"] = [e.model_dump() for e in parsed]

    if isinstance(analyst.get("competencies"), list):
        comps: list[tuple[str, float]] = []
        for row in analyst["competencies"]:
            if isinstance(row, dict) and row.get("name"):
                weight = row.get("weight", 1)
                try:
                    comps.append((str(row["name"]), float(weight)))
                except (TypeError, ValueError):
                    degraded = True
        if comps:
            data["competencies"] = [c.model_dump() for c in renormalize_competencies(comps)]

    assignment_raw = analyst.get("assignment")
    base_assignment = base.assignment
    if isinstance(assignment_raw, dict):
        merged_assignment = base_assignment.model_dump()
        for field in ("mode", "difficulty"):
            val = assignment_raw.get(field)
            if isinstance(val, str):
                merged_assignment[field] = val
        if isinstance(assignment_raw.get("ai_assistant"), bool):
            merged_assignment["ai_assistant"] = assignment_raw["ai_assistant"]

        # Block analyst flipping coding → cognitive when JD has tech skills
        proposed_type = assignment_raw.get("type")
        if proposed_type == "cognitive" and has_tech_skills(base.required_skills):
            degraded = True
        elif proposed_type in ("coding", "cognitive"):
            merged_assignment["type"] = proposed_type

        data["assignment"] = merged_assignment
    else:
        degraded = True

    facts = GroundingFacts.model_validate(data)
    facts.analyst_degraded = degraded
    return facts


ANALYST_SYSTEM = """You are a hiring analyst. Read CV markdown and JD, return ONE minified JSON object only.
No markdown fences. Keys:
seniority_level, seniority_reason, domain, required_skills, mandatory_skills,
evidenced_skills, skills_evidence[{name,years,evidence}], skill_gaps,
competencies[{name,weight}], assignment{type,mode,ai_assistant,difficulty}.
Weights are relative (renormalized later). Keep evidence quotes under 120 chars."""