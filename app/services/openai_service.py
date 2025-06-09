import os
from pathlib import Path

import requests
from dotenv import load_dotenv

from app.utils.file_utils import FileConverter
from app.utils.logger_utils import Logger

logger = Logger.setup_logging().getChild("openai_service")

prompt_path: Path = Path("app/prompts/diagnostic_prompt.txt")
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")


class OpenAIService:
    @staticmethod
    def extract_emogramma_from_image(image_paths: list[Path], prompt_path: Path = prompt_path) -> str:
        system_prompt: str = FileConverter.load_prompt_from_file(prompt_path)

        image_messages: list[dict] = []
        for image_path in image_paths:
            base64_img: str = FileConverter.image_to_base64(image_path)
            image_messages.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_img}"}
            })

        headers: dict = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload: dict[str, any] = {  # type: ignore
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Estrai i dati ematologici e morfologici come specificato nel prompt."}
                    ] + image_messages
                }
            ],
            "temperature": 0.2
        }

        response: requests.Response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )

        return response.json()["choices"][0]["message"]["content"].strip()

    @staticmethod
    async def interpret_bloodwork_via_openai(image_path_list: list[Path], prompt_path: Path = prompt_path):

        diagnostic_prompt = FileConverter.load_prompt_from_file(prompt_path)
        images: list = []
        for image_path in image_path_list:
            base64_img = FileConverter.image_to_base64(image_path)
            images.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_img}"}
            })

        headers: dict = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        payload: dict = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": diagnostic_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text",
                            "text": "Segui istruzioni come specificato nel prompt."}
                    ] + images
                }
            ],
            "temperature": 0.2
        }

        response: requests.Response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload
        )

        return response.json()["choices"][0]["message"]["content"].strip()
