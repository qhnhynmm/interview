import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.database import Base
from app.main import app
from app.models.interview import Interview

SQLALCHEMY_TEST_URL = "sqlite://"

engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def fast_ai(monkeypatch):
    async def _mock_plan(**_kwargs):
        return {
            "competencies": [
                {"name": "Technical depth", "weight": 0.6},
                {"name": "Communication", "weight": 0.4},
            ]
        }

    async def _mock_assignment(**_kwargs):
        return {"type": "coding", "coding": {"title": "Two Sum", "ai_assistant_enabled": False}}

    monkeypatch.setattr("app.api.v1.interviews.fetch_interview_plan", _mock_plan)
    monkeypatch.setattr("app.api.v1.interviews.fetch_assignment", _mock_assignment)


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    db.close()


def _auth_headers(client: TestClient) -> dict[str, str]:
    reg = client.post(
        "/api/v1/auth/register",
        json={"username": "hr_slots", "email": "hr_slots@demo.com", "password": "demo12345"},
    )
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_slots_requires_auth(client: TestClient):
    res = client.get("/api/v1/interviews/slots")
    assert res.status_code == 401


def test_slots_returns_shape(client: TestClient):
    res = client.get("/api/v1/interviews/slots", headers=_auth_headers(client))
    assert res.status_code == 200
    body = res.json()
    assert "slots" in body
    assert "instant_available" in body
    assert isinstance(body["slots"], list)
    if body["slots"]:
        slot = body["slots"][0]
        assert "start" in slot
        assert "available" in slot
        assert "active_count" in slot


def test_generate_link_and_list(client: TestClient):
    headers = _auth_headers(client)
    cv = io.BytesIO(b"Python, React, 4 years experience")
    res = client.post(
        "/api/v1/interviews/generate-link",
        headers=headers,
        data={
            "candidate_name": "Tran Minh Anh",
            "candidate_email": "minhanh@email.com",
            "position": "Backend Engineer",
            "jd_text": "Build APIs with FastAPI",
            "special_requirements": "Focus on system design",
            "interview_language": "vi",
            "seniority": "Mid",
        },
        files={"cv_file": ("cv.txt", cv, "text/plain")},
    )
    assert res.status_code == 201
    created = res.json()
    assert created["candidate_name"] == "Tran Minh Anh"
    assert created["position"] == "Backend Engineer"
    assert created["status"] == "scheduled"
    assert created["meeting_url"].endswith(f"/interview/{created['id']}")
    assert created["report"] is None

    listing = client.get("/api/v1/interviews", headers=headers)
    assert listing.status_code == 200
    rows = listing.json()
    assert len(rows) == 1
    assert rows[0]["id"] == created["id"]

    row = TestingSessionLocal().get(Interview, created["id"])
    assert row is not None
    assert row.cv_filename == "cv.txt"
    assert row.cv_text == "Python, React, 4 years experience"
    assert row.cv_fields is not None
    assert "raw_text" not in row.cv_fields


def test_end_interview_public(client: TestClient, monkeypatch):
    headers = _auth_headers(client)
    cv = io.BytesIO(b"skills: python")
    created = client.post(
        "/api/v1/interviews/generate-link",
        headers=headers,
        data={
            "candidate_name": "End Test",
            "candidate_email": "end@email.com",
            "position": "Engineer",
            "jd_text": "JD",
        },
        files={"cv_file": ("cv.txt", cv, "text/plain")},
    ).json()

    res = client.post(
        f"/api/v1/interviews/{created['id']}/end",
        json={"reason": "proctoring", "detail": "tab_switch"},
    )
    assert res.status_code == 204

    row = TestingSessionLocal().get(Interview, created["id"])
    assert row is not None
    assert row.status.value == "abandoned"


def test_proctor_event_public(client: TestClient, monkeypatch):
    async def _noop_broadcast(**_kwargs):
        return None

    monkeypatch.setattr(
        "app.api.v1.interviews.broadcast_proctor_violation",
        _noop_broadcast,
    )
    headers = _auth_headers(client)
    cv = io.BytesIO(b"skills: python")
    created = client.post(
        "/api/v1/interviews/generate-link",
        headers=headers,
        data={
            "candidate_name": "Proctor Test",
            "candidate_email": "proctor@email.com",
            "position": "Engineer",
            "jd_text": "JD",
        },
        files={"cv_file": ("cv.txt", cv, "text/plain")},
    ).json()

    res = client.post(
        f"/api/v1/interviews/{created['id']}/proctor-event",
        json={"kind": "tab_switch", "severity": "high", "detail": "Left for 2.1s", "ts": 1.0},
    )
    assert res.status_code == 204

    row = TestingSessionLocal().get(Interview, created["id"])
    assert row is not None
    assert len(row.proctoring_events) == 1
    assert row.proctoring_events[0]["kind"] == "tab_switch"


def test_get_interview_public(client: TestClient):
    headers = _auth_headers(client)
    cv = io.BytesIO(b"skills: go, python")
    created = client.post(
        "/api/v1/interviews/generate-link",
        headers=headers,
        data={
            "candidate_name": "Guest",
            "candidate_email": "guest@email.com",
            "position": "Engineer",
            "jd_text": "JD text",
            "special_requirements": "none",
        },
        files={"cv_file": ("cv.txt", cv, "text/plain")},
    ).json()

    detail = client.get(f"/api/v1/interviews/{created['id']}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == created["id"]
    assert body["assignment"]["coding"]["title"] == "Two Sum"
    assert body["assistant_enabled"] is False