from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_hr_user
from app.config import get_settings
from app.database import get_db
from app.models.interview import Interview, InterviewStatus, new_interview_id
from app.models.user import User
from app.schemas.interview import InterviewDetail, InterviewListItem, JoinTokenResponse, SlotsResponse
from app.services.cv_extractor import extract_cv
from app.services.assignment import fetch_assignment
from app.services.planning import fetch_interview_plan
from app.services.slots import generate_slots, instant_available
from app.services.livekit_tokens import (
    assert_join_allowed,
    build_join_token_response,
    mark_candidate_joined,
)
from app.services.storage import save_cv

router = APIRouter(prefix="/interviews", tags=["interviews"])


def _meeting_url(interview_id: str) -> str:
    settings = get_settings()
    return f"{settings.frontend_url.rstrip('/')}/interview/{interview_id}"


def _assistant_enabled(row: Interview) -> bool:
    assignment = row.assignment or {}
    coding = assignment.get("coding") or {}
    if "ai_assistant_enabled" in coding:
        return bool(coding["ai_assistant_enabled"])
    legacy = (row.plan or {}).get("coding_assignment") or {}
    return bool(legacy.get("ai_assistant_enabled", True))


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


def _to_detail(row: Interview) -> InterviewDetail:
    return InterviewDetail(
        id=row.id,
        candidate_name=row.candidate_name,
        candidate_email=row.candidate_email,
        position=row.position,
        language=row.language,
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
    )


def _parse_scheduled_at(raw: str | None) -> datetime | None:
    if not raw or not raw.strip():
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)


@router.get("/slots", response_model=SlotsResponse)
def list_slots(
    hours_ahead: int = 8,
    from_utc: datetime | None = None,
    db: Session = Depends(get_db),
    _hr: User = Depends(require_hr_user),
) -> SlotsResponse:
    data = generate_slots(db, hours_ahead=hours_ahead, from_utc=from_utc)
    return SlotsResponse(**data)


@router.get("", response_model=list[InterviewListItem])
def list_interviews(
    db: Session = Depends(get_db),
    hr_user: User = Depends(require_hr_user),
) -> list[InterviewListItem]:
    rows = db.scalars(
        select(Interview)
        .where(Interview.created_by_id == hr_user.id)
        .order_by(Interview.created_at.desc())
    ).all()
    return [_to_list_item(row) for row in rows]


@router.get("/{interview_id}/join-token", response_model=JoinTokenResponse)
def join_token(
    interview_id: str,
    role: Literal["candidate", "agent"] = Query("candidate"),
    db: Session = Depends(get_db),
) -> JoinTokenResponse:
    row = db.get(Interview, interview_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    assert_join_allowed(row)
    if role == "candidate":
        if mark_candidate_joined(row):
            db.add(row)
            db.commit()
            db.refresh(row)

    payload = build_join_token_response(row, role=role)  # type: ignore[arg-type]
    return JoinTokenResponse(**payload)


@router.get("/{interview_id}", response_model=InterviewDetail)
def get_interview(
    interview_id: str,
    db: Session = Depends(get_db),
) -> InterviewDetail:
    row = db.get(Interview, interview_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return _to_detail(row)


@router.post("/generate-link", response_model=InterviewListItem, status_code=status.HTTP_201_CREATED)
async def generate_link(
    candidate_name: str = Form(...),
    candidate_email: str = Form(""),
    position: str = Form(...),
    jd_text: str = Form(...),
    special_requirements: str = Form(""),
    interview_language: str = Form("en"),
    seniority: str = Form(""),
    scheduled_at: str | None = Form(None),
    cv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    hr_user: User = Depends(require_hr_user),
) -> InterviewListItem:
    settings = get_settings()
    name = candidate_name.strip()
    email = candidate_email.strip().lower()
    role = position.strip()
    jd = jd_text.strip()
    requests = special_requirements.strip() or None
    lang = (interview_language or "en").strip() or "en"
    level = seniority.strip() or None

    if not name or not role or not jd:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing required fields")

    parsed_at = _parse_scheduled_at(scheduled_at)
    if parsed_at is None:
        if instant_available(db):
            parsed_at = datetime.now(UTC)
        else:
            parsed_at = datetime.now(UTC) + timedelta(minutes=settings.schedule_offset_minutes)

    interview_id = new_interview_id()
    cv_filename, cv_path, cv_bytes = save_cv(interview_id, cv_file)
    cv_fields = await extract_cv(cv_bytes, cv_filename, cv_file.content_type)
    cv_text, cv_fields_json = cv_fields.to_db_fields()

    plan = await fetch_interview_plan(
        position=role,
        seniority=level,
        jd_text=jd,
        special_requirements=requests,
        language=lang,
        cv_text=cv_text,
        candidate_name=name,
    )
    assignment = await fetch_assignment(
        interview_id=interview_id,
        position=role,
        seniority=level,
        jd_text=jd,
        cv_text=cv_text,
        assignment_brief=(plan or {}).get("assignment_brief", ""),
        special_requirements=requests,
    )

    row = Interview(
        id=interview_id,
        created_by_id=hr_user.id,
        candidate_name=name,
        candidate_email=email,
        position=role,
        seniority=level,
        language=lang,
        jd_text=jd,
        special_requirements=requests,
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
    return _to_list_item(row)