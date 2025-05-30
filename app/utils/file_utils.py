import fitz  # PyMuPDF
from pathlib import Path
from typing import Any
import re

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


class ModelOutputParserUtility:
	@staticmethod
	def parse_model_output_from_txt(model_output_path: Path) -> dict[str, Any]:
		if not model_output_path.exists():
			raise FileNotFoundError(f"Model output not found for UUID: "
									f"{str(model_output_path).split('/')[-2]}")

		with open(model_output_path, "r", encoding = "utf-8") as f:
			raw_text = f.read()

		structured_result: dict[str, Any] = {}

		def extract_section(title: str, next_title: str | None = None) -> str:
			pattern = rf"\*\*{re.escape(title)}\*\*(.*?)"
			if next_title:
				pattern += rf"\*\*{re.escape(next_title)}\*\*"
			match = re.search(pattern, raw_text, re.DOTALL)
			return match.group(1).strip() if match else ""

		# Extract and parse table section
		table_raw = extract_section("Tabella dei Parametri",
									"2. Analisi Matematica")
		structured_result[
			"parametri"] = ModelOutputParserUtility._parse_markdown_table(
			table_raw)

		# Extract and clean key sections
		structured_result["analisi_matematica"] = extract_section(
			"2. Analisi Matematica", "3. Interpretazione Clinica")
		structured_result["interpretazione_clinica"] = extract_section(
			"3. Interpretazione Clinica", "Diagnosi Differenziali")
		structured_result["diagnosi_differenziali"] = extract_section(
			"Diagnosi Differenziali", "Compatibilità con pattern")
		structured_result["compatibilita"] = extract_section(
			"Compatibilità con pattern",
			"4. Integrazione con Citologia/Istologia")
		structured_result["citologia_istologia"] = extract_section(
			"4. Integrazione con Citologia/Istologia",
			"5. Classificazione dell'Urgenza")
		structured_result["urgenza"] = extract_section(
			"5. Classificazione dell'Urgenza", "6. Piano Diagnostico")
		structured_result["piano_diagnostico"] = extract_section(
			"6. Piano Diagnostico", "7. Terapia Iniziale/Supporto")
		structured_result["terapia"] = extract_section(
			"7. Terapia Iniziale/Supporto", "8. Follow-up")
		structured_result["followup"] = extract_section("8. Follow-up",
														"9. Educazione al Proprietario")
		structured_result["educazione"] = extract_section(
			"9. Educazione al Proprietario", "10. Bandierine Rosse")
		structured_result["bandierine_rosse"] = extract_section(
			"10. Bandierine Rosse", "11. Contesto")
		structured_result["contesto"] = extract_section("11. Contesto",
														"12. Fonti Rapide")
		structured_result["fonti"] = extract_section("12. Fonti Rapide",
													 "13. Disclaimer Finale")
		structured_result["disclaimer"] = extract_section(
			"13. Disclaimer Finale")

		return structured_result

	@staticmethod
	def _parse_markdown_table(table_text: str) -> list[dict[str, str]]:
		lines = [line.strip() for line in table_text.split("\n") if
				 line.strip()]
		data = []
		section = None
		for line in lines:
			if line.startswith("| **") and line.endswith("** | | | | |"):
				section = line.replace("|", "").replace("**", "").strip()
				continue
			if line.startswith("|") and not "---" in line:
				columns = [col.strip() for col in line.strip("|").split("|")]
				if len(columns) == 5:
					data.append({
						"sezione": section,
						"parametro": columns[0],
						"valore": columns[1],
						"unita": columns[2],
						"range": columns[3],
						"evidenza": columns[4],
					})
		return data
