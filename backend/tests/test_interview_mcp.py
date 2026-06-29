import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

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


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("INTERNAL_SERVICE_KEY", "test-service-key")
    from app.config import get_settings

    get_settings.cache_clear()
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


def _service_headers() -> dict[str, str]:
    return {"X-Service-Key": "test-service-key"}


def _seed_interview(db) -> str:
    from app.models.user import User, UserRole

    user = User(username="mcp_hr", email="mcp_hr@test.com", hashed_password="x", role=UserRole.hr)
    db.add(user)
    db.flush()
    row = Interview(
        id="itv-mcp01",
        created_by_id=user.id,
        candidate_name="MCP Test",
        candidate_email="mcp@test.com",
        position="Engineer",
        jd_text="JD",
        plan={"interview_brief": "Warm-up then Python."},
        assignment={"coding": {"title": "Two Sum", "description": "Find pair"}},
    )
    db.add(row)
    db.commit()
    return row.id


def test_append_transcript_turn(client: TestClient):
    db = TestingSessionLocal()
    interview_id = _seed_interview(db)
    res = client.post(
        f"/api/v1/interviews/{interview_id}/transcript/append",
        headers=_service_headers(),
        json={"role": "agent", "content": "Hello, ready to begin?"},
    )
    assert res.status_code == 204
    row = db.get(Interview, interview_id)
    assert row is not None
    assert len(row.conversation_history or []) == 1
    assert row.conversation_history[0]["role"] == "agent"


def test_switch_mode(client: TestClient, monkeypatch):
    async def _noop(**_kwargs):
        return True

    monkeypatch.setattr("app.api.v1.interview_agent.broadcast_room_data", _noop)
    db = TestingSessionLocal()
    interview_id = _seed_interview(db)
    res = client.post(
        f"/api/v1/interviews/{interview_id}/switch-mode",
        headers=_service_headers(),
        json={"mode": "code"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["mode"] == "code"
    row = db.get(Interview, interview_id)
    assert row is not None
    assert row.ui_mode == "code"