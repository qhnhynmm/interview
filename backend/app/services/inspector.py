import base64
import logging
from typing import Any

import httpx

from app.config import get_settings
from app.models.interview import Interview
from app.services.object_storage import upload_bytes

logger = logging.getLogger(__name__)


def _infer_track(row: Interview) -> str:
    assignment = row.assignment or {}
    if str(assignment.get("type") or "").lower() == "cognitive":
        return "nontech"
    if assignment.get("coding") or str(assignment.get("type") or "").lower() == "coding":
        return "tech"
    return "tech"


def build_evaluation_payload(row: Interview) -> dict[str, Any]:
    plan = row.plan or {}
    return {
        "interview_id": row.id,
        "candidate_name": row.candidate_name,
        "position": row.position,
        "language": row.language or "en",
        "track": _infer_track(row),
        "evaluation_brief": plan.get("evaluation_brief") or "",
        "interview_brief": plan.get("interview_brief") or "",
        "transcript": list(row.conversation_history or []),
        "assignment": row.assignment,
        "assignment_result": row.last_run_result,
        "last_run_result": row.last_run_result,
        "proctor_events": list(row.proctoring_events or []),
        "coding_submission": row.current_code,
        "plan": plan,
    }


def normalize_report(row: Interview, raw: dict[str, Any]) -> dict[str, Any]:
    """Shape Inspector output for the HR Result / Candidate profile UI."""
    scorecard = raw.get("scorecard") or {}
    scoring_source = raw.get("scoring_source") or ("llm" if raw.get("llm_scored") else "fallback")
    competencies = scorecard.get("competencies") or raw.get("competency_scores") or []

    competency_list: list[dict[str, Any]] = []
    if isinstance(competencies, list) and competencies and isinstance(competencies[0], dict):
        for c in competencies:
            if "competency" in c:
                competency_list.append(c)
            else:
                competency_list.append(
                    {
                        "competency": c.get("name", ""),
                        "weight": c.get("weight", 0),
                        "score": c.get("score", 0),
                        "rationale": c.get("rationale", ""),
                    }
                )
    elif isinstance(competencies, dict):
        plan = row.plan or {}
        plan_comps = (plan.get("grounding") or {}).get("competencies") or plan.get("competencies") or []
        weight_map = {}
        for pc in plan_comps:
            if isinstance(pc, dict):
                w = float(pc.get("weight", 0))
                weight_map[pc.get("name")] = w / 100.0 if w > 1 else w
        for name, score in competencies.items():
            competency_list.append(
                {
                    "competency": str(name),
                    "weight": weight_map.get(name, 1.0 / len(competencies)),
                    "score": round(float(score), 1),
                }
            )

    summary = (
        raw.get("interview_summary")
        or raw.get("summary")
        or scorecard.get("summary")
        or ""
    )
    return {
        "overall_score": raw.get("overall_score") or scorecard.get("overall_score"),
        "max_score": raw.get("max_score", 5),
        "scoring_source": scoring_source,
        "llm_scored": scoring_source == "llm",
        "is_mock": scoring_source != "llm",
        "candidate_name": row.candidate_name,
        "position": row.position,
        "recommendation": raw.get("recommendation") or scorecard.get("recommendation"),
        "headline": raw.get("headline") or scorecard.get("headline"),
        "competency_scores": competency_list,
        "interview_summary": summary,
        "strengths": raw.get("strengths") or scorecard.get("strengths") or [],
        "concerns": raw.get("concerns") or scorecard.get("concerns") or [],
        "integrity": raw.get("integrity"),
        "scorecard": scorecard or None,
        "transcript_turns": raw.get("transcript_turns"),
        "track": raw.get("track") or scorecard.get("track"),
    }


async def fetch_inspector_report(row: Interview) -> tuple[dict[str, Any], str | None, str]:
    """Returns (report_dict, pdf_s3_uri_or_none, report_markdown)."""
    settings = get_settings()
    payload = build_evaluation_payload(row)
    try:
        async with httpx.AsyncClient(timeout=settings.ai_request_timeout) as client:
            response = await client.post(settings.inspector_url, json=payload)
            if response.is_success:
                data = response.json()
                report = data.get("report") if isinstance(data, dict) else data
                if not isinstance(report, dict):
                    report = data if isinstance(data, dict) else {}
                markdown = data.get("report_markdown", "") if isinstance(data, dict) else ""
                pdf_uri = None
                pdf_b64 = data.get("pdf_base64", "") if isinstance(data, dict) else ""
                if pdf_b64 and settings.minio_enabled:
                    try:
                        pdf_bytes = base64.b64decode(pdf_b64)
                        key = f"{row.id}/report.pdf"
                        upload_bytes(
                            bucket=settings.minio_bucket_reports,
                            key=key,
                            data=pdf_bytes,
                            content_type="application/pdf",
                        )
                        pdf_uri = f"s3://{settings.minio_bucket_reports}/{key}"
                    except Exception as exc:
                        logger.warning("PDF upload failed for %s: %s", row.id, exc)
                return report, pdf_uri, markdown
    except Exception as exc:
        logger.warning("Inspector agent unavailable for %s: %s", row.id, exc)

    return _fallback_report(row), None, ""


def _fallback_report(row: Interview) -> dict[str, Any]:
    """Backend-only fallback when ai-services Inspector is unreachable."""
    plan = row.plan or {}
    grounding = plan.get("grounding") or {}
    competencies = grounding.get("competencies") or plan.get("competencies") or [
        {"name": "Technical depth", "weight": 30},
        {"name": "Problem solving", "weight": 25},
        {"name": "Communication", "weight": 25},
        {"name": "Culture fit", "weight": 20},
    ]
    turns = len(row.conversation_history or [])
    base = 3.5 if turns >= 4 else 3.0 if turns >= 1 else 2.5

    competency_list: list[dict[str, Any]] = []
    for i, c in enumerate(competencies):
        if not isinstance(c, dict):
            continue
        name = str(c.get("name") or f"competency_{i}")
        w = float(c.get("weight", 0.25))
        weight = w / 100.0 if w > 1.0 else w
        competency_list.append(
            {
                "competency": name,
                "weight": weight,
                "score": base,
                "rationale": f"Provisional — Inspector unavailable ({turns} transcript turns).",
            }
        )

    overall = round(
        sum(x["score"] * x["weight"] for x in competency_list)
        / (sum(x["weight"] for x in competency_list) or 1),
        2,
    )
    return {
        "scoring_source": "degraded",
        "llm_scored": False,
        "is_mock": True,
        "overall_score": overall,
        "max_score": 5,
        "competency_scores": competency_list,
        "transcript_turns": turns,
        "interview_summary": (
            f"Automated evaluation for {row.candidate_name}. "
            f"{turns} transcript turn(s) recorded. "
            "Inspector service was unavailable — scores are provisional."
        ),
        "summary": (
            f"Automated evaluation for {row.candidate_name}. "
            f"{turns} transcript turn(s) recorded. "
            "Inspector service was unavailable — scores are provisional."
        ),
        "concerns": ["Inspector service unavailable — re-run evaluation when ai-services is up"],
    }