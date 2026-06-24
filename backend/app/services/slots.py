from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.interview import Interview, InterviewStatus


def _active_statuses() -> tuple[InterviewStatus, ...]:
    return (InterviewStatus.scheduled, InterviewStatus.in_progress)


def _as_utc(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)
    return moment.astimezone(UTC)


def count_active_at(db: Session, moment: datetime) -> int:
    settings = get_settings()
    window = timedelta(minutes=settings.session_window_minutes)
    moment = _as_utc(moment)

    rows = db.scalars(
        select(Interview).where(
            Interview.status.in_(_active_statuses()),
            Interview.scheduled_at.is_not(None),
        )
    ).all()

    count = 0
    for row in rows:
        start = _as_utc(row.scheduled_at)  # type: ignore[arg-type]
        if start <= moment < start + window:
            count += 1
    return count


def instant_available(db: Session, now: datetime | None = None) -> bool:
    settings = get_settings()
    now = _as_utc(now or datetime.now(UTC))
    return count_active_at(db, now) < settings.max_concurrent_sessions


def generate_slots(
    db: Session,
    *,
    hours_ahead: int = 8,
    from_utc: datetime | None = None,
) -> dict:
    settings = get_settings()
    now = _as_utc(datetime.now(UTC))
    base = _as_utc(from_utc) if from_utc else now
    base = base.replace(second=0, microsecond=0)

    max_moment = now + timedelta(hours=hours_ahead + 24)
    slots: list[dict] = []

    day_start = base.replace(hour=0, minute=0, second=0, microsecond=0)
    for day_offset in range(15):
        day = day_start + timedelta(days=day_offset)
        for hour in range(7, 23):
            for minute in (0, 30):
                if hour == 22 and minute > 0:
                    break
                slot = _as_utc(day.replace(hour=hour, minute=minute))
                if slot <= now or slot > max_moment:
                    continue
                active = count_active_at(db, slot)
                slots.append(
                    {
                        "start": slot,
                        "available": active < settings.max_concurrent_sessions,
                        "active_count": active,
                    }
                )

    return {
        "slots": slots,
        "instant_available": instant_available(db, now),
    }