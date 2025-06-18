import hashlib
from datetime import datetime, timezone

from bson import ObjectId

from app.models.database_models import RefreshToken
from app.services.database_service import DatabaseService
from app.utils.logger_utils import ApplicationLogger


class RefreshTokenRepository:
    """Repository for RefreshToken data access operations"""

    def __init__(self, database_service: DatabaseService):
        self.db_service = database_service
        self.collection = database_service.get_collection("refresh_tokens")
        self.logger = ApplicationLogger.get_logger(__name__)

    def _hash_token(self, token: str) -> str:
        """Hash a token for secure storage"""
        return hashlib.sha256(token.encode()).hexdigest()

    async def create(self, user_id: str | ObjectId, token: str,
                     expires_at: datetime, device_info: str | None = None,
                     ip_address: str | None = None) -> RefreshToken | None:
        """Create a new refresh token record"""
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)

            refresh_token = RefreshToken(
                user_id=user_id,
                token_hash=self._hash_token(token),
                expires_at=expires_at,
                device_info=device_info,
                ip_address=ip_address
            )

            result = await self.collection.insert_one(
                refresh_token.model_dump(by_alias=True, exclude={"id"})
            )
            refresh_token.id = result.inserted_id

            self.logger.info(f"Created refresh token for user: {user_id}")
            return refresh_token

        except Exception as e:
            self.logger.error(f"Error creating refresh token: {e}")
            return None

    async def is_valid(self, token: str) -> bool:
        """Check if a refresh token is valid and active"""
        try:
            token_hash = self._hash_token(token)
            doc = await self.collection.find_one({
                "token_hash": token_hash,
                "is_active": True,
                "expires_at": {"$gt": datetime.now(timezone.utc)}
            })
            return doc is not None

        except Exception as e:
            self.logger.error(f"Error validating refresh token: {e}")
            return False

    async def get_by_token(self, token: str) -> RefreshToken | None:
        """Get refresh token record by token value"""
        try:
            token_hash = self._hash_token(token)
            doc = await self.collection.find_one({"token_hash": token_hash})
            return RefreshToken(**doc) if doc else None

        except Exception as e:
            self.logger.error(f"Error getting refresh token: {e}")
            return None

    async def revoke_token(self, token: str) -> bool:
        """Revoke a specific refresh token"""
        try:
            token_hash = self._hash_token(token)
            result = await self.collection.update_one(
                {"token_hash": token_hash},
                {"$set": {"is_active": False}}
            )

            if result.modified_count > 0:
                self.logger.info("Refresh token revoked")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error revoking refresh token: {e}")
            return False

    async def revoke_all_user_tokens(self, user_id: str | ObjectId) -> bool:
        """Revoke all refresh tokens for a user"""
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)

            result = await self.collection.update_many(
                {"user_id": user_id, "is_active": True},
                {"$set": {"is_active": False}}
            )

            self.logger.info(
                f"Revoked {result.modified_count} tokens for user: {user_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error revoking user tokens: {e}")
            return False

    async def cleanup_expired_tokens(self) -> int:
        """Remove expired refresh tokens from database"""
        try:
            result = await self.collection.delete_many({
                "expires_at": {"$lt": datetime.now(timezone.utc)}
            })

            if result.deleted_count > 0:
                self.logger.info(
                    f"Cleaned up {result.deleted_count} expired tokens")

            return result.deleted_count

        except Exception as e:
            self.logger.error(f"Error cleaning up expired tokens: {e}")
            return 0
