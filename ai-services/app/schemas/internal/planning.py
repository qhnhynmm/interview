from pydantic import BaseModel, Field


class SkillEvidence(BaseModel):
    skill: str
    evidence: str = ""
    confidence: float = Field(default=0.5, ge=0, le=1)


class AnalystGrounding(BaseModel):
    """Structured facts extracted from CV + JD before the planner writes the brief."""

    candidate_name: str = ""
    position: str = ""
    seniority: str | None = None
    language: str = "en"
    jd_keywords: list[str] = Field(default_factory=list)
    cv_skills: list[str] = Field(default_factory=list)
    skill_evidence: list[SkillEvidence] = Field(default_factory=list)
    summary: str = ""


class PlannerContext(BaseModel):
    request_position: str
    request_seniority: str | None
    jd_text: str
    special_requirements: str | None
    language: str
    cv_text: str
    candidate_name: str
    grounding: AnalystGrounding