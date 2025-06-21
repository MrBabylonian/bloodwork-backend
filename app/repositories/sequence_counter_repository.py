"""
Sequence counter repository for generating sequential IDs.

This module provides functionality to generate human-readable sequential IDs
for various entity types (patients, users, admins, diagnostics).
"""

from app.services.database_service import DatabaseService
from app.utils.logger_utils import ApplicationLogger


class SequenceCounterRepository:
    """Repository for managing sequence counters used for ID generation"""

    def __init__(self, database_service: DatabaseService):
        self.db_service = database_service
        self.collection = database_service.sequence_counters
        self.logger = ApplicationLogger.get_logger(__name__)

    async def get_next_id(self, counter_type: str) -> str:
        """
        Get the next sequential ID for a given entity type.

        Args:
            counter_type: Type of counter (patient, veterinarian, technician, admin, diagnostic)

        Returns:
            str: Next ID in format PREFIX-XXX (e.g., PAT-001, VET-001)
        """
        # Define mapping of counter types to prefixes
        prefix_map = {
            "patient": "PAT",
            "veterinarian": "VET",
            "technician": "TEC",
            "admin": "ADM",
            "diagnostic": "DGN",
            "token": "TKN"
        }

        counter_id = f"{counter_type}_seq"
        # Default to UNK if unknown type
        prefix = prefix_map.get(counter_type, "UNK")

        try:
            # Find and update in one atomic operation
            result = await self.collection.find_one_and_update(
                {"_id": counter_id},
                {"$inc": {"current_value": 1}},
                return_document=True,
                upsert=True
            )

            # If this is a new counter (upsert), set the prefix
            if "prefix" not in result:
                await self.collection.update_one(
                    {"_id": counter_id},
                    {"$set": {"prefix": prefix}}
                )

            # Format the ID with leading zeros (e.g., PAT-001)
            next_value = result.get("current_value", 1)
            next_id = f"{prefix}-{next_value:03d}"

            self.logger.info(
                f"Generated next ID for {counter_type}: {next_id}")
            return next_id

        except Exception as e:
            self.logger.error(f"Error generating sequence ID: {e}")
            # Fallback to a timestamp-based ID in case of error
            import time
            timestamp = int(time.time())
            return f"{prefix}-{timestamp}"

    async def initialize_counters(self) -> bool:
        """
        Initialize sequence counters if they don't exist.
        This ensures all required counters are created during system startup.

        Returns:
            bool: True if successful, False otherwise
        """
        counter_types = {
            "patient_seq": "PAT",
            "veterinarian_seq": "VET",
            "technician_seq": "TEC",
            "admin_seq": "ADM",
            "diagnostic_seq": "DGN",
            "token_seq": "TKN"
        }

        try:
            for counter_id, prefix in counter_types.items():
                # Create counter if it doesn't exist
                await self.collection.update_one(
                    {"_id": counter_id},
                    {"$setOnInsert": {"current_value": 0, "prefix": prefix}},
                    upsert=True
                )

            self.logger.info("Sequence counters initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize sequence counters: {e}")
            return False
