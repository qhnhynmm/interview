from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.schemas.inspector.evaluation import EvaluationRequest, EvaluationResponse


class InspectorEvaluateRequest(EvaluationRequest):
    """Backward-compatible — accepts legacy `proctoring_events` field."""

    proctoring_events: list[dict[str, Any]] | None = None

    @model_validator(mode="after")
    def _merge_proctoring(self) -> "InspectorEvaluateRequest":
        if self.proctoring_events and not self.proctor_events:
            self.proctor_events = list(self.proctoring_events)
        return self


class InspectorEvaluateResponse(EvaluationResponse):
    meta: dict = Field(default_factory=dict)