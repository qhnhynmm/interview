from app.agents.inspector.llm_scorer import parse_llm_scorecard
from app.agents.inspector.plan_adapter import PlanContext
from app.schemas.inspector.evaluation import EvaluationRequest


def test_parse_llm_scorecard_maps_competencies():
    plan_ctx = PlanContext(
        evaluation_brief="test",
        interview_brief="",
        competencies=[
            {"name": "Technical depth", "weight": 0.6},
            {"name": "Communication", "weight": 0.4},
        ],
        track="tech",
    )
    req = EvaluationRequest(
        interview_id="itv-parse",
        candidate_name="Alex",
        position="Engineer",
        language="en",
    )
    card = parse_llm_scorecard(
        {
            "competencies": [
                {
                    "name": "Technical depth",
                    "score": 4.2,
                    "rationale": "Strong API examples",
                    "evidence": "built payment APIs",
                },
                {"name": "Communication", "score": 3.5, "rationale": "Clear", "evidence": "explained trade-offs"},
            ],
            "headline": "Solid backend engineer",
            "summary": "Good depth, adequate communication.",
            "recommendation": "hire",
            "strengths": ["FastAPI experience"],
            "concerns": [],
            "red_flags": [],
        },
        req,
        plan_ctx,
    )
    assert card.overall_score > 3.5
    assert card.recommendation.value == "hire"
    assert len(card.competencies) == 2
    assert card.competencies[0].name == "Technical depth"