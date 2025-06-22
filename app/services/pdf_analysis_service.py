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
from typing import Any, Dict, List, Union

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
        # Track processing metrics
        self._last_processing_time_ms = 0
        self._model_version = "gpt-4o"
        self._confidence_score = 0.0

    async def process_uploaded_pdf_in_background(
        self,
        uploaded_file: UploadFile,
        patient_id: str,
        background_tasks: BackgroundTasks,
        current_user: Union[Admin, User]
    ) -> Dict[str, str]:
        """
        Process an uploaded PDF file and schedule AI analysis in the background.

        This method stores the PDF in GridFS, creates a diagnostic record,
        then schedules the AI analysis to run in the background.

        Args:
            uploaded_file (UploadFile): The uploaded PDF file
            patient_id (str): The patient ID to link the analysis to
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
            f"Processing PDF: {uploaded_file.filename} (user: {current_user.username}, patient: {patient_id})")

        try:
            # Verify patient exists
            patient_repo = self._repo_factory.patient_repository
            patient = await patient_repo.get_by_id(patient_id)

            if not patient:
                self._logger.error(f"Patient not found: {patient_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Patient not found: {patient_id}"
                )

            # Read PDF file data
            pdf_data = await uploaded_file.read()

            # Store PDF in GridFS
            filename = uploaded_file.filename or "unknown.pdf"
            gridfs_id = await self._db_service.store_pdf_file(pdf_data, filename)

            # Generate a new diagnostic ID using sequence counter
            seq_counter_repo = self._repo_factory.sequence_counter_repository
            diagnostic_id = await seq_counter_repo.get_next_id("diagnostic")

            # Get user ID based on user type
            from app.models.database_models import Admin
            if isinstance(current_user, Admin):
                creator_id = current_user.admin_id
            else:
                creator_id = current_user.user_id

            # Get next sequence number for this patient
            ai_repo = self._repo_factory.ai_diagnostic_repository
            sequence_number = await ai_repo.get_next_sequence_number(patient_id)

            # Create diagnostic record linked to the patient
            diagnostic = AiDiagnostic(
                _id=diagnostic_id,
                patient_id=patient_id,
                sequence_number=sequence_number,
                test_date=datetime.now(timezone.utc),
                ai_diagnostic={},  # Will be filled by AI analysis
                pdf_metadata={
                    "original_filename": filename,
                    "file_size": len(pdf_data),
                    "gridfs_id": gridfs_id,
                    "upload_date": datetime.now(timezone.utc)
                },
                created_by=creator_id
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
                created_diagnostic.diagnostic_id,
                gridfs_id
            )

            return {
                "diagnostic_id": created_diagnostic.diagnostic_id,
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

    async def get_analysis_result(
        self,
        diagnostic_id: str
    ) -> dict[str, Any] | None:
        """
        Get the stored analysis result for a diagnostic.

        Args:
            diagnostic_id (str): The diagnostic ID

        Returns:
            dict | None: The analysis result as a dict, or None if not found
        """
        try:
            ai_repo = self._repo_factory.ai_diagnostic_repository
            diagnostic = await ai_repo.get_by_id(diagnostic_id)

            if not diagnostic:
                self._logger.error(f"Diagnostic not found: {diagnostic_id}")
                return None

            # Check if analysis is complete
            if not diagnostic.ai_diagnostic:
                self._logger.info(
                    f"No analysis found for diagnostic: {diagnostic_id}")
                return None

            # Return the AI diagnostic data
            return diagnostic.ai_diagnostic

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

        self._logger.debug(f"Validated PDF: {uploaded_file.filename}")

    async def _perform_ai_analysis_and_save_results(
        self,
        diagnostic_id: str,
        gridfs_id: str
    ) -> None:
        """
        Execute AI analysis on PDF and save results to database.

        This method runs in the background, processes the PDF through
        OpenAI, and updates the diagnostic record with the results.

        Args:
            diagnostic_id (str): The diagnostic ID
            gridfs_id (str): The GridFS file ID for the PDF
        """
        self._logger.info(
            f"Starting AI analysis for diagnostic: {diagnostic_id}")

        try:
            # Get PDF from GridFS
            pdf_data = await self._db_service.get_pdf_file(gridfs_id)

            # Save PDF to temporary file
            with TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                pdf_path = temp_dir_path / \
                    f"bloodwork{self._config.temp_file_suffix}"

                with open(pdf_path, "wb") as f:
                    f.write(pdf_data)

                # Convert PDF to images
                image_paths = self._convert_pdf_to_images_temp(
                    pdf_path, temp_dir_path)

                if not image_paths:
                    self._logger.error(
                        f"Failed to extract images from PDF: {diagnostic_id}")
                    await self._save_error_to_diagnostic(
                        diagnostic_id, "Failed to extract images from PDF")
                    return

                # Track processing start time
                start_time = datetime.now()

                # Process images with OpenAI API
                analysis_result = await self._ai_service.analyze_bloodwork_images(image_paths)

                # Calculate processing time
                self._last_processing_time_ms = (
                    datetime.now() - start_time).total_seconds() * 1000

                if not analysis_result:
                    self._logger.error(
                        f"Failed to analyze bloodwork: {diagnostic_id}")
                    await self._save_error_to_diagnostic(
                        diagnostic_id, "AI analysis failed")
                    return

                # Save analysis results to database
                await self._save_analysis_to_database(diagnostic_id, analysis_result)

        except Exception as error:
            error_msg = f"Error during AI analysis for diagnostic {diagnostic_id}: {error}"
            self._logger.exception(error_msg)
            await self._save_error_to_diagnostic(
                diagnostic_id, f"Analysis error: {error}")

    def _convert_pdf_to_images_temp(
        self,
        pdf_path: Path,
        temp_dir: Path
    ) -> List[Path]:
        """
        Convert PDF pages to images in temporary directory.

        Args:
            pdf_path (Path): Path to the PDF file
            temp_dir (Path): Path to the temporary directory

        Returns:
            List[Path]: List of paths to the extracted images
        """
        try:
            return self._pdf_converter.convert_pdf_to_image_list(
                pdf_path, temp_dir, "bloodwork_page_"
            )
        except Exception as error:
            self._logger.error(
                f"Error converting PDF to images: {error}")
            return []

    async def _save_analysis_to_database(
        self,
        diagnostic_id: str,
        analysis_result: str
    ) -> None:
        """
        Save AI analysis results to the diagnostic record.

        Args:
            diagnostic_id (str): The diagnostic ID
            analysis_result (str): JSON string with analysis results
        """
        try:
            ai_repo = self._repo_factory.ai_diagnostic_repository

            # Update processing info
            processing_info = {
                "model_version": self.get_model_version(),
                "processing_time_ms": self.get_last_processing_time(),
                "confidence_score": self.get_confidence_score(),
                "processed_at": datetime.now(timezone.utc)
            }

            # Update diagnostic record
            diagnostic = await ai_repo.get_by_id(diagnostic_id)
            if not diagnostic:
                self._logger.error(
                    f"Diagnostic not found for updating: {diagnostic_id}")
                return

            # Update only the necessary fields
            await ai_repo.update_processing_info(diagnostic_id, processing_info)

            # Parse JSON string to dict and update AI diagnostic
            import json
            ai_diagnostic_dict = json.loads(analysis_result)
            update_data = {"ai_diagnostic": ai_diagnostic_dict}
            await ai_repo.collection.update_one(
                {"_id": diagnostic_id},
                {"$set": update_data}
            )

            self._logger.info(
                f"Analysis saved for diagnostic: {diagnostic_id}")

        except Exception as error:
            self._logger.exception(
                f"Error saving analysis to database: {error}")

    async def _save_error_to_diagnostic(
        self,
        diagnostic_id: str,
        error_message: str
    ) -> None:
        """
        Save error message to the diagnostic record.

        Args:
            diagnostic_id (str): The diagnostic ID
            error_message (str): Error message to save
        """
        try:
            ai_repo = self._repo_factory.ai_diagnostic_repository

            processing_info = {
                "error": error_message,
                "failed_at": datetime.now(timezone.utc)
            }

            await ai_repo.update_processing_info(diagnostic_id, processing_info)
            self._logger.info(
                f"Error saved for diagnostic: {diagnostic_id}")

        except Exception as error:
            self._logger.exception(
                f"Error saving diagnostic error: {error}")

    def get_model_version(self) -> str:
        """Get the OpenAI model version used for analysis."""
        return self._model_version

    def get_last_processing_time(self) -> float:
        """Get the processing time of the last analysis in milliseconds."""
        return self._last_processing_time_ms

    def get_confidence_score(self) -> float:
        """Get the confidence score of the last analysis."""
        return self._confidence_score
