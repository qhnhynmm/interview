from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.inspector.scorecard import CompetencyScore, ScoreCard


@dataclass
class InspectorState:
    competencies: list[CompetencyScore] = field(default_factory=list)
    scorecard: ScoreCard | None = None
    report_markdown: str = ""
    pdf_base64: str = ""