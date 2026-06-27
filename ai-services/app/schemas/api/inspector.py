from typing import Any

from pydantic import BaseModel, Field


class InspectorEvaluateRequest(BaseModel):
    interview_id: str
    transcript: list[dict[str, Any]] = Field(default_factory=list)
    assignment_result: dict[str, Any] | None = None
    proctoring_events: list[dict[str, Any]] = Field(default_factory=list)
    plan: dict[str, Any] = Field(default_factory=dict)


class InspectorEvaluateResponse(BaseModel):
    report: dict[str, Any]
    meta: dict = Field(default_factory=dict)