#!/usr/bin/env python
"""
Admin Account Creation Script

This script creates a new admin account in the database.
Fill in the credentials before running.

Usage:
    python create_admin.py
"""

import asyncio
import os
import socket
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

from app.auth.password_service import PasswordService
from app.config.database_config import DatabaseConfig
from app.models.database_models import Admin
from app.repositories.admin_repository import AdminRepository
from app.services.database_service import DatabaseService

# Add the parent directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


def check_mongodb_running(connection_string):
    """Check if MongoDB is running at the given connection string."""
    try:
        # Parse the MongoDB URI
        parsed_uri = urlparse(connection_string)

        # Extract host and port
        host = parsed_uri.hostname or 'localhost'
        port = parsed_uri.port or 27017

        # Try to connect to the MongoDB port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)  # 2 second timeout
        result = sock.connect_ex((host, port))
        sock.close()

        if result == 0:
            return True
        else:
            print(f"❌ MongoDB does not appear to be running at {host}:{port}")
            print("   Please make sure MongoDB is installed and running.")
            print(
                "   On macOS, you can start it with: brew services start mongodb-community")
            print("   On Windows, ensure the MongoDB service is running.")
            print("   On Linux, use: sudo systemctl start mongod")
            return False
    except Exception as e:
        print(f"❌ Error checking MongoDB connection: {e}")
        return False


async def test_database_connection(db_service):
    """Test the database connection and print diagnostic information."""
    try:
        # Check if client is connected
        if db_service.client is None:
            print("❌ MongoDB client is not initialized")
            return False

        # Check if database is accessible
        if db_service.database is None:
            print("❌ Database is not accessible")
            return False

        # Print connection info
        print(f"MongoDB URI: {db_service.client.address}")
        print(f"Database name: {db_service.database.name}")

        # Test if we can list collections
        collections = await db_service.database.list_collection_names()
        print(f"Collections in database: {', '.join(collections)}")

        # Check if admins collection exists
        if "admins" in collections:
            count = await db_service.admins.count_documents({})
            print(f"Number of existing admin documents: {count}")
        else:
            print("Warning: 'admins' collection does not exist yet (will be created)")

        return True
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")
        return False


async def create_admin_account():
    """Create a new admin account with the provided credentials."""

    # ===== FILL IN THESE CREDENTIALS =====
    username = "b.gilgiler"  # e.g., "admin"
    email = "b.gilgiler@abivet.com"     # e.g., "admin@example.com"
    password = "Nicetry+34"  # e.g., "SecurePassword123!"
    # =====================================

    # Validate inputs
    if not username or not email or not password:
        print("Error: Please fill in the username, email, and password in the script.")
        return False

    try:
        # Initialize database connection
        print("Connecting to database...")
        db_config = DatabaseConfig()

        # Print database configuration for debugging
        print(f"MongoDB URI: {db_config.connection_string}")
        print(f"Database name: {db_config.database_name}")

        # Check if MongoDB is running
        if not check_mongodb_running(db_config.connection_string):
            return False

        db_service = DatabaseService(db_config)

        # Connect to the database
        print("Establishing database connection...")
        connection_success = await db_service.connect()
        if not connection_success:
            print("❌ Failed to connect to MongoDB using the connection string.")
            return False

        # Test database connection
        print("\nTesting database connection...")
        connection_ok = await test_database_connection(db_service)
        if not connection_ok:
            print("\n❌ Failed to connect to the database. Please check:")
            print("   1. Is MongoDB running?")
            print("   2. Is the connection string correct?")
            print("   3. Does the database exist?")
            print("   4. Do you have the right permissions?")
            return False

        print("\n✅ Database connection successful!")

        # Initialize repositories
        admin_repo = AdminRepository(db_service)

        # Check if admin with username or email already exists
        print(f"\nChecking if username '{username}' already exists...")
        existing_admin_by_username = await admin_repo.get_by_username(username)
        if existing_admin_by_username:
            print(f"❌ Error: Admin with username '{username}' already exists.")
            return False

        print(f"Checking if email '{email}' already exists...")
        existing_admin_by_email = await admin_repo.get_by_email(email)
        if existing_admin_by_email:
            print(f"❌ Error: Admin with email '{email}' already exists.")
            return False

        # Generate admin ID using MongoDB's atomic operations
        print("\nGenerating admin ID...")
        admin_id = await db_service.get_next_sequential_id("admin")
        print(f"Generated admin ID: {admin_id}")

        # Hash password
        print("Hashing password...")
        password_service = PasswordService()
        hashed_password = password_service.hash_password(password)

        # Create admin object
        print("\nCreating admin object...")
        admin = Admin(
            _id=admin_id,
            username=username,
            email=email,
            hashed_password=hashed_password,
            profile={
                "first_name": "",
                "last_name": ""
            },
            created_at=datetime.now(timezone.utc)
        )

        # Save admin to database
        print("Saving admin to database...")
        created_admin = await admin_repo.create(admin)

        if created_admin:
            print("\n✅ Admin account created successfully!")
            print(f"ID: {created_admin.admin_id}")
            print(f"Username: {created_admin.username}")
            print(f"Email: {created_admin.email}")

            # Disconnect from the database
            await db_service.disconnect()
            return True
        else:
            print("\n❌ Error: Failed to create admin account.")

            # Disconnect from the database
            await db_service.disconnect()
            return False

    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Admin Account Creation Script")
    print("============================")
    print("This script will create a new admin account.")
    print()

    asyncio.run(create_admin_account())
