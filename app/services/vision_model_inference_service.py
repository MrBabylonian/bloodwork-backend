from pathlib import Path
import re
import httpx

from app.utils.logger_utils import Logger

logger = Logger.setup_logging().getChild("vision_model_inference_service")

prompt_file_path: Path = Path("app/services/prompt.txt")
with open(prompt_file_path, "r", encoding = "utf-8") as prompt_file:
	prompt: str = prompt_file.read()


def clean_model_response(model_response: dict[str, str]) -> dict[str, str]:
	"""
	Cleans up model output by:
	- Removing ANSI escape sequences
	- Fixing broken UTF-8 characters
	- Replacing escaped \n and \t with real newlines and tabs
	- Normalizing problematic Markdown-breaking characters
	"""

	try:
		logger.info(f"Cleaning model response for frontend")

		# Remove ANSI terminal escape sequences
		ansi_escape_pattern: re.Pattern = re.compile(
			r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'
		)

		# Fix common UTF-8 encoding artifacts
		replacements: dict[str, str] = {
			"Âµ": "μ",  # micro symbol
			"â€“": "–",  # en dash
			"â€”": "—",  # em dash
			"â€˜": "‘",  # single quote
			"â€™": "’",  # single quote
			"â€œ": "“",  # double quote
			"â€�": "”",  # double quote
			"â€¢": "•",  # bullet
			"â€¦": "…",  # ellipsis
			"â„¢": "™",  # trademark
			"âˆ’": "−",  # minus
			"â€": "\"",  # generic quote
			"â": "",  # remove unknown remnants
		}

		for key in model_response:
			if isinstance(model_response[key], str):
				cleaned_text: str = ansi_escape_pattern.sub('', model_response[
					key])

				for bad, good in replacements.items():
					cleaned_text = cleaned_text.replace(bad, good)

				# Replace escaped characters with real formatting
				cleaned_text = cleaned_text.replace("\\n", "\n")
				cleaned_text = cleaned_text.replace("\\t", "\t")
				cleaned_text = cleaned_text.replace("\\r",
													"")  # remove carriage returns
				cleaned_text = cleaned_text.replace("*", "")

				# Normalize stray backslashes that may break Markdown tables
				cleaned_text = cleaned_text.replace("\\", "")

				# Strip extra whitespace from start/end
				cleaned_text = cleaned_text.strip()

				model_response[key] = cleaned_text

		logger.info("Model response cleaned successfully")

		return model_response

	except Exception as regex_error:
		logger.exception(f"Error cleaning ANSI sequences: {regex_error}")
		raise


class RemoveVisionInferenceService:
	def __init__(self, inference_server_url: str):
		self.inference_server_url = inference_server_url
		self.inference_service_endpoint = \
			f"{self.inference_server_url}/vision_model_inference/"

	async def run_remote_inference(
			self, image_file_paths: list[Path],
			model_name: str = "gemma3:27b",
			diagnostic_prompt: str = prompt,
	) -> dict[str, str]:
		"""

		:param image_file_paths:
		:param diagnostic_prompt:
		:param model_name:
		:return:
		"""
		files = [
			("images", (Path(path).name, open(path, "rb"), "image/png"))
			for path in image_file_paths]
		form_fields = {
			"prompt": diagnostic_prompt,
			"model_name": model_name
		}

		logger.info(f"Sending request to inference server: "
					f"{self.inference_service_endpoint}")

		try:
			async with httpx.AsyncClient() as client:
				response = await client.post(
					url = self.inference_service_endpoint,
					data = form_fields,
					files = files,
					timeout = 300,
				)

			response.raise_for_status()
			logger.info("Inference completed successfully on remote server")

			response_dict: dict[str, str] = clean_model_response(
				response.json())

			return clean_model_response(response_dict)
		except Exception as remote_inference_error:
			logger.exception(
				f"Remote inference failed: {remote_inference_error}")
			raise
