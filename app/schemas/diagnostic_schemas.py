"""
Pydantic schemas for diagnostic and analysis API endpoints.

This module defines the request and response schemas for PDF analysis,
diagnostic results, and AI-powered bloodwork analysis endpoints.

Last updated: 2025-06-20
Author: Bedirhan Gilgiler
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# Request Schemas
class AnalysisRequest(BaseModel):
    """Schema for analysis request with patient context."""
    patient_id: Optional[str] = Field(
        None, description="Associated patient ID (format: PAT-XXX)")
    notes: Optional[str] = Field(
        None, max_length=1000, description="Additional analysis notes")


class DiagnosticSearchRequest(BaseModel):
    """Schema for searching diagnostics."""
    patient_id: Optional[str] = None
    status: Optional[str] = Field(
        None, pattern=r"^(pending|completed|failed)$")
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    limit: int = Field(10, ge=1, le=100)
    skip: int = Field(0, ge=0)


# Response Schemas
class AnalysisResponseMinimal(BaseModel):
    """Minimal response schema for analysis initiation."""
    diagnostic_id: str = Field(...,
                               description="Unique diagnostic identifier (e.g., DGN-001)")
    status: str = Field(..., description="Analysis status")
    message: str = Field(..., description="Human-readable status message")
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimated completion time")


class PatientInfo(BaseModel):
    """Patient information extracted from analysis."""
    nome: Optional[str] = None
    specie: Optional[str] = None
    razza: Optional[str] = None
    eta: Optional[str] = None
    sesso: Optional[str] = None
    peso: Optional[str] = None
    proprietario: Optional[str] = None
    data_referto: Optional[str] = None


class ParameterAnalysis(BaseModel):
    """Individual parameter analysis result."""
    parametro: str
    valore: str
    unita: Optional[str] = None
    range: Optional[str] = None
    stato: str = Field(...,
                       pattern=r"^(normale|alterato_lieve|alterato_grave)$")


class MathematicalAnalysis(BaseModel):
    """Mathematical ratio analysis."""
    bun_creatinina: Dict[str, str] = Field(default_factory=dict)
    calcio_fosforo: Dict[str, str] = Field(default_factory=dict)
    neutrofili_linfociti: Dict[str, str] = Field(default_factory=dict)
    na_k: Dict[str, str] = Field(default_factory=dict)
    albumina_globuline: Dict[str, str] = Field(default_factory=dict)


class DifferentialDiagnosis(BaseModel):
    """Differential diagnosis with confidence."""
    diagnosi: str
    confidenza: str


class ClinicalInterpretation(BaseModel):
    """Clinical interpretation of results."""
    alterazioni: List[str] = Field(default_factory=list)
    diagnosi_differenziali: List[DifferentialDiagnosis] = Field(
        default_factory=list)
    pattern_compatibili: Dict[str, str] = Field(default_factory=dict)


class UrgencyClassification(BaseModel):
    """Urgency classification with reasoning."""
    livello: str = Field(..., pattern=r"^(EMERGENZA|URGENZA A BREVE|ROUTINE)$")
    motivazione: str


class DiagnosticPlan(BaseModel):
    """Diagnostic plan item."""
    esame: str
    priorita: str = Field(..., pattern=r"^(Alta|Media|Bassa)$")
    invasivita: str = Field(..., pattern=r"^(Alta|Media|Bassa)$")


class TreatmentPlan(BaseModel):
    """Treatment plan item."""
    trattamento: str
    dosaggio: Optional[str] = None
    via: Optional[str] = None
    durata: Optional[str] = None


class FollowUpPlan(BaseModel):
    """Follow-up plan details."""
    quando_ripetere: str
    parametri_monitorare: List[str] = Field(default_factory=list)
    segni_clinici: List[str] = Field(default_factory=list)


class AnalysisResultDetailed(BaseModel):
    """Detailed analysis result schema."""
    paziente: PatientInfo
    parametri: List[ParameterAnalysis] = Field(default_factory=list)
    analisi_matematica: MathematicalAnalysis = Field(
        default_factory=MathematicalAnalysis)
    interpretazione_clinica: ClinicalInterpretation = Field(
        default_factory=ClinicalInterpretation)
    referto_citologico: Optional[str] = None
    classificazione_urgenza: Optional[UrgencyClassification] = None
    piano_diagnostico: List[DiagnosticPlan] = Field(default_factory=list)
    piano_terapeutico: List[TreatmentPlan] = Field(default_factory=list)
    follow_up: Optional[FollowUpPlan] = None
    educazione_proprietario: Optional[str] = None
    bandierine_rosse: List[str] = Field(default_factory=list)
    disclaimer: Optional[str] = None


class DiagnosticResponse(BaseModel):
    """Complete diagnostic response schema."""
    diagnostic_id: str
    patient_id: str
    sequence_number: int
    test_date: datetime
    ai_diagnostic: dict
    pdf_metadata: dict
    processing_info: dict
    veterinarian_review: Optional[dict] = None
    created_by: str
    created_at: datetime

    class Config:
        orm_mode = True


class DiagnosticListResponse(BaseModel):
    """Response schema for diagnostic list."""
    diagnostics: List[DiagnosticResponse]
    total: int
    limit: int
    skip: int
    has_more: bool


class ErrorResponse(BaseModel):
    """Error response schema."""
    error: str
    detail: str
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Status-specific response schemas
class AnalysisInProgressResponse(BaseModel):
    """Response schema for analysis in progress."""
    status: str = "in_progress"
    message: str = "Analisi in corso. Torna più tardi per vedere i risultati."
    estimated_completion: Optional[datetime] = None


class AnalysisCompletedResponse(BaseModel):
    """Response schema for completed analysis."""
    status: str = "completed"
    result: AnalysisResultDetailed
    processed_at: datetime


class AnalysisFailedResponse(BaseModel):
    """Response schema for failed analysis."""
    status: str = "failed"
    error: str
    detail: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Validation helpers
class AnalysisStatusValidator:
    """Validator for analysis status values."""

    VALID_STATUSES = {"pending", "in_progress", "completed", "failed"}

    @classmethod
    def validate_status(cls, status: str) -> str:
        """
        Validate analysis status value.

        Args:
            status (str): Status to validate

        Returns:
            str: Validated status

        Raises:
            ValueError: If status is invalid
        """
        if status not in cls.VALID_STATUSES:
            raise ValueError(
                f"Invalid status: {status}. Must be one of {cls.VALID_STATUSES}")
        return status


# File upload validation schemas
class FileUploadResponse(BaseModel):
    """Response schema for file upload validation."""
    filename: str
    size: int
    content_type: str
    is_valid: bool
    validation_message: Optional[str] = None
