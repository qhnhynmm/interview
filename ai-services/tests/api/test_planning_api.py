from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

SAMPLE = {
    "jd_text": "Backend Engineer: Python, FastAPI, PostgreSQL, Redis, Kubernetes",
    "cv_markdown": "# Alex\nBuilt FastAPI services with PostgreSQL at VinPay.",
    "position": "Backend Engineer",
    "special_requirements": "Focus Redis gap",
}


def test_health():
    response = client.get("/health")
    assert response.status_code == 200


def test_planning_plan_three_briefs():
    response = client.post("/api/v1/planning/plan", json=SAMPLE)
    assert response.status_code == 200
    body = response.json()
    plan = body["plan"]
    assert "interview_brief" in plan
    assert "evaluation_brief" in plan
    assert "assignment_brief" in plan
    assert plan["assignment_brief"].startswith("ASSIGNMENT DIRECTIVE")
    assert 45 <= plan["duration_minutes"] <= 60