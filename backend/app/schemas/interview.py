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
    voice: str = "Puck"
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


class TranscriptTurnBody(BaseModel):
    role: str
    content: str
    ts: float | None = None


class TranscriptResponse(BaseModel):
    interview_id: str
    conversation_history: list[dict] = Field(default_factory=list)


class SwitchModeBody(BaseModel):
    mode: str


class SwitchModeResponse(BaseModel):
    mode: str
    finished: bool = False
    assignment: dict | None = None
    current_code: str | None = None
    sandbox_files: dict | None = None
    cognitive_answers: dict | None = None
    problem: dict | None = None


class AgentMessageBody(BaseModel):
    message: str


class AssistantToggleBody(BaseModel):
    enabled: bool


class CodingAssistantStatus(BaseModel):
    enabled: bool


class InterviewDetail(BaseModel):
    id: str
    candidate_name: str
    candidate_email: str
    position: str
    language: str
    voice: str = "Puck"
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
    conversation_history: list[dict] = Field(default_factory=list)
    last_run_result: dict | None = None
    ui_mode: str = "interview"

    model_config = {"from_attributes": True}