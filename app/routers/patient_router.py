"""
Patient management router with protected routes.

This module provides CRUD operations for patient management,
following veterinary workflow patterns and role-based access control.
"""

from typing import List, Union

from app.dependencies.auth_dependencies import (
    get_repository_factory,
    require_admin_user,
    require_authenticated,
    require_vet_or_admin,
)
from app.models.database_models import Admin, Patient, User
from app.repositories import RepositoryFactory
from app.schemas.patient_schemas import PatientCreate, PatientResponse, PatientUpdate
from app.utils.logger_utils import ApplicationLogger
from fastapi import APIRouter, Depends, HTTPException, status

# Create router
router = APIRouter(prefix="/api/v1/patients", tags=["Patient Management"])
logger = ApplicationLogger.get_logger(__name__)


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    current_user: Union[Admin, User] = Depends(require_vet_or_admin),
    repo_factory: RepositoryFactory = Depends(get_repository_factory)
):
    """
    Create a new patient.

    Protected route - only admins and veterinarians can create patients.
    Patient is automatically assigned to the creating user.
    """
    if not current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required"
        )

    patient_repo = repo_factory.patient_repository

    # Create patient with current user as creator and assignee
    patient = Patient(
        patient_id=patient_data.patient_id,
        name=patient_data.name,
        species=patient_data.species,
        breed=patient_data.breed,
        age=patient_data.age,
        sex=patient_data.sex,
        weight=patient_data.weight,
        owner_info=patient_data.owner_info,
        medical_history=patient_data.medical_history,
        created_by=current_user.id,
        assigned_to=current_user.id
    )

    created_patient = await patient_repo.create(patient)

    if not created_patient:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient ID already exists or creation failed"
        )

    # Convert to response format
    return PatientResponse(
        id=str(created_patient.id),
        patient_id=created_patient.patient_id,
        name=created_patient.name,
        species=created_patient.species,
        breed=created_patient.breed,
        age=created_patient.age,
        sex=created_patient.sex,
        weight=created_patient.weight,
        owner_info=created_patient.owner_info,
        medical_history=created_patient.medical_history,
        diagnostic_summary=created_patient.diagnostic_summary,
        created_by=str(created_patient.created_by),
        assigned_to=str(created_patient.assigned_to),
        created_at=created_patient.created_at,
        updated_at=created_patient.updated_at,
        is_active=created_patient.is_active
    )


@router.get("/", response_model=List[PatientResponse])
async def get_all_patients(
    current_user: Union[Admin, User] = Depends(require_authenticated),
    repo_factory: RepositoryFactory = Depends(get_repository_factory)
):
    """
    Get all patients.

    Protected route - all authenticated users can view all patients.
    """
    patient_repo = repo_factory.patient_repository
    patients = await patient_repo.get_all()

    return [
        PatientResponse(
            id=str(patient.id),
            patient_id=patient.patient_id,
            name=patient.name,
            species=patient.species,
            breed=patient.breed,
            age=patient.age,
            sex=patient.sex,
            weight=patient.weight,
            owner_info=patient.owner_info,
            medical_history=patient.medical_history,
            diagnostic_summary=patient.diagnostic_summary,
            created_by=str(patient.created_by),
            assigned_to=str(patient.assigned_to),
            created_at=patient.created_at,
            updated_at=patient.updated_at,
            is_active=patient.is_active
        )
        for patient in patients
    ]


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    current_user: Union[Admin, User] = Depends(require_authenticated),
    repo_factory: RepositoryFactory = Depends(get_repository_factory)
):
    """
    Get specific patient by ID.

    Protected route - all authenticated users can view any patient.
    """
    patient_repo = repo_factory.patient_repository

    # Try by MongoDB ObjectId first, then by patient_id
    patient = await patient_repo.get_by_id(patient_id)
    if not patient:
        patient = await patient_repo.get_by_patient_id(patient_id)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    return PatientResponse(
        id=str(patient.id),
        patient_id=patient.patient_id,
        name=patient.name,
        species=patient.species,
        breed=patient.breed,
        age=patient.age,
        sex=patient.sex,
        weight=patient.weight,
        owner_info=patient.owner_info,
        medical_history=patient.medical_history,
        diagnostic_summary=patient.diagnostic_summary,
        created_by=str(patient.created_by),
        assigned_to=str(patient.assigned_to),
        created_at=patient.created_at,
        updated_at=patient.updated_at,
        is_active=patient.is_active
    )


