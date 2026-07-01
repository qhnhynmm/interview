from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml_defaults() -> dict:
    path = REPO_ROOT / "configs" / "backend-services.yml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return raw.get("backend", {})


_YAML = _load_yaml_defaults()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_ROOT / ".env", REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = Field(default=_YAML.get("app_name", "Aurelia Backend"))
    app_env: str = Field(default=_YAML.get("app_env", "development"))
    api_prefix: str = Field(default=_YAML.get("api_prefix", "/api/v1"))
    host: str = Field(default=_YAML.get("host", "0.0.0.0"))
    port: int = Field(default=int(_YAML.get("port", 8000)))

    cors_origins: str = Field(default=_YAML.get("cors_origins", "*"))
    database_url: str = Field(
        default=f"sqlite:///{(BACKEND_ROOT / 'data' / 'aurelia.db').as_posix()}",
        validation_alias="DATABASE_URL",
    )
    db_echo: bool = Field(default=bool(_YAML.get("db_echo", False)))

    jwt_secret: str = Field(default="dev-change-me-in-production", validation_alias="JWT_SECRET")
    jwt_algorithm: str = Field(default=_YAML.get("jwt_algorithm", "HS256"))
    jwt_expire_minutes: int = Field(default=int(_YAML.get("jwt_expire_minutes", 1440)))

    frontend_url: str = Field(default=_YAML.get("frontend_url", "http://localhost:3000"))
    ai_service_url: str = Field(default=_YAML.get("ai_service_url", "http://localhost:8001"))
    planning_endpoint: str = Field(default=_YAML.get("planning_endpoint", "/api/v1/planning/plan"))
    assignment_endpoint: str = Field(
        default=_YAML.get("assignment_endpoint", "/api/v1/assignment/generate"),
    )
    inspector_endpoint: str = Field(
        default=_YAML.get("inspector_endpoint", "/api/v1/inspector/evaluate"),
    )
    coding_assistant_endpoint: str = Field(
        default=_YAML.get("coding_assistant_endpoint", "/api/v1/coding-assistant/chat"),
    )
    ai_request_timeout: float = Field(default=float(_YAML.get("ai_request_timeout", 120.0)))

    livekit_url: str = Field(default=_YAML.get("livekit_url", "ws://127.0.0.1:7880"))
    livekit_public_url: str = Field(
        default=_YAML.get("livekit_public_url", "ws://127.0.0.1:7880"),
        validation_alias="LIVEKIT_PUBLIC_URL",
    )
    livekit_api_key: str = Field(default="", validation_alias="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(default="", validation_alias="LIVEKIT_API_SECRET")
    livekit_token_ttl: int = Field(default=int(_YAML.get("livekit_token_ttl", 14400)))
    livekit_agent_name: str = Field(default=_YAML.get("livekit_agent_name", "interview-agent"))

    schedule_offset_minutes: int = Field(default=int(_YAML.get("schedule_offset_minutes", 30)))
    max_concurrent_sessions: int = Field(default=int(_YAML.get("max_concurrent_sessions", 3)))
    session_window_minutes: int = Field(default=int(_YAML.get("session_window_minutes", 18)))
    slot_open_buffer_minutes: int = Field(default=int(_YAML.get("slot_open_buffer_minutes", 10)))
    storage_dir: str = Field(default=_YAML.get("storage_dir", "data/storage"))

    minio_enabled: bool = Field(default=False, validation_alias="MINIO_ENABLED")
    minio_endpoint: str = Field(default=_YAML.get("minio_endpoint", "127.0.0.1:9000"))
    minio_secure: bool = Field(default=bool(_YAML.get("minio_secure", False)))
    minio_region: str = Field(default=_YAML.get("minio_region", "us-east-1"))
    minio_bucket_cvs: str = Field(default=_YAML.get("minio_bucket_cvs", "cvs"))
    minio_bucket_reports: str = Field(default=_YAML.get("minio_bucket_reports", "reports"))
    minio_bucket_recordings: str = Field(default=_YAML.get("minio_bucket_recordings", "recordings"))
    recording_url_ttl: int = Field(default=int(_YAML.get("recording_url_ttl", 604800)))
    minio_access_key: str = Field(default="", validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(default="", validation_alias="MINIO_SECRET_KEY")

    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(
        default=_YAML.get("gemini_model", "gemini-3.1-flash-lite"),
        validation_alias="GEMINI_MODEL",
    )
    gemini_request_timeout: float = Field(
        default=float(_YAML.get("gemini_request_timeout", 60.0)),
        validation_alias="GEMINI_REQUEST_TIMEOUT",
    )
    internal_service_key: str = Field(default="", validation_alias="INTERNAL_SERVICE_KEY")

    @property
    def minio_endpoint_url(self) -> str:
        scheme = "https" if self.minio_secure else "http"
        return f"{scheme}://{self.minio_endpoint}"

    @property
    def storage_path(self) -> Path:
        p = Path(self.storage_dir)
        return p if p.is_absolute() else REPO_ROOT / p

    @property
    def planning_url(self) -> str:
        return f"{self.ai_service_url.rstrip('/')}{self.planning_endpoint}"

    @property
    def inspector_url(self) -> str:
        return f"{self.ai_service_url.rstrip('/')}{self.inspector_endpoint}"

    @property
    def coding_assistant_url(self) -> str:
        return f"{self.ai_service_url.rstrip('/')}{self.coding_assistant_endpoint}"

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.cors_origins or "*").strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()