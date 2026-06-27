from app.agents.planning.grounding import merge_analyst_overlay, run_keyword_grounding
from app.schemas.plan import PlanRequest


def test_merge_analyst_blocks_cognitive_flip():
    request = PlanRequest(
        jd_text="Python FastAPI PostgreSQL required",
        cv_markdown="Python developer",
        position="Backend Engineer",
    )
    _, _, base = run_keyword_grounding(request)
    assert base.assignment.type == "coding"

    overlay = merge_analyst_overlay(
        base,
        {
            "seniority_level": "mid",
            "assignment": {"type": "cognitive", "mode": "project", "ai_assistant": True, "difficulty": "medium"},
        },
    )
    assert overlay.assignment.type == "coding"
    assert overlay.analyst_degraded is True


def test_renormalize_competencies_sum_100():
    from app.skills.interview_planning.scripts.planning_tools import renormalize_competencies

    comps = renormalize_competencies([("A", 2), ("B", 2), ("C", 1)])
    assert sum(c.weight for c in comps) == 100
    assert len(comps) == 3