@router.put("/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: str,
    patient_data: PatientUpdate,
    current_user: Union[Admin, User] = Depends(require_authenticated),
    repo_factory: RepositoryFactory = Depends(get_repository_factory)
):
    """
    Update patient information.

    Protected route - all authenticated users can update any patient.
    """
    patient_repo = repo_factory.patient_repository

    # Get patient and verify it exists
    patient = await patient_repo.get_by_id(patient_id)
    if not patient:
        patient = await patient_repo.get_by_patient_id(patient_id)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    # Ensure patient has ID
    if not patient.id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Patient ID is missing"
        )

    # Prepare update data
    update_data = {k: v for k, v in patient_data.model_dump().items()
                   if v is not None}

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No data provided for update"
        )

    # Update patient
    success = await patient_repo.update(patient.id, update_data)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update patient"
        )

    # Return updated patient
    updated_patient = await patient_repo.get_by_id(patient.id)
    if not updated_patient:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve updated patient"
        )
    return PatientResponse(
        id=str(updated_patient.id),
        patient_id=updated_patient.patient_id,
        name=updated_patient.name,
        species=updated_patient.species,
        breed=updated_patient.breed,
        age=updated_patient.age,
        sex=updated_patient.sex,
        weight=updated_patient.weight,
        owner_info=updated_patient.owner_info,
        medical_history=updated_patient.medical_history,
        diagnostic_summary=updated_patient.diagnostic_summary,
        created_by=str(updated_patient.created_by),
        assigned_to=str(updated_patient.assigned_to),
        created_at=updated_patient.created_at,
        updated_at=updated_patient.updated_at,
        is_active=updated_patient.is_active
    )


@router.delete("/{patient_id}")
async def delete_patient(
    patient_id: str,
    current_user: Union[Admin, User] = Depends(require_vet_or_admin),
    repo_factory: RepositoryFactory = Depends(get_repository_factory)
):
    """
    Soft delete patient.

    Protected route - only veterinarians and admins can delete patients.
    """
    patient_repo = repo_factory.patient_repository

    # Get patient
    patient = await patient_repo.get_by_id(patient_id)
    if not patient:
        patient = await patient_repo.get_by_patient_id(patient_id)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    # Ensure patient has ID
    if not patient.id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Patient ID is missing"
        )

    # Soft delete
    success = await patient_repo.soft_delete(patient.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete patient"
        )

    return {"message": "Patient deleted successfully"}


@router.get("/search/{name}", response_model=List[PatientResponse])
async def search_patients(
    name: str,
    current_user: Union[Admin, User] = Depends(require_authenticated),
    repo_factory: RepositoryFactory = Depends(get_repository_factory)
):
    """
    Search patients by name.

    Protected route - all authenticated users can search patients.
    """
    patient_repo = repo_factory.patient_repository
    patients = await patient_repo.search_by_name(name)

    return [
        PatientResponse(
            id=str(patient.id),
            patient_id=patient.patient_id,
            name=patient.name,
            species=patient.species,
            breed=patient.breed,
            age=patient.age,
            sex=patient.sex,
            weight=patient.weight,
            owner_info=patient.owner_info,
            medical_history=patient.medical_history,
            diagnostic_summary=patient.diagnostic_summary,
            created_by=str(patient.created_by),
            assigned_to=str(patient.assigned_to),
            created_at=patient.created_at,
            updated_at=patient.updated_at,
            is_active=patient.is_active
        )
        for patient in patients
    ]


@router.get("/admin/recent", response_model=List[PatientResponse])
async def get_recent_patients(
    limit: int = 10,
    current_user: Admin = Depends(require_admin_user),
    repo_factory: RepositoryFactory = Depends(get_repository_factory)
):
    """
    Get recently created patients.

    Protected route - admin only.
    """
    patient_repo = repo_factory.patient_repository
    patients = await patient_repo.get_recent(limit)

    return [
        PatientResponse(
            id=str(patient.id),
            patient_id=patient.patient_id,
            name=patient.name,
            species=patient.species,
            breed=patient.breed,
            age=patient.age,
            sex=patient.sex,
            weight=patient.weight,
            owner_info=patient.owner_info,
            medical_history=patient.medical_history,
            diagnostic_summary=patient.diagnostic_summary,
            created_by=str(patient.created_by),
            assigned_to=str(patient.assigned_to),
            created_at=patient.created_at,
            updated_at=patient.updated_at,
            is_active=patient.is_active
        )
        for patient in patients
    ]


@router.get("/health")
async def health_check():
    """Health check endpoint for patient service."""
    return {"status": "healthy", "service": "patient_management"}
