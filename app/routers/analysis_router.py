"""
Analysis router for veterinary bloodwork PDF processing endpoints.

This module defines the REST API endpoints for handling PDF uploads,
processing bloodwork analysis requests, and retrieving results.
It follows FastAPI best practices and provides comprehensive error handling.

Last updated: 2025-06-22
Author: Bedirhan Gilgiler
"""

from typing import Union

from app.dependencies.auth_dependencies import require_authenticated
from app.models.database_models import Admin, User
from app.services.pdf_analysis_service import BloodworkPdfAnalysisService
from app.utils.logger_utils import ApplicationLogger
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
)
from fastapi.responses import JSONResponse


class AnalysisRouter:
    """
    Router class for bloodwork analysis endpoints.

    This class encapsulates all analysis-related API endpoints providing
    a clean interface for PDF processing operations.
    It follows the principle: "Flat is better than nested."
    """

    def __init__(self):
        """Initialize the analysis router with required dependencies."""
        self._logger = ApplicationLogger.get_logger("analysis_router")
        self._router = APIRouter(prefix="/api/v1/analysis", tags=["Analysis"])
        self._pdf_analysis_service = BloodworkPdfAnalysisService()
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Configure all routes for this router."""
        self._router.add_api_route(
            "/upload",
            self.upload_pdf_for_analysis,
            methods=["POST"],
            summary="Upload PDF for analysis",
            description="Upload a PDF bloodwork report for AI-powered analysis"
        )

    async def upload_pdf_for_analysis(
        self,
        file: UploadFile = File(...),
        patient_id: str = Form(...),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        current_user: Union[Admin, User] = Depends(require_authenticated)
    ) -> JSONResponse:
        """
        Endpoint to analyze uploaded PDF bloodwork files.

        This endpoint accepts PDF files, validates them, and initiates
        background processing for AI-powered analysis. The response includes
        a diagnostic ID for tracking the analysis progress.

        Args:
            file (UploadFile): The uploaded PDF file
            patient_id (str): The patient ID to link the analysis to
            background_tasks (BackgroundTasks): FastAPI background task manager
            current_user (User): Authenticated user from JWT token

        Returns:
            JSONResponse: Response with diagnostic ID and status message

        Raises:
            HTTPException: If file validation or processing fails

        Example:
            POST /api/v1/analysis/upload
            Content-Type: multipart/form-data

            Response:
            {
                "diagnostic_id": "DIAG-001",
                "message": "Analysis in progress. Check results later."
            }
        """
        self._logger.info(f"Received PDF analysis request: {file.filename}")
        self._logger.info(f"Current user: {current_user}")
        self._logger.info(f"Patient ID: {patient_id}")

        try:
            # Validate file type
            self._pdf_analysis_service._validate_uploaded_file(file)

            # Process the PDF file
            result = await self._pdf_analysis_service.process_uploaded_pdf_in_background(
                file, patient_id, background_tasks, current_user
            )

            self._logger.info(
                f"PDF analysis initiated successfully for: {file.filename} "
                f"(ID: {result['diagnostic_id']}, Patient: {patient_id})"
            )

            return JSONResponse(content=result)

        except HTTPException:
            # Re-raise HTTP exceptions without modification
            raise

        except Exception as error:
            error_msg = f"Unexpected error during PDF analysis: {error}"
            self._logger.exception(error_msg)
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(error)}"
            ) from error

    # def _validate_pdf_file(self, file: UploadFile) -> None:
    #     """
    #     Validate the uploaded file is a PDF.

    #     Args:
    #         file (UploadFile): File to validate

    #     Raises:
    #         HTTPException: If file is not a valid PDF
    #     """
    #     if file.content_type != "application/pdf":
    #         error_msg = f"Rejected upload: unsupported content type: {file.content_type}"
    #         self._logger.error(error_msg)
    #         raise HTTPException(
    #             status_code=400,
    #             detail="Only PDF files are accepted."
    #         )

    def get_router(self) -> APIRouter:
        """
        Get the configured APIRouter instance.

        Returns:
            APIRouter: The configured router with all endpoints
        """
        return self._router


# Legacy compatibility - create a router instance for backward compatibility
analysis_router_instance = AnalysisRouter()
router = analysis_router_instance.get_router()
