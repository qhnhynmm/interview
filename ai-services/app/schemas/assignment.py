from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class AssignmentType(str, Enum):
    coding = "coding"
    cognitive = "cognitive"


class CodingMode(str, Enum):
    dsa = "dsa"
    project = "project"


class TestCase(BaseModel):
    label: str
    inputs: list[Any] = Field(default_factory=list)
    expected: Any


class MCQQuestion(BaseModel):
    prompt: str
    options: list[str]
    answer: str
    explanation: str | None = None

    @model_validator(mode="after")
    def _validate_options(self) -> "MCQQuestion":
        if len(self.options) != 4:
            raise ValueError("MCQ must have exactly 4 options")
        if self.answer not in {"A", "B", "C", "D"}:
            raise ValueError("answer must be A|B|C|D")
        return self


class CodingChallenge(BaseModel):
    mode: CodingMode
    title: str
    difficulty: str = "medium"
    statement: str
    function_name: str = "solution"
    starter_code: str
    starter_files: dict[str, str] = Field(default_factory=dict)
    test_cases: list[TestCase] = Field(default_factory=list)
    ai_assistant_enabled: bool
    allowed_resources: list[str] = Field(default_factory=list)


class CognitiveTest(BaseModel):
    topic: str
    questions: list[MCQQuestion]


class Assignment(BaseModel):
    type: AssignmentType
    summary: str
    coding: CodingChallenge | None = None
    cognitive: CognitiveTest | None = None
    source: str = "assignment-agent"

    @model_validator(mode="after")
    def _validate_shape(self) -> "Assignment":
        if self.type == AssignmentType.coding:
            if self.coding is None:
                raise ValueError("coding assignment requires coding field")
            if self.cognitive is not None:
                raise ValueError("coding assignment must not include cognitive")
        if self.type == AssignmentType.cognitive:
            if self.cognitive is None:
                raise ValueError("cognitive assignment requires cognitive field")
            if len(self.cognitive.questions) != 10:
                raise ValueError("cognitive test must have exactly 10 questions")
            if self.coding is not None:
                raise ValueError("cognitive assignment must not include coding")
        return self


class AssignmentRequest(BaseModel):
    interview_id: str
    position: str | None = None
    jd_text: str = ""
    cv_markdown: str = ""
    level: str | None = None
    track: str | None = None
    coding_mode: str | None = None
    assignment_brief: str = ""
    special_requirements: str | None = None
    language: str = "en"
    cv_text: str | None = None

    @model_validator(mode="after")
    def _merge_cv(self) -> "AssignmentRequest":
        if not self.cv_markdown.strip() and self.cv_text:
            object.__setattr__(self, "cv_markdown", self.cv_text)
        return self


class AssignmentResponse(BaseModel):
    assignment: Assignment
    meta: dict[str, Any] = Field(default_factory=dict)