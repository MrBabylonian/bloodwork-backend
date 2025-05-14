from fastapi import HTTPException

from fastapi import APIRouter, UploadFile, File
from fastapi.responses import JSONResponse
import logging

from app.services import pdf_analysis_service
from app.utils.logger_utils import Logger

logger = Logger.setup_logging().getChild("analysis_router")

# Create a sub-router specifically for handling PDF analysis
router = APIRouter()


@router.post("/pdf_analysis")
async def analyze_pdf_file_endpoint(file: UploadFile = File(...)):
	"""
	Endpoint to accept a single PDF file and return a diagnostic result
	The PDF passed to the inference service which will process and analyze it
	:param file: The PDF file to be analyzed
	:return: A JSON response containing the analysis result
	"""

	logger.info(f"Received PDF analysis request: filename={file.filename}, "
				f"content_type: {file.content_type}")

	if file.content_type != "application/pdf":
		logger.exception(
			f"Rejected upload: unsupported content type: {file.content_type}")
		raise

	try:
		result_dictionary = await pdf_analysis_service.analyze_uploaded_pdf_file(
			file
		)
		logger.info(f"PDF analysis completed successfully for:"
					f" {file.filename}")
		return JSONResponse(content = result_dictionary)

	except HTTPException as http_exception:
		logger.error(f"HTTPException occurred during PDF analysis: "
					 f"{http_exception}")
		raise

	except Exception as error:
		logger.exception(
			"An unexpected error occurred during PDF analysis: %s", error)
		raise Exception(
			f"An unexpected error occurred during PDF analysis. "
			f"Please try again later. {error}"
		)
