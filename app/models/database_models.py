"""
Database models for veterinary bloodwork analysis system.

This module defines all Pydantic models used for database operations including
Patient, User, Admin, and AiDiagnostic entities. All models use human-readable
sequential IDs with role-based prefixes for better usability and maintenance.

Features:
- Human-readable sequential IDs (PAT-001, VET-001, TEC-001, ADM-001)
- Role-based user ID prefixes (VET for veterinarians, TEC for technicians)
- Comprehensive data validation with Pydantic
- Enum-based status and role management
- Proper datetime handling with timezone awareness
- Clean foreign key relationships using readable IDs

ID Schemes:
- Patients: PAT-001, PAT-002, PAT-003...
- Veterinarians: VET-001, VET-002, VET-003...
- Technicians: TEC-001, TEC-002, TEC-003...
- Admins: ADM-001, ADM-002, ADM-003...
- Diagnostics: DGN-001, DGN-002, DGN-003...

Last updated: 2025-06-20
Author: Bedirhan Gilgiler
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class UserRole(str, Enum):
    """User role enumeration for role-based access control."""
    VETERINARIAN = "veterinarian"
    VETERINARY_TECHNICIAN = "veterinary_technician"


class ApprovalStatus(str, Enum):
    """User approval status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Patient(BaseModel):
    """
    Patient model representing veterinary patients in the system.

    This model stores comprehensive patient information including demographics,
    medical history, and administrative data for veterinary practice management.
    Uses human-readable IDs like PAT-001, PAT-002, etc.
    """
    patient_id: str = Field(..., alias="_id")
    name: str
    species: str  # e.g., "Canine", "Feline"
    breed: str
    birthdate: datetime
    sex: str
    weight: float | None = None
    owner_info: dict[str, str]
    medical_history: dict[str, Any] = {}

    # Metadata with human-readable references
    created_by: str      # Reference to User.user_id or Admin.admin_id
    assigned_to: str     # Reference to User.user_id or Admin.admin_id
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

    class Config:
        populate_by_name = True


class AiDiagnostic(BaseModel):
    """
    AI diagnostic model for bloodwork analysis results.

    This model stores AI-generated analysis results, PDF metadata,
    and processing information. Uses human-readable IDs like DGN-001.
    """
    diagnostic_id: str = Field(..., alias="_id")
    patient_id: str
    sequence_number: int  # Order of tests for this patient (1, 2, 3...)
    test_date: datetime
    diagnostic_summary: dict[str, Any] = {}  # Summary of diagnostic results

    # Full OpenAI Analysis (stored as native JSON document)
    ai_diagnostic: dict[str, Any] = {}  # JSON document from OpenAI API

    # PDF metadata
    pdf_metadata: dict[str, Any] = {
        "original_filename": "",
        "file_size": 0,
        "gridfs_id": None,  # Reference to GridFS file
        "upload_date": None,
    }

    # Processing information
    processing_info: dict[str, Any] = {
        "model_version": "",
        "processing_time_ms": 0,
        "confidence_score": 0.0,
    }

    # Veterinarian review
    veterinarian_review: dict[str, Any] | None = None

    # Metadata with human-readable references
    created_by: str      # Reference to User.user_id or Admin.admin_id
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))

    class Config:
        populate_by_name = True


class User(BaseModel):
    """
    User model for veterinarians and veterinary technicians.

    This model stores user account information with role-based human-readable IDs.
    Veterinarians get VET-001 format, technicians get TEC-001 format.
    """
    user_id: str = Field(..., alias="_id")
    username: str       # Login identifier (unique)
    email: str
    hashed_password: str
    role: UserRole      # "veterinarian" or "veterinary_technician"

    # Professional profile
    profile: dict[str, Any] = {
        "first_name": "",
        "last_name": "",
        "license_number": "",
        "clinic_name": "",
        "phone": ""
    }

    # Approval system with human-readable references
    approval_status: ApprovalStatus = ApprovalStatus.APPROVED
    approved_by: str | None = None  # Reference to Admin.admin_id
    approved_at: datetime | None = None

    # Metadata
    is_active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    last_login: datetime | None = None

    class Config:
        populate_by_name = True


class Admin(BaseModel):
    """
    Admin model for system administrators.

    This model stores admin account information with human-readable IDs
    like ADM-001, ADM-002, etc.
    """
    admin_id: str = Field(..., alias="_id")
    username: str       # Login identifier (unique)
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
    profile: dict[str, Any] = {
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


class RefreshToken(BaseModel):
    """
    Refresh token model for JWT token management.

    This model stores refresh tokens with human-readable references
    to users and admins.
    """
    token_id: str = Field(..., alias="_id")
    user_id: str         # Reference to User.user_id or Admin.admin_id
    token_hash: str      # Hashed version of the token
    expires_at: datetime
    is_active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))

    # Optional metadata for security tracking
    device_info: str | None = None  # User agent, device name, etc.
    ip_address: str | None = None

    class Config:
        populate_by_name = True
