"""
File processing utilities for the Veterinary Bloodwork Analyzer.

This module provides comprehensive file handling capabilities including
PDF to image conversion, prompt loading, and image encoding utilities.
All operations follow Python's principle of explicit error handling.

Last updated: 2025-06-17
Author: Bedirhan Gilgiler
"""

import base64
from pathlib import Path
from typing import List

import fitz  # PyMuPDF

from app.utils.logger_utils import ApplicationLogger


class PdfImageConverter:
    """
    Handles PDF to image conversion operations.

    This class encapsulates all PDF processing logic using PyMuPDF library.
    It follows the principle: "Errors should never pass silently."
    """

    def __init__(self):
        """Initialize the PDF converter with logging."""
        self._logger = ApplicationLogger.get_logger("pdf_image_converter")
        self._default_dpi = 300  # High resolution for better OCR results

    def convert_pdf_to_image_list(
        self,
        pdf_file_path: Path,
        output_directory: Path,
        filename_prefix: str
    ) -> List[Path]:
        """
        Convert a PDF file into high-resolution PNG images, one per page.

        This method processes each page of the PDF document and converts it
        to a PNG image with 300 DPI resolution for optimal quality.

        Args:
            pdf_file_path (Path): Full path to the PDF file to convert
            output_directory (Path): Directory where images will be saved
            filename_prefix (str): Prefix for generated image filenames (usually UUID)

        Returns:
            List[Path]: List of paths to the generated image files

        Raises:
            FileNotFoundError: If the PDF file doesn't exist
            RuntimeError: If PDF processing fails

        Example:
            >>> converter = PdfImageConverter()
            >>> images = converter.convert_pdf_to_image_list(
            ...     Path("report.pdf"),
            ...     Path("output/"),
            ...     "report_123"
            ... )
        """
        self._logger.info(f"Starting PDF to image conversion: {pdf_file_path}")

        if not pdf_file_path.exists():
            error_msg = f"PDF file not found: {pdf_file_path}"
            self._logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        # Ensure output directory exists
        output_directory.mkdir(parents=True, exist_ok=True)

        try:
            pdf_document = fitz.open(str(pdf_file_path))
        except Exception as error:
            error_msg = f"Failed to open PDF document: {pdf_file_path}"
            self._logger.exception(f"{error_msg} - Error: {error}")
            raise RuntimeError(error_msg) from error

        converted_image_paths: List[Path] = []
        total_pages = len(pdf_document)

        self._logger.info(
            f"PDF opened successfully. Total pages: {total_pages}")

        try:
            for page_index in range(total_pages):
                image_path = self._convert_single_page(
                    pdf_document,
                    page_index,
                    output_directory,
                    filename_prefix
                )
                converted_image_paths.append(image_path)

        finally:
            # Always close the PDF document to free memory
            pdf_document.close()

        self._logger.info(
            f"PDF conversion completed. Generated {len(converted_image_paths)} images"
        )

        return converted_image_paths

    def _convert_single_page(
        self,
        pdf_document: fitz.Document,
        page_index: int,
        output_directory: Path,
        filename_prefix: str
    ) -> Path:
        """
        Convert a single PDF page to PNG image.

        Args:
            pdf_document (fitz.Document): Open PDF document
            page_index (int): Zero-based page index
            output_directory (Path): Output directory for image
            filename_prefix (str): Filename prefix

        Returns:
            Path: Path to the generated image file

        Raises:
            RuntimeError: If page conversion fails
        """
        try:
            self._logger.info(f"Converting page {page_index + 1}")

            # Load the specific page
            pdf_page = pdf_document[page_index]

            # Calculate scaling matrix for desired DPI
            zoom_factor = self._default_dpi / 72  # PyMuPDF default is 72 DPI
            scaling_matrix = fitz.Matrix(zoom_factor, zoom_factor)

            # Render page to pixmap (bitmap)
            page_pixmap = pdf_page.get_pixmap(matrix=scaling_matrix)

            # Generate unique filename for this page
            image_filename = f"{filename_prefix}_page_{page_index + 1}.png"
            image_file_path = output_directory / image_filename

            # Save the image
            page_pixmap.save(str(image_file_path))

            self._logger.info(
                f"Page {page_index + 1} saved as: {image_file_path}")

            return image_file_path

        except Exception as error:
            error_msg = f"Failed to convert page {page_index + 1}"
            self._logger.exception(f"{error_msg} - Error: {error}")
            raise RuntimeError(error_msg) from error


class FileProcessor:
    """
    General file processing utilities.

    This class provides common file operations like loading text files
    and encoding images for API transmission.
    """

    def __init__(self):
        """Initialize the file processor with logging."""
        self._logger = ApplicationLogger.get_logger("file_processor")

    def load_text_file(self, file_path: Path) -> str:
        """
        Load text content from a file.

        Args:
            file_path (Path): Path to the text file

        Returns:
            str: Content of the file

        Raises:
            FileNotFoundError: If file doesn't exist
            RuntimeError: If file reading fails
        """
        if not file_path.exists():
            error_msg = f"File not found: {file_path}"
            self._logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()

            self._logger.info(f"Successfully loaded text file: {file_path}")
            return content

        except Exception as error:
            error_msg = f"Failed to read file: {file_path}"
            self._logger.exception(f"{error_msg} - Error: {error}")
            raise RuntimeError(error_msg) from error

    def encode_image_to_base64(self, image_path: Path) -> str:
        """
        Encode an image file to base64 string for API transmission.

        Args:
            image_path (Path): Path to the image file

        Returns:
            str: Base64 encoded image data

        Raises:
            FileNotFoundError: If image file doesn't exist
            RuntimeError: If encoding fails
        """
        if not image_path.exists():
            error_msg = f"Image file not found: {image_path}"
            self._logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            with open(image_path, "rb") as image_file:
                image_data = image_file.read()
                base64_data = base64.b64encode(image_data).decode("utf-8")

            self._logger.info(f"Successfully encoded image: {image_path}")
            return base64_data

        except Exception as error:
            error_msg = f"Failed to encode image: {image_path}"
            self._logger.exception(f"{error_msg} - Error: {error}")
            raise RuntimeError(error_msg) from error


# Backward compatibility class
class FileConverter:
    """
    Legacy file converter class for backward compatibility.

    This class provides static methods that delegate to the new OOP classes.
    It maintains compatibility while encouraging migration to the new structure.
    """

    @staticmethod
    def convert_pdf_to_image_list(
        full_pdf_file_path: Path,
        output_folder: Path,
        base_filename_prefix: str
    ) -> List[Path]:
        """Legacy method - use PdfImageConverter class instead."""
        converter = PdfImageConverter()
        return converter.convert_pdf_to_image_list(
            full_pdf_file_path,
            output_folder,
            base_filename_prefix
        )

    @staticmethod
    def load_prompt_from_file(prompt_path: Path) -> str:
        """Legacy method - use FileProcessor class instead."""
        processor = FileProcessor()
        return processor.load_text_file(prompt_path)

    @staticmethod
    def image_to_base64(image_path: Path) -> str:
        """Legacy method - use FileProcessor class instead."""
        processor = FileProcessor()
        return processor.encode_image_to_base64(image_path)
