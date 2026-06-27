from app.skills.jd_analysis import analyze_jd, extract_cv_skills


def test_extract_cv_skills():
    skills = extract_cv_skills("Experienced with Python, FastAPI, and Docker.")
    assert "python" in skills
    assert "fastapi" in skills


def test_analyze_jd_overlap():
    grounding = analyze_jd(
        jd_text="Looking for Python and PostgreSQL backend engineer",
        cv_text="Python FastAPI developer with PostgreSQL",
        position="Backend Engineer",
        seniority="Mid",
        language="en",
        candidate_name="Alex",
    )
    assert grounding.position == "Backend Engineer"
    assert len(grounding.cv_skills) >= 2