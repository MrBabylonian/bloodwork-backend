from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from bson import ObjectId
from pydantic import BaseModel, BeforeValidator, Field


def validate_object_id(v):
    """Validate and convert to ObjectId"""
    if isinstance(v, ObjectId):
        return v
    if isinstance(v, str) and ObjectId.is_valid(v):
        return ObjectId(v)
    raise ValueError("Invalid ObjectId")


# Use Annotated for Pydantic v2 compatibility
PyObjectId = Annotated[ObjectId, BeforeValidator(validate_object_id)]


class Patient(BaseModel):
    id: PyObjectId | None = Field(default_factory=ObjectId, alias="_id")
    patient_id: str  # Human readable ID like "Pat-2024-001"
    name: str
    species: str
    breed: str
    age: dict[str, int]  # {"years": 12, "months": 3}
    sex: str
    weight: float | None = None
    owner_info: dict[str, str]
    medical_history: dict[str, any] = {}  # type: ignore

    # Extended references - key diagnostic info for fast queries
    diagnostic_summary: dict[str, any] = {}  # type: ignore

    # Metadata
    created_by: PyObjectId
    assigned_to: PyObjectId
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AiDiagnostic(BaseModel):
    id: PyObjectId | None = Field(default_factory=ObjectId, alias="_id")
    patient_id: PyObjectId  # Reference to Patient
    sequence_number: int  # Order of tests for this patient (1, 2, 3...)
    test_date: datetime

    # Full OpenAI Analysis
    openai_analysis: dict[str, any]  # type: ignore

    # PDF metadata
    pdf_metadata: dict[str, any] = {  # type: ignore
        "original_filename": "",
        "file_size": 0,
        "gridfs_id": None,  # Reference to GridFS file
        "upload_date": None,
    }

    # Processing information
    processing_info: dict[str, any] = {  # type: ignore
        "model_version": "",
        "processing_time_ms": 0,
        "confidence_score": 0.0,
    }

    # Veterinarian review
    veterinarian_review: dict[str, any] | None = None  # type: ignore

    # Metadata
    created_by: PyObjectId
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class UserRole(str, Enum):
    VETERINARIAN = "veterinarian"
    VETERINARY_TECHNICIAN = "veterinary_technician"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(BaseModel):
    id: PyObjectId | None = Field(default_factory=ObjectId, alias="_id")
    username: str
    email: str
    hashed_password: str
    role: UserRole  # "veterinarian" or "veterinary_technician"

    # Professional profile
    profile: dict[str, any] = {  # type: ignore
        "first_name": "",
        "last_name": "",
        "license_number": "",
        "clinic_name": "",
        "phone": ""
    }

    # Approval system
    # "pending", "approved", "rejected"
    approval_status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: PyObjectId | None = None  # Admin who approved
    approved_at: datetime | None = None

    # Metadata
    is_active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    last_login: datetime | None = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class Admin(BaseModel):
    id: PyObjectId | None = Field(default_factory=ObjectId, alias="_id")
    username: str
    email: str
    hashed_password: str
    role: str = "admin"  # Always "admin"

    # Admin permissions
    permissions: list[str] = [
        "user_management",
        "system_configuration",
        "data_analytics",
        "backup_restore"
    ]

    # Profile
    profile: dict[str, any] = {  # type: ignore
        "first_name": "",
        "last_name": ""
    }

    # Metadata
    is_active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    last_login: datetime | None = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class RefreshToken(BaseModel):
    """Refresh token model for JWT token management"""
    id: PyObjectId | None = Field(default_factory=ObjectId, alias="_id")
    user_id: PyObjectId  # Reference to User
    token_hash: str  # Hashed version of the token
    expires_at: datetime
    is_active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))

    # Optional metadata
    device_info: str | None = None  # User agent, device name, etc.
    ip_address: str | None = None

    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
