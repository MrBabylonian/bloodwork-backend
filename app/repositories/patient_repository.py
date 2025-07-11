from datetime import datetime, timezone

from app.models.database_models import Patient
from app.services.database_service import DatabaseService
from app.utils.logger_utils import ApplicationLogger
from pymongo.errors import DuplicateKeyError


class PatientRepository:
    """Repository for Patient data access operations"""

    def __init__(self, database_service: DatabaseService):
        self.db_service = database_service
        self.collection = database_service.patients
        self.logger = ApplicationLogger.get_logger(__name__)

    async def _generate_patient_id(self) -> str:
        """
        Generate a sequential human-readable patient ID using MongoDB's atomic operations.

        Returns:
            str: Generated patient ID in PAT-XXX format
        """
        return await self.db_service.get_next_sequential_id("patient")

    async def create(self, patient: Patient) -> Patient | None:
        """Create a new patient"""
        try:
            # Check if we need to generate a patient_id
            if not patient.patient_id:
                # Generate new ID
                patient_id = await self._generate_patient_id()

                # Create a new patient with the generated ID
                patient_dict = patient.model_dump()
                patient = Patient(_id=patient_id, **patient_dict)

            patient.created_at = datetime.now(timezone.utc)
            patient.updated_at = datetime.now(timezone.utc)

            # Debug: Check if patient ID already exists before attempting insert
            existing = await self.collection.find_one({"_id": patient.patient_id})
            if existing:
                self.logger.error(
                    f"DEBUG: Patient ID {patient.patient_id} already exists in database!")
                self.logger.error(
                    f"DEBUG: Existing patient: {existing.get('name', 'Unknown')}")
            else:
                self.logger.info(
                    f"DEBUG: Patient ID {patient.patient_id} is available for creation")

            await self.collection.insert_one(patient.model_dump(by_alias=True))
            self.logger.info(f"Created patient: {patient.patient_id}")
            return patient

        except DuplicateKeyError:
            self.logger.error(
                f"Patient ID already exists: {patient.patient_id}")
            return None
        except Exception as e:
            self.logger.error(f"Error creating patient: {e}")
            return None

    async def get_by_id(self, patient_id: str) -> Patient | None:
        """Get patient by patient_id"""
        try:
            doc = await self.collection.find_one({"_id": patient_id})
            return Patient(**doc) if doc else None

        except Exception as e:
            self.logger.error(f"Error getting patient by id: {e}")
            return None

    async def get_by_user_id(self, user_id: str) -> list[Patient]:
        """Get all patients assigned to a user"""
        try:
            cursor = self.collection.find(
                {"assigned_to": user_id, "is_active": True})
            docs = await cursor.to_list(length=None)
            return [Patient(**doc) for doc in docs]

        except Exception as e:
            self.logger.error(f"Error getting patients by user_id: {e}")
            return []

    async def get_all(self, skip: int = 0, limit: int = 10) -> tuple[list[Patient], int]:
        """
        Get all active patients with pagination support.

        Args:
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return

        Returns:
            tuple[list[Patient], int]: List of patients and total count
        """
        try:
            # Debug logging to see what database and collection we're using
            database_name = self.db_service.database.name if self.db_service.database is not None else 'Unknown'
            self.logger.info(f"Querying database: {database_name}")
            self.logger.info(f"Querying collection: {self.collection.name}")

            # Get total count first (for pagination metadata)
            total = await self.collection.count_documents({"is_active": True})

            # Then get the paginated results
            cursor = self.collection.find(
                {"is_active": True}
            ).sort("created_at", -1).skip(skip).limit(limit)

            docs = await cursor.to_list(length=limit)
            self.logger.info(
                f"Found {len(docs)} patient documents (page {skip//limit + 1}, total: {total})")

            # Debug: let's see what the first document looks like
            if docs:
                first_doc = docs[0]
                self.logger.info(
                    f"First document: patient_id={first_doc.get('patient_id')}, created_by={first_doc.get('created_by')}, assigned_to={first_doc.get('assigned_to')}")

            return [Patient(**doc) for doc in docs], total

        except Exception as e:
            self.logger.error(f"Error getting all patients: {e}")
            return [], 0

    async def search_by_name(self, name: str, skip: int = 0, limit: int = 10) -> tuple[list[Patient], int]:
        """
        Search patients by name with pagination support.

        Args:
            name (str): Name to search for
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return

        Returns:
            tuple[list[Patient], int]: List of matching patients and total count
        """
        try:
            # Get total count first (for pagination metadata)
            total = await self.collection.count_documents(
                {"$text": {"$search": name}, "is_active": True}
            )

            # Then get the paginated results
            cursor = self.collection.find(
                {"$text": {"$search": name}, "is_active": True}
            ).sort("created_at", -1).skip(skip).limit(limit)

            docs = await cursor.to_list(length=limit)
            self.logger.info(
                f"Found {len(docs)} patients matching '{name}' (page {skip//limit + 1}, total: {total})")

            return [Patient(**doc) for doc in docs], total

        except Exception as e:
            self.logger.error(f"Error searching patients by name: {e}")
            return [], 0

    async def update(self, patient_id: str, update_data: dict) -> bool:
        """Update patient data"""
        try:
            update_data["updated_at"] = datetime.now(timezone.utc)

            result = await self.collection.update_one(
                {"_id": patient_id},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                self.logger.info(f"Updated patient: {patient_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error updating patient: {e}")
            return False

    async def soft_delete(self, patient_id: str) -> bool:
        """Soft delete patient (set is_active to False)"""
        try:
            result = await self.collection.update_one(
                {"_id": patient_id},
                {"$set": {"is_active": False,
                          "updated_at": datetime.now(timezone.utc)}}
            )

            if result.modified_count > 0:
                self.logger.info(f"Soft deleted patient: {patient_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error soft deleting patient: {e}")
            return False

    async def get_recent(self, limit: int = 10) -> list[Patient]:
        """Get recently created active patients"""
        try:
            cursor = self.collection.find(
                {"is_active": True}
            ).sort("created_at", -1).limit(limit)

            docs = await cursor.to_list(length=limit)
            return [Patient(**doc) for doc in docs]

        except Exception as e:
            self.logger.error(f"Error getting recent patients: {e}")
            return []
