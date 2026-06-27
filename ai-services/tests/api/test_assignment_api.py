from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

DSA_SAMPLE = {
    "interview_id": "itv-api-dsa-001",
    "position": "Backend Engineer",
    "jd_text": "Junior backend: Python required",
    "cv_markdown": "# Dev\nPython basics",
    "level": "junior",
    "assignment_brief": (
        "ASSIGNMENT DIRECTIVE → type: coding · mode: dsa · ai_assistant: disabled · difficulty: easy\n\n"
        "Probe Python fundamentals."
    ),
}

COGNITIVE_SAMPLE = {
    "interview_id": "itv-api-cog-001",
    "position": "Marketing Manager",
    "jd_text": "Drive campaigns and brand growth",
    "cv_markdown": "# Marketer\n5 years B2B campaigns",
    "track": "nontech",
    "level": "mid",
}


def test_assignment_generate_dsa():
    response = client.post("/api/v1/assignment/generate", json=DSA_SAMPLE)
    assert response.status_code == 200
    body = response.json()
    assignment = body["assignment"]
    assert assignment["type"] == "coding"
    assert assignment["coding"]["mode"] == "dsa"
    assert assignment["coding"]["ai_assistant_enabled"] is False
    assert assignment["coding"]["title"] == "Two Sum"
    assert body["meta"]["path"] == "deterministic-dsa"


def test_assignment_generate_cognitive():
    response = client.post("/api/v1/assignment/generate", json=COGNITIVE_SAMPLE)
    assert response.status_code == 200
    body = response.json()
    assignment = body["assignment"]
    assert assignment["type"] == "cognitive"
    assert len(assignment["cognitive"]["questions"]) == 10