from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.config import get_settings
from app.database import Base
from app.main import app
from app.models.interview import Interview, InterviewStatus
from app.models.user import User

SQLALCHEMY_TEST_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_TEST_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


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


@pytest.fixture(autouse=True)
def _livekit_settings(monkeypatch):
    monkeypatch.setenv("LIVEKIT_API_KEY", "devkey")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "aurelia_dev_livekit_secret_32chars_min")
    monkeypatch.setenv("LIVEKIT_PUBLIC_URL", "ws://127.0.0.1:7880")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _auth_headers(client: TestClient) -> dict[str, str]:
    reg = client.post(
        "/api/v1/auth/register",
        json={"username": "hr_join", "email": "hr_join@demo.com", "password": "demo12345"},
    )
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _seed_interview(
    db,
    hr_user: User,
    interview_id: str,
    *,
    scheduled_at: datetime,
    status: InterviewStatus = InterviewStatus.scheduled,
) -> Interview:
    row = Interview(
        id=interview_id,
        created_by_id=hr_user.id,
        candidate_name="Huy",
        candidate_email="huy@test.com",
        position="AI Engineer",
        jd_text="JD",
        scheduled_at=scheduled_at,
        status=status,
        plan={},
        assignment={"type": "coding", "coding": {"mode": "dsa", "ai_assistant_enabled": False}},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def test_join_token_success(client: TestClient):
    headers = _auth_headers(client)
    client.get("/api/v1/interviews/slots", headers=headers)

    db = TestingSessionLocal()
    hr_user = db.scalar(select(User))
    assert hr_user is not None
    row = _seed_interview(db, hr_user, "itv-jointest01", scheduled_at=datetime.now(UTC))

    res = client.get(f"/api/v1/interviews/{row.id}/join-token?role=candidate")
    assert res.status_code == 200
    body = res.json()
    assert body["room_name"] == row.id
    assert body["livekit_url"] == "ws://127.0.0.1:7880"
    assert body["token"]

    settings = get_settings()
    claims = jwt.decode(
        body["token"],
        settings.livekit_api_secret,
        algorithms=["HS256"],
        issuer=settings.livekit_api_key,
    )
    assert claims["sub"] == f"candidate-{row.id}"
    assert claims["video"]["room"] == row.id
    assert claims["video"]["roomJoin"] is True

    refreshed = db.get(Interview, row.id)
    assert refreshed is not None
    assert refreshed.status == InterviewStatus.in_progress


def test_join_token_403_too_early(client: TestClient):
    headers = _auth_headers(client)
    client.get("/api/v1/interviews/slots", headers=headers)

    db = TestingSessionLocal()
    hr_user = db.scalar(select(User))
    future = datetime.now(UTC) + timedelta(hours=2)
    row = _seed_interview(db, hr_user, "itv-jointest02", scheduled_at=future)

    res = client.get(f"/api/v1/interviews/{row.id}/join-token")
    assert res.status_code == 403


def test_join_token_410_expired(client: TestClient):
    headers = _auth_headers(client)
    client.get("/api/v1/interviews/slots", headers=headers)

    db = TestingSessionLocal()
    hr_user = db.scalar(select(User))
    settings = get_settings()
    past = datetime.now(UTC) - timedelta(minutes=settings.session_window_minutes + 5)
    row = _seed_interview(db, hr_user, "itv-jointest03", scheduled_at=past)

    res = client.get(f"/api/v1/interviews/{row.id}/join-token")
    assert res.status_code == 410


def test_join_token_404(client: TestClient):
    res = client.get("/api/v1/interviews/itv-missing/join-token")
    assert res.status_code == 404