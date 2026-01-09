"""Enhanced application configuration with production settings."""

from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Database
    MONGODB_URL: str = "mongodb://localhost:27017"
    DATABASE_NAME: str = "iquitos_ev_db"
    
    # API Settings
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Security
    SECRET_KEY: str = "change-this-in-production-use-openssl-rand-hex-32"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds
    
    # Metrics
    ENABLE_METRICS: bool = True
    
    # Carbon Intensity (Iquitos thermal grid)
    GRID_CARBON_INTENSITY: float = 0.4521  # kg CO2/kWh
    TARIFF_USD_PER_KWH: float = 0.20

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
