from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Recommendation(str, Enum):
    strong_hire = "strong_hire"
    hire = "hire"
    lean_hire = "lean_hire"
    no_hire = "no_hire"
    strong_no_hire = "strong_no_hire"


Track = Literal["tech", "nontech"]


class CompetencyScore(BaseModel):
    name: str = Field(max_length=22)
    score: float = Field(ge=0, le=5)
    weight: float = Field(ge=0, le=1)
    rationale: str = ""
    evidence: str | None = None


class CodingEval(BaseModel):
    correctness: float = Field(ge=0, le=5, default=0)
    code_quality: float = Field(ge=0, le=5, default=0)
    problem_solving: float = Field(ge=0, le=5, default=0)
    communication: float = Field(ge=0, le=5, default=0)
    tests_passed: int | None = None
    tests_total: int | None = None
    notes: str = ""


class ScoreCard(BaseModel):
    candidate_name: str
    position: str
    track: Track = "tech"
    overall_score: float = Field(ge=0, le=5)
    recommendation: Recommendation
    headline: str = ""
    summary: str = ""
    competencies: list[CompetencyScore] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    red_flags: list[str] = Field(default_factory=list)
    coding_eval: CodingEval | None = None
    next_steps: str | None = None


class IntegritySummary(BaseModel):
    total_violations: int = 0
    high_severity_count: int = 0
    counts_by_kind: dict[str, int] = Field(default_factory=dict)
    risk: Literal["clean", "low", "medium", "high"] = "clean"
    note: str = ""