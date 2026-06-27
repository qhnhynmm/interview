from pydantic import BaseModel, Field

from app.schemas.api.common import InterviewPlan


class PlanningRequest(BaseModel):
    position: str
    seniority: str | None = None
    jd_text: str
    special_requirements: str | None = None
    language: str = "en"
    cv_text: str = ""
    candidate_name: str = ""


class PlanningResponse(BaseModel):
    plan: InterviewPlan
    meta: dict = Field(default_factory=dict)