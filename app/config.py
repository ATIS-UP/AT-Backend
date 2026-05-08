"""Configuración de la aplicación"""
from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Fernet
    FERNET_KEY: str

    # App
    APP_NAME: str = "Sistema de Alertas Tempranas"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    CORS_ORIGIN: str = "http://localhost:5173"

    # Rate Limiting
    LOGIN_RATE_LIMIT_PER_MINUTE: int = 5
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 15

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()