from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "golden_incubator"
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080  # 7 days
    pat_encryption_key: str = "change-me"
    anthropic_api_key: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
