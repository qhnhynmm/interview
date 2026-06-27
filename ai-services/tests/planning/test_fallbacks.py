from app.agents.planning.fallbacks import (
    fallback_assignment_brief,
    fallback_evaluation_brief,
    fallback_interview_brief,
)
from app.agents.planning.grounding import run_keyword_grounding
from app.schemas.plan import PlanRequest


def test_fallback_briefs_contain_competencies():
    request = PlanRequest(
        jd_text="Python FastAPI Redis Kubernetes",
        cv_markdown="# Dev\nBuilt FastAPI services with PostgreSQL",
        position="Backend Engineer",
    )
    _, _, facts = run_keyword_grounding(request)

    iv = fallback_interview_brief(facts, request.cv_markdown)
    ev = fallback_evaluation_brief(facts)
    asn = fallback_assignment_brief(facts)

    for comp in facts.competencies:
        assert comp.name in iv
        assert comp.name in ev
    assert "ASSIGNMENT DIRECTIVE" in asn
    assert "type: coding" in asn or "type: cognitive" in asn