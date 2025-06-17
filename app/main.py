"""
Main application entry point for the Veterinary Bloodwork Analyzer.

This module initializes the FastAPI application and configures all necessary
components including routers, logging, and startup events.

Last updated: 2025-06-17
Author: Bedirhan Gilgiler
"""

from fastapi import FastAPI

from app.routers.analysis_router import AnalysisRouter
from app.utils.logger_utils import ApplicationLogger


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

    def _configure_routers(self) -> None:
        """Configure and mount all application routers."""
        analysis_router = AnalysisRouter()
        self._app.include_router(
            analysis_router.get_router(),
            prefix="/analysis"
        )

    def _configure_events(self) -> None:
        """Configure application startup and shutdown events."""
        @self._app.on_event("startup")
        async def startup_event():
            """Handle application startup."""
            self._logger.info("FastAPI application has started successfully.")

        @self._app.on_event("shutdown")
        async def shutdown_event():
            """Handle application shutdown."""
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
