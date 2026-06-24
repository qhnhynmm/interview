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

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.cors_origins or "*").strip()
        if raw == "*":
            return ["*"]
        return [o.strip() for o in raw.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()