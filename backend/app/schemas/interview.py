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


class CandidateDossier(BaseModel):
    id: str
    candidate_name: str
    candidate_email: str
    position: str
    language: str
    status: str
    scheduled_at: datetime | None
    cv_filename: str | None = None
    cv_text: str | None = None
    cv_fields: dict | None = None
    recording_url: str | None = None
    report: dict | None = None
    report_pdf_url: str | None = None
    conversation_history: list[dict] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SyncCodeBody(BaseModel):
    code: str = ""


class SyncSandboxBody(BaseModel):
    files: dict[str, str] = Field(default_factory=dict)


class SyncAnswersBody(BaseModel):
    answers: dict = Field(default_factory=dict)


class RunCodeBody(BaseModel):
    code: str = ""


class RunCodeResponse(BaseModel):
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    timed_out: bool = False
    test_results: list[dict] = Field(default_factory=list)
    tests_passed: int = 0
    tests_total: int = 0


class SubmitAssignmentBody(BaseModel):
    type: str = "coding"
    code: str | None = None
    mode: str | None = None
    files: dict[str, str] | None = None
    answers: dict | None = None


class CodeAssistMessage(BaseModel):
    role: str
    content: str


class CodeAssistBody(BaseModel):
    messages: list[CodeAssistMessage] = Field(default_factory=list)
    code: str = ""
    language: str = "en"


class CodeAssistResponse(BaseModel):
    reply: str
    message: str | None = None


class ChatBody(BaseModel):
    message: str


class RecordingUploadResponse(BaseModel):
    ok: bool = True
    url: str | None = None


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