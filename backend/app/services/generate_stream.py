"""Stream real agent progress while creating an interview link."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models.interview import Interview, InterviewStatus, new_interview_id
from app.models.user import User
from app.services.ai_stream import stream_ai_post
from app.services.cv_extractor import extract_cv
from app.services.planning import build_mock_plan
from app.services.assignment import MOCK_ASSIGNMENT
from app.services.slots import instant_available
from app.services.storage import save_cv

logger = logging.getLogger(__name__)


def _sse(payload: dict[str, Any], *, event: str | None = None) -> str:
    lines: list[str] = []
    if event:
        lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(payload, ensure_ascii=False)}")
    return "\n".join(lines) + "\n\n"


async def generate_link_event_stream(
    *,
    db: Session,
    hr_user: User,
    candidate_name: str,
    candidate_email: str,
    position: str,
    jd_text: str,
    special_requirements: str | None,
    interview_language: str,
    seniority: str | None,
    scheduled_at: datetime | None,
    cv_file: UploadFile,
    settings: Settings | None = None,
) -> AsyncIterator[str]:
    cfg = settings or get_settings()
    name = candidate_name.strip()
    email = candidate_email.strip().lower()
    role = position.strip()
    jd = jd_text.strip()
    lang = (interview_language or "en").strip() or "en"
    level = seniority.strip() or None

    try:
        yield _sse({"type": "progress", "agent": "System", "text": "Uploading CV…"}, event="progress")

        interview_id = new_interview_id()
        cv_filename, cv_path, cv_bytes = save_cv(interview_id, cv_file)

        yield _sse({"type": "progress", "agent": "System", "text": "Extracting CV with Gemini…"}, event="progress")
        cv_fields = await extract_cv(cv_bytes, cv_filename, cv_file.content_type)
        cv_text, cv_fields_json = cv_fields.to_db_fields()

        planning_payload = {
            "position": role,
            "seniority": level,
            "jd_text": jd,
            "special_requirements": special_requirements,
            "language": lang,
            "cv_markdown": cv_text,
            "cv_text": cv_text,
            "candidate_name": name,
        }
        planning_url = f"{cfg.ai_service_url.rstrip('/')}/api/v1/planning/plan/stream"
        plan: dict[str, Any] | None = None

        try:
            async for event in stream_ai_post(planning_url, planning_payload, timeout=cfg.ai_request_timeout):
                if event.get("type") == "progress":
                    yield _sse(event, event="progress")
                elif event.get("type") == "result":
                    plan = event.get("plan")
                elif event.get("type") == "error":
                    raise RuntimeError(event.get("detail") or "Planning stream failed")
        except Exception as exc:
            logger.warning("Planning stream unavailable, using mock plan: %s", exc)
            yield _sse(
                {
                    "type": "progress",
                    "agent": "Planning",
                    "text": "Planning agent unavailable — using fallback plan.",
                },
                event="progress",
            )
            plan = build_mock_plan(
                position=role,
                seniority=level,
                jd_text=jd,
                special_requirements=special_requirements,
                language=lang,
            )

        if not plan:
            plan = build_mock_plan(
                position=role,
                seniority=level,
                jd_text=jd,
                special_requirements=special_requirements,
                language=lang,
            )

        assignment_payload = {
            "interview_id": interview_id,
            "position": role,
            "level": level,
            "jd_text": jd,
            "cv_markdown": cv_text,
            "cv_text": cv_text,
            "assignment_brief": (plan or {}).get("assignment_brief", ""),
            "special_requirements": special_requirements,
        }
        assignment_url = f"{cfg.ai_service_url.rstrip('/')}/api/v1/assignment/generate/stream"
        assignment: dict[str, Any] | None = None

        try:
            async for event in stream_ai_post(assignment_url, assignment_payload, timeout=cfg.ai_request_timeout):
                if event.get("type") == "progress":
                    yield _sse(event, event="progress")
                elif event.get("type") == "result":
                    assignment = event.get("assignment")
                elif event.get("type") == "error":
                    raise RuntimeError(event.get("detail") or "Assignment stream failed")
        except Exception as exc:
            logger.warning("Assignment stream unavailable, using mock assignment: %s", exc)
            yield _sse(
                {
                    "type": "progress",
                    "agent": "Assignment",
                    "text": "Assignment agent unavailable — using fallback task.",
                },
                event="progress",
            )
            assignment = MOCK_ASSIGNMENT

        if not assignment:
            assignment = MOCK_ASSIGNMENT

        yield _sse(
            {
                "type": "progress",
                "agent": "Planning",
                "text": "Three briefs aligned. Generating meeting link and scheduling…",
            },
            event="progress",
        )

        parsed_at = scheduled_at
        if parsed_at is None:
            if instant_available(db):
                parsed_at = datetime.now(UTC)
            else:
                parsed_at = datetime.now(UTC) + timedelta(minutes=cfg.schedule_offset_minutes)

        row = Interview(
            id=interview_id,
            created_by_id=hr_user.id,
            candidate_name=name,
            candidate_email=email,
            position=role,
            seniority=level,
            language=lang,
            jd_text=jd,
            special_requirements=special_requirements,
            cv_filename=cv_filename,
            cv_path=cv_path,
            cv_text=cv_text,
            cv_fields=cv_fields_json,
            scheduled_at=parsed_at,
            status=InterviewStatus.scheduled,
            plan=plan,
            assignment=assignment,
        )
        db.add(row)
        db.commit()
        db.refresh(row)

        meeting_url = f"{cfg.frontend_url.rstrip('/')}/interview/{row.id}"
        interview_item = {
            "id": row.id,
            "candidate_name": row.candidate_name,
            "candidate_email": row.candidate_email,
            "position": row.position,
            "seniority": row.seniority,
            "scheduled_at": row.scheduled_at.isoformat() if row.scheduled_at else None,
            "meeting_url": meeting_url,
            "status": row.status.value,
            "language": row.language,
            "report": row.report,
        }
        yield _sse({"type": "done", "interview": interview_item}, event="done")
    except Exception as exc:
        logger.exception("generate-link stream failed")
        yield _sse({"type": "error", "detail": str(exc)}, event="error")