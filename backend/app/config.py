# backend/app/config.py
# Central place for environment-driven settings. Every other module
# should read config from here rather than calling os.environ directly.
#
# DATABASE_URL and REDIS_URL have local-dev defaults so the backend can
# start without Postgres/Redis running — useful for running just the
# Engine/Health Index/Dead Code modules locally. Override both via .env
# once DB-backed features are wired in.
#
# extra="ignore" because .env holds variables for BOTH backend and
# frontend (e.g. VITE_API_BASE_URL is Vite's, not Python's) — without
# this, Settings() errors on any variable it doesn't explicitly declare.

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://adw:adw_password@localhost:5432/adw_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8000

    AI_LAYER_ENABLED: bool = False
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()