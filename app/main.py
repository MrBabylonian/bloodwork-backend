from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import analysis_router
from app.utils.logger_utils import Logger

# Initialize the application logger
logger = Logger.setup_logging().getChild("main")

# Create the FastAPI app instance
app = FastAPI(
	title="Veterinary Bloodwork Analyzer",
	description="API for processing veterinary PDF blood test reports via vision model",
	version="1.0.0",
)

# CORS configuration to allow frontend access
app.add_middleware(
	CORSMiddleware,
	allow_origins=["https://main.d1wrcuj3ftjjx5.amplifyapp.com"],
	allow_credentials=True,
	allow_methods=["GET, POST"],  # Allow GET, POST, etc.
	allow_headers=["*"],  # Allow custom headers like Content-Type
)

# Mount the router for analysis functionality
app.include_router(analysis_router.router, prefix="/analysis")

# Optional: log app startup
@app.on_event("startup")
async def startup_event():
	logger.info("FastAPI application has started.")
