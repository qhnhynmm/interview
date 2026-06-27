from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

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
    app_env: str = Field(default=_YAML.get("app_env", "development"))
    api_prefix: str = "/api/v1"
    host: str = Field(default=_YAML.get("mcp_host", "0.0.0.0"))
    port: int = Field(default=int(_YAML.get("mcp_port", 8001)))

    backend_url: str = Field(
        default=_YAML.get("backend_url", "http://localhost:8000"),
        validation_alias="BACKEND_URL",
    )

    openai_api_key: str = Field(default="", validation_alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default=_YAML.get("openai_base_url", "https://api.openai.com/v1"))

    planning_model: str = Field(default=_YAML.get("planning_model", "google/gemma-4-31b-it"))
    planning_temperature: float = Field(default=float(_YAML.get("planning_temperature", 0.4)))
    planning_max_tokens: int = Field(default=int(_YAML.get("planning_max_tokens", 1536)))
    planning_request_timeout: float = Field(default=float(_YAML.get("planning_request_timeout", 75)))
    planning_analyst_model: str = Field(default=_YAML.get("planning_analyst_model", "") or "")
    planning_analyst_max_tokens: int = Field(default=int(_YAML.get("planning_analyst_max_tokens", 1100)))

    assignment_model: str = Field(default=_YAML.get("assignment_model", "google/gemma-4-31b-it"))
    assignment_temperature: float = Field(default=float(_YAML.get("assignment_temperature", 0.4)))
    assignment_max_tokens: int = Field(default=int(_YAML.get("assignment_max_tokens", 8192)))

    coding_assistant_model: str = Field(default=_YAML.get("coding_assistant_model", "google/gemma-4-31b-it"))
    coding_assistant_temperature: float = Field(default=float(_YAML.get("coding_assistant_temperature", 0.3)))
    coding_assistant_max_tokens: int = Field(default=int(_YAML.get("coding_assistant_max_tokens", 2048)))

    inspector_model: str = Field(default=_YAML.get("inspector_model", "google/gemma-4-31b-it"))
    inspector_temperature: float = Field(default=float(_YAML.get("inspector_temperature", 0.3)))
    inspector_max_tokens: int = Field(default=int(_YAML.get("inspector_max_tokens", 4096)))

    otel_enabled: bool = Field(default=bool(_YAML.get("otel_enabled", False)))
    otel_otlp_endpoint: str = Field(default=_YAML.get("otel_otlp_endpoint", "http://localhost:6006/v1/traces"))

    # Interview worker (separate process — see app/worker.py)
    livekit_url: str = Field(default=_INTERVIEW_YAML.get("livekit_url", "ws://localhost:7880"))
    agent_name: str = Field(default=_INTERVIEW_YAML.get("agent_name", "interview-agent"))
    mcp_sse_url: str = Field(default=_INTERVIEW_YAML.get("mcp_sse_url", "http://localhost:8001/mcp/sse"))

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key.strip())

    @property
    def planning_analyst_effective_model(self) -> str:
        return self.planning_analyst_model.strip() or self.planning_model


@lru_cache
def get_settings() -> Settings:
    return Settings()