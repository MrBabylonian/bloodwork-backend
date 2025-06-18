from datetime import datetime, timezone

from app.auth.auth_config import AuthConfig
from app.auth.password_service import PasswordService
from app.auth.token_service import TokenService
from app.models.database_models import ApprovalStatus, User, UserRole
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.repositories.user_repository import UserRepository
from app.utils.logger_utils import ApplicationLogger


class AuthService:
    """Main authentication service"""

    def __init__(self, user_repo: UserRepository, refresh_token_repo: RefreshTokenRepository,
                 config: AuthConfig | None = None):
        self.user_repo = user_repo
        self.refresh_token_repo = refresh_token_repo
        self.config = config or AuthConfig()
        self.password_service = PasswordService()
        self.token_service = TokenService(self.config)
        self.logger = ApplicationLogger.get_logger(__name__)

    async def register_user(self, username: str, email: str, password: str,
                            role: UserRole, profile: dict | None = None) -> User | None:
        """Register a new user (pending approval)"""
        try:
            # Validate password
            if not self.password_service.is_valid_password(password, self.config.password_min_length):
                self.logger.warning(f"Invalid password for user: {username}")
                return None

            # Create user with hashed password
            user = User(
                username=username,
                email=email,
                hashed_password=self.password_service.hash_password(password),
                role=role,
                profile=profile or {}
            )

            created_user = await self.user_repo.create(user)
            if created_user:
                self.logger.info(f"User registered successfully: {username}")

            return created_user

        except Exception as e:
            self.logger.error(f"Error registering user: {e}")
            return None

    async def login(self, username: str, password: str,
                    device_info: str | None = None, ip_address: str | None = None) -> dict | None:
        """Authenticate user and return tokens"""
        try:
            # Get user by username
            user = await self.user_repo.get_by_username(username)
            if not user:
                self.logger.warning(
                    f"Login attempt with non-existent username: {username}")
                return None

            # Check if user is approved and active
            if user.approval_status != ApprovalStatus.APPROVED:
                self.logger.warning(
                    f"Login attempt by unapproved user: {username}")
                return None

            if not user.is_active:
                self.logger.warning(
                    f"Login attempt by inactive user: {username}")
                return None

            # Verify password
            if not self.password_service.verify_password(password, user.hashed_password):
                self.logger.warning(f"Invalid password for user: {username}")
                return None

            # Ensure user has an ID
            if not user.id:
                self.logger.error(f"User {username} has no ID")
                return None

            # Create tokens
            access_token = self.token_service.create_access_token(
                user_id=user.id,
                username=user.username,
                role=user.role
            )

            refresh_token = self.token_service.create_refresh_token(
                user_id=user.id,
                username=user.username
            )

            # Store refresh token
            refresh_expires_at = datetime.now(
                timezone.utc) + self.config.refresh_token_expire_time
            await self.refresh_token_repo.create(
                user_id=user.id,
                token=refresh_token,
                expires_at=refresh_expires_at,
                device_info=device_info,
                ip_address=ip_address
            )

            # Update last login
            await self.user_repo.update_last_login(user.id)

            self.logger.info(f"User logged in successfully: {username}")

            return {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": self.config.access_token_expire_minutes * 60,
                "user": {
                    "id": str(user.id),
                    "username": user.username,
                    "role": user.role,
                    "profile": user.profile
                }
            }

        except Exception as e:
            self.logger.error(f"Error during login: {e}")
            return None

    async def refresh_access_token(self, refresh_token: str) -> dict | None:
        """Create new access token using refresh token"""
        try:
            # Verify refresh token
            payload = self.token_service.verify_token(refresh_token)
            if not payload or not self.token_service.is_refresh_token(payload):
                self.logger.warning("Invalid refresh token provided")
                return None

            # Check if refresh token exists and is valid
            if not await self.refresh_token_repo.is_valid(refresh_token):
                self.logger.warning("Refresh token not found or expired")
                return None

            # Get user
            user_id = self.token_service.get_user_id_from_payload(payload)
            if not user_id:
                self.logger.warning("No user ID in refresh token payload")
                return None

            user = await self.user_repo.get_by_id(user_id)
            if not user or not user.is_active or user.approval_status != ApprovalStatus.APPROVED:
                self.logger.warning(
                    f"Refresh token used by inactive/unapproved user: {user_id}")
                return None

            if not user.id:
                self.logger.error(f"User {user_id} has no ID")
                return None

            # Create new access token
            access_token = self.token_service.create_access_token(
                user_id=user.id,
                username=user.username,
                role=user.role
            )

            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": self.config.access_token_expire_minutes * 60
            }

        except Exception as e:
            self.logger.error(f"Error refreshing access token: {e}")
            return None

    async def logout(self, refresh_token: str) -> bool:
        """Logout user by revoking refresh token"""
        try:
            success = await self.refresh_token_repo.revoke_token(refresh_token)
            if success:
                self.logger.info("User logged out successfully")
            return success

        except Exception as e:
            self.logger.error(f"Error during logout: {e}")
            return False

    async def logout_all_devices(self, user_id: str) -> bool:
        """Logout user from all devices"""
        try:
            success = await self.refresh_token_repo.revoke_all_user_tokens(user_id)
            if success:
                self.logger.info(
                    f"User logged out from all devices: {user_id}")
            return success

        except Exception as e:
            self.logger.error(f"Error logging out all devices: {e}")
            return False

    async def verify_access_token(self, token: str) -> dict | None:
        """Verify access token and return user info"""
        try:
            payload = self.token_service.verify_token(token)
            if not payload or not self.token_service.is_access_token(payload):
                return None

            # Get user to ensure they're still active
            user_id = self.token_service.get_user_id_from_payload(payload)
            if not user_id:
                return None

            user = await self.user_repo.get_by_id(user_id)
            if not user or not user.is_active or user.approval_status != ApprovalStatus.APPROVED:
                return None

            return {
                "user_id": user_id,
                "username": self.token_service.get_username_from_payload(payload),
                "role": self.token_service.get_role_from_payload(payload)
            }

        except Exception as e:
            self.logger.error(f"Error verifying access token: {e}")
            return None
