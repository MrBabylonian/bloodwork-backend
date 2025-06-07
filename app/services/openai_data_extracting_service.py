import os
import base64
import json
import requests
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

prompt_path: Path = Path("app/services/openai_prompt.txt")
api_key = os.getenv("OPENAI_API_KEY")


def load_prompt_from_file(prompt_path: Path) -> str:
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def image_to_base64(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def extract_emogramma_from_image(image_paths: list[Path], prompt_path: Path = prompt_path) -> str:
    system_prompt: str = load_prompt_from_file(prompt_path)

    image_messages: list[dict] = []
    for image_path in image_paths:
        base64_img: str = image_to_base64(image_path)
        image_messages.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{base64_img}"}
        })

    headers: dict = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    payload: dict[str, any] = {
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


image_paths: list[Path] = [
    "data/blood_work_pdfs/9edbdb81-34fd-4a5a-9667-a33ad4e2c5ab/9edbdb81-34fd-4a5a-9667-a33ad4e2c5ab._page_1.png",
    "data/blood_work_pdfs/9edbdb81-34fd-4a5a-9667-a33ad4e2c5ab/9edbdb81-34fd-4a5a-9667-a33ad4e2c5ab._page_2.png",
    "data/blood_work_pdfs/9edbdb81-34fd-4a5a-9667-a33ad4e2c5ab/9edbdb81-34fd-4a5a-9667-a33ad4e2c5ab._page_3.png", "data/blood_work_pdfs/9edbdb81-34fd-4a5a-9667-a33ad4e2c5ab/9edbdb81-34fd-4a5a-9667-a33ad4e2c5ab._page_4.png"]
prompt_path: Path = Path("app/services/openai_prompt.txt")

print(extract_emogramma_from_image(image_paths))
