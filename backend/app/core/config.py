from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PACE API"
    app_env: Literal["development", "production"] = "development"
    database_url: str = "postgresql+psycopg://pace:pace@localhost:5432/pace"
    jwt_secret: str = Field(min_length=32)
    access_token_minutes: int = 60 * 24 * 7
    allow_registration: bool = False
    secure_cookie: bool = False
    frontend_origin: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    @field_validator("jwt_secret")
    @classmethod
    def reject_example_secrets(cls, value: str) -> str:
        normalized = value.lower()
        if value != value.strip() or "replace" in normalized or "change-this-secret" in normalized:
            raise ValueError("JWT_SECRET must be a deployment-specific random value")
        return value

    @model_validator(mode="after")
    def require_secure_production_cookie(self):
        if self.app_env == "production" and not self.secure_cookie:
            raise ValueError("SECURE_COOKIE must be true in production")
        return self


settings = Settings()