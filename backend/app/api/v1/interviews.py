import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_hr_user, require_hr_user_sse
from app.config import get_settings
from app.constants.voices import normalize_live_voice
from app.database import get_db
from app.models.interview import Interview, InterviewStatus, new_interview_id
from app.models.user import User
from app.schemas.interview import (
    CandidateDossier,
    ChatBody,
    CodeAssistBody,
    CodeAssistResponse,
    EndInterviewBody,
    InterviewDetail,
    InterviewListItem,
    JoinTokenResponse,
    ProctorEventBody,
    RecordingUploadResponse,
    RunCodeBody,
    RunCodeResponse,
    SlotsResponse,
    SubmitAssignmentBody,
    SyncAnswersBody,
    SyncCodeBody,
    SyncSandboxBody,
)
from app.services.report_worker import ensure_report_scheduled, schedule_report_generation
from app.services.livekit_proctor import broadcast_proctor_violation
from app.services.cv_extractor import extract_cv
from app.services.assignment import fetch_assignment
from app.services.planning import fetch_interview_plan
from app.services.slots import generate_slots, instant_available
from app.services.livekit_tokens import (
    dispatch_interview_agent,
    assert_join_allowed,
    build_join_token_response,
    mark_candidate_joined,
)
from app.services.generate_stream import generate_link_event_stream
from app.services.object_storage import download_object, is_s3_uri, parse_s3_uri
from app.services.storage import save_cv
from app.services.code_runner import run_python_tests
from app.services.coding_assistant import fetch_code_assist
from app.services.recording_storage import append_recording_chunk, finalize_recording

router = APIRouter(prefix="/interviews", tags=["interviews"])
logger = logging.getLogger(__name__)


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
        voice=row.voice or "Puck",
        report=row.report,
    )


def _report_pdf_url(row: Interview) -> str | None:
    if not row.report_pdf_path:
        return None
    settings = get_settings()
    return f"{settings.api_prefix}/interviews/{row.id}/report.pdf"


def _recording_url(row: Interview) -> str | None:
    if not row.recording_path:
        return None
    settings = get_settings()
    return f"{settings.api_prefix}/interviews/{row.id}/recording"


