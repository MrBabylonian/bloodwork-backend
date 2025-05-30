import subprocess
from pathlib import Path
from typing import Union
import re
import httpx

from app.utils.logger_utils import Logger

logger = Logger.setup_logging().getChild("vision_model_inference_service")

prompt_file_path: Path = Path("app/services/prompt.txt")
with open(prompt_file_path, "r", encoding = "utf-8") as prompt_file:
	prompt: str = prompt_file.read()


def remove_ansi_escape_sequences(text: str) -> str:
	"""
	Cleans up model output by:
	- Removing ANSI escape sequences
	- Fixing broken UTF-8 characters
	- Replacing escaped \n and \t with real newlines and tabs
	- Normalizing problematic Markdown-breaking characters
	"""

	try:
		# Remove ANSI terminal escape sequences
		ansi_escape_pattern: re.Pattern = re.compile(
			r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'
		)
		cleaned_text: str = ansi_escape_pattern.sub('', text)

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

		logger.info("Model response cleaned successfully")
		return cleaned_text

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
			model_name: str = "llava:7b",
			diagnostic_prompt: str = prompt,
	) -> str:
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
			return remove_ansi_escape_sequences(response.text)
		except Exception as remote_inference_error:
			logger.exception(
				f"Remote inference failed: {remote_inference_error}")
			raise


class OllamaVisionInferenceService:
	"""
	Encapsulates vision inference via Ollama
	Provides methods to run inference and clean model output
	"""

	def __init__(self, model_name: str):
		self.model_name = model_name
		logger.info(
			f"OllamaVisionInferenceService initialized with model: {model_name}")

	def run_inference_on_images(self,
								list_of_image_paths: list[
									Union[str, Path]],
								user_prompt: str = prompt
								) -> str:
		"""
		Sends all page-level images from a PDF as a unified multimodal prompt
		to a persistent Ollama vision model, running in server mode.

		Each image is referenced in the prompt using Ollama's <image:path> syntax,
		preserving full-document context during inference.

		This approach assumes Ollama is actively running via `ollama serve` and
		that the model is cached locally for rapid response.

		:param list_of_image_paths: list of image paths (as Path or str)
		:param user_prompt: prompt appended after the image tags
		:return: model_output: textual model response
		"""

		try:

			image_tags: list[str] = [
				f"<image:{str(image_path)}>" for image_path in
				list_of_image_paths
			]
			# Combines all image tags with the medical prompt. This becomes the
			# complete instruction we send to the model.
			full_prompt = "\n".join(image_tags) + "\n" + user_prompt
			logger.info(
				f"Build prompt with {len(image_tags)} images and user prompt")
		except Exception as prompt_error:
			logger.exception(f"Failed to build prompt {prompt_error}")

		# Compose the command to send the prompt to the ollama model
		ollama_command: list[str] = ["ollama", "run", self.model_name]

		try:
			logger.info(
				f"Invoking ollama subprocess: {ollama_command}")
			# Send prompt to ollama and capture model output
			raw_output: str = subprocess.check_output(
				ollama_command,
				input = full_prompt,  # noqa
				stderr = subprocess.STDOUT,
				timeout = 180,
				universal_newlines = True
			)
			logger.info(f"Ollama inference completed successfully")

			model_output: str = raw_output.strip() if raw_output else "No output returned from the model"

			return remove_ansi_escape_sequences(model_output)
		except subprocess.CalledProcessError as called_process_error:
			logger.exception(
				f"Model inference failed with code {called_process_error.returncode}\n"
				f"Ollama output:\n{called_process_error.output}"
			)
			raise
		except subprocess.TimeoutExpired as timeout_expired_error:
			logger.exception(
				f"Inference timed out {timeout_expired_error}")
			raise
		except Exception as error:
			logger.exception(f"Unexpected error during model execution:"
							 f" {str(error)}")
			raise
