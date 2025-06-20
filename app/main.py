"""
Main application entry point for the Veterinary Bloodwork Analyzer.

This module initializes the FastAPI application and configures all necessary
components including routers, logging, and startup events.

Last updated: 2025-06-17
Author: Bedirhan Gilgiler
"""

from app.routers import auth_router, patient_router
from app.routers.analysis_router import AnalysisRouter
from app.utils.logger_utils import ApplicationLogger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


class BloodworkAnalyzerApplication:
    """
    Main application class that encapsulates the FastAPI application configuration.

    This class follows the Zen of Python principle: "Simple is better than complex."
    It provides a clean interface for initializing and configuring the application.
    """

    def __init__(self):
        """Initialize the application with default configuration."""
        self._logger = ApplicationLogger.setup_logging().getChild("main")
        self._app = self._create_fastapi_instance()
        self._configure_middleware()
        self._configure_routers()
        self._configure_events()

    def _create_fastapi_instance(self) -> FastAPI:
        """
        Create and configure the FastAPI application instance.

        Returns:
            FastAPI: Configured FastAPI application instance
        """
        return FastAPI(
            title="Veterinary Bloodwork Analyzer",
            description="API for processing veterinary PDF blood test reports via vision model",
            version="1.0.0"
        )

    def _configure_middleware(self) -> None:
        """Configure application middleware including CORS for development."""
        # Add request logging middleware
        @self._app.middleware("http")
        async def log_requests(request, call_next):
            from app.utils.logger_utils import ApplicationLogger
            logger = ApplicationLogger.get_logger("request_middleware")

            logger.info(
                f"=== REQUEST: {request.method} {request.url.path} ===")
            logger.info(f"Headers: {dict(request.headers)}")

            response = await call_next(request)

            logger.info(f"=== RESPONSE: {response.status_code} ===")
            return response

        # CORS configuration for development
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins="*",
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["*"],
        )
        self._logger.info("CORS middleware configured for development")

    def _configure_routers(self) -> None:
        """Configure and mount all application routers."""
        # Legacy analysis router (original functionality)
        analysis_router = AnalysisRouter()
        self._app.include_router(
            analysis_router.get_router(),
            prefix="/analysis",
            tags=["Legacy Analysis"],
        )

        # Authentication and patient routers
        self._app.include_router(auth_router.router)
        self._app.include_router(patient_router.router)

    def _configure_events(self) -> None:
        """Configure application startup and shutdown events."""
        @self._app.on_event("startup")
        async def startup_event():
            """Handle application startup."""
            from app.dependencies.auth_dependencies import get_database_service
            db_service = get_database_service()
            await db_service.connect()
            await db_service.initialize_database()
            self._logger.info("FastAPI application has started successfully.")

        @self._app.on_event("shutdown")
        async def shutdown_event():
            """Handle application shutdown."""
            from app.dependencies.auth_dependencies import get_database_service
            db_service = get_database_service()
            await db_service.disconnect()
            self._logger.info("FastAPI application is shutting down.")

    def get_app(self) -> FastAPI:
        """
        Get the configured FastAPI application instance.

        Returns:
            FastAPI: The configured application instance
        """
        return self._app


# Create application instance
bloodwork_app = BloodworkAnalyzerApplication()
app = bloodwork_app.get_app()
