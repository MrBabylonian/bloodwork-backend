"""
Admin repository for veterinary bloodwork analysis system.

This module provides data access operations for Admin entities including
CRUD operations, authentication support, and profile management with
human-readable IDs (ADM-001, ADM-002, etc.).

Features:
- Admin creation with human-readable ID generation
- Authentication support with string IDs
- Profile updates and search operations
- Proper error handling and logging
- Sequential ID generation with ADM prefix

Last updated: 2025-06-20
Author: Bedirhan Gilgiler
"""

from datetime import datetime, timezone

from app.models.database_models import Admin
from app.services.database_service import DatabaseService
from app.utils.logger_utils import ApplicationLogger
from pymongo.errors import DuplicateKeyError


class AdminRepository:
    """Repository for Admin data access operations"""

    def __init__(self, database_service: DatabaseService):
        self.db_service = database_service
        self.collection = database_service.admins
        self.logger = ApplicationLogger.get_logger(__name__)

    async def _generate_admin_id(self) -> str:
        """
        Generate a sequential human-readable admin ID.

        Returns:
            Generated admin ID (ADM-001, ADM-002, etc.)
        """
        counter_id = "admin_seq"

        # Get or create sequence counter
        counter = await self.db_service.counters.find_one_and_update(
            {"_id": counter_id},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=True
        )

        if not counter:
            # Fallback for first time
            counter = {"seq": 1}

        sequence_number = counter["seq"]
        return f"ADM-{sequence_number:03d}"

    async def create(self, admin: Admin) -> Admin | None:
        """Create a new admin account"""
        try:
            admin.created_at = datetime.now(timezone.utc)

            await self.collection.insert_one(admin.model_dump(by_alias=True))
            self.logger.info(f"Created admin: {admin.username}")
            return admin

        except DuplicateKeyError:
            self.logger.error(
                f"Admin with username or email already exists: {admin.username}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating admin: {e}")
            return None

    async def get_by_id(self, admin_id: str) -> Admin | None:
        """Get admin by admin_id"""
        try:
            doc = await self.collection.find_one({"_id": admin_id})
            return Admin(**doc) if doc else None
        except Exception as e:
            self.logger.error(f"Error getting admin by id: {e}")
            return None

    async def get_by_username(self, username: str) -> Admin | None:
        """Get admin by username"""
        try:
            doc = await self.collection.find_one({"username": username})
            return Admin(**doc) if doc else None
        except Exception as e:
            self.logger.error(f"Error getting admin by username: {e}")
            return None

    async def get_by_email(self, email: str) -> Admin | None:
        """Get admin by email"""
        try:
            doc = await self.collection.find_one({"email": email})
            return Admin(**doc) if doc else None
        except Exception as e:
            self.logger.error(f"Error getting admin by email: {e}")
            return None

    async def get_all(self) -> list[Admin]:
        """Get all admins"""
        try:
            cursor = self.collection.find({}).sort("created_at", -1)
            docs = await cursor.to_list(length=None)
            return [Admin(**doc) for doc in docs]
        except Exception as e:
            self.logger.error(f"Error getting all admins: {e}")
            return []

    async def update_profile(self, admin_id: str, profile_data: dict) -> bool:
        """Update admin profile fields"""
        try:
            # Extract email if present
            email = None
            if 'email' in profile_data:
                email = profile_data.pop('email')

            # Prepare update data
            update_data = {}

            # Add profile fields if any remain
            if profile_data:
                # Update individual profile fields instead of replacing the whole profile
                profile_updates = {
                    f"profile.{key}": value for key, value in profile_data.items()}
                update_data.update(profile_updates)

            # Add email if present
            if email:
                update_data["email"] = email

            # Only update if we have data to update
            if not update_data:
                return False

            self.logger.info(
                f"Updating profile for admin: {admin_id} with data: {update_data}")

            result = await self.collection.update_one(
                {"_id": admin_id},
                {"$set": update_data}
            )

            if result.matched_count > 0:
                self.logger.info(f"Updated profile for admin: {admin_id}")
                return True
            else:
                self.logger.warning(
                    f"Admin not found for profile update: {admin_id}")
                return False
        except Exception as e:
            self.logger.error(f"Error updating admin profile: {e}")
            return False

    async def update_password(self, admin_id: str, hashed_password: str) -> bool:
        """Update admin password"""
        try:
            self.logger.info(f"Updating password for admin: {admin_id}")

            result = await self.collection.update_one(
                {"_id": admin_id},
                {"$set": {"hashed_password": hashed_password}}
            )

            if result.matched_count > 0:
                self.logger.info(f"Updated password for admin: {admin_id}")
                return True
            else:
                self.logger.warning(
                    f"Admin not found for password update: {admin_id}")
                return False
        except Exception as e:
            self.logger.error(f"Error updating admin password: {e}")
            return False

    async def update_last_login(self, admin_id: str) -> bool:
        """Update admin's last login timestamp"""
        try:
            result = await self.collection.update_one(
                {"_id": admin_id},
                {"$set": {"last_login": datetime.now(timezone.utc)}}
            )

            if result.modified_count > 0:
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error updating last login: {e}")
            return False

    async def update_permissions(self, admin_id: str, permissions: list[str]) -> bool:
        """Update admin permissions"""
        try:
            result = await self.collection.update_one(
                {"_id": admin_id},
                {"$set": {"permissions": permissions}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Updated permissions for admin: {admin_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error updating admin permissions: {e}")
            return False

    async def deactivate(self, admin_id: str) -> bool:
        """Deactivate an admin account"""
        try:
            result = await self.collection.update_one(
                {"_id": admin_id},
                {"$set": {"is_active": False}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Deactivated admin: {admin_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error deactivating admin: {e}")
            return False

    async def reactivate(self, admin_id: str) -> bool:
        """Reactivate an admin account"""
        try:
            result = await self.collection.update_one(
                {"_id": admin_id},
                {"$set": {"is_active": True}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Reactivated admin: {admin_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error reactivating admin: {e}")
            return False

    async def has_permission(self, admin_id: str, permission: str) -> bool:
        """Check if admin has a specific permission"""
        try:
            admin = await self.get_by_id(admin_id)
            if not admin:
                return False

            return permission in admin.permissions
        except Exception as e:
            self.logger.error(f"Error checking admin permission: {e}")
            return False
