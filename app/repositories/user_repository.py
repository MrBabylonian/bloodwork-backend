from datetime import datetime, timezone

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.models.database_models import ApprovalStatus, User, UserRole
from app.services.database_service import DatabaseService
from app.utils.logger_utils import ApplicationLogger


class UserRepository:
    """Repository for User data access operations"""

    def __init__(self, database_service: DatabaseService):
        self.db_service = database_service
        self.collection = database_service.users
        self.logger = ApplicationLogger.get_logger(__name__)

    async def create(self, user: User) -> User | None:
        """Create a new user"""
        try:
            user.created_at = datetime.now(timezone.utc)

            result = await self.collection.insert_one(user.model_dump(by_alias=True, exclude={"id"}))
            user.id = result.inserted_id

            self.logger.info(f"Created user: {user.username}")
            return user

        except DuplicateKeyError as e:
            if "username" in str(e):
                self.logger.error(f"Username already exists: {user.username}")
            elif "email" in str(e):
                self.logger.error(f"Email already exists: {user.email}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating user: {e}")
            return None

    async def get_by_id(self, user_id: str | ObjectId) -> User | None:
        """Get user by ObjectId"""
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)

            doc = await self.collection.find_one({"_id": user_id})
            return User(**doc) if doc else None

        except Exception as e:
            self.logger.error(f"Error getting user by id: {e}")
            return None

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username"""
        try:
            doc = await self.collection.find_one({"username": username})
            return User(**doc) if doc else None

        except Exception as e:
            self.logger.error(f"Error getting user by username: {e}")
            return None

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email"""
        try:
            doc = await self.collection.find_one({"email": email})
            return User(**doc) if doc else None

        except Exception as e:
            self.logger.error(f"Error getting user by email: {e}")
            return None

    async def get_pending_approvals(self) -> list[User]:
        """Get all users pending approval"""
        try:
            cursor = self.collection.find(
                {"approval_status": ApprovalStatus.PENDING}
            ).sort("created_at", 1)

            docs = await cursor.to_list(length=None)
            return [User(**doc) for doc in docs]

        except Exception as e:
            self.logger.error(f"Error getting pending approvals: {e}")
            return []

    async def get_by_role(self, role: UserRole) -> list[User]:
        """Get all users by role"""
        try:
            cursor = self.collection.find(
                {"role": role, "is_active": True,
                    "approval_status": ApprovalStatus.APPROVED}
            ).sort("created_at", -1)

            docs = await cursor.to_list(length=None)
            return [User(**doc) for doc in docs]

        except Exception as e:
            self.logger.error(f"Error getting users by role: {e}")
            return []

    async def approve_user(self, user_id: str | ObjectId, approved_by: str | ObjectId) -> bool:
        """Approve a user"""
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            if isinstance(approved_by, str):
                approved_by = ObjectId(approved_by)

            result = await self.collection.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "approval_status": ApprovalStatus.APPROVED,
                        "approved_by": approved_by,
                        "approved_at": datetime.now(timezone.utc)
                    }
                }
            )

            if result.modified_count > 0:
                self.logger.info(f"Approved user: {user_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error approving user: {e}")
            return False

    async def reject_user(self, user_id: str | ObjectId) -> bool:
        """Reject a user"""
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)

            result = await self.collection.update_one(
                {"_id": user_id},
                {"$set": {"approval_status": ApprovalStatus.REJECTED}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Rejected user: {user_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error rejecting user: {e}")
            return False

    async def update_last_login(self, user_id: str | ObjectId) -> bool:
        """Update user's last login timestamp"""
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)

            result = await self.collection.update_one(
                {"_id": user_id},
                {"$set": {"last_login": datetime.now(timezone.utc)}}
            )

            return result.modified_count > 0

        except Exception as e:
            self.logger.error(f"Error updating last login: {e}")
            return False

    async def update_profile(self, user_id: str | ObjectId, profile_data: dict) -> bool:
        """Update user profile data"""
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)

            # Update nested profile fields
            update_data = {f"profile.{key}": value for key,
                           value in profile_data.items()}

            result = await self.collection.update_one(
                {"_id": user_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                self.logger.info(f"Updated profile for user: {user_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error updating user profile: {e}")
            return False

    async def deactivate(self, user_id: str | ObjectId) -> bool:
        """Deactivate a user"""
        try:
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)

            result = await self.collection.update_one(
                {"_id": user_id},
                {"$set": {"is_active": False}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Deactivated user: {user_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error deactivating user: {e}")
            return False
