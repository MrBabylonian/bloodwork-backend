"""
Authentication router for veterinary bloodwork analysis system.

This module provides comprehensive JWT-based authentication endpoints including
user registration, login, logout, token refresh, and profile management.
All endpoints follow REST API best practices and implement proper security measures.

Features:
- User registration with admin approval workflow
- Secure JWT token-based authentication
- Automatic token refresh mechanism
- Profile management capabilities
- Role-based access control
- Device and IP tracking for security

Last updated: 2025-06-20
Author: Bedirhan Gilgiler
"""

from typing import Union

from app.auth.auth_service import AuthService
from app.dependencies.auth_dependencies import get_auth_service, require_authenticated
from app.models.database_models import Admin, ApprovalStatus, User, UserRole
from app.schemas.auth_schemas import (
    AccessTokenResponse,
    TokenRefresh,
    TokenResponse,
    UserLogin,
    UserProfile,
    UserProfileUpdate,
    UserRegistration,
)
from app.utils.logger_utils import ApplicationLogger
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer

# Initialize router and security components
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
security = HTTPBearer()
logger = ApplicationLogger.get_logger("auth_router")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegistration,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user account.

    Creates a new user account with 'pending' approval status.
    Admin approval is required before the user can log in.

    Args:
        user_data (UserRegistration): User registration details
        auth_service (AuthService): Authentication service instance

    Returns:
        dict: Registration result with user ID and approval status

    Raises:
        HTTPException: 400 if username or email already exists

    Example:
        POST /api/v1/auth/register
        {
            "username": "john_doe",
            "email": "john@example.com",
            "password": "secure_password",
            "role": "veterinarian"
        }
    """
    logger.info(f"User registration attempt: {user_data.username}")

    user = await auth_service.register_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        role=user_data.role,
        profile=user_data.profile
    )

    if not user:
        logger.warning(
            f"Registration failed: {user_data.username} - username/email exists")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )

    logger.info(
        f"User registered successfully: {user.username} (ID: {user.user_id})")

    return {
        "message": "User registered successfully. Awaiting admin approval.",
        "user_id": user.user_id,
        "approval_status": user.approval_status
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Authenticate user and return JWT tokens.

    Validates user credentials and returns access and refresh tokens
    for approved users only. Tracks device and IP information for security.

    Args:
        user_data (UserLogin): Username and password
        request (Request): HTTP request for client info extraction
        auth_service (AuthService): Authentication service instance

    Returns:
        TokenResponse: Access and refresh tokens with metadata

    Raises:
        HTTPException: 401 if credentials invalid or user not approved

    Example:
        POST /api/v1/auth/login
        {
            "username": "john_doe",
            "password": "secure_password"
        }
    """
    logger.info(f"Login attempt: {user_data.username}")

    # Extract client info for refresh token tracking
    device_info = request.headers.get("user-agent", "Unknown")
    ip_address = request.client.host if request.client else None

    logger.debug(f"Login from device: {device_info}, IP: {ip_address}")

    tokens = await auth_service.login(
        username=user_data.username,
        password=user_data.password,
        device_info=device_info,
        ip_address=ip_address
    )

    if not tokens:
        logger.warning(
            f"Login failed: {user_data.username} - invalid credentials or not approved")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or account not approved"
        )

    logger.info(f"Login successful: {user_data.username}")
    return tokens


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using valid refresh token.

    Provides seamless token renewal for continuous user sessions
    without requiring re-authentication.

    Args:
        token_data (TokenRefresh): Refresh token data  
        auth_service (AuthService): Authentication service instance

    Returns:
        AccessTokenResponse: New access token with metadata

    Raises:
        HTTPException: 401 if refresh token invalid or expired

    Example:
        POST /api/v1/auth/refresh
        {
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
        }
    """
    logger.info("Token refresh request received")

    tokens = await auth_service.refresh_access_token(token_data.refresh_token)

    if not tokens:
        logger.warning(
            "Token refresh failed - invalid or expired refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    logger.info("Token refreshed successfully")
    return tokens


@router.post("/logout")
async def logout(
    token_data: TokenRefresh,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout user by invalidating their refresh token.

    Ensures security by invalidating refresh token, requiring 
    re-authentication for future access.

    Args:
        token_data (TokenRefresh): Refresh token to invalidate
        auth_service (AuthService): Authentication service instance

    Returns:
        dict: Logout success message

    Raises:
        HTTPException: 401 if token invalid or already invalidated

    Example:
        POST /api/v1/auth/logout
        {
            "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
        }
    """
    logger.info("Logout request received")

    success = await auth_service.logout(token_data.refresh_token)

    if not success:
        logger.warning("Logout failed - invalid or already invalidated token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token or already logged out"
        )

    logger.info("User logged out successfully")
    return {"message": "Successfully logged out"}


