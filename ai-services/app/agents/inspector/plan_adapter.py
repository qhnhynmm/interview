"""Normalize Planning Agent output (real + mock legacy) for Inspector."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PlanContext:
    evaluation_brief: str
    interview_brief: str
    competencies: list[dict[str, Any]]  # {name, weight: 0-1}
    track: str  # tech | nontech


def _normalize_weight(raw: Any) -> float:
    if raw is None:
        return 0.0
    val = float(raw)
    if val > 1.0:
        return round(val / 100.0, 4)
    return round(val, 4)


def _extract_competencies(plan: dict[str, Any]) -> list[dict[str, Any]]:
    grounding = plan.get("grounding") or {}
    if isinstance(grounding, dict) and grounding.get("competencies"):
        rows = grounding["competencies"]
    else:
        rows = plan.get("competencies") or []

    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        out.append({"name": name[:22], "weight": _normalize_weight(row.get("weight"))})

    if not out:
        defaults = [
            ("Technical depth", 0.3),
            ("Problem solving", 0.25),
            ("Communication", 0.25),
            ("Culture fit", 0.2),
        ]
        out = [{"name": n, "weight": w} for n, w in defaults]

    total = sum(c["weight"] for c in out) or 1.0
    for c in out:
        c["weight"] = round(c["weight"] / total, 4)
    return out


def infer_track(assignment: dict[str, Any] | None, plan: dict[str, Any]) -> str:
    if assignment:
        atype = str(assignment.get("type") or "").lower()
        if atype == "cognitive":
            return "nontech"
        if atype == "coding" or assignment.get("coding"):
            return "tech"
    grounding = plan.get("grounding") or {}
    if isinstance(grounding, dict):
        ad = grounding.get("assignment") or {}
        if isinstance(ad, dict) and ad.get("type") == "cognitive":
            return "nontech"
    if plan.get("coding_assignment"):
        return "tech"
    return "tech"


def extract_plan_context(
    plan: dict[str, Any] | None,
    assignment: dict[str, Any] | None = None,
    *,
    track_override: str | None = None,
) -> PlanContext:
    plan = plan or {}
    return PlanContext(
        evaluation_brief=str(plan.get("evaluation_brief") or "").strip(),
        interview_brief=str(plan.get("interview_brief") or "").strip(),
        competencies=_extract_competencies(plan),
        track=track_override or infer_track(assignment, plan),
    )