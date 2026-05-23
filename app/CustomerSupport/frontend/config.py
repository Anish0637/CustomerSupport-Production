from __future__ import annotations

import secrets
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Security — MUST be set via env var in production; never hardcode
    secret_key: str = secrets.token_hex(32)  # auto-generated fallback for local dev

    # Cognito
    cognito_client_id: str = "4hqbuvfji23kgdeqqn2cujs5p4"
    cognito_domain: str = "https://customersupport-workshop.auth.us-east-1.amazoncognito.com"
    redirect_uri: str = "http://localhost:8501/callback"
    region: str = "us-east-1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8501
    debug: bool = False
    https_only: bool = False  # Set True behind TLS terminator in production

    # AWS
    aws_profile: Optional[str] = None
    aws_default_region: str = "us-east-1"


settings = Settings()
