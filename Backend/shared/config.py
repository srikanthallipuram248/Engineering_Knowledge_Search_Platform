from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Engineering Knowledge Search Platform"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://eksp_user:eksp_password@postgres:5432/eksp_db"

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # AI pipeline internal URL
    AI_PIPELINE_URL: str = "http://ai-pipeline:8000"

    # Qdrant (used by search + chat services)
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_COLLECTION: str = "eksp_knowledge"

    # RAG thresholds (tunable without code changes)
    RAG_HIGH_THRESHOLD: float = 0.80
    RAG_LOW_THRESHOLD: float = 0.60


settings = Settings()
