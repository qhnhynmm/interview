"""Service-authenticated endpoints consumed by MCP interview tools."""

from __future__ import annotations

import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_service_key
from app.database import get_db
from app.models.interview import Interview, InterviewStatus
from app.schemas.interview import (
    AgentMessageBody,
    AssistantToggleBody,
    CodingAssistantStatus,
    InterviewDetail,
    InterviewListItem,
    SwitchModeBody,
    SwitchModeResponse,
    TranscriptResponse,
    TranscriptTurnBody,
)
from app.services.livekit_room import broadcast_room_data

router = APIRouter(prefix="/interviews", tags=["interview-agent"])
logger = logging.getLogger(__name__)

_VALID_ROLES = frozenset({"agent", "candidate"})
_VALID_MODES = frozenset({"interview", "code"})


def _meeting_url(interview_id: str) -> str:
    from app.config import get_settings

    return f"{get_settings().frontend_url.rstrip('/')}/interview/{interview_id}"


def _assistant_enabled(row: Interview) -> bool:
    assignment = row.assignment or {}
    coding = assignment.get("coding") or {}
    if "ai_assistant_enabled" in coding:
        return bool(coding["ai_assistant_enabled"])
    legacy = (row.plan or {}).get("coding_assignment") or {}
    return bool(legacy.get("ai_assistant_enabled", True))


def _to_detail(row: Interview) -> InterviewDetail:
    return InterviewDetail(
        id=row.id,
        candidate_name=row.candidate_name,
        candidate_email=row.candidate_email,
        position=row.position,
        language=row.language,
        voice=row.voice or "Puck",
        status=row.status.value,
        scheduled_at=row.scheduled_at,
        meeting_url=_meeting_url(row.id),
        assistant_enabled=_assistant_enabled(row),
        assignment_finished=row.assignment_finished,
        plan=row.plan or {},
        assignment=row.assignment,
        current_code=row.current_code,
        sandbox_files=row.sandbox_files,
        cognitive_answers=row.cognitive_answers,
        proctoring_events=list(row.proctoring_events or []),
        conversation_history=list(row.conversation_history or []),
        last_run_result=row.last_run_result,
        ui_mode=row.ui_mode or "interview",
    )


def _to_list_item(row: Interview) -> InterviewListItem:
    return InterviewListItem(
        id=row.id,
        candidate_name=row.candidate_name,
        candidate_email=row.candidate_email,
        position=row.position,
        seniority=row.seniority,
        scheduled_at=row.scheduled_at,
        meeting_url=_meeting_url(row.id),
        status=row.status.value,
        language=row.language,
        report=row.report,
    )


def _get_row(db: Session, interview_id: str) -> Interview:
    row = db.get(Interview, interview_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return row


def _coding_problem(row: Interview) -> dict | None:
    assignment = row.assignment or {}
    coding = assignment.get("coding")
    if isinstance(coding, dict):
        return coding
    legacy = (row.plan or {}).get("coding_assignment")
    return legacy if isinstance(legacy, dict) else None


def _append_turn(row: Interview, *, role: str, content: str, ts: float | None) -> None:
    history = list(row.conversation_history or [])
    history.append(
        {
            "role": role,
            "content": content,
            "ts": ts if ts is not None else time.time(),
        }
    )
    row.conversation_history = history


@router.get("/active", response_model=list[InterviewListItem])
def list_active_interviews(
    db: Session = Depends(get_db),
    _service: None = Depends(require_service_key),
) -> list[InterviewListItem]:
    rows = db.scalars(
        select(Interview)
        .where(Interview.status == InterviewStatus.in_progress)
        .order_by(Interview.updated_at.desc())
    ).all()
    return [_to_list_item(row) for row in rows]


@router.get("/{interview_id}/transcript", response_model=TranscriptResponse)
def get_transcript(
    interview_id: str,
    db: Session = Depends(get_db),
    _service: None = Depends(require_service_key),
) -> TranscriptResponse:
    row = _get_row(db, interview_id)
    return TranscriptResponse(
        interview_id=row.id,
        conversation_history=list(row.conversation_history or []),
    )


@router.post("/{interview_id}/transcript/append", status_code=status.HTTP_204_NO_CONTENT)
def append_transcript_turn(
    interview_id: str,
    body: TranscriptTurnBody,
    db: Session = Depends(get_db),
    _service: None = Depends(require_service_key),
) -> None:
    role = body.role.strip().lower()
    if role not in _VALID_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="role must be agent or candidate")
    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="content is required")

    row = _get_row(db, interview_id)
    _append_turn(row, role=role, content=content, ts=body.ts)
    if row.status == InterviewStatus.scheduled:
        row.status = InterviewStatus.in_progress
    db.add(row)
    db.commit()


