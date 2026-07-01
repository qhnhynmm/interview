from app.agents.inspector.plan_adapter import extract_plan_context


def test_real_plan_grounding_competencies():
    plan = {
        "evaluation_brief": "Rubric here",
        "interview_brief": "Context",
        "grounding": {
            "competencies": [
                {"name": "Technical depth", "weight": 40},
                {"name": "Communication", "weight": 60},
            ],
            "assignment": {"type": "coding"},
        },
    }
    ctx = extract_plan_context(plan, {"type": "coding"})
    assert ctx.evaluation_brief == "Rubric here"
    assert ctx.track == "tech"
    assert len(ctx.competencies) == 2
    assert abs(ctx.competencies[0]["weight"] - 0.4) < 0.01


def test_legacy_mock_competencies():
    plan = {
        "competencies": [
            {"name": "Problem solving", "weight": 0.25},
            {"name": "Communication", "weight": 0.75},
        ]
    }
    ctx = extract_plan_context(plan)
    assert ctx.competencies[0]["name"] == "Problem solving"