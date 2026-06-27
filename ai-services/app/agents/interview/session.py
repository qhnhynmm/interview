from dataclasses import dataclass, field
from typing import Any


@dataclass
class InterviewSession:
    interview_id: str
    language: str = "en"
    plan: dict[str, Any] = field(default_factory=dict)
    transcript: list[dict[str, Any]] = field(default_factory=list)