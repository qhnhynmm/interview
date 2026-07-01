from types import SimpleNamespace

import pytest

from app.security import validate_backend_settings


def _settings(**kwargs):
    defaults = {
        "app_env": "production",
        "jwt_secret": "x" * 40,
        "cors_origins": "https://aurelia.io.vn",
        "internal_service_key": "x" * 32,
        "livekit_api_key": "prod-livekit-key",
        "livekit_api_secret": "x" * 40,
        "database_url": "postgresql+psycopg://aurelia:strong-pass@127.0.0.1:5432/aurelia",
        "minio_enabled": False,
        "minio_secret_key": "",
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_production_rejects_insecure_jwt():
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        validate_backend_settings(_settings(jwt_secret="change-me-to-a-long-random-string"))


def test_production_rejects_wildcard_cors():
    with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
        validate_backend_settings(_settings(cors_origins="*"))


def test_development_allows_dev_defaults():
    validate_backend_settings(
        _settings(
            app_env="development",
            jwt_secret="change-me-to-a-long-random-string",
            cors_origins="http://localhost:8080",
            livekit_api_key="devkey",
            livekit_api_secret="aurelia_dev_livekit_secret_32chars_min",
        )
    )