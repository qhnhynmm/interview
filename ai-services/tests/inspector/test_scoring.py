from app.agents.inspector.plan_adapter import PlanContext
from app.agents.inspector.scoring import apply_integrity_and_gates
from app.schemas.inspector.scorecard import (
    CompetencyScore,
    IntegritySummary,
    Recommendation,
    ScoreCard,
)


def _card(score: float = 4.0, gate_score: float = 4.0) -> ScoreCard:
    return ScoreCard(
        candidate_name="Alex",
        position="Engineer",
        track="tech",
        overall_score=score,
        recommendation=Recommendation.hire,
        headline="Good",
        summary="Summary",
        competencies=[
            CompetencyScore(name="Technical depth", score=gate_score, weight=0.5, rationale=""),
            CompetencyScore(name="Communication", score=4.0, weight=0.5, rationale=""),
        ],
        strengths=[],
        concerns=[],
        red_flags=[],
    )


def test_hard_gate_caps_recommendation():
    plan = PlanContext(
        evaluation_brief="## HARD GATE — Technical depth: score ≤2 → cap LEAN-HIRE",
        interview_brief="",
        competencies=[{"name": "Technical depth", "weight": 0.5}],
        track="tech",
    )
    integrity = IntegritySummary(total_violations=0, high_severity_count=0, counts_by_kind={}, risk="clean", note="")
    result = apply_integrity_and_gates(
        _card(gate_score=1.5),
        plan_ctx=plan,
        integrity=integrity,
        evaluation_brief=plan.evaluation_brief,
    )
    assert result.recommendation in (Recommendation.no_hire, Recommendation.lean_hire, Recommendation.strong_no_hire)


def test_integrity_high_caps_overall():
    plan = PlanContext(evaluation_brief="", interview_brief="", competencies=[], track="tech")
    integrity = IntegritySummary(
        total_violations=5,
        high_severity_count=3,
        counts_by_kind={"tab_switch": 3},
        risk="high",
        note="high risk",
    )
    result = apply_integrity_and_gates(
        _card(score=4.5),
        plan_ctx=plan,
        integrity=integrity,
        evaluation_brief="",
    )
    assert result.overall_score <= 2.5
    assert result.recommendation == Recommendation.strong_no_hire