from typing import Any

from pydantic import BaseModel, Field

from app.schemas.api.common import CodingAssignment


class AssignmentGenerateRequest(BaseModel):
    interview_id: str
    mode: str = "dsa"
    plan: dict[str, Any] = Field(default_factory=dict)
    language: str = "en"


class AssignmentGenerateResponse(BaseModel):
    assignment: CodingAssignment | dict[str, Any]
    meta: dict = Field(default_factory=dict)