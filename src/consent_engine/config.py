from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # LLM
    anthropic_api_key: str | None = None
    # Defaults use the direct Gemini API (GEMINI_API_KEY), not Vertex AI, so
    # `uvx consent-engine audit` doesn't need GCP service-account credentials.
    # The deterministic fallback in generate_executive_summary() handles the
    # "no key set" case gracefully — the audit still completes.
    default_audit_model: str = "gemini/gemini-2.5-pro"
    default_classify_model: str = "gemini/gemini-2.5-flash"

    # Gemini / Vertex AI
    gemini_api_key: str | None = None
    vertex_project: str | None = None  # GCP project ID for Vertex AI
    vertex_location: str = "us-central1"

    # App
    environment: str = "development"
    log_level: str = "INFO"

    # Playwright proxy (optional — empty string treated as None)
    playwright_proxy_url: str | None = None

    @field_validator("playwright_proxy_url", mode="before")
    @classmethod
    def empty_str_to_none(cls, v: object) -> object:
        if isinstance(v, str) and (not v.strip() or v.strip() == "placeholder"):
            return None
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg,unused-ignore]
