"""
Pydantic schemas for API request and response validation.

This package contains all the schema definitions used throughout the API
for request validation, response serialization, and data transfer.

Last updated: 2025-06-17
Author: Bedirhan Gilgiler
"""

from .auth_schemas import *
from .patient_schemas import *
from .diagnostic_schemas import *

__all__ = [
    # Auth schemas
    "UserRegistrationRequest",
    "UserLoginRequest", 
    "TokenResponse",
    "RefreshTokenRequest",
    "UserResponse",
    "PasswordResetRequest",
    
    # Patient schemas
    "PatientCreateRequest",
    "PatientUpdateRequest",
    "PatientResponse",
    "PatientListResponse",
    "PatientSearchRequest",
    
    # Diagnostic schemas
    "AnalysisRequest",
    "DiagnosticSearchRequest",
    "AnalysisResponseMinimal",
    "PatientInfo",
    "ParameterAnalysis", 
    "MathematicalAnalysis",
    "DifferentialDiagnosis",
    "ClinicalInterpretation",
    "UrgencyClassification",
    "DiagnosticPlan",
    "TreatmentPlan",
    "FollowUpPlan",
    "AnalysisResultDetailed",
    "DiagnosticResponse",
    "DiagnosticListResponse",
    "ErrorResponse",
    "AnalysisInProgressResponse",
    "AnalysisCompletedResponse",
    "AnalysisFailedResponse",
    "FileUploadResponse",
]
