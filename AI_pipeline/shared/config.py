from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    GROQ_API_KEY: str
    GROQ_MODEL: str

    EMBEDDING_MODEL: str

    QDRANT_URL: str
    QDRANT_COLLECTION: str

    UPLOAD_DIR: str
    MAX_UPLOAD_SIZE_MB: int

    class Config:
        env_file = ".env"


settings = Settings()