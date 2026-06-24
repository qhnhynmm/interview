import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.database import Base
from app.main import app

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


def _register(client: TestClient, username: str = "hr_user", email: str = "hr@demo.com"):
    return client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": email, "password": "demo12345"},
    )


def test_register_login_and_me(client: TestClient):
    reg = _register(client)
    assert reg.status_code == 201
    assert "access_token" in reg.json()

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "hr@demo.com", "password": "demo12345"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    body = me.json()
    assert body["email"] == "hr@demo.com"
    assert body["username"] == "hr_user"
    assert body["role"] == "hr"


def test_login_wrong_password_is_401(client: TestClient):
    _register(client)
    bad = client.post(
        "/api/v1/auth/login",
        json={"email": "hr@demo.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401


def test_me_requires_auth(client: TestClient):
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401


def test_hr_guard_allows_hr(client: TestClient):
    reg = _register(client)
    token = reg.json()["access_token"]
    res = client.get("/api/v1/auth/me/hr", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200