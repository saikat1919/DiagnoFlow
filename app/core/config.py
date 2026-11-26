from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL
from pydantic import SecretStr


class Settings(BaseSettings):
    APP_NAME: str = 'DiagnoFlow'
    DEBUG: bool = False
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_NAME: str
    DB_SCHEMA: str

    JWT_SECRET: SecretStr
    JWT_ALGORITHM: str
    ACCESS_TOKEN_MINUTES: int

    GROQ_API_KEY: SecretStr
    GROQ_MODEL: str
    GROQ_BASE_URL: str
    GEMINI_API_KEY: SecretStr

    UPLOAD_DIR: str = "uploads"

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:5174"

    @property
    def DATABASE_URL(self) -> URL:
        return URL.create(
            drivername='postgresql+asyncpg',
            database=self.DB_NAME,
            username=self.DB_USER,
            password=self.DB_PASSWORD.get_secret_value(),
            host=self.DB_HOST,
            port=self.DB_PORT
        )

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

@lru_cache
def get_settings():
    return Settings()