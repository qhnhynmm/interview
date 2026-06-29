import asyncio
import logging
import threading

from app.database import SessionLocal
from app.models.interview import Interview, InterviewStatus
from app.services.inspector import fetch_inspector_report, normalize_report

logger = logging.getLogger(__name__)

_pending: set[str] = set()
_lock = threading.Lock()


def schedule_report_generation(interview_id: str) -> None:
    """Fire-and-forget report generation (safe to call multiple times)."""
    with _lock:
        if interview_id in _pending:
            return
        _pending.add(interview_id)

    def _runner() -> None:
        try:
            asyncio.run(_generate_report(interview_id))
        finally:
            with _lock:
                _pending.discard(interview_id)

    threading.Thread(target=_runner, daemon=True).start()


async def _generate_report(interview_id: str) -> None:
    try:
        db = SessionLocal()
        try:
            row = db.get(Interview, interview_id)
            if row is None:
                return
            if row.report is not None:
                if row.status == InterviewStatus.evaluating:
                    row.status = InterviewStatus.completed
                    db.add(row)
                    db.commit()
                return
            if row.status not in (InterviewStatus.evaluating, InterviewStatus.completed):
                return

            raw = await fetch_inspector_report(row)
            row.report = normalize_report(row, raw)
            row.status = InterviewStatus.completed
            db.add(row)
            db.commit()
            logger.info(
                "report_ready interview=%s score=%s",
                interview_id,
                row.report.get("overall_score"),
            )
        finally:
            db.close()
    except Exception:
        logger.exception("report_generation_failed interview=%s", interview_id)


def ensure_report_scheduled(db, row: Interview) -> bool:
    """Queue report generation when an interview ended without a report."""
    if row.report is not None:
        return False
    if row.status not in (InterviewStatus.completed, InterviewStatus.evaluating):
        return False
    if row.status == InterviewStatus.completed:
        row.status = InterviewStatus.evaluating
        db.add(row)
        db.commit()
        db.refresh(row)
    schedule_report_generation(row.id)
    return True