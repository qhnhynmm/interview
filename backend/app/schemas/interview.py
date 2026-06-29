from datetime import datetime

from pydantic import BaseModel, Field


class SlotItem(BaseModel):
    start: datetime
    available: bool
    active_count: int


class SlotsResponse(BaseModel):
    slots: list[SlotItem]
    instant_available: bool


class InterviewListItem(BaseModel):
    id: str
    candidate_name: str
    candidate_email: str
    position: str
    seniority: str | None = None
    scheduled_at: datetime | None
    meeting_url: str
    status: str
    language: str
    report: dict | None = None

    model_config = {"from_attributes": True}


class JoinTokenResponse(BaseModel):
    token: str
    livekit_url: str
    room_name: str


class ProctorEventBody(BaseModel):
    kind: str
    severity: str = "medium"
    detail: str = ""
    ts: float | None = None


class EndInterviewBody(BaseModel):
    reason: str = "completed"
    detail: str = ""


class InterviewDetail(BaseModel):
    id: str
    candidate_name: str
    candidate_email: str
    position: str
    language: str
    status: str
    scheduled_at: datetime | None
    meeting_url: str
    assistant_enabled: bool = True
    assignment_finished: bool = False
    plan: dict = Field(default_factory=dict)
    assignment: dict | None = None
    current_code: str | None = None
    sandbox_files: dict | None = None
    cognitive_answers: dict | None = None
    proctoring_events: list[dict] = Field(default_factory=list)

    model_config = {"from_attributes": True}