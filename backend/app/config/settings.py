"""
Application settings loaded from environment variables.
Uses Pydantic BaseSettings for type-safe, validated config.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────
    app_name: str = "AI Workforce OS"
    app_version: str = "1.0.0"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production-use-32-char-random-string"

    # ── Database ─────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./ai_workforce.db"

    # ── JWT Auth ─────────────────────────────────────────
    jwt_secret_key: str = "change-me-in-production-jwt-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # ── AI / LLM ─────────────────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    use_mock_llm: bool = True

    # ── External Integrations ────────────────────────────
    aviationstack_api_key: str = ""
    demo_mode: bool = True

    # ── ChromaDB ─────────────────────────────────────────
    chroma_persist_dir: str = "./chroma_db"

    # ── Rate Limiting ─────────────────────────────────────
    rate_limit_per_minute: int = 100

    # ── CORS ─────────────────────────────────────────────
    allowed_origins: str = "http://localhost:3000,http://localhost:3001"

    # ── Logging ──────────────────────────────────────────
    log_level: str = "INFO"

    # ── Demo Tenants ─────────────────────────────────────
    demo_tenant_1: str = "GlobalTech Corp"
    demo_tenant_2: str = "Acme Industries"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def has_gemini_key(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def has_aviationstack_key(self) -> bool:
        return bool(self.aviationstack_api_key)

    @property
    def effective_use_mock_llm(self) -> bool:
        """Use mock LLM if key not provided or explicitly set."""
        return self.use_mock_llm or not self.has_gemini_key


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
