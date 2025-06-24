"""
Patient management router for veterinary bloodwork analysis system.

This module provides comprehensive CRUD operations for patient management,
implementing role-based access control and following veterinary workflow patterns.
All endpoints are protected and require authentication.

Features:
- Patient creation with automatic user assignment
- Role-based access control (Admin/Vet permissions)
- Comprehensive patient data management
- Search and filtering capabilities
- Data validation and error handling

Last updated: 2025-06-20
Author: Bedirhan Gilgiler
"""

from datetime import datetime, timezone
from typing import Union

from app.dependencies.auth_dependencies import (
    get_repository_factory,
    require_authenticated,
    require_vet_or_admin,
)
from app.models.database_models import Admin, Patient, User
from app.repositories import RepositoryFactory
from app.schemas.patient_schemas import (
    PatientCreate,
    PatientListResponse,
    PatientResponse,
    PatientUpdate,
)
from app.utils.logger_utils import ApplicationLogger
from fastapi import APIRouter, Depends, HTTPException, status

# Initialize router and logger
router = APIRouter(prefix="/api/v1/patients", tags=["Patient Management"])
logger = ApplicationLogger.get_logger("patient_router")


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
async def create_patient(
    patient_data: PatientCreate,
    current_user: Union[Admin, User] = Depends(require_vet_or_admin),
    repo_factory: RepositoryFactory = Depends(get_repository_factory)
):
    """
    Create a new patient record in the system.

    This endpoint allows veterinarians and administrators to create new
    patient records. The patient_id will be auto-generated using the sequence counter.

    Args:
        patient_data (PatientCreate): Patient information
        current_user (Union[Admin, User]): Authenticated user (must be veterinarian or admin)
        repo_factory (RepositoryFactory): Database repository factory

    Returns:
        PatientResponse: Created patient details

    Raises:
        HTTPException: If user is not authenticated or patient creation fails

    Example:
        POST /api/v1/patients/
        Request body: {
            "name": "Max",
            "species": "Dog",
            "breed": "Golden Retriever",
            ...
        }
        Response: {
            "patient_id": "PAT-001",
            "name": "Max",
            "species": "Dog",
            ...
        }
    """
    logger.info(f"Patient creation request by user: {current_user.username}")

    # Determine creator ID based on user type
    if isinstance(current_user, Admin):
        creator_id = current_user.admin_id
    else:
        creator_id = current_user.user_id

    if not creator_id:
        logger.error("Patient creation failed: missing user ID")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ID is required"
        )

    patient_repo = repo_factory.patient_repository

    # Create patient without ID - repository will generate one
    patient = Patient(
        _id="",  # Empty ID will trigger generation in repository
        name=patient_data.name,
        species=patient_data.species,
        breed=patient_data.breed,
        birthdate=patient_data.birthdate,
        sex=patient_data.sex,
        weight=patient_data.weight,
        owner_info=patient_data.owner_info,
        medical_history=patient_data.medical_history,
        created_by=creator_id,
        assigned_to=creator_id
    )

    created_patient = await patient_repo.create(patient)

    if not created_patient:
        logger.error("Failed to create patient")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patient creation failed"
        )

    logger.info(f"Patient created successfully: {created_patient.patient_id}")

    # Convert to response format
    return PatientResponse(
        patient_id=created_patient.patient_id,
        name=created_patient.name,
        species=created_patient.species,
        breed=created_patient.breed,
        birthdate=created_patient.birthdate,
        sex=created_patient.sex,
        weight=created_patient.weight,
        owner_info=created_patient.owner_info,
        medical_history=created_patient.medical_history,
        created_by=created_patient.created_by,
        assigned_to=created_patient.assigned_to,
        created_at=created_patient.created_at,
        updated_at=created_patient.updated_at,
        is_active=created_patient.is_active
    )


@router.get("/", response_model=PatientListResponse)
async def get_all_patients(
    page: int = 1,
    limit: int = 10,
    current_user: Union[Admin, User] = Depends(require_authenticated),
    repo_factory: RepositoryFactory = Depends(get_repository_factory)
):
    """
    Retrieve all patients from the system with pagination.

    This endpoint returns a paginated list of patients in the database,
    accessible to all authenticated users.

    Args:
        page (int): Page number (1-indexed)
        limit (int): Number of items per page
        current_user (Union[Admin, User]): Authenticated user
        repo_factory (RepositoryFactory): Database repository factory

    Returns:
        PatientListResponse: List of patients with pagination metadata

    Example:
        GET /api/v1/patients/?page=1&limit=10
        Response: {
            "patients": [
                {
                    "patient_id": "PAT-001",
                    "name": "Max",
                    "species": "Dog",
                    ...
                }
            ],
            "total": 45,
            "page": 1,
            "limit": 10
        }
    """
    logger.info(f"Retrieving patients (page {page}, limit {limit})")

    # Validate pagination parameters
    if page < 1:
        page = 1
    if limit < 1:
        limit = 10
    elif limit > 100:
        limit = 100

    # Calculate skip value for pagination
    skip = (page - 1) * limit

    patient_repo = repo_factory.patient_repository
    patients, total = await patient_repo.get_all(skip=skip, limit=limit)

    logger.info(
        f"Retrieved {len(patients)} patients (page {page} of {(total + limit - 1) // limit})")

    # Convert to response format
    patient_responses = [
        PatientResponse(
            patient_id=patient.patient_id,
            name=patient.name,
            species=patient.species,
            breed=patient.breed,
            birthdate=patient.birthdate,
            sex=patient.sex,
            weight=patient.weight,
            owner_info=patient.owner_info,
            medical_history=patient.medical_history,
            created_by=patient.created_by,
            assigned_to=patient.assigned_to,
            created_at=patient.created_at,
            updated_at=patient.updated_at,
            is_active=patient.is_active
        )
        for patient in patients
    ]

    return PatientListResponse(
        patients=patient_responses,
        total=total,
        page=page,
        limit=limit
    )


