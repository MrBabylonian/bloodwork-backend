"""
PDF analysis service for veterinary bloodwork processing.

This module orchestrates the complete PDF analysis workflow including PDF 
storage in database, temporary image extraction, AI analysis, and result storage.
It maintains data integrity by storing PDFs in GridFS and analysis results in MongoDB.

Last updated: 2025-06-18
Author: Bedirhan Gilgiler
"""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional, Union

from app.dependencies.auth_dependencies import (
    get_database_service,
    get_repository_factory,
)
from app.models.database_models import Admin, AiDiagnostic, User
from app.services.openai_service import BloodworkAnalysisService
from app.utils.file_utils import PdfImageConverter
from app.utils.logger_utils import ApplicationLogger
from fastapi import BackgroundTasks, HTTPException, UploadFile


class PdfAnalysisConfiguration:
    """
    Configuration settings for PDF analysis operations.

    This class centralizes configuration parameters for the PDF analysis
    workflow with database storage instead of file-based approach.
    """

    def __init__(self):
        """Initialize configuration with default settings."""
        self.supported_content_type = "application/pdf"
        self.temp_file_suffix = ".pdf"


class BloodworkPdfAnalysisService:
    """
    Main service for processing veterinary PDF bloodwork reports.

    This service handles the complete workflow from PDF upload to AI analysis,
    storing PDFs in GridFS and results in MongoDB instead of the file system.
    """

    def __init__(self):
        """Initialize the PDF analysis service with required dependencies."""
        self._logger = ApplicationLogger.get_logger("pdf_analysis_service")
        self._config = PdfAnalysisConfiguration()
        self._pdf_converter = PdfImageConverter()
        self._ai_service = BloodworkAnalysisService()
        self._db_service = get_database_service()
        self._repo_factory = get_repository_factory(self._db_service)

    async def process_uploaded_pdf_in_background(
        self,
        uploaded_file: UploadFile,
        background_tasks: BackgroundTasks,
        current_user: Union[Admin, User]
    ) -> Dict[str, str]:
        """
        Process an uploaded PDF file and schedule AI analysis in the background.

        This method stores the PDF in GridFS, creates a diagnostic record,
        then schedules the AI analysis to run in the background.

        Args:
            uploaded_file (UploadFile): The uploaded PDF file
            background_tasks (BackgroundTasks): FastAPI background tasks manager
            current_user (User): The authenticated user

        Returns:
            Dict[str, str]: Response containing diagnostic ID and status message

        Raises:
            HTTPException: If file validation or processing fails
        """
        # Validate file type
        self._validate_uploaded_file(uploaded_file)

        self._logger.info(
            f"Starting PDF analysis for: {uploaded_file.filename} "
            f"by user: {current_user.username}"
        )

        try:
            # Read PDF file data
            pdf_data = await uploaded_file.read()

            # Store PDF in GridFS
            filename = uploaded_file.filename or "unknown.pdf"
            gridfs_id = await self._db_service.store_pdf_file(pdf_data, filename)

            # Create diagnostic record (will be linked to patient later)
            from bson import ObjectId
            diagnostic = AiDiagnostic(
                patient_id=ObjectId(),  # Temporary placeholder - will be updated when linked
                sequence_number=1,  # Will be updated when linked to patient
                test_date=datetime.now(timezone.utc),
                openai_analysis="",  # Will be filled by AI analysis
                pdf_metadata={
                    "original_filename": filename,
                    "file_size": len(pdf_data),
                    "gridfs_id": gridfs_id,
                    "upload_date": datetime.now(timezone.utc)
                },
                created_by=ObjectId(
                    current_user.id) if current_user.id else ObjectId()
            )

            # Save diagnostic to database
            ai_repo = self._repo_factory.ai_diagnostic_repository
            created_diagnostic = await ai_repo.create(diagnostic)

            if not created_diagnostic:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create diagnostic record"
                )

            # Schedule AI analysis in background
            background_tasks.add_task(
                self._perform_ai_analysis_and_save_results,
                str(created_diagnostic.id),
                gridfs_id
            )

            return {
                "diagnostic_id": str(created_diagnostic.id),
                "message": "Analisi in corso. Torna più tardi per vedere i risultati."
            }

        except HTTPException:
            raise
        except Exception as error:
            error_msg = f"Failed to process PDF: {uploaded_file.filename}"
            self._logger.exception(f"{error_msg} - Error: {error}")
            raise HTTPException(
                status_code=500,
                detail="Errore durante l'analisi del PDF"
            ) from error

    async def get_analysis_result_from_database(
        self,
        diagnostic_id: str,
        current_user: Union[Admin, User]
    ) -> Optional[str]:
        """
        Retrieve analysis result from database.

        Args:
            diagnostic_id (str): The diagnostic ID
            current_user (User): The authenticated user

        Returns:
            Optional[str]: JSON string of analysis result or None if not ready
        """
        try:
            ai_repo = self._repo_factory.ai_diagnostic_repository
            diagnostic = await ai_repo.get_by_id(diagnostic_id)

            if not diagnostic:
                return None

            # Check if analysis is complete
            if not diagnostic.openai_analysis:
                return None

            # Return the OpenAI analysis as-is (already a JSON string)
            return diagnostic.openai_analysis

        except Exception as error:
            self._logger.exception(
                f"Error retrieving analysis result: {error}")
            return None

    def _validate_uploaded_file(self, uploaded_file: UploadFile) -> None:
        """
        Validate the uploaded file meets requirements.

        Args:
            uploaded_file (UploadFile): File to validate

        Raises:
            HTTPException: If file validation fails
        """
        if uploaded_file.content_type != self._config.supported_content_type:
            error_msg = f"Unsupported file type: {uploaded_file.content_type}"
            self._logger.error(error_msg)
            raise HTTPException(
                status_code=400,
                detail="Solo file PDF sono accettati."
            )

        self._logger.info(f"File validation passed: {uploaded_file.filename}")

    async def _perform_ai_analysis_and_save_results(
        self,
        diagnostic_id: str,
        gridfs_id: str
    ) -> None:
        """
        Perform AI analysis on PDF and save results to database.

        This method retrieves the PDF from GridFS, converts it to images temporarily,
        performs AI analysis, saves results to database, and cleans up temporary files.

        Args:
            diagnostic_id (str): The diagnostic record ID
            gridfs_id (str): The GridFS file ID
        """
        try:
            self._logger.info(
                f"Starting AI analysis for diagnostic: {diagnostic_id}")

            # Retrieve PDF from GridFS
            pdf_data = await self._db_service.get_pdf_file(gridfs_id)

            # Create temporary directory for image processing
            with TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)

                # Save PDF temporarily
                temp_pdf_path = temp_dir_path / "temp.pdf"
                with open(temp_pdf_path, "wb") as f:
                    f.write(pdf_data)

                # Convert PDF to images
                image_paths = self._convert_pdf_to_images_temp(
                    temp_pdf_path, temp_dir_path
                )

                # Perform AI analysis
                analysis_result = await self._ai_service.analyze_bloodwork_images(
                    image_paths
                )

                # OpenAI already returns structured JSON as per the prompt
                # Save the result directly to database
                await self._save_analysis_to_database(diagnostic_id, analysis_result)

                # Images are automatically cleaned up when temp directory is deleted

            self._logger.info(
                f"AI analysis completed for diagnostic: {diagnostic_id}")

        except Exception as error:
            self._logger.exception(
                f"Error during AI analysis for diagnostic {diagnostic_id}: {error}"
            )

    def _convert_pdf_to_images_temp(
        self,
        pdf_path: Path,
        temp_dir: Path
    ) -> List[Path]:
        """
        Convert PDF to images in temporary directory.

        Args:
            pdf_path (Path): Path to the PDF file
            temp_dir (Path): Temporary directory for images

        Returns:
            List[Path]: List of image file paths
        """
        try:
            image_paths = self._pdf_converter.convert_pdf_to_image_list(
                pdf_path, temp_dir, "page"
            )
            return [Path(path) for path in image_paths]

        except Exception as error:
            self._logger.exception(f"Error converting PDF to images: {error}")
            raise

    async def _save_analysis_to_database(
        self,
        diagnostic_id: str,
        analysis_result: str
    ) -> None:
        """
        Save AI analysis result to database.

        Args:
            diagnostic_id (str): The diagnostic record ID
            analysis_result (str): The AI analysis result as JSON string
        """
        try:
            ai_repo = self._repo_factory.ai_diagnostic_repository

            # Update diagnostic with analysis result
            from bson import ObjectId
            diagnostic = await ai_repo.get_by_id(diagnostic_id)

            if diagnostic:
                # Store the OpenAI response exactly as received (no parsing)
                diagnostic.openai_analysis = analysis_result

                # Update in database with the original JSON string
                await ai_repo.collection.update_one(
                    {"_id": ObjectId(diagnostic_id)},
                    {"$set": {"openai_analysis": analysis_result}}
                )

                self._logger.info(
                    f"Analysis result saved for diagnostic: {diagnostic_id}")
            else:
                self._logger.error(f"Diagnostic not found: {diagnostic_id}")

        except Exception as error:
            self._logger.exception(
                f"Error saving analysis to database: {error}")
            raise
