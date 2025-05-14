import fitz  # PyMuPDF
from pathlib import Path

from app.utils.logger_utils import Logger

logger = Logger.setup_logging().getChild("file_converter")


class FileConverter:
	@staticmethod
	def convert_pdf_to_image_list(
			full_pdf_file_path: str,
			output_folder: Path,
			base_filename_prefix: str
	) -> list[Path]:
		"""
	    Converts a PDF into PNG images, one per page, using PyMuPDF.

	    All images are stored in the given output folder, with filenames
	    that start with the base UUID to match the original PDF.

	    :param full_pdf_file_path: full path to the saved PDF
	    :param output_folder: folder to save images into
	    :param base_filename_prefix: shared prefix (usually the UUID)
	    :return: list of image file paths as forward-slash strings
		"""

		logger.info(
			f"Starting PDF to image conversion for: {full_pdf_file_path}")

		try:
			# Open the PDF using PyMuPDF
			pdf_document = fitz.open(full_pdf_file_path)
		except Exception as error:
			logger.exception(f"Failed to open PDF document:"
							 f"{full_pdf_file_path} error: {error}")
			raise
		# Collect each generated image path here
		converted_image_path_list: list[Path] = []
		total_pages = len(pdf_document)
		logger.info(f"PDF has opened successfully, total pages: {total_pages}")

		for page_index in range(total_pages):
			try:
				logger.info(f"Rendering page {page_index + 1}/{total_pages}")
				# Load a single page from the PDF
				pdf_page = pdf_document[page_index]

				# Calculate scaling for desired PDI
				desired_dpi: int = 300
				# Use a zoom factor to control the DPI of the output image
				# The default DPI for PyMuPDF is 72, so we scale accordingly
				zoom: float = desired_dpi / 72
				scaling_matrix = fitz.Matrix(zoom, zoom)
				# Render the page into a pixel-based image(pixmap)
				page_pixmap = pdf_page.get_pixmap(  # noqa
					matrix = scaling_matrix)

				# Generate a unique image file name for each page
				image_filename = (
					f"{base_filename_prefix}._page_{page_index + 1}.png"
				)
				# Save path of the image
				image_file_path: Path = output_folder / image_filename

				# Save the image to disk
				page_pixmap.save(str(image_file_path))

				# Add the image path(as a string( to our result list
				converted_image_path_list.append(
					str(image_file_path.as_posix()))  # noqa

				logger.info(
					f"Saved page {page_index + 1} as image: "
					f"{image_file_path}")
			except Exception as page_error:
				logger.exception(
					f"Error converting page {page_index + 1}"
					f"{full_pdf_file_path}: {page_error}"
				)

		# Free the memory used by the PDF
		pdf_document.close()

		return converted_image_path_list
