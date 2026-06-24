import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base

JsonType = JSON().with_variant(JSONB, "postgresql")


class InterviewStatus(str, enum.Enum):
    scheduled = "scheduled"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    abandoned = "abandoned"


def new_interview_id() -> str:
    return f"itv-{uuid.uuid4().hex[:8]}"


class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_interview_id)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    candidate_name: Mapped[str] = mapped_column(String(128))
    candidate_email: Mapped[str] = mapped_column(String(255))
    position: Mapped[str] = mapped_column(String(128))
    seniority: Mapped[str | None] = mapped_column(String(32), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en")

    jd_text: Mapped[str] = mapped_column(Text)
    special_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)

    cv_filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    cv_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    cv_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cv_fields: Mapped[dict | None] = mapped_column(JsonType, nullable=True)

    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[InterviewStatus] = mapped_column(
        Enum(InterviewStatus), default=InterviewStatus.scheduled, index=True
    )

    plan: Mapped[dict] = mapped_column(JsonType, default=dict)
    assignment: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    report: Mapped[dict | None] = mapped_column(JsonType, nullable=True)

    assignment_finished: Mapped[bool] = mapped_column(Boolean, default=False)
    current_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    sandbox_files: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    cognitive_answers: Mapped[dict | None] = mapped_column(JsonType, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )