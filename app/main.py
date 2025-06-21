"""
Main FastAPI application for veterinary bloodwork analysis system.

This module sets up the FastAPI application with all routers, middleware,
startup/shutdown events, and dependencies.

Last updated: 2025-06-20
Author: Bedirhan Gilgiler
"""

import os
import sys

import uvicorn
from app.dependencies.auth_dependencies import (
    get_database_service,
    get_repository_factory,
    require_authenticated,
)
from app.routers import analysis_router, auth_router, patient_router
from app.utils.logger_utils import ApplicationLogger
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

# Add parent directory to path for local imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Initialize the FastAPI application
app = FastAPI(
    title="Veterinary Bloodwork Analysis API",
    description="API for veterinary bloodwork analysis with AI-powered diagnostics",
    version="1.0.0",
)

# Logger
logger = ApplicationLogger.get_logger(__name__)

# Initialize services - use the same instances as in the dependency injection system
db_service = get_database_service()
repository_factory = get_repository_factory(db_service)

# CORS Configuration
origins = [
    '*'
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files only if the directory exists
static_dir = os.path.join(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    logger.info(f"Static files directory mounted from: {static_dir}")
else:
    logger.warning(
        f"Static files directory not found at: {static_dir}. Static files will not be served.")


# Startup and Shutdown Events
@app.on_event("startup")
async def startup_db_client():
    """Connect to database on startup"""
    logger.info("Starting up application...")

    try:
        await db_service.connect()
        await db_service.initialize_database()

        # Initialize sequence counters
        await repository_factory.sequence_counter_repository.initialize_counters()

        logger.info("Application startup completed")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        # Exit application if critical services fail
        sys.exit(1)


@app.on_event("shutdown")
async def shutdown_db_client():
    """Disconnect from database on shutdown"""
    logger.info("Shutting down application...")
    await db_service.disconnect()


# Register Routers
app.include_router(auth_router.router, tags=["Authentication"])
app.include_router(
    patient_router.router, tags=["Patient Management"]
)
app.include_router(
    analysis_router.router, prefix="/api/analysis", tags=["Bloodwork Analysis"]
)


# Error Handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Global exception handler for uncaught exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error, please try again later"},
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/protected")
async def protected_route(current_user=Depends(require_authenticated)):
    """Test protected route"""
    return {"message": f"Hello, {current_user.role}!"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
