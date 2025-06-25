from datetime import datetime, timezone

from app.models.database_models import AiDiagnostic
from app.services.database_service import DatabaseService
from app.utils.logger_utils import ApplicationLogger


class AiDiagnosticRepository:
    """Repository for AiDiagnostic data access operations"""

    def __init__(self, database_service: DatabaseService):
        self.db_service = database_service
        self.collection = database_service.ai_diagnostics
        self.logger = ApplicationLogger.get_logger(__name__)

    async def _generate_diagnostic_id(self) -> str:
        """
        Generate a sequential human-readable diagnostic ID using MongoDB's atomic operations.

        Returns:
            str: Generated diagnostic ID in DGN-XXX format
        """
        return await self.db_service.get_next_sequential_id("diagnostic")

    async def create(self, diagnostic: AiDiagnostic) -> AiDiagnostic | None:
        """Create a new diagnostic record"""
        try:
            # Check if we need to generate a diagnostic_id
            if not diagnostic.diagnostic_id or diagnostic.diagnostic_id == "placeholder":
                # Generate new ID
                diagnostic_id = await self._generate_diagnostic_id()

                # Create a new diagnostic with the generated ID
                diagnostic_dict = diagnostic.model_dump()
                diagnostic = AiDiagnostic(_id=diagnostic_id, **diagnostic_dict)

            diagnostic.created_at = datetime.now(timezone.utc)

            await self.collection.insert_one(diagnostic.model_dump(by_alias=True))
            self.logger.info(
                f"Created diagnostic for patient: {diagnostic.patient_id}")
            return diagnostic

        except Exception as e:
            self.logger.error(f"Error creating diagnostic: {e}")
            return None

    async def get_by_id(self, diagnostic_id: str) -> AiDiagnostic | None:
        """Get diagnostic by diagnostic_id"""
        try:
            doc = await self.collection.find_one({"_id": diagnostic_id})
            return AiDiagnostic(**doc) if doc else None

        except Exception as e:
            self.logger.error(f"Error getting diagnostic by id: {e}")
            return None

    async def get_by_patient_id_paginated(
        self,
        patient_id: str,
        skip: int = 0,
        limit: int = 10
    ) -> tuple[list[AiDiagnostic], int]:
        """
        Get paginated diagnostics for a patient, ordered by test date (newest first)

        Args:
            patient_id: The patient ID to get diagnostics for
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            tuple: (list of diagnostics, total count)
        """
        try:
            # Get total count
            total = await self.collection.count_documents({"patient_id": patient_id})

            # Get paginated results
            cursor = self.collection.find(
                {"patient_id": patient_id}
            ).sort("test_date", -1).skip(skip).limit(limit)

            docs = await cursor.to_list(length=limit)
            diagnostics = [AiDiagnostic(**doc) for doc in docs]

            self.logger.info(
                f"Retrieved {len(diagnostics)} of {total} diagnostics for patient: {patient_id}"
            )

            return diagnostics, total

        except Exception as e:
            self.logger.error(
                f"Error getting paginated diagnostics by patient_id: {e}")
            return [], 0

    async def get_latest_patient_diagnostic(self, patient_id: str) -> AiDiagnostic | None:
        """Get the most recent diagnostic for a patient"""
        try:
            doc = await self.collection.find_one(
                {"patient_id": patient_id},
                sort=[("test_date", -1)]
            )

            return AiDiagnostic(**doc) if doc else None

        except Exception as e:
            self.logger.error(f"Error getting latest patient diagnostic: {e}")
            return None

    async def get_by_created_by(self, user_id: str, limit: int = 50) -> list[AiDiagnostic]:
        """Get diagnostics created by a specific user"""
        try:
            cursor = self.collection.find(
                {"created_by": user_id}
            ).sort("created_at", -1).limit(limit)

            docs = await cursor.to_list(length=limit)
            return [AiDiagnostic(**doc) for doc in docs]

        except Exception as e:
            self.logger.error(f"Error getting diagnostics by created_by: {e}")
            return []

    async def get_next_sequence_number(self, patient_id: str) -> int:
        """Get the next sequence number for a patient's diagnostics"""
        try:
            # Find the highest sequence number for this patient
            doc = await self.collection.find_one(
                {"patient_id": patient_id},
                sort=[("sequence_number", -1)]
            )

            return (doc["sequence_number"] + 1) if doc else 1

        except Exception as e:
            self.logger.error(f"Error getting next sequence number: {e}")
            return 1

    async def add_veterinarian_review(
        self,
        diagnostic_id: str,
        review_data: dict
    ) -> bool:
        """Add veterinarian review to a diagnostic"""
        try:
            review_data["reviewed_at"] = datetime.now(timezone.utc)

            result = await self.collection.update_one(
                {"_id": diagnostic_id},
                {"$set": {"veterinarian_review": review_data}}
            )

            if result.modified_count > 0:
                self.logger.info(
                    f"Added veterinarian review to diagnostic: {diagnostic_id}")
                return True
            return False

        except Exception as e:
            self.logger.error(f"Error adding veterinarian review: {e}")
            return False

    async def get_pending_reviews(self) -> list[AiDiagnostic]:
        """Get diagnostics that need veterinarian review"""
        try:
            cursor = self.collection.find(
                {"veterinarian_review": None}
            ).sort("created_at", 1)

            # Limit to 100 pending reviews
            docs = await cursor.to_list(length=100)
            return [AiDiagnostic(**doc) for doc in docs]

        except Exception as e:
            self.logger.error(f"Error getting pending reviews: {e}")
            return []

    async def update_processing_info(
        self,
        diagnostic_id: str,
        processing_info: dict
    ) -> bool:
        """Update processing information for a diagnostic"""
        try:
            result = await self.collection.update_one(
                {"_id": diagnostic_id},
                {"$set": {"processing_info": processing_info}}
            )

            return result.modified_count > 0

        except Exception as e:
            self.logger.error(f"Error updating processing info: {e}")
            return False

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    async def count_for_patient(self, patient_id: str) -> int:
        """Return total number of diagnostics (tests) linked to a patient."""
        try:
            return await self.collection.count_documents({"patient_id": patient_id})
        except Exception as e:
            self.logger.error(
                f"Error counting diagnostics for patient {patient_id}: {e}")
            return 0
