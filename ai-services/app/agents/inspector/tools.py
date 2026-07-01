"""Inspector Agent MAF tools — accumulate ScoreCard in shared state."""

from __future__ import annotations

import base64
import json
from typing import Any

from app.agents.inspector.plan_adapter import PlanContext
from app.agents.inspector.state import InspectorState
from app.schemas.inspector.evaluation import EvaluationRequest
from app.schemas.inspector.scorecard import (
    CodingEval,
    CompetencyScore,
    Recommendation,
    ScoreCard,
)
from app.skills.inspector_report.scripts.pdf_builder import build_markdown, build_pdf

try:
    from agent_framework import tool
    _HAS_TOOL = True
except ImportError:  # pragma: no cover
    _HAS_TOOL = False

    def tool(**kwargs):  # type: ignore[misc]
        def deco(fn):
            return fn
        return deco


def _search_transcript_impl(transcript: list[dict], query: str, *, limit: int = 5) -> list[dict]:
    q = (query or "").strip().lower()
    if not q:
        return transcript[:limit]
    hits: list[dict] = []
    for turn in transcript:
        content = str(turn.get("content") or "").lower()
        if q in content:
            hits.append(turn)
        if len(hits) >= limit:
            break
    return hits or transcript[:limit]


def _weighted_overall(competencies: list[CompetencyScore]) -> float:
    if not competencies:
        return 0.0
    total_w = sum(c.weight for c in competencies) or 1.0
    return round(sum(c.score * c.weight for c in competencies) / total_w, 2)


def _rec_from_score(score: float, integrity_risk: str) -> Recommendation:
    if integrity_risk == "high" and score < 3.5:
        return Recommendation.strong_no_hire
    if score >= 4.5:
        return Recommendation.strong_hire
    if score >= 4.0:
        return Recommendation.hire
    if score >= 3.2:
        return Recommendation.lean_hire
    if score >= 2.5:
        return Recommendation.no_hire
    return Recommendation.strong_no_hire


def make_inspector_tools(
    req: EvaluationRequest,
    plan_ctx: PlanContext,
    integrity_dict: dict[str, Any],
    state: InspectorState,
):
    transcript = list(req.transcript or [])
    integrity_risk = str(integrity_dict.get("risk") or "clean")

    @tool(approval_mode="never_require")
    def get_evaluation_brief() -> str:
        """Return the Planning Agent evaluation rubric. Call this first."""
        return req.evaluation_brief or plan_ctx.evaluation_brief or "(no evaluation brief)"

    @tool(approval_mode="never_require")
    def get_candidate_context() -> str:
        """Return candidate name, position, track, and interview brief."""
        return json.dumps(
            {
                "candidate_name": req.candidate_name,
                "position": req.position,
                "track": plan_ctx.track,
                "interview_brief": req.interview_brief or plan_ctx.interview_brief,
                "language": req.language,
            },
            ensure_ascii=False,
        )

    @tool(approval_mode="never_require")
    def search_transcript(query: str) -> str:
        """Search transcript turns by keyword; returns matching turns with role/content."""
        hits = _search_transcript_impl(transcript, query)
        return json.dumps(hits[:8], ensure_ascii=False)

    @tool(approval_mode="never_require")
    def get_coding_context() -> str:
        """Return assignment, submitted code, and last test run (tech track only)."""
        if plan_ctx.track != "tech":
            return json.dumps({"track": "nontech", "available": False})
        coding = (req.assignment or {}).get("coding") or {}
        return json.dumps(
            {
                "track": "tech",
                "assignment_title": coding.get("title") or coding.get("statement", "")[:200],
                "coding_submission": (req.coding_submission or "")[:4000],
                "last_run_result": req.last_run_result or req.assignment_result,
            },
            ensure_ascii=False,
        )

    @tool(approval_mode="never_require")
    def get_integrity_report() -> str:
        """Return pre-computed deterministic proctoring integrity summary."""
        return json.dumps(integrity_dict, ensure_ascii=False)

    @tool(approval_mode="never_require")
    def score_competency(
        name: str,
        score: float,
        weight: float,
        rationale: str,
        evidence: str = "",
    ) -> str:
        """Record one competency score (0-5). Call once per competency."""
        state.competencies.append(
            CompetencyScore(
                name=(name or "Competency")[:22],
                score=max(0.0, min(5.0, float(score))),
                weight=max(0.0, min(1.0, float(weight))),
                rationale=rationale or "",
                evidence=evidence or None,
            )
        )
        return f"Recorded {name}: {score}/5"

    @tool(approval_mode="never_require")
    def finalize_scorecard(
        headline: str,
        summary: str,
        recommendation: str,
        strengths: str,
        concerns: str,
        red_flags: str = "",
        next_steps: str = "",
    ) -> str:
        """Finalize the ScoreCard after all competencies are scored."""
        overall = _weighted_overall(state.competencies)
        try:
            rec = Recommendation(recommendation.strip().lower())
        except ValueError:
            rec = _rec_from_score(overall, integrity_risk)

        coding_eval = None
        if plan_ctx.track == "tech":
            run = req.last_run_result or req.assignment_result or {}
            coding_eval = CodingEval(
                correctness=float(run.get("tests_passed", 0) / max(run.get("tests_total", 1), 1) * 5),
                code_quality=3.0,
                problem_solving=overall,
                communication=overall,
                tests_passed=run.get("tests_passed"),
                tests_total=run.get("tests_total"),
                notes=str(run.get("stderr") or "")[:300],
            )

        def _split_csv(text: str) -> list[str]:
            return [p.strip() for p in text.split(";") if p.strip()]

        state.scorecard = ScoreCard(
            candidate_name=req.candidate_name,
            position=req.position,
            track=plan_ctx.track,  # type: ignore[arg-type]
            overall_score=overall,
            recommendation=rec,
            headline=headline,
            summary=summary,
            competencies=list(state.competencies),
            strengths=_split_csv(strengths),
            concerns=_split_csv(concerns),
            red_flags=_split_csv(red_flags),
            coding_eval=coding_eval,
            next_steps=next_steps or None,
        )
        return f"ScoreCard finalized — overall {overall}/5, recommendation {rec.value}"

    @tool(approval_mode="never_require")
    def generate_report() -> str:
        """Build deterministic PDF + markdown from ScoreCard. Call last."""
        if state.scorecard is None:
            return "Error: call finalize_scorecard first"
        from app.schemas.inspector.scorecard import IntegritySummary

        integrity = IntegritySummary.model_validate(integrity_dict)
        pdf_bytes = build_pdf(state.scorecard, integrity, req.language)
        state.report_markdown = build_markdown(state.scorecard, integrity, req.language)
        state.pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
        return f"Report generated ({len(pdf_bytes)} bytes PDF)"

    tools = [
        get_evaluation_brief,
        get_candidate_context,
        search_transcript,
        get_coding_context,
        get_integrity_report,
        score_competency,
        finalize_scorecard,
        generate_report,
    ]
    return tools, state