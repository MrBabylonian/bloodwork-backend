from fastapi import UploadFile, HTTPException, BackgroundTasks
from uuid import uuid4
from pathlib import Path
from tempfile import NamedTemporaryFile
from shutil import copyfileobj
import asyncio

from app.utils.file_utils import FileConverter
from app.utils.logger_utils import Logger
from app.services.vision_model_inference_service import \
	RemoveVisionInferenceService

logger = Logger.setup_logging().getChild("pdf_analysis_service")

PDF_UPLOADS_ROOT_DIRECTORY: Path = Path("data/blood_work_pdfs")
PDF_UPLOADS_ROOT_DIRECTORY.mkdir(parents = True, exist_ok = True)

VISION_SERVER_URL = "http://localhost:4000"
remote_vision_inference_service = RemoveVisionInferenceService(
	VISION_SERVER_URL)


def call_inference_and_save_output(
		image_path_list: list[Path],
		upload_folder: Path,
		pdf_uuid: str
) -> None:
	try:
		logger.info(f"Running inference on images for UUID {pdf_uuid}...")

		loop = asyncio.new_event_loop()
		asyncio.set_event_loop(loop)

		model_response: str = loop.run_until_complete(
			remote_vision_inference_service.run_remote_inference(
				image_file_paths = image_path_list,
				model_name = "llava:7b"
			)
		)

		model_output_path: Path = upload_folder / "model_output.txt"
		with open(model_output_path, "w", encoding = "utf-8") as f:
			f.write(model_response)

		logger.info(f"Model output saved to {model_output_path}")

	except Exception as error:
		logger.exception(
			f"Failed to run or save inference for UUID: {pdf_uuid} Error: {error}")
		raise


async def analyze_uploaded_pdf_file_background(
		file: UploadFile,
		background_tasks: BackgroundTasks
) -> dict[str, str]:
	try:
		pdf_uuid: str = str(uuid4())
		upload_folder: Path = PDF_UPLOADS_ROOT_DIRECTORY / pdf_uuid
		upload_folder.mkdir(parents = True, exist_ok = True)

		# Save uploaded PDF to disk
		pdf_path: Path = upload_folder / file.filename
		with NamedTemporaryFile(delete = False) as tmp:
			copyfileobj(file.file, tmp)
			tmp_path = Path(tmp.name)
		tmp_path.replace(pdf_path)

		logger.info(f"PDF saved: {pdf_path}")

		image_path_list: list[Path] = FileConverter.convert_pdf_to_image_list(
			str(pdf_path),
			output_folder = upload_folder,
			base_filename_prefix = pdf_uuid
		)
		logger.info(f"Converted to {len(image_path_list)} image(s)")

		background_tasks.add_task(call_inference_and_save_output,
								  image_path_list, upload_folder, pdf_uuid)

		return {
			"pdf_uuid": pdf_uuid,
			"message": "Analisi in corso. Torna più tardi per vedere i risultati."
		}

	except Exception as error:
		logger.error(f"Failed to process PDF: {error}")
		raise HTTPException(status_code = 500,
							detail = "Errore interno durante l'analisi")
