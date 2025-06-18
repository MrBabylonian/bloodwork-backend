import os
from datetime import timedelta


class AuthConfig:
    """Authentication configuration settings"""

    def __init__(self):
        # JWT Settings
        self.secret_key = os.getenv(
            "JWT_SECRET_KEY", "your-super-secret-jwt-key-change-in-production")
        self.algorithm = "HS256"
        self.access_token_expire_minutes = int(
            os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
        self.refresh_token_expire_days = int(
            os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "30"))

        # Password Settings
        self.password_min_length = 8

        # Token Types
        self.access_token_type = "access"
        self.refresh_token_type = "refresh"

    @property
    def access_token_expire_time(self) -> timedelta:
        """Get access token expiration time"""
        return timedelta(minutes=self.access_token_expire_minutes)

    @property
    def refresh_token_expire_time(self) -> timedelta:
        """Get refresh token expiration time"""
        return timedelta(days=self.refresh_token_expire_days)
