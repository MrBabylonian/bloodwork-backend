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

    async def create(self, diagnostic: AiDiagnostic) -> AiDiagnostic | None:
        """Create a new diagnostic record"""
        try:
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
            doc = await self.collection.find_one({"diagnostic_id": diagnostic_id})
            return AiDiagnostic(**doc) if doc else None

        except Exception as e:
            self.logger.error(f"Error getting diagnostic by id: {e}")
            return None

    async def get_by_patient_id(self, patient_id: str) -> list[AiDiagnostic]:
        """Get all diagnostics for a patient, ordered by test date"""
        try:
            cursor = self.collection.find(
                {"patient_id": patient_id}
            ).sort("test_date", -1)

            docs = await cursor.to_list(length=None)
            return [AiDiagnostic(**doc) for doc in docs]

        except Exception as e:
            self.logger.error(f"Error getting diagnostics by patient_id: {e}")
            return []

    async def get_latest_by_patient_id(self, patient_id: str) -> AiDiagnostic | None:
        """Get the most recent diagnostic for a patient"""
        try:
            doc = await self.collection.find_one(
                {"patient_id": patient_id},
                sort=[("test_date", -1)]
            )

            return AiDiagnostic(**doc) if doc else None

        except Exception as e:
            self.logger.error(f"Error getting latest diagnostic: {e}")
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
                {"diagnostic_id": diagnostic_id},
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

    async def get_recent(self, limit: int = 20) -> list[AiDiagnostic]:
        """Get recently created diagnostics"""
        try:
            cursor = self.collection.find({}).sort(
                "created_at", -1).limit(limit)
            docs = await cursor.to_list(length=limit)
            return [AiDiagnostic(**doc) for doc in docs]

        except Exception as e:
            self.logger.error(f"Error getting recent diagnostics: {e}")
            return []

    async def get_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> list[AiDiagnostic]:
        """Get diagnostics within a date range"""
        try:
            cursor = self.collection.find({
                "test_date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }).sort("test_date", -1)

            docs = await cursor.to_list(length=None)
            return [AiDiagnostic(**doc) for doc in docs]

        except Exception as e:
            self.logger.error(f"Error getting diagnostics by date range: {e}")
            return []

    async def update_processing_info(
        self,
        diagnostic_id: str,
        processing_info: dict
    ) -> bool:
        """Update processing information for a diagnostic"""
        try:
            result = await self.collection.update_one(
                {"diagnostic_id": diagnostic_id},
                {"$set": {"processing_info": processing_info}}
            )

            return result.modified_count > 0

        except Exception as e:
            self.logger.error(f"Error updating processing info: {e}")
            return False
