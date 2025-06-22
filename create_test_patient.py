#!/usr/bin/env python3
"""
Script to create a test patient in the database for testing purposes.
"""

import asyncio
import datetime
from datetime import timezone

from app.config.database_config import DatabaseConfig
from app.repositories.repository_factory import RepositoryFactory
from app.services.database_service import DatabaseService


async def create_test_patient():
    """Create a test patient in the database"""
    # Connect to database
    db_config = DatabaseConfig()
    db_service = DatabaseService(db_config)

    connected = await db_service.connect()
    if not connected:
        print("Failed to connect to database")
        return

    print("Connected to database successfully")

    try:
        # Create repository factory
        repo_factory = RepositoryFactory(db_service)

        # Initialize sequence counters if needed
        await repo_factory.sequence_counter_repository.initialize_counters()

        # Generate patient ID
        patient_id = await repo_factory.sequence_counter_repository.get_next_id("patient")

        # Use datetime for birthdate since MongoDB can't handle Python date objects
        birthdate = datetime.datetime(
            2018, 5, 15, 0, 0, 0, tzinfo=timezone.utc)

        # Create patient document directly for MongoDB
        # This bypasses the Pydantic model validation that would convert datetime to date
        patient_data = {
            "_id": patient_id,
            "name": "Max",
            "species": "Canine",
            "breed": "Golden Retriever",
            "birthdate": birthdate,  # MongoDB can store this datetime
            "sex": "Male",
            "weight": 32.5,
            "owner_info": {
                "name": "John Doe",
                "phone": "555-123-4567",
                "email": "john.doe@example.com",
                "address": "123 Main St, Anytown, USA"
            },
            "medical_history": {
                "allergies": ["Chicken"],
                "previous_conditions": ["Ear infection (2022)"],
                "medications": ["Heartworm preventative"]
            },
            "created_by": "VET-001",
            "assigned_to": "VET-001",
            "created_at": datetime.datetime.now(timezone.utc),
            "updated_at": datetime.datetime.now(timezone.utc),
            "is_active": True
        }

        # Insert directly into collection
        result = await db_service.patients.insert_one(patient_data)

        if result.acknowledged:
            print(f"Test patient created successfully with ID: {patient_id}")
            print("Patient details: Max, Canine, Golden Retriever")
        else:
            print("Failed to create test patient")

    except Exception as e:
        print(f"Error creating test patient: {e}")

    finally:
        # Disconnect from database
        await db_service.disconnect()
        print("Disconnected from database")


if __name__ == "__main__":
    asyncio.run(create_test_patient())
