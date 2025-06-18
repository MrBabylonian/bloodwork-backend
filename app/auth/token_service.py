from datetime import datetime, timezone
from typing import Any, Dict

from bson import ObjectId
from jose import JWTError, jwt

from app.auth.auth_config import AuthConfig
from app.utils.logger_utils import ApplicationLogger


class TokenService:
    """JWT token creation and validation service"""

    def __init__(self, config: AuthConfig):
        self.config = config
        self.logger = ApplicationLogger.get_logger(__name__)

    def create_access_token(self, user_id: str | ObjectId, username: str, role: str) -> str:
        """Create a short-lived access token"""
        return self._create_token(
            user_id=str(user_id),
            username=username,
            role=role,
            token_type=self.config.access_token_type,
            expires_delta=self.config.access_token_expire_time
        )

    def create_refresh_token(self, user_id: str | ObjectId, username: str) -> str:
        """Create a long-lived refresh token"""
        return self._create_token(
            user_id=str(user_id),
            username=username,
            role=None,  # Refresh tokens don't need role info
            token_type=self.config.refresh_token_type,
            expires_delta=self.config.refresh_token_expire_time
        )

    def _create_token(self, user_id: str, username: str, role: str | None,
                      token_type: str, expires_delta) -> str:
        """Create a JWT token with given parameters"""
        now = datetime.now(timezone.utc)
        expire = now + expires_delta

        payload = {
            "sub": user_id,  # Subject (user ID)
            "username": username,
            "type": token_type,
            "iat": now,  # Issued at
            "exp": expire  # Expires
        }

        # Add role only for access tokens
        if role and token_type == self.config.access_token_type:
            payload["role"] = role

        return jwt.encode(payload, self.config.secret_key, algorithm=self.config.algorithm)

    def verify_token(self, token: str) -> Dict[str, Any] | None:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.config.secret_key,
                algorithms=[self.config.algorithm]
            )
            return payload

        except JWTError as e:
            self.logger.warning(f"Token verification failed: {e}")
            return None

    def is_access_token(self, payload: Dict[str, Any]) -> bool:
        """Check if payload is from an access token"""
        return payload.get("type") == self.config.access_token_type

    def is_refresh_token(self, payload: Dict[str, Any]) -> bool:
        """Check if payload is from a refresh token"""
        return payload.get("type") == self.config.refresh_token_type

    def get_user_id_from_payload(self, payload: Dict[str, Any]) -> str | None:
        """Extract user ID from token payload"""
        return payload.get("sub")

    def get_username_from_payload(self, payload: Dict[str, Any]) -> str | None:
        """Extract username from token payload"""
        return payload.get("username")

    def get_role_from_payload(self, payload: Dict[str, Any]) -> str | None:
        """Extract role from token payload (access tokens only)"""
        return payload.get("role")
