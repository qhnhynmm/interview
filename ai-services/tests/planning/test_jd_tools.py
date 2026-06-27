from app.skills.jd_analysis.scripts.jd_tools import extract_requirements, has_tech_skills


JD_BACKEND = """
## Backend Engineer (Mid)
Requirements:
- 3+ years Python and FastAPI
- PostgreSQL, Redis
- Docker, Kubernetes (nice to have)
- Strong REST API design
"""

CV_MARKDOWN = """
# Alex Nguyen
## Experience
- Built payment APIs in **Python/FastAPI** serving 2M req/day (2021–2024)
- PostgreSQL schema design and query tuning
- Dockerized services; no production Kubernetes yet
"""


def test_extract_requirements_backend_mid():
    result = extract_requirements(JD_BACKEND, "Backend Engineer")
    assert result.domain == "backend"
    assert result.seniority_level in ("mid", "junior", "senior")
    assert "python" in result.required_skills
    assert "postgresql" in result.required_skills
    assert has_tech_skills(result.required_skills)


def test_match_skills_finds_gaps():
    from app.skills.interview_planning.scripts.planning_tools import match_skills

    req = extract_requirements(JD_BACKEND, "Backend Engineer")
    match = match_skills(CV_MARKDOWN, req.required_skills)
    assert "python" in match.matched_skills
    assert "redis" in match.skill_gaps or "kubernetes" in match.skill_gaps
    assert 0 < match.match_score < 1