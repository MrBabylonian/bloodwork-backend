"""
Analysis router for veterinary bloodwork PDF processing endpoints.

This module defines the REST API endpoints for handling PDF uploads,
processing bloodwork analysis requests, and retrieving results.
It follows FastAPI best practices and provides comprehensive error handling.

Last updated: 2025-06-17
Author: Bedirhan Gilgiler
"""

from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Response,
    UploadFile,
)
from fastapi.responses import JSONResponse

from app.services.pdf_analysis_service import BloodworkPdfAnalysisService
from app.utils.logger_utils import ApplicationLogger


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
            "/pdf_analysis_result/{uuid}",
            self.get_analysis_result,
            methods=["GET"],
            summary="Get analysis result",
            description="Retrieve the analysis result for a specific UUID"
        )

    async def analyze_pdf_file_endpoint(
        self,
        file: UploadFile = File(...),
        background_tasks: BackgroundTasks = BackgroundTasks()
    ) -> JSONResponse:
        """
        Endpoint to analyze uploaded PDF bloodwork files.

        This endpoint accepts PDF files, validates them, and initiates
        background processing for AI-powered analysis. The response includes
        a UUID for tracking the analysis progress.

        Args:
            file (UploadFile): The uploaded PDF file
            background_tasks (BackgroundTasks): FastAPI background task manager

        Returns:
            JSONResponse: Response with UUID and status message

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

        try:
            # Validate file type
            self._validate_pdf_file(file)

            # Process the PDF file
            result = await self._pdf_analysis_service.process_uploaded_pdf_in_background(
                file, background_tasks
            )

            self._logger.info(
                f"PDF analysis initiated successfully for: {file.filename} "
                f"(UUID: {result['pdf_uuid']})"
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
        uuid: str,
        structured: Optional[bool] = False
    ) -> Response:
        """
        Endpoint to retrieve analysis results by UUID.

        This endpoint checks for the existence of analysis results and returns
        them if available. If results are not ready, it returns a 202 status.

        Args:
            uuid (str): The analysis UUID to retrieve results for
            structured (Optional[bool]): Whether to return structured data (unused)

        Returns:
            Response: Analysis results or status message

        Raises:
            HTTPException: If result retrieval fails

        Example:
            GET /analysis/pdf_analysis_result/12345678-1234-1234-1234-123456789012

            Response (if ready):
            HTTP 200 - Analysis result content

            Response (if not ready):
            HTTP 202 - {"detail": "Risultato non ancora pronto"}
        """
        try:
            # Check for the new model output filename first
            result_file_path = Path(
                f"data/blood_work_pdfs/{uuid}/model_output.json")

            # Check if any result file exists
            if not result_file_path.exists():
                self._logger.info(
                    f"Analysis result not ready yet for UUID: {uuid}")
                return JSONResponse(
                    status_code=202,
                    content={"detail": "Risultato non ancora pronto"}
                )

            # Read and return the result
            analysis_result = self._read_analysis_result_file(result_file_path)

            self._logger.info(
                f"Analysis result successfully retrieved for UUID: {uuid} "
                f"from file: {result_file_path.name}"
            )

            return Response(
                content=analysis_result,
                media_type="application/json"
            )

        except Exception as error:
            error_msg = f"Error retrieving analysis result for UUID: {uuid}"
            self._logger.exception(f"{error_msg} - Error: {error}")
            raise HTTPException(
                status_code=500,
                detail=f"Errore interno del server: {str(error)}"
            ) from error

    def _read_analysis_result_file(self, file_path: Path) -> str:
        """
        Read the analysis result from file.

        Args:
            file_path (Path): Path to the result file

        Returns:
            str: Content of the result file

        Raises:
            RuntimeError: If file reading fails
        """
        try:
            with open(file_path, "r", encoding="utf-8") as result_file:
                return result_file.read()

        except Exception as error:
            error_msg = f"Failed to read result file: {file_path}"
            self._logger.exception(f"{error_msg} - Error: {error}")
            raise RuntimeError(error_msg) from error

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
