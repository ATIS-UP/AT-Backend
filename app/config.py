"""Configuración de la aplicación"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

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

    # Storage (local or s3)
    STORAGE_BACKEND: str = "local"
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "at-artefactos"
    MINIO_USE_SSL: bool = False

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/app.log"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()