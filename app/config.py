from __future__ import annotations

import json
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(default="sqlite+aiosqlite:///./cartridge_cast.db", alias="DATABASE_URL")
    auth0_domain: str = Field(default="", alias="AUTH0_DOMAIN")
    auth0_api_audience: str = Field(default="", alias="AUTH0_API_AUDIENCE")
    auth0_client_id: str = Field(default="", alias="AUTH0_CLIENT_ID")
    auth0_client_secret: str = Field(default="", alias="AUTH0_CLIENT_SECRET")

    stripe_secret_key: str = Field(default="", alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(default="", alias="STRIPE_WEBHOOK_SECRET")
    stripe_platform_account: str = Field(default="", alias="STRIPE_PLATFORM_ACCOUNT")
    platform_fee_percentage: float = Field(default=0.12, alias="PLATFORM_FEE_PERCENTAGE")
    deposit_percentage: float = Field(default=0.30, alias="DEPOSIT_PERCENTAGE")

    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    s3_bucket_photos: str = Field(default="", alias="S3_BUCKET_PHOTOS")
    cloudfront_distribution_id: str = Field(default="", alias="CLOUDFRONT_DISTRIBUTION_ID")
    cloudfront_domain: str = Field(default="", alias="CLOUDFRONT_DOMAIN")

    resend_api_key: str = Field(default="", alias="RESEND_API_KEY")
    from_email: str = Field(default="bookings@cartridgeandcast.com", alias="FROM_EMAIL")
    outreach_from_email: str = Field(default="ryan@cartridgeandcast.com", alias="OUTREACH_FROM_EMAIL")

    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    google_maps_api_key: str = Field(default="", alias="GOOGLE_MAPS_API_KEY")

    app_env: str = Field(default="local", alias="APP_ENV")
    app_url: str = Field(default="http://localhost:3000", alias="APP_URL")
    api_url: str = Field(default="http://localhost:8000", alias="API_URL")
    cors_origins: str = Field(default='["http://localhost:3000"]', alias="CORS_ORIGINS")
    public_rate_limit_per_minute: int = Field(default=60, alias="PUBLIC_RATE_LIMIT_PER_MINUTE")
    authenticated_rate_limit_per_minute: int = Field(default=300, alias="AUTHENTICATED_RATE_LIMIT_PER_MINUTE")
    worker_poll_interval_seconds: int = Field(default=5, alias="WORKER_POLL_INTERVAL_SECONDS")
    auth_session_cookie_name: str = Field(default="cc_session", alias="AUTH_SESSION_COOKIE_NAME")
    auth_csrf_cookie_name: str = Field(default="cc_csrf", alias="AUTH_CSRF_COOKIE_NAME")
    auth_csrf_header_name: str = Field(default="X-CSRF-Token", alias="AUTH_CSRF_HEADER_NAME")
    auth_session_ttl_seconds: int = Field(default=60 * 60 * 24 * 30, alias="AUTH_SESSION_TTL_SECONDS")
    auth_password_reset_ttl_seconds: int = Field(default=60 * 60, alias="AUTH_PASSWORD_RESET_TTL_SECONDS")
    auth_email_verification_ttl_seconds: int = Field(default=60 * 60 * 48, alias="AUTH_EMAIL_VERIFICATION_TTL_SECONDS")
    auth_require_email_verification: bool = Field(default=False, alias="AUTH_REQUIRE_EMAIL_VERIFICATION")
    auth_cookie_secure: bool = Field(default=False, alias="AUTH_COOKIE_SECURE")
    auth_cookie_samesite: str = Field(default="lax", alias="AUTH_COOKIE_SAMESITE")

    @property
    def cors_origins_list(self) -> List[str]:
        if not self.cors_origins:
            return []
        if self.cors_origins.startswith("["):
            return list(json.loads(self.cors_origins))
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
