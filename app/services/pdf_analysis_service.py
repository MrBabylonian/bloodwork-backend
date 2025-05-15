from fastapi import UploadFile
from uuid import uuid4
from pathlib import Path

from app.utils.file_utils import FileConverter
from app.utils.logger_utils import Logger
from app.services.vision_model_inference_service import \
	RemoveVisionInferenceService
from app.services.vision_model_inference_service import prompt

logger = Logger.setup_logging().getChild("pdf_analysis_service")

# Define the directory where uploaded PDF files will be saved
PDF_UPLOADS_ROOT_DIRECTORY: Path = Path("data/blood_work_pdfs")
PDF_UPLOADS_ROOT_DIRECTORY.mkdir(parents = True, exist_ok = True)


async def analyze_uploaded_pdf_file(file: UploadFile) -> dict:
	"""
	Orchestrates the workflow: saves the uploaded PDF, converts to images,
	runs vision inference, and returns the parsed results.
	:param file: FastAPI UploadFile for the PDF
	:return: dict: dict with inference results
	"""
	# Generate a unique UUID to track this PDF
	pdf_uuid: str = str(uuid4())

	# Create a dedicated folder for this upload
	upload_folder: Path = PDF_UPLOADS_ROOT_DIRECTORY / pdf_uuid
	upload_folder.mkdir(parents = True, exist_ok = True)

	# Build the full path where the PDF file will be saved
	pdf_file_path: Path = upload_folder / f"{pdf_uuid}.pdf"

	logger.info(f"Saving uploaded PDF to {pdf_file_path}")

	try:
		# Write the PDF to the disk
		content = await file.read()
		with open(pdf_file_path, "wb") as saved_file:
			saved_file.write(content)
		logger.info(f"PDF file saved successfully: {saved_file.name}")
	except Exception as pdf_saving_error:
		logger.exception(
			f"Failed to save the uploaded PDF file: {pdf_saving_error}")

	# Create the subfolder to hold the converted images
	image_output_folder: Path = upload_folder / "converted_images"
	image_output_folder.mkdir(parents = True, exist_ok = True)

	try:
		# Convert the PDF to images and get their paths
		image_path_list: list = FileConverter.convert_pdf_to_image_list(
			full_pdf_file_path = str(pdf_file_path),
			output_folder = image_output_folder,
			base_filename_prefix = pdf_uuid,
		)
		logger.info(f"PDF conversion produced {len(image_path_list)} images")
	except Exception as pdf_to_image_conversion_error:
		logger.exception(
			f"PDF to image conversion failed with error: {pdf_to_image_conversion_error}")

	try:
		logger.info("Starting vision model inference")
		vision_inference_service = RemoveVisionInferenceService(
			"http://127.0.0.1:4000")
		model_response = await vision_inference_service.run_remote_inference(
			image_file_paths = image_path_list,  # noqa
			diagnostic_prompt = prompt,
			model_name = "gemma3:27b",
		)
		logger.info("Vision model inference completed")
	except Exception as vision_model_inference_error:
		logger.exception(
			f"Vision model inference failed with error: {vision_model_inference_error}"
		)
		model_response = "Error during vision model inference"

	# Return a structured response
	return {
		"pdf_uuid": pdf_uuid,
		"pdf_path": pdf_file_path.as_posix(),
		"converted_images": image_path_list,
		"model_output": model_response,
		"suggestion": (
			"The PDF was successfully processed and analyzed by the vision "
			"model"
		)
	}
