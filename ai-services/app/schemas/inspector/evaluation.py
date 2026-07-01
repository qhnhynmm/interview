from typing import Any

from pydantic import BaseModel, Field


class EvaluationRequest(BaseModel):
    interview_id: str
    candidate_name: str = ""
    position: str = ""
    language: str = "en"
    track: str | None = None
    evaluation_brief: str = ""
    interview_brief: str = ""
    transcript: list[dict[str, Any]] = Field(default_factory=list)
    assignment: dict[str, Any] | None = None
    assignment_result: dict[str, Any] | None = None
    last_run_result: dict[str, Any] | None = None
    proctor_events: list[dict[str, Any]] = Field(default_factory=list)
    coding_submission: str | None = None
    plan: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_legacy(cls, body: dict[str, Any]) -> "EvaluationRequest":
        """Map InspectorEvaluateRequest + backend row fields."""
        plan = body.get("plan") or {}
        return cls(
            interview_id=body.get("interview_id", ""),
            candidate_name=body.get("candidate_name", ""),
            position=body.get("position", ""),
            language=(body.get("language") or "en")[:2],
            track=body.get("track"),
            evaluation_brief=body.get("evaluation_brief") or plan.get("evaluation_brief") or "",
            interview_brief=body.get("interview_brief") or plan.get("interview_brief") or "",
            transcript=list(body.get("transcript") or []),
            assignment=body.get("assignment"),
            assignment_result=body.get("assignment_result"),
            last_run_result=body.get("last_run_result"),
            proctor_events=list(body.get("proctor_events") or body.get("proctoring_events") or []),
            coding_submission=body.get("coding_submission"),
            plan=plan,
        )


class EvaluationResponse(BaseModel):
    interview_id: str
    report: dict[str, Any]
    report_markdown: str = ""
    pdf_base64: str = ""
    source: str = "inspector-agent"