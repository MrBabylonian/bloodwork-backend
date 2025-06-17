"""
PDF analysis service for veterinary bloodwork processing.

This module orchestrates the complete PDF analysis workflow including file
upload handling, PDF to image conversion, AI analysis, and result storage.
It maintains the core business logic while ensuring data integrity.

Last updated: 2025-06-17
Author: Bedirhan Gilgiler
"""

import json
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import BackgroundTasks, HTTPException, UploadFile

from app.services.openai_service import BloodworkAnalysisService
from app.utils.file_utils import PdfImageConverter
from app.utils.logger_utils import ApplicationLogger


class PdfAnalysisConfiguration:
    """
    Configuration settings for PDF analysis operations.

    This class centralizes all configuration parameters for the PDF analysis
    workflow, making it easy to modify settings without changing core logic.
    """

    def __init__(self):
        """Initialize configuration with default settings."""
        self.uploads_root_directory = Path("data/blood_work_pdfs")
        self.model_output_filename = "model_output.json"
        self.supported_content_type = "application/pdf"
        self.temp_file_suffix = ".pdf"

        # Ensure uploads directory exists
        self.uploads_root_directory.mkdir(parents=True, exist_ok=True)


class BloodworkPdfAnalysisService:
    """
    Main service for processing veterinary PDF bloodwork reports.

    This service handles the complete workflow from PDF upload to AI analysis,
    maintaining the original functionality while improving code organization
    and following OOP principles.
    """

    def __init__(self):
        """Initialize the PDF analysis service with required dependencies."""
        self._logger = ApplicationLogger.get_logger("pdf_analysis_service")
        self._config = PdfAnalysisConfiguration()
        self._pdf_converter = PdfImageConverter()
        self._ai_service = BloodworkAnalysisService()

    async def process_uploaded_pdf_in_background(
        self,
        uploaded_file: UploadFile,
        background_tasks: BackgroundTasks
    ) -> Dict[str, str]:
        """
        Process an uploaded PDF file and schedule AI analysis in the background.

        This method handles the initial PDF processing steps synchronously,
        then schedules the AI analysis to run in the background to avoid
        blocking the API response.

        Args:
            uploaded_file (UploadFile): The uploaded PDF file
            background_tasks (BackgroundTasks): FastAPI background tasks manager

        Returns:
            Dict[str, str]: Response containing PDF UUID and status message

        Raises:
            HTTPException: If file validation or processing fails

        Example:
            >>> service = BloodworkPdfAnalysisService()
            >>> result = await service.process_uploaded_pdf_in_background(
            ...     pdf_file, background_tasks
            ... )
        """
        # Validate file type
        self._validate_uploaded_file(uploaded_file)

        # Generate unique identifier for this analysis session
        analysis_uuid = str(uuid4())

        self._logger.info(
            f"Starting PDF analysis for: {uploaded_file.filename} "
            f"(UUID: {analysis_uuid})"
        )

        temp_pdf_path: Optional[Path] = None

        try:
            # Create working directory for this analysis
            analysis_directory = self._create_analysis_directory(analysis_uuid)

            # Save uploaded file to temporary location
            temp_pdf_path = await self._save_uploaded_file_temporarily(uploaded_file)

            # Convert PDF to images
            image_paths = self._convert_pdf_to_images(
                temp_pdf_path,
                analysis_directory,
                analysis_uuid
            )

            # Schedule AI analysis in background
            background_tasks.add_task(
                self._perform_ai_analysis_and_save_results,
                image_paths,
                analysis_directory,
                analysis_uuid
            )

            return {
                "pdf_uuid": analysis_uuid,
                "message": "Analisi in corso. Torna più tardi per vedere i risultati."
            }

        except Exception as error:
            error_msg = f"Failed to process PDF: {uploaded_file.filename}"
            self._logger.exception(f"{error_msg} - Error: {error}")
            raise HTTPException(
                status_code=500,
                detail="Errore durante l'analisi del PDF"
            ) from error

        finally:
            # Clean up temporary file
            self._cleanup_temporary_file(temp_pdf_path)

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

    def _create_analysis_directory(self, analysis_uuid: str) -> Path:
        """
        Create a dedicated directory for this analysis session.

        Args:
            analysis_uuid (str): Unique identifier for the analysis

        Returns:
            Path: Path to the created analysis directory
        """
        analysis_directory = self._config.uploads_root_directory / analysis_uuid
        analysis_directory.mkdir(parents=True, exist_ok=True)

        self._logger.info(f"Created analysis directory: {analysis_directory}")
        return analysis_directory

    async def _save_uploaded_file_temporarily(self, uploaded_file: UploadFile) -> Path:
        """
        Save the uploaded file to a temporary location.

        Args:
            uploaded_file (UploadFile): File to save

        Returns:
            Path: Path to the temporary file

        Raises:
            RuntimeError: If file saving fails
        """
        try:
            with NamedTemporaryFile(
                delete=False,
                suffix=self._config.temp_file_suffix
            ) as temp_file:
                file_content = await uploaded_file.read()
                temp_file.write(file_content)
                temp_file_path = Path(temp_file.name)

            self._logger.info(f"Saved temporary file: {temp_file_path}")
            return temp_file_path

        except Exception as error:
            error_msg = "Failed to save uploaded file temporarily"
            self._logger.exception(f"{error_msg}: {error}")
            raise RuntimeError(error_msg) from error

    def _convert_pdf_to_images(
        self,
        pdf_path: Path,
        output_directory: Path,
        filename_prefix: str
    ) -> List[Path]:
        """
        Convert PDF to high-resolution images.

        Args:
            pdf_path (Path): Path to the PDF file
            output_directory (Path): Directory for output images
            filename_prefix (str): Prefix for image filenames

        Returns:
            List[Path]: List of generated image file paths
        """
        try:
            image_paths = self._pdf_converter.convert_pdf_to_image_list(
                pdf_path,
                output_directory,
                filename_prefix
            )

            self._logger.info(f"Generated {len(image_paths)} images from PDF")
            return image_paths

        except Exception as error:
            error_msg = "Failed to convert PDF to images"
            self._logger.exception(f"{error_msg}: {error}")
            raise RuntimeError(error_msg) from error

    async def _perform_ai_analysis_and_save_results(
        self,
        image_paths: List[Path],
        analysis_directory: Path,
        analysis_uuid: str
    ) -> None:
        """
        Perform AI analysis on images and save results (BACKGROUND TASK).

        This method runs the AI analysis and saves the raw OpenAI response
        to model_output.json as specified in your constraints.

        Args:
            image_paths (List[Path]): List of image file paths
            analysis_directory (Path): Directory for analysis outputs
            analysis_uuid (str): Unique analysis identifier
        """
        try:
            self._logger.info(
                f"Starting AI analysis for {len(image_paths)} images "
                f"(UUID: {analysis_uuid})"
            )

            # Perform AI analysis
            ai_analysis_result = await self._ai_service.analyze_bloodwork_images(
                image_paths
            )

            # Save the raw OpenAI response (as per your constraint)
            await self._save_analysis_result(
                ai_analysis_result,
                analysis_directory,
                analysis_uuid
            )

            self._logger.info(
                f"AI analysis completed for UUID: {analysis_uuid}")

        except Exception as error:
            error_msg = f"AI analysis failed for UUID: {analysis_uuid}"
            self._logger.exception(f"{error_msg} - Error: {error}")

            # Save error information for debugging
            await self._save_error_result(
                error_msg,
                analysis_directory,
                analysis_uuid
            )

    async def _save_analysis_result(
        self,
        analysis_result: str,
        analysis_directory: Path,
        analysis_uuid: str
    ) -> None:
        """
        Save the AI analysis result to file.

        This method saves the raw OpenAI response without modification
        as specified in your constraints.

        Args:
            analysis_result (str): Raw AI analysis result
            analysis_directory (Path): Directory for output files
            analysis_uuid (str): Analysis identifier
        """
        try:
            output_file_path = analysis_directory / self._config.model_output_filename

            # Save the raw response without modification (as per constraint)
            with open(output_file_path, "w", encoding="utf-8") as output_file:
                output_file.write(analysis_result)

            self._logger.info(
                f"Analysis result saved to: {output_file_path} "
                f"(UUID: {analysis_uuid})"
            )

        except Exception as error:
            error_msg = f"Failed to save analysis result for UUID: {analysis_uuid}"
            self._logger.exception(f"{error_msg} - Error: {error}")
            raise RuntimeError(error_msg) from error

    async def _save_error_result(
        self,
        error_message: str,
        analysis_directory: Path,
        analysis_uuid: str
    ) -> None:
        """
        Save error information when analysis fails.

        Args:
            error_message (str): Error message to save
            analysis_directory (Path): Directory for output files
            analysis_uuid (str): Analysis identifier
        """
        try:
            error_file_path = analysis_directory / "error.json"
            error_data = {
                "error": error_message,
                "uuid": analysis_uuid,
                "status": "failed"
            }

            with open(error_file_path, "w", encoding="utf-8") as error_file:
                json.dump(error_data, error_file, indent=2, ensure_ascii=False)

            self._logger.info(f"Error information saved to: {error_file_path}")

        except Exception as save_error:
            self._logger.exception(
                f"Failed to save error information: {save_error}")

    def _cleanup_temporary_file(self, temp_file_path: Optional[Path] = None) -> None:
        """
        Clean up temporary files.

        Args:
            temp_file_path (Optional[Path]): Path to temporary file to remove
        """
        if temp_file_path and temp_file_path.exists():
            try:
                temp_file_path.unlink()
                self._logger.info(
                    f"Cleaned up temporary file: {temp_file_path}")
            except Exception as error:
                self._logger.warning(
                    f"Failed to cleanup temporary file: {error}")


