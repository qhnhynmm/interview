from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TopicItem(BaseModel):
    topic: str
    weight: float = Field(ge=0, le=1)
    minutes: int = Field(ge=0)


class CompetencyItem(BaseModel):
    name: str
    weight: float = Field(ge=0, le=1)


class CodingAssignment(BaseModel):
    model_config = ConfigDict(extra="allow")

    title: str
    difficulty: str = "medium"
    mode: str = "dsa"
    ai_assistant_enabled: bool = True
    description: str
    starter_code: str


class InterviewPlan(BaseModel):
    """Public plan contract — must stay compatible with backend Interview.plan JSON."""

    is_mock: bool = False
    language: str = "en"
    position: str
    seniority: str = "Mid"
    summary: str
    topics: list[TopicItem]
    competencies: list[CompetencyItem]
    jd_excerpt: str = ""
    special_requirements: str = ""
    coding_assignment: CodingAssignment | dict[str, Any]