"""Production security checks for ai-services and the interview worker."""

from __future__ import annotations

_INSECURE_LIVEKIT_KEYS = frozenset({"", "devkey"})
_INSECURE_LIVEKIT_SECRETS = frozenset(
    {
        "",
        "aurelia_dev_livekit_secret_32chars_min",
    }
)


def is_production(app_env: str) -> bool:
    return (app_env or "").strip().lower() in {"production", "prod"}


def validate_ai_settings(settings) -> None:
    if not is_production(settings.app_env):
        return

    errors: list[str] = []

    if not settings.gemini_api_key.strip() and not settings.openai_api_key.strip():
        errors.append("GEMINI_API_KEY or OPENAI_API_KEY is required in production")

    if settings.livekit_api_key in _INSECURE_LIVEKIT_KEYS:
        errors.append("LIVEKIT_API_KEY must not use the dev default in production")
    if settings.livekit_api_secret in _INSECURE_LIVEKIT_SECRETS or len(
        settings.livekit_api_secret or ""
    ) < 32:
        errors.append("LIVEKIT_API_SECRET must be a unique random string (>=32 chars)")

    if not settings.internal_service_key.strip() or len(settings.internal_service_key.strip()) < 16:
        errors.append("INTERNAL_SERVICE_KEY must be set (>=16 chars) in production")

    if errors:
        joined = "\n  - ".join(errors)
        raise RuntimeError(f"Insecure production configuration:\n  - {joined}")