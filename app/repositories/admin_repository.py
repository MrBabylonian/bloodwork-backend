from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.models.database_models import Admin
from app.services.database_service import DatabaseService
from app.utils.logger_utils import ApplicationLogger


class AdminRepository:
    """Repository for Admin data access operations"""

    def __init__(self, database_service: DatabaseService):
        self.db_service = database_service
        self.collection = database_service.admins
        self.logger = ApplicationLogger.get_logger(__name__)

    async def create(self, admin: Admin) -> Admin | None:
        """Create a new admin"""
        try:
            admin.created_at = datetime.now(timezone.utc)

            result = await self.collection.insert_one(admin.model_dump(by_alias=True, exclude={"id"}))
            admin.id = result.inserted_id

            self.logger.info(f"Created admin: {admin.username}")
            return admin

        except DuplicateKeyError as e:
            if "username" in str(e):
                self.logger.error(
                    f"Admin username already exists: {admin.username}")
            elif "email" in str(e):
                self.logger.error(f"Admin email already exists: {admin.email}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating admin: {e}")
            return None

    async def get_by_id(self, admin_id: str | ObjectId) -> Admin | None:
        """Get admin by ObjectId"""
        try:
            if isinstance(admin_id, str):
                admin_id = ObjectId(admin_id)

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

    async def get_all_active(self) -> list[Admin]:
        """Get all active admins"""
        try:
            cursor = self.collection.find(
                {"is_active": True}).sort("created_at", -1)
            docs = await cursor.to_list(length=None)
            return [Admin(**doc) for doc in docs]

        except Exception as e:
            self.logger.error(f"Error getting all active admins: {e}")
            return []

    async def update_last_login(self, admin_id: str | ObjectId) -> bool:
        """Update admin's last login timestamp"""
        try:
            if isinstance(admin_id, str):
                admin_id = ObjectId(admin_id)

            result = await self.collection.update_one(
                {"_id": admin_id},
                {"$set": {"last_login": datetime.now(timezone.utc)}}
            )

            return result.modified_count > 0

        except Exception as e:
            self.logger.error(f"Error updating admin last login: {e}")
            return False

    async def update_profile(self, admin_id: str | ObjectId, profile_data: dict) -> bool:
        """Update admin profile data"""
        try:
            if isinstance(admin_id, str):
                admin_id = ObjectId(admin_id)

            # Update nested profile fields
            update_data = {f"profile.{key}": value for key,
                           value in profile_data.items()}

            result = await self.collection.update_one(
                {"_id": admin_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                self.logger.info(f"Updated profile for admin: {admin_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error updating admin profile: {e}")
            return False

    async def update_permissions(self, admin_id: str | ObjectId, permissions: list[str]) -> bool:
        """Update admin permissions"""
        try:
            if isinstance(admin_id, str):
                admin_id = ObjectId(admin_id)

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

    async def deactivate(self, admin_id: str | ObjectId) -> bool:
        """Deactivate an admin"""
        try:
            if isinstance(admin_id, str):
                admin_id = ObjectId(admin_id)

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

    async def has_permission(self, admin_id: str | ObjectId, permission: str) -> bool:
        """Check if admin has a specific permission"""
        try:
            if isinstance(admin_id, str):
                admin_id = ObjectId(admin_id)

            doc = await self.collection.find_one(
                {"_id": admin_id, "permissions": permission, "is_active": True}
            )

            return doc is not None

        except Exception as e:
            self.logger.error(f"Error checking admin permissions: {e}")
            return False
