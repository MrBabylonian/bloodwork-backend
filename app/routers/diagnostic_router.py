"""
Diagnostic router for veterinary bloodwork analysis system.

This module provides API endpoints for retrieving diagnostic results
organized by patient. It allows fetching the latest diagnostic for a patient
and retrieving all diagnostics for a patient sorted by date.

Last updated: 2025-06-22
Author: Bedirhan Gilgiler
"""

from typing import Union

from app.dependencies.auth_dependencies import (
    get_repository_factory,
    require_authenticated,
)
from app.models.database_models import Admin, User
from app.repositories import RepositoryFactory
from app.schemas.diagnostic_schemas import DiagnosticListResponse, DiagnosticResponse
from app.utils.logger_utils import ApplicationLogger
from fastapi import APIRouter, Depends, HTTPException, Path, Query, status

# Initialize router and logger
router = APIRouter(prefix="/api/v1/diagnostics", tags=["Diagnostics"])
logger = ApplicationLogger.get_logger("diagnostic_router")


@router.get("/patient/{patient_id}/latest", response_model=DiagnosticResponse)
async def get_latest_patient_diagnostic(
    patient_id: str = Path(...,
                           description="Patient ID to retrieve latest diagnostic for"),
    current_user: Union[Admin, User] = Depends(require_authenticated),
    repo_factory: RepositoryFactory = Depends(get_repository_factory)
):
    """
    Retrieve the latest diagnostic for a specific patient.

    This endpoint returns the most recent diagnostic result for the specified patient,
    sorted by test date in descending order.

    Args:
        patient_id (str): Patient ID to retrieve latest diagnostic for
        current_user (Union[Admin, User]): Authenticated user
        repo_factory (RepositoryFactory): Database repository factory

    Returns:
        DiagnosticResponse: Latest diagnostic result for the patient

    Raises:
        HTTPException: 
            - 404: If no diagnostics found for the patient
            - 500: If an error occurs during retrieval

    Example:
        GET /api/v1/diagnostics/patient/PAT-001/latest
    """
    logger.info(f"Retrieving latest diagnostic for patient: {patient_id}")

    try:
        # Verify patient exists
        patient_repo = repo_factory.patient_repository
        patient = await patient_repo.get_by_id(patient_id)

        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient not found: {patient_id}"
            )

        # Get the latest diagnostic for the patient
        ai_diagnostic_repo = repo_factory.ai_diagnostic_repository
        diagnostic = await ai_diagnostic_repo.get_latest_patient_diagnostic(patient_id)

        if not diagnostic:
            logger.warning(f"No diagnostics found for patient: {patient_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No diagnostics found for patient: {patient_id}"
            )

        logger.info(
            f"Retrieved latest diagnostic: {diagnostic.diagnostic_id} for patient: {patient_id}")

        # Convert to response model
        return DiagnosticResponse(
            diagnostic_id=diagnostic.diagnostic_id,
            patient_id=diagnostic.patient_id,
            sequence_number=diagnostic.sequence_number,
            test_date=diagnostic.test_date,
            ai_diagnostic=diagnostic.ai_diagnostic,
            pdf_metadata=diagnostic.pdf_metadata,
            processing_info=diagnostic.processing_info,
            veterinarian_review=diagnostic.veterinarian_review,
            created_by=diagnostic.created_by,
            created_at=diagnostic.created_at
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(
            f"Error retrieving latest diagnostic for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving diagnostic"
        )


@router.get("/patient/{patient_id}", response_model=DiagnosticListResponse)
async def get_patient_diagnostics(
    patient_id: str = Path(...,
                           description="Patient ID to retrieve diagnostics for"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: Union[Admin, User] = Depends(require_authenticated),
    repo_factory: RepositoryFactory = Depends(get_repository_factory)
):
    """
    Retrieve all diagnostics for a specific patient with pagination.

    This endpoint returns all diagnostic results for the specified patient,
    sorted by test date in descending order (newest to oldest).

    Args:
        patient_id (str): Patient ID to retrieve diagnostics for
        page (int): Page number (1-indexed)
        limit (int): Number of items per page
        current_user (Union[Admin, User]): Authenticated user
        repo_factory (RepositoryFactory): Database repository factory

    Returns:
        DiagnosticListResponse: List of diagnostic results with pagination metadata

    Raises:
        HTTPException: 
            - 404: If patient not found
            - 500: If an error occurs during retrieval

    Example:
        GET /api/v1/diagnostics/patient/PAT-001?page=1&limit=10
    """
    logger.info(
        f"Retrieving diagnostics for patient: {patient_id} (page {page}, limit {limit})")

    try:
        # Verify patient exists
        patient_repo = repo_factory.patient_repository
        patient = await patient_repo.get_by_id(patient_id)

        if not patient:
            logger.warning(f"Patient not found: {patient_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient not found: {patient_id}"
            )

        # Calculate skip value for pagination
        skip = (page - 1) * limit

        # Get all diagnostics for the patient with pagination
        ai_diagnostic_repo = repo_factory.ai_diagnostic_repository
        diagnostics, total = await ai_diagnostic_repo.get_by_patient_id_paginated(
            patient_id, skip, limit
        )

        if not diagnostics and total > 0:
            # If we got no results but there are diagnostics, the page is out of range
            logger.warning(
                f"Page {page} is out of range for patient: {patient_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page {page} is out of range"
            )

        logger.info(
            f"Retrieved {len(diagnostics)} diagnostics for patient: {patient_id}")

        # Convert to response models
        diagnostic_responses = [
            DiagnosticResponse(
                diagnostic_id=diagnostic.diagnostic_id,
                patient_id=diagnostic.patient_id,
                sequence_number=diagnostic.sequence_number,
                test_date=diagnostic.test_date,
                ai_diagnostic=diagnostic.ai_diagnostic,
                pdf_metadata=diagnostic.pdf_metadata,
                processing_info=diagnostic.processing_info,
                veterinarian_review=diagnostic.veterinarian_review,
                created_by=diagnostic.created_by,
                created_at=diagnostic.created_at
            )
            for diagnostic in diagnostics
        ]

        # Calculate if there are more results
        has_more = (skip + limit) < total

        return DiagnosticListResponse(
            diagnostics=diagnostic_responses,
            total=total,
            limit=limit,
            skip=skip,
            has_more=has_more
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception(
            f"Error retrieving diagnostics for patient {patient_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while retrieving diagnostics"
        )
