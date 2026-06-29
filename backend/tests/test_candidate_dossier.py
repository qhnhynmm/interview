import asyncio
import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.database import Base
from app.main import app
from app.models.interview import Interview, InterviewStatus
from app.services.inspector import normalize_report

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

    monkeypatch.setattr("app.services.planning.fetch_interview_plan", _mock_plan)
    monkeypatch.setattr("app.services.assignment.fetch_assignment", _mock_assignment)


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
        json={"username": "hr_dossier", "email": "hr_dossier@demo.com", "password": "demo12345"},
    )
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_interview(client: TestClient, headers: dict[str, str]) -> dict:
    cv = io.BytesIO(b"Python, React, 4 years experience")
    res = client.post(
        "/api/v1/interviews/generate-link",
        headers=headers,
        data={
            "candidate_name": "Tran Minh Anh",
            "candidate_email": "minhanh@email.com",
            "position": "Backend Engineer",
            "jd_text": "Build APIs with Python",
        },
        files={"cv_file": ("cv.txt", cv, "text/plain")},
    )
    assert res.status_code == 201
    return res.json()


def test_candidate_dossier_requires_auth(client: TestClient):
    headers = _auth_headers(client)
    created = _create_interview(client, headers)
    res = client.get(f"/api/v1/interviews/{created['id']}/dossier")
    assert res.status_code == 401


def test_candidate_dossier_returns_profile(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "app.services.report_worker.schedule_report_generation",
        lambda _interview_id: None,
    )

    headers = _auth_headers(client)
    created = _create_interview(client, headers)

    db = TestingSessionLocal()
    row = db.get(Interview, created["id"])
    assert row is not None
    row.status = InterviewStatus.completed
    row.conversation_history = [
        {"role": "agent", "content": "Hello", "timestamp": "2026-06-29T10:00:00Z"},
        {"role": "candidate", "content": "Hi there", "timestamp": "2026-06-29T10:00:05Z"},
    ]
    row.report = normalize_report(
        row,
        {
            "overall_score": 4.1,
            "competency_scores": {"Technical depth": 4.2, "Communication": 3.8},
            "summary": "Strong backend fundamentals.",
        },
    )
    db.add(row)
    db.commit()
    db.close()

    res = client.get(f"/api/v1/interviews/{created['id']}/dossier", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["candidate_name"] == "Tran Minh Anh"
    assert body["cv_filename"] == "cv.txt"
    assert len(body["conversation_history"]) == 2
    assert body["status"] == "completed"
    assert body["report"]["overall_score"] == 4.1


async def _mock_inspector_report(_row):
    return {
        "overall_score": 4.0,
        "competency_scores": {"Technical depth": 4.0},
        "summary": "Done.",
    }


def test_report_worker_generates_report(monkeypatch):
    from app.services import report_worker

    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr("app.services.report_worker.SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(
        "app.services.report_worker.fetch_inspector_report",
        _mock_inspector_report,
    )

    db = TestingSessionLocal()
    row = Interview(
        id="itv-report01",
        created_by_id=1,
        candidate_name="Worker Test",
        candidate_email="worker@email.com",
        position="Engineer",
        jd_text="JD",
        status=InterviewStatus.evaluating,
        plan={"competencies": [{"name": "Technical depth", "weight": 1.0}]},
    )
    db.add(row)
    db.commit()
    db.close()

    asyncio.run(report_worker._generate_report("itv-report01"))

    db = TestingSessionLocal()
    saved = db.get(Interview, "itv-report01")
    assert saved is not None
    assert saved.status == InterviewStatus.completed
    assert saved.report is not None
    assert saved.report["overall_score"] == 4.0
    db.close()


def test_end_interview_triggers_evaluating(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        "app.api.v1.interviews.schedule_report_generation",
        lambda _interview_id: None,
    )
    headers = _auth_headers(client)
    created = _create_interview(client, headers)

    res = client.post(
        f"/api/v1/interviews/{created['id']}/end",
        json={"reason": "completed", "detail": "session ended"},
    )
    assert res.status_code == 204

    row = TestingSessionLocal().get(Interview, created["id"])
    assert row is not None
    assert row.status.value == "evaluating"