# Legacy compatibility class
class PdfAnalysisService:
    """
    Legacy PDF analysis service for backward compatibility.

    This class provides methods that delegate to the new OOP service
    while maintaining the original interface.
    """

    def __init__(self):
        """Initialize with new service instance."""
        self._new_service = BloodworkPdfAnalysisService()

    async def analyze_with_openai(
        self,
        image_path_list: List[Path],
        upload_folder: Path,
        pdf_uuid: str
    ) -> None:
        """
        Legacy method that maintains the exact same functionality.

        This method preserves your original implementation where the
        OpenAI response is saved to analysis_output.json without modification.
        """
        try:
            logger = ApplicationLogger.get_logger("pdf_analysis_service")
            logger.info(
                f"Running OpenAI analysis for blood work images for UUID {pdf_uuid}"
            )

            # Use the new AI service
            ai_service = BloodworkAnalysisService()
            openai_interpretation = await ai_service.analyze_bloodwork_images(
                image_path_list
            )

            # Save exactly as in your original implementation
            analysis_output_path = upload_folder / "analysis_output.json"
            with open(analysis_output_path, "w", encoding="utf-8") as f:
                f.write(openai_interpretation)

            logger.info(
                f"OpenAI interpretation saved to {analysis_output_path}")

        except Exception as error:
            logger = ApplicationLogger.get_logger("pdf_analysis_service")
            logger.exception(
                f"Failed to run or save OpenAI analysis for UUID: {pdf_uuid} "
                f"Error: {error}"
            )
            raise

    async def analyze_uploaded_pdf_file_background(
        self,
        file: UploadFile,
        background_tasks: BackgroundTasks
    ) -> Dict[str, str]:
        """
        Legacy method that delegates to the new service.

        Args:
            file (UploadFile): Uploaded PDF file
            background_tasks (BackgroundTasks): Background tasks manager

        Returns:
            Dict[str, str]: Analysis result with UUID and message
        """
        return await self._new_service.process_uploaded_pdf_in_background(
            file, background_tasks
        )
