from datetime import datetime
from pydantic import BaseModel, EmailStr

from app.models.database_models import UserRole, ApprovalStatus


# Authentication Schemas
class UserRegistration(BaseModel):
    """User registration request"""
    username: str
    email: EmailStr
    password: str
    role: UserRole
    profile: dict = {}


class UserLogin(BaseModel):
    """User login request"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response"""
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
    id: str
    username: str
    email: str
    role: UserRole
    approval_status: ApprovalStatus
    profile: dict
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None


class UserProfileUpdate(BaseModel):
    """User profile update request"""
    first_name: str | None = None
    last_name: str | None = None
    license_number: str | None = None
    clinic_name: str | None = None
    phone: str | None = None


class UserResponse(BaseModel):
    """User response"""
    id: str
    username: str
    email: str
    role: UserRole
    approval_status: ApprovalStatus
    profile: dict
    is_active: bool
    created_at: datetime
    last_login: datetime | None = None


class UserApproval(BaseModel):
    """User approval request"""
    user_id: str
    approved: bool  # True for approve, False for reject
