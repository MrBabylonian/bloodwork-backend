"""
Authentication schemas for veterinary bloodwork analysis system.

This module defines Pydantic schemas for authentication-related API operations
including user registration, login, token management, and profile updates.
All schemas include proper validation and documentation.

Features:
- User registration and login validation
- JWT token response schemas
- Profile management schemas
- Email validation with EmailStr
- Comprehensive field documentation

Last updated: 2025-06-20
Author: Bedirhan Gilgiler
"""

from datetime import datetime

from app.models.database_models import ApprovalStatus, UserRole
from pydantic import BaseModel, EmailStr


class UserRegistration(BaseModel):
    """
    Schema for user registration requests.

    Used when new users sign up for the system. All users start with
    'pending' approval status requiring admin approval.
    """
    username: str
    email: EmailStr
    password: str
    role: UserRole
    profile: dict = {}


class UserLogin(BaseModel):
    """
    Schema for user login requests.

    Accepts username and password for authentication.
    """
    username: str
    password: str


class TokenResponse(BaseModel):
    """
    Schema for JWT token responses.

    Returned after successful login containing both access and refresh tokens.
    """
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


class TokenRefresh(BaseModel):
    """Token refresh request"""
    refresh_token: str


class AccessTokenResponse(BaseModel):
    """Access token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# User Schemas
class UserProfile(BaseModel):
    """User profile response"""
    user_id: str
    username: str
    email: str
    role: UserRole
    approval_status: ApprovalStatus
    profile: dict
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None

    class Config:
        orm_mode = True


class UserProfileUpdate(BaseModel):
    """User profile update request"""
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    license_number: str | None = None
    clinic_name: str | None = None
    phone: str | None = None


class UserResponse(BaseModel):
    """User response"""
    user_id: str
    username: str
    email: str
    role: UserRole
    approval_status: ApprovalStatus
    profile: dict
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None

    class Config:
        orm_mode = True


class AdminResponse(BaseModel):
    """Admin response"""
    admin_id: str
    username: str
    email: str
    role: str
    permissions: list[str]
    profile: dict
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None

    class Config:
        orm_mode = True


class UserApproval(BaseModel):
    """User approval request"""
    user_id: str
    approved: bool  # True for approve, False for reject
