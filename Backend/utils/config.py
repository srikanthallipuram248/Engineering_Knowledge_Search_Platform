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
    EMBEDDING_REQUEST_TIMEOUT: float = 60.0

    # Qdrant (used by search + chat services)
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_COLLECTION: str = "eksp_knowledge"

    # Groq - used by analyzer_service
    GROQ_API_KEY: str = ""
    GROQ_ANALYSIS_MODEL: str = "llama-3.3-70b-versatile"

    # RAG thresholds (tunable without code changes)
    HYBRID_RAG_THRESHOLD: float = 5.0


settings = Settings()