@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: Union[Admin, User] = Depends(require_authenticated)):
    """
    Get authenticated user's profile information.

    Returns the current user's profile information including role,
    approval status, and custom profile fields.

    Args:
        current_user (User): Current authenticated user

    Returns:
        UserProfile: User profile information

    Example:
        GET /api/v1/auth/profile
        Response: {
            "id": "VET-001",
            "username": "john_doe",
            "email": "john@example.com",
            "role": "veterinarian",
            ...
        }
    """
    logger.info(f"Profile requested by {current_user.username}")

    # Extract the appropriate ID based on user type
    from app.models.database_models import Admin
    if isinstance(current_user, Admin):
        user_id = current_user.admin_id
        # Admin has fixed role
        role = UserRole.VETERINARIAN if current_user.role == "veterinarian" else UserRole.VETERINARY_TECHNICIAN
        # Admins don't have approval status, set as approved by default
        approval_status = ApprovalStatus.APPROVED
    else:  # User
        user_id = current_user.user_id
        # Ensure role is proper enum type
        role = current_user.role if isinstance(
            current_user.role, UserRole) else UserRole(current_user.role)
        # Ensure approval status is proper enum type
        status_value = getattr(
            current_user, 'approval_status', ApprovalStatus.PENDING)
        approval_status = status_value if isinstance(
            status_value, ApprovalStatus) else ApprovalStatus(status_value)

    return UserProfile(
        user_id=user_id,
        username=current_user.username,
        email=current_user.email,
        role=role,
        approval_status=approval_status,
        profile=current_user.profile,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@router.put("/profile")
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: Union[Admin, User] = Depends(require_authenticated),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Update authenticated user's profile information.

    Updates the current user's profile with the provided fields.
    Only fields included in the request are updated.

    Args:
        profile_data (UserProfileUpdate): Profile fields to update
        current_user (User): Current authenticated user
        auth_service (AuthService): Authentication service instance

    Returns:
        dict: Update success message and updated fields

    Raises:
        HTTPException: 400 if update fails

    Example:
        PUT /api/v1/auth/profile
        {
            "first_name": "John",
            "last_name": "Doe",
            "clinic_name": "Pet Care Clinic"
        }
    """
    logger.info(f"Profile update requested by {current_user.username}")

    # Extract the appropriate ID based on user type
    from app.models.database_models import Admin

    # Build profile data update dictionary
    update_data = {}
    for key, value in profile_data.dict(exclude_unset=True).items():
        if value is not None:
            update_data[key] = value

    if not update_data:
        logger.warning("Profile update failed - no valid fields to update")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )

    # Update profile based on user type
    if isinstance(current_user, Admin):
        admin_repo = auth_service.admin_repo
        success = await admin_repo.update_profile(current_user.admin_id, update_data)
    else:  # User
        user_repo = auth_service.user_repo
        success = await user_repo.update_profile(current_user.user_id, update_data)

    if not success:
        logger.error(f"Profile update failed for {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update profile"
        )

    logger.info(f"Profile updated successfully for {current_user.username}")
    return {
        "message": "Profile updated successfully",
        "updated_fields": list(update_data.keys())
    }


@router.get("/health")
async def health_check():
    """
    Health check endpoint for authentication router.

    Returns a simple status message to verify that the auth router is operational.
    Useful for monitoring and automated health checks.

    Returns:
        dict: Service status message
    """
    return {"status": "Auth router operational"}
