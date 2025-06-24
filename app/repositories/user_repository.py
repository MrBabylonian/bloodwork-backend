"""
User repository for veterinary bloodwork analysis system.

This module provides data access operations for User entities including
CRUD operations, authentication support, and profile management.
It handles MongoDB operations with human-readable IDs (VET-001, TEC-001).

Features:
- User creation with human-readable ID generation
- Authentication and approval status management
- Profile updates and search operations with string IDs
- Proper error handling and logging
- Sequential ID generation with role-based prefixes

Last updated: 2025-06-20
Author: Bedirhan Gilgiler
"""

from datetime import datetime, timezone
from typing import List, Optional

from app.models.database_models import ApprovalStatus, User, UserRole
from app.services.database_service import DatabaseService
from app.utils.logger_utils import ApplicationLogger
from pymongo.errors import DuplicateKeyError


class UserRepository:
    """
    Repository class for User data access operations.

    This repository provides comprehensive CRUD operations for User entities
    including authentication support, profile management, and approval workflows.
    """

    def __init__(self, database_service: DatabaseService):
        """
        Initialize user repository with database service.

        Args:
            database_service (DatabaseService): Database service instance
        """
        self.db_service = database_service
        self.collection = database_service.users
        self.logger = ApplicationLogger.get_logger(__name__)

    async def _generate_user_id(self, role: UserRole) -> str:
        """
        Generate a sequential human-readable user ID based on role.

        Args:
            role: User role (VETERINARIAN or VETERINARY_TECHNICIAN)

        Returns:
            Generated user ID (VET-001, TEC-001, etc.)
        """
        prefix = "VET" if role == UserRole.VETERINARIAN else "TEC"
        counter_id = f"{role.value}_seq"

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
        return f"{prefix}-{sequence_number:03d}"

    async def create(self, user: User) -> User | None:
        """
        Create a new user in the database with human-readable ID generation.

        Args:
            user (User): User object to create

        Returns:
            User | None: Created user with assigned ID, or None if creation fails

        Note:
            Automatically generates human-readable ID and sets created_at timestamp
        """
        try:
            # Generate human-readable user ID
            if not user.user_id:
                user.user_id = await self._generate_user_id(user.role)

            user.created_at = datetime.now(timezone.utc)

            await self.collection.insert_one(user.model_dump(by_alias=True))

            self.logger.info(f"User created: {user.username} ({user.user_id})")
            return user

        except DuplicateKeyError as e:
            if "username" in str(e):
                self.logger.warning(f"Username exists: {user.username}")
            elif "email" in str(e):
                self.logger.warning(f"Email exists: {user.email}")
            return None
        except Exception as e:
            self.logger.error(f"User creation failed: {e}")
            return None

    async def get_by_id(self, user_id: str) -> User | None:
        """
        Retrieve user by human-readable ID.

        Args:
            user_id (str): User ID to search for (e.g., VET-001, TEC-001)

        Returns:
            User | None: User object if found, None otherwise
        """
        try:
            doc = await self.collection.find_one({"_id": user_id})
            return User(**doc) if doc else None

        except Exception as e:
            self.logger.error(f"Error retrieving user by ID: {e}")
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

    async def get_all(self) -> List[User]:
        """Get all users"""
        try:
            cursor = self.collection.find({}).sort("created_at", -1)
            docs = await cursor.to_list(length=None)
            return [User(**doc) for doc in docs]
        except Exception as e:
            self.logger.error(f"Error getting all users: {e}")
            return []

    async def get_by_role(self, role: UserRole) -> List[User]:
        """Get users by role"""
        try:
            cursor = self.collection.find(
                {"role": role}).sort("created_at", -1)
            docs = await cursor.to_list(length=None)
            return [User(**doc) for doc in docs]
        except Exception as e:
            self.logger.error(f"Error getting users by role: {e}")
            return []

    async def get_by_approval_status(self, status: ApprovalStatus) -> List[User]:
        """Get users by approval status"""
        try:
            cursor = self.collection.find(
                {"approval_status": status}).sort("created_at", -1)
            docs = await cursor.to_list(length=None)
            return [User(**doc) for doc in docs]
        except Exception as e:
            self.logger.error(f"Error getting users by approval status: {e}")
            return []

    async def update_profile(self, user_id: str, profile_data: dict) -> bool:
        """
        Update user profile with human-readable ID.

        Args:
            user_id: User ID (e.g., VET-001)
            profile_data: Profile data to update
        """
        try:
            # Extract email if present
            email = None
            if 'email' in profile_data:
                email = profile_data.pop('email')

            # Prepare update data
            update_data = {}

            # Add profile fields if any remain
            if profile_data:
                update_data["profile"] = profile_data

            # Add email if present
            if email:
                update_data["email"] = email

            # Only update if we have data to update
            if not update_data:
                return False

            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                self.logger.info(f"Updated profile for user: {user_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error updating user profile: {e}")
            return False

    async def update_password(self, user_id: str, hashed_password: str) -> bool:
        """Update user password"""
        try:
            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": {"hashed_password": hashed_password}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Updated password for user: {user_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error updating user password: {e}")
            return False

    async def update_last_login(self, user_id: str) -> bool:
        """
        Update last login timestamp with human-readable ID.

        Args:
            user_id: User ID (e.g., VET-001)
        """
        try:
            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": {"last_login": datetime.now(timezone.utc)}}
            )

            return result.modified_count > 0

        except Exception as e:
            self.logger.error(f"Error updating last login: {e}")
            return False

    async def update_approval_status(
        self,
        user_id: str,
        status: ApprovalStatus,
        approved_by: Optional[str] = None
    ) -> bool:
        """Update user approval status"""
        try:
            update_data = {}
            update_data["approval_status"] = status

            if status == ApprovalStatus.APPROVED and approved_by is not None:
                update_data["approved_by"] = approved_by
                update_data["approved_at"] = datetime.now(timezone.utc)

            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                self.logger.info(
                    f"Updated approval status for user: {user_id} to {status}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error updating approval status: {e}")
            return False

    async def deactivate(self, user_id: str) -> bool:
        """
        Deactivate a user with human-readable ID.

        Args:
            user_id: User ID to deactivate (e.g., VET-001)
        """
        try:
            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": {"is_active": False}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Deactivated user: {user_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error deactivating user: {e}")
            return False

    async def reactivate(self, user_id: str) -> bool:
        """Reactivate a user account"""
        try:
            result = await self.collection.update_one(
                {"user_id": user_id},
                {"$set": {"is_active": True}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Reactivated user: {user_id}")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error reactivating user: {e}")
            return False
