import subprocess
from pathlib import Path
from typing import Union
import re
import httpx

from app.utils.logger_utils import Logger

logger = Logger.setup_logging().getChild("vision_model_inference_service")

prompt = """
Agisci come un medico veterinario specializzato in ematologia e medicina interna con oltre 15 anni di esperienza clinica su CANI e GATTI.

◆ INPUT fornito
– Uno o più immagini che contengono i risultati emato-chimici di un [SPECIE: CANE/GATTO], descritti in lingua [ITALIANO/INGLESE].
– Se possibile, leggi le reference ranges stampate nel referto; in caso manchino, usa i range generici di letteratura per la specie, l’età e il sesso se disponibili.
– Valida i valori estratti per potenziali errori di lettura OCR (es. virgole errate, interpretazioni sbagliate delle unità di misura, simboli mancanti).

◆ COMPITI

Trascrivi in tabella tutti i parametri con: Valore misurato, Unità, Range di riferimento, Evidenziazione ↑/↓.

Analisi matematica: calcola rapporti utili (ad es. Ca/P, rapporto BUN/Creatinina, Neutrofili/Linfociti, ecc.) e segnala quelli anomali.

Interpretazione clinica

Spiega le alterazioni di ciascun parametro.

Indica le possibili cause primarie e differenziali (almeno 3, ordinate per probabilità, con % di confidenza).

Integrazione multi-parametro: incrocia i dati per individuare pattern patologici (es. anemia rigenerativa, insufficienza epatica, sindrome nefrosica, Cushing, diabete, FIV/FeLV, pancreatite, ecc.).

Piano diagnostico

Esami aggiuntivi consigliati (test rapidi, imaging, profili ormonali, colture, citologia, ecc.) – indica invasività e priorità (Alta/Media/Bassa).

Terapia iniziale o di supporto

Farmaci di prima linea (dosaggi mg/kg, via di somministrazione, durata)

Terapie nutrizionali o dietetiche consigliate

Follow-up (quando ripetere esami, segni clinici da monitorare a casa)

Valutazione urgenza: classifica il caso come EMERGENZA / URGENZA A BREVE / ROUTINE, con motivazione.

Educazione al proprietario: riassunto in linguaggio semplice (< 250 parole) di cosa significano i risultati e i prossimi passi.

Bandierine rosse: elenca eventuali valori che richiedono intervento immediato (es. potassio > 6 mEq/L).

Contesto: commenta se i risultati possono essere influenzati da farmaci in uso, stato di digiuno, stress da trasporto, stagione, razza, ecc.

Fonti rapide: cita linee guida o studi (formato breve, es. “IRIS 2023”).

Disclaimer professionale: ricorda che la risposta non sostituisce la visita clinica in presenza.

◆ FORMATO DI USCITA
Includi ✅, ⚠️, ❌ per indicare normalità, lieve alterazione, grave alterazione.  

Dopo la tabella principale, lascia una riga vuota e scrivi sempre il disclaimer.

◆ SE MANCANO DATI
Se non riesci a leggere un valore o mancano range di riferimento, chiedi di inserire manualmente quei dati prima di procedere oltre.

◆ LINGUA DI USCITA
Rispondi in italiano tecnico, ma chiaro.
"""


def remove_ansi_escape_sequences(text: str) -> str:
	"""
	Cleans up model output by removing ANSI escape sequences
	and fixing common character encoding issues that appear
	in terminal output or subprocess results.

	This includes:
	- Removing terminal control codes
	- Replacing broken UTF-8 artifacts (e.g., Âµ → μ)
	- Stripping spinner icons (â ™, â ¸, etc.)
	"""
	try:
		# Remove ANSI terminal control codes
		ansi_escape_pattern = re.compile(
			r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])'
		)
		cleaned_text = ansi_escape_pattern.sub('', text)

		# Fix common UTF-8 encoding artifacts
		replacements = {
			"Âµ": "μ",  # micro symbol
			"â€“": "–",  # en dash
			"â€”": "—",  # em dash
			"â€˜": "‘",  # opening single quote
			"â€™": "’",  # closing single quote
			"â€œ": "“",  # opening double quote
			"â€�": "”",  # closing double quote
			"â€¢": "•",  # bullet
			"â€¦": "…",  # ellipsis
			"â€": "\"",  # malformed quote
			"â„¢": "™",  # trademark
			"âˆ’": "−",  # minus sign
			"â": "",  # catch-all for malformed spinner characters
		}

		for bad, good in replacements.items():
			cleaned_text = cleaned_text.replace(bad, good)
		logger.info(f"Model response cleaned successfully")
		return cleaned_text.strip()
	except Exception as regex_error:
		logger.exception(
			f"Error cleaning ANSI sequences: {regex_error}")
		raise


class RemoveVisionInferenceService:
	def __init__(self, inference_server_url: str):
		self.inference_server_url = inference_server_url
		self.inference_service_endpoint = \
			f"{self.inference_server_url}/vision_model_inference/"

	async def run_remote_inference(
			self, image_file_paths: list[Path],
			diagnostic_prompt: str = prompt,
			model_name: str = "llava:7b"
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
