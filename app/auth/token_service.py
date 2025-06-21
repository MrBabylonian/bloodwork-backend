"""
JWT token service for veterinary bloodwork analysis system.

This module provides JWT token creation and validation for authentication
using human-readable user IDs instead of ObjectIds.

Features:
- Access and refresh token generation
- Token validation and payload extraction
- Human-readable ID support (VET-001, TEC-001, ADM-001)
- Secure token encoding with configurable algorithms

Last updated: 2025-06-20
Author: Bedirhan Gilgiler
"""

from datetime import datetime, timezone
from typing import Any, Dict

from app.auth.auth_config import AuthConfig
from app.utils.logger_utils import ApplicationLogger
from jose import JWTError, jwt


class TokenService:
    """
    JWT token creation and validation service.

    Handles token operations for both users and admins using human-readable IDs
    like VET-001, TEC-001, ADM-001 instead of MongoDB ObjectIds.
    """

    def __init__(self, config: AuthConfig):
        """
        Initialize token service with authentication configuration.

        Args:
            config (AuthConfig): Authentication configuration object
        """
        self.config = config
        self.logger = ApplicationLogger.get_logger("token_service")

    def create_access_token(self, user_id: str, username: str, role: str) -> str:
        """
        Create a short-lived access token.

        Args:
            user_id (str): Human-readable user ID (VET-001, TEC-001, ADM-001)
            username (str): Username for login
            role (str): User role for authorization

        Returns:
            str: Encoded JWT access token
        """
        return self._create_token(
            user_id=user_id,
            username=username,
            role=role,
            token_type=self.config.access_token_type,
            expires_delta=self.config.access_token_expire_time
        )

    def create_refresh_token(self, user_id: str, username: str) -> str:
        """
        Create a long-lived refresh token.

        Args:
            user_id (str): Human-readable user ID (VET-001, TEC-001, ADM-001)
            username (str): Username for login

        Returns:
            str: Encoded JWT refresh token
        """
        return self._create_token(
            user_id=user_id,
            username=username,
            role=None,  # Refresh tokens don't need role info
            token_type=self.config.refresh_token_type,
            expires_delta=self.config.refresh_token_expire_time
        )

    def _create_token(self, user_id: str, username: str, role: str | None,
                      token_type: str, expires_delta) -> str:
        """
        Create a JWT token with given parameters.

        Args:
            user_id (str): Human-readable user ID
            username (str): Username
            role (str | None): User role (only for access tokens)
            token_type (str): Type of token (access/refresh)
            expires_delta: Token expiration time delta

        Returns:
            str: Encoded JWT token
        """
        now = datetime.now(timezone.utc)
        expire = now + expires_delta

        payload = {
            "sub": user_id,  # Subject (human-readable user ID)
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
        """
        Verify and decode a JWT token.

        Args:
            token (str): JWT token to verify

        Returns:
            Dict[str, Any] | None: Token payload if valid, None otherwise
        """
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
        """
        Check if payload is from an access token.

        Args:
            payload (Dict[str, Any]): Token payload

        Returns:
            bool: True if access token, False otherwise
        """
        return payload.get("type") == self.config.access_token_type

    def is_refresh_token(self, payload: Dict[str, Any]) -> bool:
        """
        Check if payload is from a refresh token.

        Args:
            payload (Dict[str, Any]): Token payload

        Returns:
            bool: True if refresh token, False otherwise
        """
        return payload.get("type") == self.config.refresh_token_type

    def get_user_id_from_payload(self, payload: Dict[str, Any]) -> str | None:
        """
        Extract human-readable user ID from token payload.

        Args:
            payload (Dict[str, Any]): Token payload

        Returns:
            str | None: User ID (VET-001, TEC-001, ADM-001) if found
        """
        return payload.get("sub")

    def get_username_from_payload(self, payload: Dict[str, Any]) -> str | None:
        """
        Extract username from token payload.

        Args:
            payload (Dict[str, Any]): Token payload

        Returns:
            str | None: Username if found
        """
        return payload.get("username")

    def get_role_from_payload(self, payload: Dict[str, Any]) -> str | None:
        """
        Extract role from token payload (access tokens only).

        Args:
            payload (Dict[str, Any]): Token payload

        Returns:
            str | None: User role if found (access tokens only)
        """
        return payload.get("role")
