import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class DatabaseConfig:
    """
    MongoDB database configuration settings
    """
    # Connection_string
    connection_string: str = os.getenv(
        "MONGODB_URI", "mongodb://localhost:27017")
    database_name: str = os.getenv("DATABASE_NAME", "veterinary_bloodwork")

    # Connection pool settings
    max_pool_size: int = 10
    min_pool_size: int = 1
    timeout_ms: int = 5000

    # Collection names
    patients_collection: str = "patients"
    ai_diagnostics_collection: str = "ai_diagnostics"
    users_collection: str = "users"
    admins_collection: str = "admins"

    # GridFS settings (for PDF storage)
    gridfs_bucket_name: str = "bloodwork_pdfs"
