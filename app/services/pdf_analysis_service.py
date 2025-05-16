from fastapi import UploadFile
from uuid import uuid4
from pathlib import Path

from app.utils.file_utils import FileConverter
from app.utils.logger_utils import Logger
from app.services.vision_model_inference_service import \
	RemoveVisionInferenceService
from app.services.vision_model_inference_service import prompt

logger = Logger.setup_logging().getChild("pdf_analysis_service")

PDF_UPLOADS_ROOT_DIRECTORY: Path = Path("data/blood_work_pdfs")
PDF_UPLOADS_ROOT_DIRECTORY.mkdir(parents=True, exist_ok=True)


async def analyze_uploaded_pdf_file(file: UploadFile) -> dict:
	pdf_uuid: str = str(uuid4())
	upload_folder: Path = PDF_UPLOADS_ROOT_DIRECTORY / pdf_uuid
	upload_folder.mkdir(parents=True, exist_ok=True)

	pdf_file_path: Path = upload_folder / f"{pdf_uuid}.pdf"
	logger.info(f"Saving uploaded PDF to {pdf_file_path}")

	try:
		content = await file.read()
		with open(pdf_file_path, "wb") as saved_file:
			saved_file.write(content)
		logger.info(f"PDF file saved successfully: {saved_file.name}")
	except Exception as pdf_saving_error:
		logger.exception(f"Failed to save the uploaded PDF: {pdf_saving_error}")

	image_output_folder: Path = upload_folder / "converted_images"
	image_output_folder.mkdir(parents=True, exist_ok=True)

	try:
		image_path_list: list = FileConverter.convert_pdf_to_image_list(
			full_pdf_file_path=str(pdf_file_path),
			output_folder=image_output_folder,
			base_filename_prefix=pdf_uuid,
		)
		logger.info(f"PDF conversion produced {len(image_path_list)} images")
	except Exception as conversion_error:
		logger.exception(f"PDF to image conversion failed: {conversion_error}")

	try:
		logger.info("Starting vision model inference")
		vision_inference_service = RemoveVisionInferenceService("http://127.0.0.1:4000")
		model_response = await vision_inference_service.run_remote_inference(
			image_file_paths=image_path_list,
			diagnostic_prompt=prompt,
			model_name="llava:7b",
		)
		logger.info("Vision model inference completed")
	except Exception as inference_error:
		logger.exception(f"Vision model inference failed: {inference_error}")
		model_response = "Errore durante l'analisi del referto PDF."

	# Save model output to disk for later retrieval
	try:
		result_file_path = upload_folder / "model_output.txt"
		with open(result_file_path, "w", encoding="utf-8") as f:
			f.write(model_response)
		logger.info(f"Model output saved at {result_file_path}")
	except Exception as save_error:
		logger.warning(f"Could not save model output: {save_error}")

	return {
		"pdf_uuid": pdf_uuid,
		"pdf_path": pdf_file_path.as_posix(),
		"converted_images": image_path_list,
		"model_output": model_response,
		"suggestion": (
			"Il referto è stato analizzato correttamente dal modello. "
			"Controlla i risultati e procedi con valutazione clinica."
		)
	}
