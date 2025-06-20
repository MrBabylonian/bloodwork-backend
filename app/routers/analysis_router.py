"""
Analysis router for veterinary bloodwork PDF processing endpoints.

This module defines the REST API endpoints for handling PDF uploads,
processing bloodwork analysis requests, and retrieving results.
It follows FastAPI best practices and provides comprehensive error handling.

Last updated: 2025-06-17
Author: Bedirhan Gilgiler
"""

from typing import Optional, Union

from app.dependencies.auth_dependencies import require_authenticated
from app.models.database_models import Admin, User
from app.services.pdf_analysis_service import BloodworkPdfAnalysisService
from app.utils.logger_utils import ApplicationLogger
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Response,
    UploadFile,
)
from fastapi.responses import JSONResponse


class AnalysisRouter:
    """
    Router class for bloodwork analysis endpoints.

    This class encapsulates all analysis-related API endpoints providing
    a clean interface for PDF processing and result retrieval operations.
    It follows the principle: "Flat is better than nested."
    """

    def __init__(self):
        """Initialize the analysis router with required dependencies."""
        self._logger = ApplicationLogger.get_logger("analysis_router")
        self._router = APIRouter()
        self._pdf_analysis_service = BloodworkPdfAnalysisService()
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Configure all routes for this router."""
        self._router.add_api_route(
            "/pdf_analysis",
            self.analyze_pdf_file_endpoint,
            methods=["POST"],
            summary="Analyze PDF bloodwork report",
            description="Upload a PDF bloodwork report for AI-powered analysis"
        )

        self._router.add_api_route(
            "/pdf_analysis_result/{diagnostic_id}",
            self.get_analysis_result,
            methods=["GET"],
            summary="Get analysis result",
            description="Retrieve the analysis result for a specific diagnostic ID"
        )

    async def analyze_pdf_file_endpoint(
        self,
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = BackgroundTasks(),
        current_user: Union[Admin, User] = Depends(require_authenticated)
    ) -> JSONResponse:
        """
        Endpoint to analyze uploaded PDF bloodwork files.

        This endpoint accepts PDF files, validates them, and initiates
        background processing for AI-powered analysis. The response includes
        a UUID for tracking the analysis progress.

        Args:
            file (UploadFile): The uploaded PDF file
            background_tasks (BackgroundTasks): FastAPI background task manager
            current_user (User): Authenticated user from JWT token

        Returns:
            JSONResponse: Response with diagnostic ID and status message

        Raises:
            HTTPException: If file validation or processing fails

        Example:
            POST /analysis/pdf_analysis
            Content-Type: multipart/form-data

            Response:
            {
                "pdf_uuid": "12345678-1234-1234-1234-123456789012",
                "message": "Analisi in corso. Torna più tardi per vedere i risultati."
            }
        """
        self._logger.info(f"Received PDF analysis request: {file.filename}")
        self._logger.info(f"Current user: {current_user}")

        try:
            # Validate file type
            self._validate_pdf_file(file)

            # Process the PDF file
            result = await self._pdf_analysis_service.process_uploaded_pdf_in_background(
                file, background_tasks, current_user
            )

            self._logger.info(
                f"PDF analysis initiated successfully for: {file.filename} "
                f"(ID: {result['diagnostic_id']})"
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
                detail=f"Errore interno del server: {str(error)}"
            ) from error

    def _validate_pdf_file(self, file: UploadFile) -> None:
        """
        Validate the uploaded file is a PDF.

        Args:
            file (UploadFile): File to validate

        Raises:
            HTTPException: If file is not a valid PDF
        """
        if file.content_type != "application/pdf":
            error_msg = f"Rejected upload: unsupported content type: {file.content_type}"
            self._logger.error(error_msg)
            raise HTTPException(
                status_code=400,
                detail="Solo file PDF sono accettati."
            )

    async def get_analysis_result(
        self,
        diagnostic_id: str,
        structured: Optional[bool] = False,
        current_user: Union[Admin, User] = Depends(require_authenticated)
    ) -> Response:
        """
        Endpoint to retrieve analysis results by diagnostic ID.

        This endpoint retrieves analysis results from the database instead of 
        the file system, providing better data persistence and access control.

        Args:
            diagnostic_id (str): The diagnostic ID to retrieve results for
            structured (Optional[bool]): Whether to return structured data (unused)
            current_user (User): Authenticated user from JWT token

        Returns:
            Response: Analysis results or status message

        Raises:
            HTTPException: If result retrieval fails

        Example:
            GET /analysis/pdf_analysis_result/60a1b2c3d4e5f6789012345a

            Response (if ready):
            HTTP 200 - Analysis result content

            Response (if not ready):
            HTTP 202 - {"detail": "Risultato non ancora pronto"}
        """
        try:
            # Get analysis result from database
            result = await self._pdf_analysis_service.get_analysis_result_from_database(
                diagnostic_id, current_user
            )

            if result is None:
                self._logger.info(
                    f"Analysis result not ready yet for diagnostic ID: {diagnostic_id}")
                return JSONResponse(
                    status_code=202,
                    content={"detail": "Risultato non ancora pronto"}
                )

            self._logger.info(
                f"Analysis result successfully retrieved for diagnostic ID: {diagnostic_id}"
            )

            return Response(
                content=result,
                media_type="application/json"
            )

        except Exception as error:
            error_msg = f"Error retrieving analysis result for diagnostic ID: {diagnostic_id}"
            self._logger.exception(f"{error_msg} - Error: {error}")
            raise HTTPException(
                status_code=500,
                detail=f"Errore interno del server: {str(error)}"
            ) from error

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
