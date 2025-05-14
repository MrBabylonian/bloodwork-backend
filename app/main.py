from fastapi import FastAPI
from app.routers import analysis_router

from app.utils.logger_utils import Logger

Logger.setup_logging()

logger = Logger.setup_logging().getChild("bloodwork.main")

try:
	# Create a FastAPI instance
	app = FastAPI(
		title = "Blood Work Analysis Backend",
		description = "API for analyzing veterinary blood test PDFs using a "
					  "vision model ",
		version = "0.1.0",
	)
	logger.info("FastAPI app initialized successfully.")

	# Include the router that handles PDF upload and analysis
	# This keeps our endpoint modular and easier to maintain
	app.include_router(
		analysis_router.router, prefix = "/analysis", tags = ["PDF Analysis"]
	)
	logger.info("Router for PDF analysis included successfully.")
except Exception as error:
	logger.exception("Failed to initialize FastAPI app: %s", error)
	raise
