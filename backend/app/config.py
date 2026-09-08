# backend/app/config.py
# Central place for environment-driven settings. Every other module
# should read config from here rather than calling os.environ directly.

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    CHROMA_HOST: str = "chromadb"
    CHROMA_PORT: int = 8000

    AI_LAYER_ENABLED: bool = False
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()