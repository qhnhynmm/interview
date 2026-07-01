"""Assemble API report dict from ScoreCard + integrity (UI backward-compat)."""

from __future__ import annotations

import base64

from app.schemas.inspector.scorecard import IntegritySummary, ScoreCard
from app.skills.inspector_report.scripts.pdf_builder import build_markdown, build_pdf


def scorecard_to_report(
    scorecard: ScoreCard,
    integrity: IntegritySummary,
    *,
    interview_id: str,
    language: str,
    scoring_source: str = "fallback",
    llm_used: bool | None = None,
    pdf_base64: str = "",
    report_markdown: str = "",
) -> tuple[dict, str, str]:
    # Backward compat: llm_used overrides scoring_source when explicitly passed.
    if llm_used is not None:
        effective_source = "llm" if llm_used else "fallback"
    else:
        effective_source = scoring_source
    if not pdf_base64:
        pdf_bytes = build_pdf(scorecard, integrity, language)
        pdf_base64 = base64.b64encode(pdf_bytes).decode("ascii")
    if not report_markdown:
        report_markdown = build_markdown(scorecard, integrity, language)

    competency_scores = [
        {
            "competency": c.name,
            "weight": c.weight,
            "score": c.score,
            "rationale": c.rationale,
        }
        for c in scorecard.competencies
    ]

    report = {
        "interview_id": interview_id,
        "scoring_source": effective_source,
        "is_mock": effective_source != "llm",
        "llm_scored": effective_source == "llm",
        "overall_score": scorecard.overall_score,
        "max_score": 5,
        "candidate_name": scorecard.candidate_name,
        "position": scorecard.position,
        "recommendation": scorecard.recommendation.value,
        "headline": scorecard.headline,
        "summary": scorecard.summary,
        "interview_summary": scorecard.summary,
        "competency_scores": competency_scores,
        "strengths": scorecard.strengths,
        "concerns": scorecard.concerns,
        "red_flags": scorecard.red_flags,
        "coding_eval": scorecard.coding_eval.model_dump() if scorecard.coding_eval else None,
        "next_steps": scorecard.next_steps,
        "track": scorecard.track,
        "integrity": integrity.model_dump(),
        "scorecard": scorecard.model_dump(),
        "transcript_turns": None,
    }
    return report, report_markdown, pdf_base64