@router.post("/{interview_id}/switch-mode", response_model=SwitchModeResponse)
async def switch_mode(
    interview_id: str,
    body: SwitchModeBody,
    db: Session = Depends(get_db),
    _service: None = Depends(require_service_key),
) -> SwitchModeResponse:
    mode = body.mode.strip().lower()
    if mode not in _VALID_MODES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="mode must be interview or code")

    row = _get_row(db, interview_id)
    if mode == "code" and row.assignment_finished:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Assignment is finished — cannot switch back to code mode",
        )

    row.ui_mode = mode
    if row.status == InterviewStatus.scheduled:
        row.status = InterviewStatus.in_progress
    db.add(row)
    db.commit()
    db.refresh(row)

    problem = _coding_problem(row) if mode == "code" else None
    payload: dict = {
        "type": "ui:switch_mode",
        "mode": mode,
        "finished": row.assignment_finished,
    }
    if problem:
        payload["problem"] = problem
    if row.assignment:
        payload["assignment"] = row.assignment
    if row.current_code is not None:
        payload["current_code"] = row.current_code
    if row.sandbox_files:
        payload["sandbox_files"] = row.sandbox_files
    if row.cognitive_answers:
        payload["cognitive_answers"] = row.cognitive_answers

    await broadcast_room_data(room_name=row.id, payload=payload)

    return SwitchModeResponse(
        mode=mode,
        finished=row.assignment_finished,
        assignment=row.assignment,
        current_code=row.current_code,
        sandbox_files=row.sandbox_files,
        cognitive_answers=row.cognitive_answers,
        problem=problem,
    )


@router.post("/{interview_id}/send-agent-message", status_code=status.HTTP_204_NO_CONTENT)
async def send_agent_message(
    interview_id: str,
    body: AgentMessageBody,
    db: Session = Depends(get_db),
    _service: None = Depends(require_service_key),
) -> None:
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="message is required")

    row = _get_row(db, interview_id)
    _append_turn(row, role="agent", content=message, ts=time.time())
    db.add(row)
    db.commit()

    await broadcast_room_data(
        room_name=row.id,
        payload={"type": "ui:agent_message", "message": message},
    )


@router.post("/{interview_id}/set-assistant", response_model=CodingAssistantStatus)
async def set_coding_assistant(
    interview_id: str,
    body: AssistantToggleBody,
    db: Session = Depends(get_db),
    _service: None = Depends(require_service_key),
) -> CodingAssistantStatus:
    row = _get_row(db, interview_id)
    assignment = dict(row.assignment or {})
    coding = dict(assignment.get("coding") or {})
    coding["ai_assistant_enabled"] = body.enabled
    assignment["coding"] = coding
    row.assignment = assignment
    db.add(row)
    db.commit()

    await broadcast_room_data(
        room_name=row.id,
        payload={"type": "ui:assistant_toggle", "enabled": body.enabled},
    )
    await broadcast_room_data(
        room_name=row.id,
        payload={"type": "ui:coding_assistant", "enabled": body.enabled},
    )
    return CodingAssistantStatus(enabled=body.enabled)


@router.post("/{interview_id}/coding-assistant", response_model=CodingAssistantStatus)
async def update_coding_assistant(
    interview_id: str,
    body: AssistantToggleBody,
    db: Session = Depends(get_db),
    _service: None = Depends(require_service_key),
) -> CodingAssistantStatus:
    return await set_coding_assistant(interview_id, body, db=db, _service=_service)


@router.get("/{interview_id}/coding-assistant", response_model=CodingAssistantStatus)
def get_coding_assistant_status(
    interview_id: str,
    db: Session = Depends(get_db),
    _service: None = Depends(require_service_key),
) -> CodingAssistantStatus:
    row = _get_row(db, interview_id)
    return CodingAssistantStatus(enabled=_assistant_enabled(row))