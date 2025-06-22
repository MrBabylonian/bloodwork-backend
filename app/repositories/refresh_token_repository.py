"""
Refresh token repository for veterinary bloodwork analysis system.

This module provides data access operations for RefreshToken entities
using human-readable user IDs instead of ObjectIds for better usability.

Features:
- Secure token hashing for storage
- Human-readable user ID support (VET-001, TEC-001, ADM-001)
- Token validation with expiration checks
- Device and IP tracking for security
- Proper error handling and logging

Last updated: 2025-06-20
Author: Bedirhan Gilgiler
"""

import hashlib
from datetime import datetime, timezone

from app.models.database_models import RefreshToken
from app.services.database_service import DatabaseService
from app.utils.logger_utils import ApplicationLogger


class RefreshTokenRepository:
    """Repository for RefreshToken data access operations"""

    def __init__(self, database_service: DatabaseService):
        self.db_service = database_service
        self.collection = database_service.refresh_tokens
        self.logger = ApplicationLogger.get_logger(__name__)

    def _hash_token(self, token: str) -> str:
        """
        Hash a token for secure storage.

        Args:
            token (str): Raw JWT token

        Returns:
            str: SHA256 hash of the token
        """
        return hashlib.sha256(token.encode()).hexdigest()

    async def create(self, token: RefreshToken) -> RefreshToken | None:
        """Create a new refresh token record"""
        try:
            token.created_at = datetime.now(timezone.utc)

            await self.collection.insert_one(token.model_dump(by_alias=True))
            self.logger.info(
                f"Created refresh token for user: {token.user_id}")
            return token

        except Exception as e:
            self.logger.error(f"Error creating refresh token: {e}")
            return None

    async def get_by_token_id(self, token_id: str) -> RefreshToken | None:
        """Get refresh token by token_id"""
        try:
            doc = await self.collection.find_one({"_id": token_id})
            return RefreshToken(**doc) if doc else None

        except Exception as e:
            self.logger.error(f"Error getting refresh token by id: {e}")
            return None

    async def get_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        """Get refresh token by hash"""
        try:
            doc = await self.collection.find_one({"token_hash": token_hash})
            return RefreshToken(**doc) if doc else None

        except Exception as e:
            self.logger.error(f"Error getting refresh token by hash: {e}")
            return None

    async def get_by_user_id(self, user_id: str) -> list[RefreshToken]:
        """Get all refresh tokens for a user"""
        try:
            cursor = self.collection.find(
                {"user_id": user_id, "is_active": True}
            ).sort("created_at", -1)

            docs = await cursor.to_list(length=None)
            return [RefreshToken(**doc) for doc in docs]

        except Exception as e:
            self.logger.error(f"Error getting refresh tokens by user_id: {e}")
            return []

    async def invalidate(self, token_id: str) -> bool:
        """Invalidate a refresh token by setting is_active to False"""
        try:
            result = await self.collection.update_one(
                {"_id": token_id},
                {"$set": {"is_active": False}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Invalidated refresh token: {token_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error invalidating refresh token: {e}")
            return False

    async def invalidate_by_hash(self, token_hash: str) -> bool:
        """Invalidate a refresh token by hash"""
        try:
            result = await self.collection.update_one(
                {"token_hash": token_hash},
                {"$set": {"is_active": False}}
            )

            if result.modified_count > 0:
                self.logger.info("Invalidated refresh token by hash")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error invalidating refresh token by hash: {e}")
            return False

    async def invalidate_all_for_user(self, user_id: str) -> bool:
        """Invalidate all refresh tokens for a user"""
        try:
            result = await self.collection.update_many(
                {"user_id": user_id, "is_active": True},
                {"$set": {"is_active": False}}
            )

            self.logger.info(
                f"Invalidated {result.modified_count} refresh tokens for user: {user_id}")
            return True

        except Exception as e:
            self.logger.error(
                f"Error invalidating refresh tokens for user: {e}")
            return False

    async def clean_expired(self) -> int:
        """Clean up expired refresh tokens"""
        try:
            now = datetime.now(timezone.utc)
            result = await self.collection.delete_many(
                {"expires_at": {"$lt": now}}
            )

            count = result.deleted_count
            self.logger.info(f"Cleaned up {count} expired refresh tokens")
            return count

        except Exception as e:
            self.logger.error(f"Error cleaning expired refresh tokens: {e}")
            return 0