@router.get("/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: str,
    current_user: Union[Admin, User] = Depends(require_authenticated),
    repo_factory: RepositoryFactory = Depends(get_repository_factory)
):
    """
    Retrieve a specific patient by ID.

    This endpoint returns detailed information for a specific patient,
    accessible to all authenticated users.

    Args:
        patient_id (str): Patient ID to retrieve
        current_user (Union[Admin, User]): Authenticated user
        repo_factory (RepositoryFactory): Database repository factory

    Returns:
        PatientResponse: Patient details

    Raises:
        HTTPException: 404 if patient not found

    Example:
        GET /api/v1/patients/PAT-001
        Response: {
            "patient_id": "PAT-001",
            "name": "Max",
            ...
        }
    """
    logger.info(f"Retrieving patient: {patient_id}")

    patient_repo = repo_factory.patient_repository
    patient = await patient_repo.get_by_id(patient_id)

    if not patient:
        logger.warning(f"Patient not found: {patient_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    logger.info(f"Patient retrieved: {patient_id}")

    return PatientResponse(
        patient_id=patient.patient_id,
        name=patient.name,
        species=patient.species,
        breed=patient.breed,
        birthdate=patient.birthdate,
        sex=patient.sex,
        weight=patient.weight,
        owner_info=patient.owner_info,
        medical_history=patient.medical_history,
        created_by=patient.created_by,
        assigned_to=patient.assigned_to,
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
    Update a patient's information.

    This endpoint updates a patient's information with the provided data.
    Only fields included in the request are updated.

    Args:
        patient_id (str): Patient ID to update
        patient_data (PatientUpdate): Patient fields to update
        current_user (Union[Admin, User]): Authenticated user
        repo_factory (RepositoryFactory): Database repository factory

    Returns:
        PatientResponse: Updated patient details

    Raises:
        HTTPException:
            - 404: If patient not found
            - 400: If update fails

    Example:
        PUT /api/v1/patients/PAT-001
        {
            "weight": 32.5,
            "medical_history": {
                "vaccinations": ["Rabies", "Distemper"]
            }
        }
    """
    logger.info(f"Updating patient: {patient_id}")

    patient_repo = repo_factory.patient_repository
    patient = await patient_repo.get_by_id(patient_id)

    if not patient:
        logger.warning(f"Patient not found: {patient_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    # Build update data from request
    update_data = {}
    for field, value in patient_data.dict(exclude_unset=True).items():
        if value is not None:
            update_data[field] = value

    if not update_data:
        logger.warning("No valid fields to update")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )

    # Add updated timestamp
    update_data["updated_at"] = datetime.now(timezone.utc)

    # Update patient
    success = await patient_repo.update(patient_id, update_data)

    if not success:
        logger.error(f"Failed to update patient: {patient_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update patient"
        )

    # Get updated patient
    updated_patient = await patient_repo.get_by_id(patient_id)
    if not updated_patient:
        logger.error(f"Failed to retrieve updated patient: {patient_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Failed to retrieve updated patient"
        )

    logger.info(f"Patient updated successfully: {patient_id}")

    return PatientResponse(
        patient_id=updated_patient.patient_id,
        name=updated_patient.name,
        species=updated_patient.species,
        breed=updated_patient.breed,
        birthdate=updated_patient.birthdate,
        sex=updated_patient.sex,
        weight=updated_patient.weight,
        owner_info=updated_patient.owner_info,
        medical_history=updated_patient.medical_history,
        created_by=updated_patient.created_by,
        assigned_to=updated_patient.assigned_to,
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
    Delete (soft-delete) a patient.

    This endpoint marks a patient as inactive (soft-delete)
    rather than permanently deleting the record.

    Args:
        patient_id (str): Patient ID to delete
        current_user (Union[Admin, User]): Authenticated user (vet or admin only)
        repo_factory (RepositoryFactory): Database repository factory

    Returns:
        dict: Deletion success message

    Raises:
        HTTPException:
            - 404: If patient not found
            - 400: If deletion fails

    Example:
        DELETE /api/v1/patients/PAT-001
        Response: {"message": "Patient deleted successfully"}
    """
    logger.info(f"Deleting patient: {patient_id}")

    patient_repo = repo_factory.patient_repository
    patient = await patient_repo.get_by_id(patient_id)

    if not patient:
        logger.warning(f"Patient not found: {patient_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found"
        )

    # Get user ID based on user type
    from app.models.database_models import Admin
    if isinstance(current_user, Admin):
        user_id = current_user.admin_id
    else:
        user_id = current_user.user_id

    # Log deletion attempt with user info
    logger.info(
        f"Deletion of patient {patient_id} requested by: {current_user.username} ({user_id})")

    # Soft delete the patient
    success = await patient_repo.soft_delete(patient_id)

    if not success:
        logger.error(f"Failed to delete patient: {patient_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete patient"
        )

    logger.info(f"Patient deleted successfully: {patient_id}")

    return {"message": "Patient deleted successfully"}


@router.get("/search/{name}", response_model=PatientListResponse)
async def search_patients(
    name: str,
    page: int = 1,
    limit: int = 10,
    current_user: Union[Admin, User] = Depends(require_authenticated),
    repo_factory: RepositoryFactory = Depends(get_repository_factory)
):
    """
    Search patients by name with pagination.

    This endpoint performs a text search on patient names and returns
    matching patients with pagination, accessible to all authenticated users.

    Args:
        name (str): Name to search for
        page (int): Page number (1-indexed)
        limit (int): Number of items per page
        current_user (Union[Admin, User]): Authenticated user
        repo_factory (RepositoryFactory): Database repository factory

    Returns:
        PatientListResponse: List of matching patients with pagination metadata

    Example:
        GET /api/v1/patients/search/Max?page=1&limit=10
        Response: {
            "patients": [
                {
                    "patient_id": "PAT-001",
                    "name": "Max",
                    ...
                }
            ],
            "total": 3,
            "page": 1,
            "limit": 10
        }
    """
    logger.info(
        f"Searching patients by name: {name} (page {page}, limit {limit})")

    # Validate pagination parameters
    if page < 1:
        page = 1
    if limit < 1:
        limit = 10
    elif limit > 100:
        limit = 100

    # Calculate skip value for pagination
    skip = (page - 1) * limit

    patient_repo = repo_factory.patient_repository
    patients, total = await patient_repo.search_by_name(name, skip=skip, limit=limit)

    logger.info(
        f"Found {len(patients)} patients matching '{name}' (page {page} of {(total + limit - 1) // limit if total > 0 else 1})")

    # Convert to response format
    patient_responses = [
        PatientResponse(
            patient_id=patient.patient_id,
            name=patient.name,
            species=patient.species,
            breed=patient.breed,
            birthdate=patient.birthdate,
            sex=patient.sex,
            weight=patient.weight,
            owner_info=patient.owner_info,
            medical_history=patient.medical_history,
            created_by=patient.created_by,
            assigned_to=patient.assigned_to,
            created_at=patient.created_at,
            updated_at=patient.updated_at,
            is_active=patient.is_active
        )
        for patient in patients
    ]

    return PatientListResponse(
        patients=patient_responses,
        total=total,
        page=page,
        limit=limit
    )

    """
    Get recently created patients (admin only).

    This endpoint returns a list of recently created patients,
    accessible to admin users only.

    Args:
        limit (int): Maximum number of patients to return
        current_user (Admin): Authenticated admin user
        repo_factory (RepositoryFactory): Database repository factory

    Returns:
        List[PatientResponse]: List of recent patients

    Example:
        GET /api/v1/patients/admin/recent?limit=5
        Response: [
            {
                "patient_id": "PAT-001",
                "name": "Max",
                ...
            }
        ]
    """
    logger.info(
        f"Admin {current_user.username} retrieving {limit} recent patients")

    patient_repo = repo_factory.patient_repository
    patients = await patient_repo.get_recent(limit)

    logger.info(f"Retrieved {len(patients)} recent patients")

    return [
        PatientResponse(
            patient_id=patient.patient_id,
            name=patient.name,
            species=patient.species,
            breed=patient.breed,
            birthdate=patient.birthdate,
            sex=patient.sex,
            weight=patient.weight,
            owner_info=patient.owner_info,
            medical_history=patient.medical_history,
            created_by=patient.created_by,
            assigned_to=patient.assigned_to,
            created_at=patient.created_at,
            updated_at=patient.updated_at,
            is_active=patient.is_active
        )
        for patient in patients
    ]


@router.get("/health")
async def health_check():
    """
    Health check endpoint for patient router.

    Returns a simple status message to verify that the patient router is operational.
    Useful for monitoring and automated health checks.

    Returns:
        dict: Service status message
    """
    return {"status": "Patient router operational"}
