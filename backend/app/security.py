"""Production security checks — refuse to start with known-insecure defaults."""

from __future__ import annotations

_INSECURE_JWT = frozenset(
    {
        "",
        "dev-change-me-in-production",
        "change-me-to-a-long-random-string",
    }
)
_INSECURE_LIVEKIT_KEYS = frozenset({"", "devkey"})
_INSECURE_LIVEKIT_SECRETS = frozenset(
    {
        "",
        "aurelia_dev_livekit_secret_32chars_min",
    }
)
_WEAK_MINIO_SECRETS = frozenset({"", "aurelia-secret", "aurelia"})
_WEAK_DB_PASSWORDS = frozenset({"", "aurelia"})


def is_production(app_env: str) -> bool:
    return (app_env or "").strip().lower() in {"production", "prod"}


def _db_password_from_url(database_url: str) -> str:
    # postgresql+psycopg://user:pass@host/db
    try:
        auth = database_url.split("://", 1)[1].split("@", 1)[0]
        if ":" in auth:
            return auth.split(":", 1)[1]
    except IndexError:
        pass
    return ""


def validate_backend_settings(settings) -> None:
    if not is_production(settings.app_env):
        return

    errors: list[str] = []

    if settings.jwt_secret in _INSECURE_JWT or len(settings.jwt_secret) < 32:
        errors.append("JWT_SECRET must be a random string with at least 32 characters")

    if (settings.cors_origins or "").strip() == "*":
        errors.append("CORS_ORIGINS must not be '*' in production — set your frontend URL(s)")

    if not settings.internal_service_key.strip() or len(settings.internal_service_key.strip()) < 16:
        errors.append("INTERNAL_SERVICE_KEY must be set (>=16 chars) in production")

    if settings.livekit_api_key in _INSECURE_LIVEKIT_KEYS:
        errors.append("LIVEKIT_API_KEY must not use the dev default in production")
    if settings.livekit_api_secret in _INSECURE_LIVEKIT_SECRETS or len(
        settings.livekit_api_secret or ""
    ) < 32:
        errors.append("LIVEKIT_API_SECRET must be a unique random string (>=32 chars)")

    if settings.minio_enabled:
        if settings.minio_secret_key in _WEAK_MINIO_SECRETS:
            errors.append("MINIO_SECRET_KEY must be changed from dev defaults in production")

    db_pass = _db_password_from_url(settings.database_url)
    if db_pass in _WEAK_DB_PASSWORDS:
        errors.append("DATABASE_URL must not use the default Postgres password in production")

    if errors:
        joined = "\n  - ".join(errors)
        raise RuntimeError(f"Insecure production configuration:\n  - {joined}")