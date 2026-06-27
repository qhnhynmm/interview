import pytest

from app.agents.planning.agent import run_planning_agent
from app.schemas.plan import PlanRequest

SAMPLE_JD = """
Backend Engineer (Mid) — 3+ years
Must have: Python, FastAPI, PostgreSQL, Redis
Nice: Kubernetes, event-driven architecture
"""

SAMPLE_CV = """
# Alex Nguyen — Backend Engineer
## VinPay (2021–2024)
- Built **Python/FastAPI** payment APIs (~2M req/day)
- **PostgreSQL** schema + index tuning
- **Docker** CI/CD; team migrating to **Kubernetes** (not on-call yet)
"""


@pytest.mark.asyncio
async def test_run_planning_agent_fallback_path():
    plan, meta = await run_planning_agent(
        PlanRequest(
            jd_text=SAMPLE_JD,
            cv_markdown=SAMPLE_CV,
            position="Backend Engineer",
            special_requirements="Probe Redis caching and K8s readiness",
        )
    )
    assert plan.interview_brief
    assert plan.evaluation_brief
    assert plan.assignment_brief.startswith("ASSIGNMENT DIRECTIVE")
    assert plan.duration_minutes in (45, 50, 60)
    assert plan.source.endswith("fallback") or plan.source == "planning-agent"
    assert meta["agent"] == "planning"
    assert plan.grounding is not None
    gaps = plan.grounding.skill_gaps
    assert "redis" in gaps or "kubernetes" in gaps