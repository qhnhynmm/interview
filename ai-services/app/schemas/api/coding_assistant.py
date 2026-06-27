from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str
    content: str


class CodingAssistantRequest(BaseModel):
    interview_id: str
    messages: list[ChatMessage]
    code: str = ""
    language: str = "en"


class CodingAssistantResponse(BaseModel):
    message: str
    meta: dict = Field(default_factory=dict)