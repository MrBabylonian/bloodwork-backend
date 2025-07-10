"""
OpenAI integration service for veterinary bloodwork analysis.

This module provides comprehensive AI-powered analysis of veterinary blood test
images using OpenAI's GPT-4o vision model. It handles image encoding, prompt
management, and API communication following best practices.

Last updated: 2025-06-17
Author: Bedirhan Gilgiler
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from app.utils.file_utils import FileProcessor
from app.utils.logger_utils import ApplicationLogger
from dotenv import load_dotenv


class OpenAiConfiguration:
    """
    Configuration manager for OpenAI API settings.

    This class encapsulates all OpenAI-related configuration including
    API keys, model settings, and default parameters.
    """

    def __init__(self):
        """Initialize OpenAI configuration from environment variables."""
        load_dotenv()
        self._api_key = os.getenv("OPENAI_API_KEY")
        self._base_url = "https://api.openai.com/v1/chat/completions"
        self._model_name = "gpt-4o"
        self._default_temperature = 0.2

        if not self._api_key:
            # Allow startup without API key for development/testing
            import warnings
            warnings.warn(
                "OPENAI_API_KEY environment variable not set. "
                "AI analysis will not work until this is configured.",
                UserWarning
            )

    @property
    def api_key(self) -> str:
        """Get the OpenAI API key."""
        if not self._api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable is required for AI operations")
        return self._api_key

    @property
    def base_url(self) -> str:
        """Get the OpenAI API base URL."""
        return self._base_url

    @property
    def model_name(self) -> str:
        """Get the default model name."""
        return self._model_name

    @property
    def default_temperature(self) -> float:
        """Get the default temperature setting."""
        return self._default_temperature


class BloodworkAnalysisService:
    """
    Main service class for AI-powered bloodwork analysis.

    This class orchestrates the entire analysis process from image processing
    to AI interpretation, providing a clean interface for bloodwork analysis.
    """

    def __init__(self, diagnostic_prompt_path: Optional[Path] = None):
        """
        Initialize the bloodwork analysis service.

        Args:
            diagnostic_prompt_path (Optional[Path]): Path to diagnostic prompt file
        """
        self._logger = ApplicationLogger.get_logger(
            "bloodwork_analysis_service")
        self._config = OpenAiConfiguration()
        self._file_processor = FileProcessor()

        # Set default prompt path if not provided
        if diagnostic_prompt_path is None:
            diagnostic_prompt_path = Path(
                "app/prompts/diagnostic_prompt_v2.txt")

        self._diagnostic_prompt_path = diagnostic_prompt_path
        self._diagnostic_prompt = self._load_diagnostic_prompt()

    def _load_diagnostic_prompt(self) -> str:
        """
        Load the diagnostic prompt from file.

        Returns:
            str: The diagnostic prompt content

        Raises:
            RuntimeError: If prompt loading fails
        """
        try:
            return self._file_processor.load_text_file(self._diagnostic_prompt_path)
        except Exception as error:
            error_msg = "Failed to load diagnostic prompt"
            self._logger.exception(f"{error_msg}: {error}")
            raise RuntimeError(error_msg) from error

    async def analyze_bloodwork_images(self, image_paths: List[Path]) -> str:
        """
        Analyze bloodwork images using OpenAI's vision model.

        This method processes multiple images representing pages of a blood test
        report and returns a comprehensive diagnostic analysis in JSON format.

        Args:
            image_paths (List[Path]): List of paths to bloodwork image files

        Returns:
            str: JSON-formatted diagnostic analysis from OpenAI

        Raises:
            ValueError: If no images provided or images don't exist
            RuntimeError: If API request fails

        Example:
            >>> service = BloodworkAnalysisService()
            >>> images = [Path("page1.png"), Path("page2.png")]
            >>> analysis = await service.analyze_bloodwork_images(images)
        """
        if not image_paths:
            raise ValueError("At least one image path must be provided")

        self._logger.info(f"Analyzing {len(image_paths)} bloodwork images")

        # Validate all image files exist
        for image_path in image_paths:
            if not image_path.exists():
                raise ValueError(f"Image file not found: {image_path}")

        try:
            # Prepare image data for API request
            image_messages = await self._prepare_image_messages(image_paths)

            # Create API request payload
            request_payload = self._create_api_request_payload(image_messages)

            # Make API request
            response = await self._make_api_request(request_payload)

            # Extract and return the analysis result
            analysis_result = self._extract_analysis_result(response)

            self._logger.info("Bloodwork analysis completed successfully")
            return analysis_result

        except Exception as error:
            error_msg = "Failed to analyze bloodwork images"
            self._logger.exception(f"{error_msg}: {error}")
            raise RuntimeError(error_msg) from error

    async def _prepare_image_messages(self, image_paths: List[Path]) -> List[Dict[str, Any]]:
        """
        Prepare image messages for OpenAI API request.

        Args:
            image_paths (List[Path]): List of image file paths

        Returns:
            List[Dict[str, Any]]: List of image message objects
        """
        image_messages = []

        for image_path in image_paths:
            try:
                # Encode image to base64
                base64_image = self._file_processor.encode_image_to_base64(
                    image_path)

                # Create image message object
                image_message = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                }

                image_messages.append(image_message)
                self._logger.debug(f"Prepared image: {image_path.name}")

            except Exception as error:
                error_msg = f"Failed to prepare image: {image_path}"
                self._logger.exception(f"{error_msg}: {error}")
                raise RuntimeError(error_msg) from error

        return image_messages

    def _create_api_request_payload(self, image_messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create the API request payload for OpenAI.

        Args:
            image_messages (List[Dict[str, Any]]): Prepared image messages

        Returns:
            Dict[str, Any]: Complete API request payload
        """
        return {
            "model": self._config.model_name,
            "messages": [
                {
                    "role": "system",
                    "content": self._diagnostic_prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Segui istruzioni come specificato nel prompt."
                        }
                    ] + image_messages
                }
            ],
            "temperature": self._config.default_temperature
        }

    async def _make_api_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make the API request to OpenAI.

        Args:
            payload (Dict[str, Any]): Request payload

        Returns:
            Dict[str, Any]: API response

        Raises:
            RuntimeError: If API request fails
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key}"
        }

        try:
            # Use asyncio to run the synchronous request in a thread pool
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.post(
                    self._config.base_url,
                    headers=headers,
                    json=payload,
                    timeout=300  # 5 minute timeout for large requests
                )
            )

            # Check for HTTP errors
            response.raise_for_status()

            return response.json()

        except requests.RequestException as error:
            error_msg = f"OpenAI API request failed: {error}"
            self._logger.exception(error_msg)
            raise RuntimeError(error_msg) from error
        except json.JSONDecodeError as error:
            error_msg = f"Failed to parse OpenAI API response: {error}"
            self._logger.exception(error_msg)
            raise RuntimeError(error_msg) from error

    def _extract_analysis_result(self, api_response: Dict[str, Any]) -> str:
        """
        Extract the analysis result from OpenAI API response.

        Args:
            api_response (Dict[str, Any]): OpenAI API response

        Returns:
            str: Extracted analysis content

        Raises:
            RuntimeError: If response format is invalid
        """
        try:
            choices = api_response.get("choices", [])
            if not choices:
                raise RuntimeError("No choices found in OpenAI response")

            message = choices[0].get("message", {})
            content = message.get("content", "").strip()

            if not content:
                raise RuntimeError("Empty content in OpenAI response")

            return content

        except (KeyError, IndexError) as error:
            error_msg = f"Invalid OpenAI API response format: {error}"
            self._logger.exception(error_msg)
            raise RuntimeError(error_msg) from error
