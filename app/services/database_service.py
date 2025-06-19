from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorGridFSBucket,
)
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.config.database_config import DatabaseConfig
from app.utils.logger_utils import ApplicationLogger


class DatabaseService:
    """
    MongoDB database service for handling connections and operations
    """

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.client: AsyncIOMotorClient | None = None
        self.database: AsyncIOMotorDatabase | None = None
        self.gridfs: AsyncIOMotorGridFSBucket | None = None
        self.logger = ApplicationLogger.get_logger(__name__)

    async def initialize_database(self) -> bool:
        """
        Initialize database with required indexes for optimal performance

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            self.logger.info("Initializing database indexes...")

            # Patient collection indexes
            await self.patients.create_index("patient_id", unique=True)
            await self.patients.create_index("assigned_to")
            await self.patients.create_index([("name", "text"), ("owner_info.name", "text")])

            # AI Diagnostics collection indexes
            await self.ai_diagnostics.create_index([("patient_id", 1), ("test_date", -1)])
            await self.ai_diagnostics.create_index("created_by")
            await self.ai_diagnostics.create_index("sequence_number")

            # Users collection indexes
            await self.users.create_index("username", unique=True)
            await self.users.create_index("email", unique=True)
            await self.users.create_index("approval_status")

            # Admins collection indexes
            await self.admins.create_index("username", unique=True)
            await self.admins.create_index("email", unique=True)

            # Refresh tokens collection indexes
            await self.refresh_tokens.create_index("token_hash", unique=True)
            await self.refresh_tokens.create_index("user_id")
            await self.refresh_tokens.create_index("expires_at")

            self.logger.info("Database indexes created successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize database indexes: {e}")
            return False

    async def connect(self) -> bool:
        """
        Connect to MongoDB database

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.logger.info("Attempting to connect to MongoDB...")

            self.client = AsyncIOMotorClient(
                self.config.connection_string,
                maxPoolSize=self.config.max_pool_size,
                minPoolSize=self.config.min_pool_size,
                serverSelectionTimeoutMS=self.config.timeout_ms
            )

            # Test the connection
            await self.client.admin.command('ping')

            # Get database reference
            self.database = self.client[self.config.database_name]

            # Initialize GridFS bucket
            self.gridfs = AsyncIOMotorGridFSBucket(self.database)

            self.logger.info(
                f"Successfully connected to MongoDB database: {self.config.database_name}")
            return True

        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            self.logger.error(
                f"Unexpected error during MongoDB connection: {e}")
            return False

    async def disconnect(self) -> None:
        """
        Disconnect from MongoDB database
        """
        if self.client:
            self.client.close()
            self.logger.info("Disconnected from MongoDB")

    def get_collection(self, collection_name: str):
        """
        Get a collection from the database

        Args:
            collection_name: Name of the collection to retrieve

        Returns:
            AsyncIOMotorCollection: The requested collection

        Raises:
            RuntimeError: If database is not connected
        """
        if self.database is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        return self.database[collection_name]

    # Collection property getters for easy access
    @property
    def patients(self):
        """Get patients collection"""
        return self.get_collection(self.config.patients_collection)

    @property
    def ai_diagnostics(self):
        """Get ai_diagnostics collection"""
        return self.get_collection(self.config.ai_diagnostics_collection)

    @property
    def users(self):
        """Get users collection"""
        return self.get_collection(self.config.users_collection)

    @property
    def admins(self):
        """Get admins collection"""
        return self.get_collection(self.config.admins_collection)

    @property
    def refresh_tokens(self):
        """Get refresh_tokens collection"""
        return self.get_collection("refresh_tokens")

    async def store_pdf_file(self, file_data: bytes, filename: str) -> str:
        """
        Store PDF file in GridFS

        Args:
            file_data: PDF file bytes
            filename: Original filename

        Returns:
            str: GridFS file ID
        """
        if self.gridfs is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        file_id = await self.gridfs.upload_from_stream(
            filename,
            file_data,
            metadata={"content_type": "application/pdf"}
        )

        self.logger.info(
            f"Stored PDF file {filename} with GridFS ID: {file_id}")
        return str(file_id)

    async def get_pdf_file(self, file_id: str) -> bytes:
        """
        Retrieve PDF file from GridFS

        Args:
            file_id: GridFS file ID

        Returns:
            bytes: PDF file data
        """
        if self.gridfs is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        from bson import ObjectId
        grid_out = await self.gridfs.open_download_stream(ObjectId(file_id))
        return await grid_out.read()
