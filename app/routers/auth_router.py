"""
Authentication router providing JWT-based authentication endpoints.

This module implements user registration, login, logout, and token refresh
endpoints following FastAPI best practices and the Zen of Python.
"""

from typing import Union

from app.auth.auth_service import AuthService
from app.dependencies.auth_dependencies import get_auth_service, require_authenticated
from app.models.database_models import Admin, User
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

# Create router
router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
security = HTTPBearer()
logger = ApplicationLogger.get_logger(__name__)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegistration,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Register a new user (pending admin approval).

    Users are created with 'pending' approval status - this is expected behavior.
    """
    user = await auth_service.register_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        role=user_data.role,
        profile=user_data.profile
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )

    return {
        "message": "User registered successfully. Awaiting admin approval.",
        "user_id": str(user.id),
        "approval_status": user.approval_status
    }


@router.post("/login", response_model=TokenResponse)
async def login(
    user_data: UserLogin,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Login user and return JWT tokens.

    Returns access and refresh tokens for approved users only.
    """
    # Extract client info for refresh token tracking
    device_info = request.headers.get("user-agent", "Unknown")
    ip_address = request.client.host if request.client else None

    tokens = await auth_service.login(
        username=user_data.username,
        password=user_data.password,
        device_info=device_info,
        ip_address=ip_address
    )

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials or account not approved"
        )

    return tokens


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_token(
    token_data: TokenRefresh,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Refresh access token using refresh token.

    Provides seamless token renewal for continuous user sessions.
    """
    tokens = await auth_service.refresh_access_token(token_data.refresh_token)

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    return tokens


@router.post("/logout")
async def logout(
    token_data: TokenRefresh,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Logout user by revoking refresh token.

    Invalidates the refresh token to prevent further access.
    """
    success = await auth_service.logout(token_data.refresh_token)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to logout"
        )

    return {"message": "Logged out successfully"}


@router.get("/profile", response_model=UserProfile)
async def get_profile(current_user: Union[Admin, User] = Depends(require_authenticated)):
    """
    Get current user profile.

    Protected route - requires valid JWT token.
    """
    # The auth dependency already validates the token and user status
    return {
        "id": str(current_user.id),
        "username": current_user.username,
        "role": current_user.role
    }


@router.put("/profile")
async def update_profile(
    profile_data: UserProfileUpdate,
    current_user: Union[Admin, User] = Depends(require_authenticated),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Update user profile.

    Protected route - users can update their own profile.
    """
    # Get repository through auth service
    user_repo = auth_service.user_repo

    # Convert profile data to dict, excluding None values
    update_data = {k: v for k, v in profile_data.model_dump().items()
                   if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data provided for update"
        )

    if not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required"
        )

    # Handle Admin and User profile updates differently
    if isinstance(current_user, Admin):
        # Use admin repository for admin users
        admin_repo = auth_service.admin_repo
        success = await admin_repo.update_profile(current_user.id, update_data)
    else:
        # Use user repository for regular users
        user_repo = auth_service.user_repo
        success = await user_repo.update_profile(current_user.id, update_data)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update profile"
        )

    return {"message": "Profile updated successfully"}


@router.get("/health")
async def health_check():
    """Health check endpoint for auth service."""
    return {"status": "healthy", "service": "authentication"}
