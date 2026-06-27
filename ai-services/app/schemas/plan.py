from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

SeniorityLevel = Literal["junior", "mid", "senior", "manager"]
Domain = Literal["backend", "frontend", "data", "devops", "ai"]
AssignmentType = Literal["coding", "cognitive"]
AssignmentMode = Literal["dsa", "project"]
Difficulty = Literal["easy", "medium", "hard"]


class PlanRequest(BaseModel):
    jd_text: str
    cv_markdown: str = ""
    position: str | None = None
    special_requirements: str | None = None
    # Backward compat — backend may still send cv_text / language / candidate_name
    cv_text: str | None = None
    language: str = "en"
    candidate_name: str = ""
    seniority: str | None = None

    @model_validator(mode="after")
    def _merge_cv(self) -> "PlanRequest":
        if not self.cv_markdown.strip() and self.cv_text:
            object.__setattr__(self, "cv_markdown", self.cv_text)
        return self


class Competency(BaseModel):
    name: str
    weight: int = Field(ge=1, le=100)


class SkillEvidence(BaseModel):
    name: str
    years: float | None = None
    evidence: str = ""


class AssignmentDirective(BaseModel):
    type: AssignmentType
    mode: AssignmentMode
    ai_assistant: bool
    difficulty: Difficulty


class RequirementsResult(BaseModel):
    required_skills: list[str]
    seniority_level: SeniorityLevel
    domain: Domain
    min_years_experience: int | None = None
    nice_to_have: list[str] = Field(default_factory=list)


class SkillMatchResult(BaseModel):
    matched_skills: list[str]
    skill_gaps: list[str]
    match_score: float = Field(ge=0, le=1)


class ProblemBankEntry(BaseModel):
    title: str
    difficulty: Difficulty
    statement: str
    function_name: str
    starter_code: str
    test_cases: list[dict[str, Any]]


class GroundingFacts(BaseModel):
    """Merged keyword + semantic grounding passed to brief generators."""

    position: str
    seniority_level: SeniorityLevel
    seniority_reason: str = ""
    domain: Domain
    required_skills: list[str] = Field(default_factory=list)
    mandatory_skills: list[str] = Field(default_factory=list)
    evidenced_skills: list[str] = Field(default_factory=list)
    skills_evidence: list[SkillEvidence] = Field(default_factory=list)
    skill_gaps: list[str] = Field(default_factory=list)
    nice_to_have: list[str] = Field(default_factory=list)
    match_score: float = 0.0
    competencies: list[Competency] = Field(default_factory=list)
    assignment: AssignmentDirective
    suggested_problem: ProblemBankEntry | None = None
    special_requirements: str = ""
    analyst_degraded: bool = False


class InterviewPlan(BaseModel):
    interview_brief: str
    evaluation_brief: str
    assignment_brief: str
    duration_minutes: int = Field(ge=45, le=60)
    source: str = "planning-agent"
    grounding: GroundingFacts | None = None


class PlanResponse(BaseModel):
    plan: InterviewPlan
    meta: dict[str, Any] = Field(default_factory=dict)