def _get_row(db: Session, interview_id: str) -> Interview:
    row = db.get(Interview, interview_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return row


def _coding_from_row(row: Interview) -> dict:
    assignment = row.assignment or {}
    coding = assignment.get("coding")
    if isinstance(coding, dict):
        return coding
    legacy = (row.plan or {}).get("coding_assignment")
    return legacy if isinstance(legacy, dict) else {}


def _to_dossier(row: Interview) -> CandidateDossier:
    return CandidateDossier(
        id=row.id,
        candidate_name=row.candidate_name,
        candidate_email=row.candidate_email,
        position=row.position,
        language=row.language,
        status=row.status.value,
        scheduled_at=row.scheduled_at,
        cv_filename=row.cv_filename,
        cv_text=row.cv_text,
        cv_fields=row.cv_fields,
        recording_url=_recording_url(row),
        report=row.report,
        report_pdf_url=_report_pdf_url(row),
        conversation_history=list(row.conversation_history or []),
    )


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
async def join_token(
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
        await dispatch_interview_agent(room_name=row.id, interview_id=row.id)

    payload = build_join_token_response(row, role=role)  # type: ignore[arg-type]
    return JoinTokenResponse(**payload)


@router.get("/{interview_id}/report")
def get_interview_report(
    interview_id: str,
    db: Session = Depends(get_db),
    hr_user: User = Depends(require_hr_user),
) -> dict:
    row = db.get(Interview, interview_id)
    if row is None or row.created_by_id != hr_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    if row.report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not ready")
    return row.report


@router.get("/{interview_id}/report.pdf")
def download_interview_report_pdf(
    interview_id: str,
    db: Session = Depends(get_db),
    hr_user: User = Depends(require_hr_user),
) -> Response:
    row = db.get(Interview, interview_id)
    if row is None or row.created_by_id != hr_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    if not row.report_pdf_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF report not available")

    settings = get_settings()
    try:
        if is_s3_uri(row.report_pdf_path):
            bucket, key = parse_s3_uri(row.report_pdf_path)
            data = download_object(bucket, key)
        else:
            path = settings.storage_path / row.report_pdf_path
            data = path.read_bytes()
    except Exception as exc:
        logger.warning("report_pdf_download_failed interview=%s err=%s", interview_id, exc)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF report not available") from exc

    safe_name = (row.candidate_name or interview_id).replace(" ", "_")
    return Response(
        content=data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_report.pdf"'},
    )


@router.get("/{interview_id}/dossier", response_model=CandidateDossier)
def get_candidate_dossier(
    interview_id: str,
    db: Session = Depends(get_db),
    hr_user: User = Depends(require_hr_user),
) -> CandidateDossier:
    row = db.get(Interview, interview_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    if row.created_by_id != hr_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    ensure_report_scheduled(db, row)
    db.refresh(row)
    return _to_dossier(row)


@router.get("/{interview_id}/events")
async def interview_events(
    interview_id: str,
    db: Session = Depends(get_db),
    hr_user: User = Depends(require_hr_user_sse),
) -> StreamingResponse:
    """SSE stream — emits status changes and report_ready when evaluation completes."""
    row = db.get(Interview, interview_id)
    if row is None or row.created_by_id != hr_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    async def _stream():
        yield f"data: {json.dumps({'event': 'connected', 'interview_id': interview_id})}\n\n"
        last_status = row.status.value
        idle_ticks = 0
        while idle_ticks < 90:
            db.refresh(row)
            status_val = row.status.value
            if status_val != last_status:
                last_status = status_val
                payload = {"event": "status", "interview_id": interview_id, "status": status_val}
                yield f"data: {json.dumps(payload)}\n\n"
            if row.report is not None and status_val == InterviewStatus.completed.value:
                payload = {
                    "event": "report_ready",
                    "interview_id": interview_id,
                    "overall_score": row.report.get("overall_score"),
                }
                yield f"data: {json.dumps(payload)}\n\n"
                break
            if status_val == InterviewStatus.evaluating.value and row.report is None:
                ensure_report_scheduled(db, row)
            idle_ticks += 1
            await asyncio.sleep(2)
        yield f"data: {json.dumps({'event': 'done', 'interview_id': interview_id})}\n\n"

    return StreamingResponse(_stream(), media_type="text/event-stream")


@router.get("/{interview_id}", response_model=InterviewDetail)
def get_interview(
    interview_id: str,
    db: Session = Depends(get_db),
) -> InterviewDetail:
    row = db.get(Interview, interview_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return _to_detail(row)


_MAX_PROCTOR_EVENTS = 500


@router.post("/{interview_id}/proctor-event", status_code=status.HTTP_204_NO_CONTENT)
async def record_proctor_event(
    interview_id: str,
    body: ProctorEventBody,
    db: Session = Depends(get_db),
) -> Response:
    """Public endpoint — browser proctoring reports fire-and-forget events."""
    row = db.get(Interview, interview_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    event = body.model_dump(exclude_none=True)
    events = list(row.proctoring_events or [])
    events.append(event)
    if len(events) > _MAX_PROCTOR_EVENTS:
        events = events[-_MAX_PROCTOR_EVENTS:]
    row.proctoring_events = events

    if row.status == InterviewStatus.scheduled:
        row.status = InterviewStatus.in_progress

    db.add(row)
    db.commit()

    logger.info(
        "proctor_event interview=%s kind=%s severity=%s detail=%s",
        interview_id,
        event.get("kind"),
        event.get("severity"),
        event.get("detail"),
    )

    # Forward to interview agent via LiveKit (skip informational unsupported notices).
    if event.get("kind") != "detection_unsupported" and event.get("severity") != "info":
        await broadcast_proctor_violation(room_name=interview_id, event=event)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{interview_id}/end", status_code=status.HTTP_204_NO_CONTENT)
def end_interview(
    interview_id: str,
    body: EndInterviewBody,
    db: Session = Depends(get_db),
) -> Response:
    """Mark interview ended (agent or candidate teardown). Idempotent."""
    row = db.get(Interview, interview_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")

    if row.status in (InterviewStatus.completed, InterviewStatus.cancelled, InterviewStatus.abandoned):
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    if body.reason == "proctoring":
        row.status = InterviewStatus.abandoned
    else:
        row.status = InterviewStatus.evaluating

    db.add(row)
    db.commit()

    if row.status == InterviewStatus.evaluating:
        schedule_report_generation(interview_id)

    logger.info(
        "interview_end interview=%s status=%s reason=%s detail=%s",
        interview_id,
        row.status.value,
        body.reason,
        body.detail,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{interview_id}/sync-code", status_code=status.HTTP_204_NO_CONTENT)
def sync_code(
    interview_id: str,
    body: SyncCodeBody,
    db: Session = Depends(get_db),
) -> Response:
    row = _get_row(db, interview_id)
    row.current_code = body.code
    if row.status == InterviewStatus.scheduled:
        row.status = InterviewStatus.in_progress
    db.add(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{interview_id}/sync-sandbox", status_code=status.HTTP_204_NO_CONTENT)
def sync_sandbox(
    interview_id: str,
    body: SyncSandboxBody,
    db: Session = Depends(get_db),
) -> Response:
    row = _get_row(db, interview_id)
    row.sandbox_files = body.files
    if row.status == InterviewStatus.scheduled:
        row.status = InterviewStatus.in_progress
    db.add(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{interview_id}/sync-answers", status_code=status.HTTP_204_NO_CONTENT)
def sync_answers(
    interview_id: str,
    body: SyncAnswersBody,
    db: Session = Depends(get_db),
) -> Response:
    row = _get_row(db, interview_id)
    row.cognitive_answers = body.answers
    if row.status == InterviewStatus.scheduled:
        row.status = InterviewStatus.in_progress
    db.add(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{interview_id}/run-code", response_model=RunCodeResponse)
def run_code(
    interview_id: str,
    body: RunCodeBody,
    db: Session = Depends(get_db),
) -> RunCodeResponse:
    row = _get_row(db, interview_id)
    coding = _coding_from_row(row)
    result = run_python_tests(code=body.code, coding=coding)
    row.current_code = body.code
    row.last_run_result = result
    if row.status == InterviewStatus.scheduled:
        row.status = InterviewStatus.in_progress
    db.add(row)
    db.commit()
    return RunCodeResponse(**result)


@router.post("/{interview_id}/submit-assignment", status_code=status.HTTP_204_NO_CONTENT)
def submit_assignment(
    interview_id: str,
    body: SubmitAssignmentBody,
    db: Session = Depends(get_db),
) -> Response:
    row = _get_row(db, interview_id)
    if body.code is not None:
        row.current_code = body.code
    if body.files is not None:
        row.sandbox_files = body.files
    if body.answers is not None:
        row.cognitive_answers = body.answers
    row.assignment_finished = True
    if row.status == InterviewStatus.scheduled:
        row.status = InterviewStatus.in_progress
    db.add(row)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{interview_id}/code-assist", response_model=CodeAssistResponse)
async def code_assist(
    interview_id: str,
    body: CodeAssistBody,
    db: Session = Depends(get_db),
) -> CodeAssistResponse:
    row = _get_row(db, interview_id)
    messages = [{"role": m.role, "content": m.content} for m in body.messages]
    reply = await fetch_code_assist(
        interview_id=interview_id,
        messages=messages,
        code=body.code,
        language=body.language or row.language or "en",
        position=row.position,
    )
    return CodeAssistResponse(reply=reply, message=reply)


@router.post("/{interview_id}/chat")
async def send_chat(
    interview_id: str,
    body: ChatBody,
    db: Session = Depends(get_db),
) -> dict:
    """Legacy text chat — appends candidate message to transcript."""
    row = _get_row(db, interview_id)
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="message is required")
    history = list(row.conversation_history or [])
    history.append({"role": "candidate", "content": message, "ts": datetime.now(UTC).timestamp()})
    row.conversation_history = history
    if row.status == InterviewStatus.scheduled:
        row.status = InterviewStatus.in_progress
    db.add(row)
    db.commit()
    return {
        "reply": "This interview uses voice — please speak to the AI interviewer.",
    }


@router.post("/{interview_id}/recording/chunk", status_code=status.HTTP_204_NO_CONTENT)
async def upload_recording_chunk(
    interview_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Response:
    _get_row(db, interview_id)
    data = await file.read()
    append_recording_chunk(interview_id, data)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{interview_id}/recording", response_model=RecordingUploadResponse)
async def upload_recording(
    interview_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> RecordingUploadResponse:
    row = _get_row(db, interview_id)
    data = await file.read()
    uri = finalize_recording(interview_id, final_blob=data if data else None)
    if uri:
        row.recording_path = uri
        db.add(row)
        db.commit()
    return RecordingUploadResponse(ok=bool(uri), url=_recording_url(row) if uri else None)


@router.get("/{interview_id}/recording")
def download_recording(
    interview_id: str,
    db: Session = Depends(get_db),
    hr_user: User = Depends(require_hr_user_sse),
) -> Response:
    row = db.get(Interview, interview_id)
    if row is None or row.created_by_id != hr_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not found")
    if not row.recording_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not available")
    settings = get_settings()
    try:
        if is_s3_uri(row.recording_path):
            bucket, key = parse_s3_uri(row.recording_path)
            data = download_object(bucket, key)
        else:
            data = Path(row.recording_path).read_bytes()
    except Exception as exc:
        logger.warning("recording_download_failed interview=%s err=%s", interview_id, exc)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording not available") from exc

    safe_name = (row.candidate_name or interview_id).replace(" ", "_")
    return Response(
        content=data,
        media_type="video/webm",
        headers={"Content-Disposition": f'inline; filename="{safe_name}_recording.webm"'},
    )


@router.post("/generate-link/stream")
async def generate_link_stream(
    candidate_name: str = Form(...),
    candidate_email: str = Form(""),
    position: str = Form(...),
    jd_text: str = Form(...),
    special_requirements: str = Form(""),
    interview_language: str = Form("en"),
    interview_voice: str = Form("Puck"),
    seniority: str = Form(""),
    scheduled_at: str | None = Form(None),
    cv_file: UploadFile = File(...),
    db: Session = Depends(get_db),
    hr_user: User = Depends(require_hr_user),
) -> StreamingResponse:
    name = candidate_name.strip()
    role = position.strip()
    jd = jd_text.strip()
    if not name or not role or not jd:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Missing required fields")

    stream = generate_link_event_stream(
        db=db,
        hr_user=hr_user,
        candidate_name=name,
        candidate_email=candidate_email,
        position=role,
        jd_text=jd,
        special_requirements=special_requirements.strip() or None,
        interview_language=interview_language,
        interview_voice=interview_voice,
        seniority=seniority.strip() or None,
        scheduled_at=_parse_scheduled_at(scheduled_at),
        cv_file=cv_file,
    )
    return StreamingResponse(stream, media_type="text/event-stream")


@router.post("/generate-link", response_model=InterviewListItem, status_code=status.HTTP_201_CREATED)
async def generate_link(
    candidate_name: str = Form(...),
    candidate_email: str = Form(""),
    position: str = Form(...),
    jd_text: str = Form(...),
    special_requirements: str = Form(""),
    interview_language: str = Form("en"),
    interview_voice: str = Form("Puck"),
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
    voice = normalize_live_voice(interview_voice)
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
        voice=voice,
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