from fastapi import HTTPException, APIRouter, UploadFile, File, BackgroundTasks
from fastapi.responses import JSONResponse
from pathlib import Path

from app.services import pdf_analysis_service
from app.utils.logger_utils import Logger
from app.utils.file_utils import ModelOutputParserUtility

logger = Logger.setup_logging().getChild("analysis_router")

router = APIRouter()


@router.post("/pdf_analysis")
async def analyze_pdf_file_endpoint(
		file: UploadFile = File(...),
		background_tasks: BackgroundTasks = BackgroundTasks()
):
	logger.info(f"Received PDF analysis request: {file.filename}")
	if file.content_type != "application/pdf":
		logger.exception(
			f"Rejected upload: unsupported content type: {file.content_type}")
		raise HTTPException(status_code = 400,
							detail = "Solo file PDF sono accettati.")

	try:
		result = await pdf_analysis_service.analyze_uploaded_pdf_file_background(
			file, background_tasks)
		logger.info(
			f"PDF analysis completed successfully for: {file.filename}")
		return JSONResponse(content = result)

	except HTTPException as http_error:
		logger.error(f"HTTPException: {http_error}")
		raise

	except Exception as error:
		logger.exception("Unexpected error during PDF analysis")
		raise HTTPException(status_code = 500,
							detail = f"Errore interno: {error}")


@router.get("/pdf_analysis_result/{uuid}")
async def get_analysis_result(uuid: str, structured: bool = False):
	try:
		result_file = Path(f"data/blood_work_pdfs/{uuid}/model_output.txt")
		if not result_file.exists():
			logger.info(f"Model output not ready yet for {uuid}")
			return JSONResponse(status_code = 202,
								content = {"detail": "Risultato non ancora "
													 "pronto"
										   })
		try:
			parsed = ModelOutputParserUtility.parse_model_output_from_txt(
				result_file)
		except Exception as parsing_error:
			logger.exception(
				f"Error parsing structured output: {parsing_error}")
			raise HTTPException(status_code = 500, detail = parsing_error)

		return {
			"uuid": uuid,
			"parsed": parsed,
		}

	except Exception as error:
		logger.exception(
			f"Errore durante il recupero del risultato per {uuid}")
		raise HTTPException(status_code = 500,
							detail = f"Errore interno: {error}")
