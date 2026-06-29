import logging
from typing import Any

import httpx

from app.config import get_settings
from app.models.interview import Interview

logger = logging.getLogger(__name__)


def normalize_report(row: Interview, raw: dict[str, Any]) -> dict[str, Any]:
    """Shape Inspector output for the HR Result / Candidate profile UI."""
    plan = row.plan or {}
    competencies = plan.get("competencies") or []
    raw_scores = raw.get("competency_scores") or {}
    overall = raw.get("overall_score")

    competency_list: list[dict[str, Any]] = []
    if isinstance(raw_scores, dict) and competencies:
        for c in competencies:
            if not isinstance(c, dict):
                continue
            name = str(c.get("name", ""))
            weight = float(c.get("weight", 0))
            score = raw_scores.get(name, overall if overall is not None else 3.0)
            competency_list.append(
                {
                    "competency": name,
                    "weight": weight,
                    "score": round(float(score), 1),
                }
            )
    elif isinstance(raw_scores, dict):
        share = 1.0 / len(raw_scores) if raw_scores else 1.0
        for name, score in raw_scores.items():
            competency_list.append(
                {
                    "competency": str(name),
                    "weight": share,
                    "score": round(float(score), 1),
                }
            )
    elif isinstance(raw_scores, list):
        competency_list = raw_scores

    summary = raw.get("interview_summary") or raw.get("summary") or ""
    return {
        "overall_score": overall,
        "max_score": raw.get("max_score", 5),
        "is_mock": bool(raw.get("is_mock", False)),
        "candidate_name": row.candidate_name,
        "position": row.position,
        "competency_scores": competency_list,
        "interview_summary": summary,
        "integrity": raw.get("integrity"),
        "transcript_turns": raw.get("transcript_turns"),
    }


async def fetch_inspector_report(row: Interview) -> dict[str, Any]:
    settings = get_settings()
    payload = {
        "interview_id": row.id,
        "transcript": list(row.conversation_history or []),
        "assignment_result": row.last_run_result,
        "proctoring_events": list(row.proctoring_events or []),
        "plan": row.plan or {},
    }
    try:
        async with httpx.AsyncClient(timeout=settings.ai_request_timeout) as client:
            response = await client.post(settings.inspector_url, json=payload)
            if response.is_success:
                data = response.json()
                if isinstance(data, dict) and data.get("report"):
                    return data["report"]
                if isinstance(data, dict):
                    return data
    except Exception as exc:
        logger.warning("Inspector agent unavailable for %s: %s", row.id, exc)

    return _fallback_report(row)


def _fallback_report(row: Interview) -> dict[str, Any]:
    plan = row.plan or {}
    competencies = plan.get("competencies") or [
        {"name": "Technical depth", "weight": 0.3},
        {"name": "Problem solving", "weight": 0.25},
        {"name": "Communication", "weight": 0.25},
        {"name": "Culture fit", "weight": 0.2},
    ]
    scores = {str(c.get("name", f"competency_{i}")): 3.5 for i, c in enumerate(competencies) if isinstance(c, dict)}
    overall = round(sum(scores.values()) / len(scores), 2) if scores else 3.5
    turns = len(row.conversation_history or [])
    return {
        "is_mock": True,
        "overall_score": overall,
        "max_score": 5,
        "competency_scores": scores,
        "transcript_turns": turns,
        "summary": (
            f"Automated evaluation for {row.candidate_name}. "
            f"{turns} transcript turn(s) recorded. Inspector agent was unavailable — scores are provisional."
        ),
    }