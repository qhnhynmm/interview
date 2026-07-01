from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.security import validate_ai_settings

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_SERVICES_ROOT = Path(__file__).resolve().parents[1]


def _load_yaml_section(section: str) -> dict:
    path = REPO_ROOT / "configs" / "ai-services.yml"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    return raw.get(section, {})


_YAML = _load_yaml_section("ai-services")
_INTERVIEW_YAML = _load_yaml_section("interview-agent")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(AI_SERVICES_ROOT / ".env", REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Aurelia AI Services"
    app_env: str = Field(default=_YAML.get("app_env", "development"), validation_alias="APP_ENV")
    api_prefix: str = "/api/v1"
    host: str = Field(default=_YAML.get("mcp_host", "0.0.0.0"))
    port: int = Field(default=int(_YAML.get("mcp_port", 8001)))

    backend_url: str = Field(
        default=_YAML.get("backend_url", "http://localhost:8000"),
        validation_alias="BACKEND_URL",
    )

    # LLM provider — Gemini (recommended) or any OpenAI-compatible gateway (MaaS).
    gemini_api_key: str = Field(default="", validation_alias="GEMINI_API_KEY")
    gemini_base_url: str = Field(
        default=_YAML.get(
            "gemini_base_url",
            "https://generativelanguage.googleapis.com/v1beta/openai/",
        ),
    )
    gemini_model: str = Field(
        default=_YAML.get("gemini_model", "gemini-3.1-flash-lite"),
        validation_alias="GEMINI_MODEL",
    )

    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="OPENAI_BASE_URL",
    )
    llm_provider: str = Field(default=_YAML.get("llm_provider", "gemini"), validation_alias="LLM_PROVIDER")

    planning_model: str = Field(default=_YAML.get("planning_model", "gemini-3.1-flash-lite"))
    planning_temperature: float = Field(default=float(_YAML.get("planning_temperature", 0.4)))
    planning_max_tokens: int = Field(default=int(_YAML.get("planning_max_tokens", 1536)))
    planning_request_timeout: float = Field(default=float(_YAML.get("planning_request_timeout", 75)))
    planning_analyst_model: str = Field(default=_YAML.get("planning_analyst_model", "") or "")
    planning_analyst_max_tokens: int = Field(default=int(_YAML.get("planning_analyst_max_tokens", 1100)))

    assignment_model: str = Field(default=_YAML.get("assignment_model", "gemini-3.1-flash-lite"))

    coding_assistant_model: str = Field(default=_YAML.get("coding_assistant_model", "google/gemma-4-31b-it"))
    coding_assistant_temperature: float = Field(default=float(_YAML.get("coding_assistant_temperature", 0.3)))
    coding_assistant_max_tokens: int = Field(default=int(_YAML.get("coding_assistant_max_tokens", 2048)))

    inspector_model: str = Field(default=_YAML.get("inspector_model", "google/gemma-4-31b-it"))
    inspector_temperature: float = Field(default=float(_YAML.get("inspector_temperature", 0.3)))
    inspector_max_tokens: int = Field(default=int(_YAML.get("inspector_max_tokens", 4096)))

    otel_enabled: bool = Field(
        default=bool(_YAML.get("otel_enabled", False)),
        validation_alias="OTEL_ENABLED",
    )
    otel_otlp_endpoint: str = Field(
        default=_YAML.get("otel_otlp_endpoint", "http://localhost:6006/v1/traces"),
        validation_alias="OTEL_OTLP_ENDPOINT",
    )
    otel_console: bool = Field(
        default=bool(_YAML.get("otel_console", False)),
        validation_alias="OTEL_CONSOLE",
    )
    otel_sensitive: bool = Field(
        default=bool(_YAML.get("otel_sensitive", True)),
        validation_alias="OTEL_SENSITIVE",
    )

    # Interview worker (separate process — see app/worker.py)
    livekit_url: str = Field(default=_INTERVIEW_YAML.get("livekit_url", "ws://localhost:7880"))
    livekit_api_key: str = Field(default="", validation_alias="LIVEKIT_API_KEY")
    livekit_api_secret: str = Field(default="", validation_alias="LIVEKIT_API_SECRET")
    livekit_worker_port: int = Field(default=8082, validation_alias="LIVEKIT_WORKER_PORT")
    agent_name: str = Field(default=_INTERVIEW_YAML.get("agent_name", "interview-agent"))
    interview_language: str = Field(default=_INTERVIEW_YAML.get("language", "en"))
    mcp_sse_url: str = Field(default=_INTERVIEW_YAML.get("mcp_sse_url", "http://localhost:8001/mcp/sse"))
    mcp_assignment_sse_url: str = Field(
        default=_INTERVIEW_YAML.get("mcp_assignment_sse_url", "http://localhost:8001/assignment-mcp/sse"),
    )
    mcp_http_timeout: float = Field(default=float(_INTERVIEW_YAML.get("mcp_http_timeout", 20)))
    internal_service_key: str = Field(default="", validation_alias="INTERNAL_SERVICE_KEY")
    interview_backend_url: str = Field(default=_INTERVIEW_YAML.get("backend_url", "http://localhost:8000"))

    interview_live_model: str = Field(
        default=_INTERVIEW_YAML.get("live_model", "gemini-2.5-flash-native-audio-preview-12-2025"),
    )
    interview_live_voice: str = Field(default=_INTERVIEW_YAML.get("live_voice", "Puck"))
    interview_openai_base_url: str = Field(
        default="https://api.openai.com/v1",
        validation_alias="INTERVIEW_OPENAI_BASE_URL",
    )
    interview_openai_model: str = Field(
        default=_INTERVIEW_YAML.get("openai_model", "gemini-3.1-flash-lite"),
    )
    interview_temperature: float = Field(
        default=float(_INTERVIEW_YAML.get("interview_temperature", 0.5)),
    )
    interview_max_tokens: int = Field(default=int(_INTERVIEW_YAML.get("interview_max_tokens", 1000)))

    silence_threshold_ms: int = Field(default=int(_INTERVIEW_YAML.get("silence_threshold_ms", 1500)))

    proctoring_cooldown_seconds: int = Field(
        default=int(_INTERVIEW_YAML.get("proctoring_cooldown_seconds", 15)),
    )
    proctoring_max_violations: int = Field(
        default=int(_INTERVIEW_YAML.get("proctoring_max_violations", 5)),
    )

    @property
    def effective_llm_provider(self) -> str:
        if self.gemini_api_key.strip():
            return "gemini"
        if self.openai_api_key.strip():
            return "openai"
        return (self.llm_provider or "gemini").strip().lower()

    @property
    def llm_api_key(self) -> str:
        if self.effective_llm_provider == "gemini":
            return self.gemini_api_key.strip()
        return self.openai_api_key.strip()

    @property
    def llm_base_url(self) -> str:
        if self.effective_llm_provider == "gemini":
            return self.gemini_base_url.rstrip("/") + "/"
        return self.openai_base_url.rstrip("/") + "/"

    @property
    def llm_enabled(self) -> bool:
        return bool(self.llm_api_key)

    @property
    def planning_model_effective(self) -> str:
        if self.effective_llm_provider == "gemini":
            # Prefer GEMINI_MODEL env; yaml planning_model may lag behind API deprecations.
            if self.gemini_model.strip():
                return self.gemini_model.strip()
            return self.planning_model
        return self.planning_model

    @property
    def assignment_model_effective(self) -> str:
        if self.effective_llm_provider == "gemini" and self.gemini_model.strip():
            return self.gemini_model.strip()
        return self.assignment_model

    @property
    def inspector_model_effective(self) -> str:
        if self.effective_llm_provider == "gemini" and self.gemini_model.strip():
            return self.gemini_model.strip()
        return self.inspector_model

    @property
    def interview_llm_api_key(self) -> str:
        if self.gemini_api_key.strip():
            return self.gemini_api_key.strip()
        return self.openai_api_key.strip()

    @property
    def interview_llm_base_url(self) -> str:
        if self.gemini_api_key.strip():
            return self.gemini_base_url.rstrip("/") + "/"
        return self.interview_openai_base_url.rstrip("/") + "/"

    @property
    def interview_llm_model(self) -> str:
        if self.gemini_api_key.strip() and self.gemini_model.strip():
            return self.gemini_model.strip()
        return self.interview_openai_model

    @property
    def planning_analyst_effective_model(self) -> str:
        analyst = self.planning_analyst_model.strip()
        if analyst:
            if self.effective_llm_provider == "gemini" and analyst.startswith("google/"):
                return self.gemini_model
            return analyst
        return self.planning_model_effective


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    validate_ai_settings(settings)
    return settings