"""Deterministic post-LLM score adjustments — integrity caps and HARD GATE."""

from __future__ import annotations

import re
from typing import Any

from app.agents.inspector.plan_adapter import PlanContext
from app.schemas.inspector.scorecard import (
    CompetencyScore,
    IntegritySummary,
    Recommendation,
    ScoreCard,
)


def _weighted_overall(competencies: list[CompetencyScore]) -> float:
    if not competencies:
        return 0.0
    total_w = sum(c.weight for c in competencies) or 1.0
    return round(sum(c.score * c.weight for c in competencies) / total_w, 2)


def _parse_hard_gate_competency(evaluation_brief: str, plan_ctx: PlanContext) -> str | None:
    text = evaluation_brief or ""
    match = re.search(r"HARD\s+GATE[^—\-\n]*[—\-]\s*([^:\n]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()[:22]
    if plan_ctx.competencies:
        return plan_ctx.competencies[0]["name"]
    return None


def _find_gate_score(gate_name: str | None, competencies: list[CompetencyScore]) -> float | None:
    if not gate_name:
        return None
    gate_lower = gate_name.lower()
    for comp in competencies:
        if comp.name.lower() in gate_lower or gate_lower in comp.name.lower():
            return comp.score
    return None


def _cap_recommendation(current: Recommendation, cap: Recommendation) -> Recommendation:
    """Downgrade recommendation if current is more positive than cap."""
    order = [
        Recommendation.strong_hire,
        Recommendation.hire,
        Recommendation.lean_hire,
        Recommendation.no_hire,
        Recommendation.strong_no_hire,
    ]
    if order.index(current) < order.index(cap):
        return cap
    return current


def apply_integrity_and_gates(
    card: ScoreCard,
    *,
    plan_ctx: PlanContext,
    integrity: IntegritySummary,
    evaluation_brief: str,
) -> ScoreCard:
    """Apply deterministic integrity caps and HARD GATE after LLM scoring."""
    competencies = list(card.competencies)
    overall = _weighted_overall(competencies)
    rec = card.recommendation
    concerns = list(card.concerns)
    red_flags = list(card.red_flags)

    if integrity.risk == "high":
        overall = min(overall, 2.5)
        rec = _cap_recommendation(rec, Recommendation.no_hire)
        if overall < 3.5:
            rec = Recommendation.strong_no_hire
        if "High proctoring risk" not in red_flags:
            red_flags.append("High proctoring risk")
    elif integrity.risk == "medium":
        overall = min(overall, 3.2)
        rec = _cap_recommendation(rec, Recommendation.lean_hire)
        note = "Proctoring risk capped overall score"
        if note not in concerns:
            concerns.append(note)

    gate_name = _parse_hard_gate_competency(evaluation_brief, plan_ctx)
    gate_score = _find_gate_score(gate_name, competencies)
    if gate_score is not None:
        if gate_score <= 1.0:
            rec = _cap_recommendation(rec, Recommendation.no_hire)
            flag = f"HARD GATE failed: {gate_name} scored {gate_score}/5"
            if flag not in red_flags:
                red_flags.append(flag)
        elif gate_score <= 2.0:
            rec = _cap_recommendation(rec, Recommendation.lean_hire)
            note = f"HARD GATE: {gate_name} ≤2 — recommendation capped"
            if note not in concerns:
                concerns.append(note)

    return card.model_copy(
        update={
            "overall_score": overall,
            "recommendation": rec,
            "competencies": competencies,
            "concerns": concerns,
            "red_flags": red_flags,
        }
    )