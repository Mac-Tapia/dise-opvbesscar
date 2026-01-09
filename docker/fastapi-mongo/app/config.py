"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "iquitos_ev_db"

    class Config:
        env_file = ".env"


settings = Settings()
