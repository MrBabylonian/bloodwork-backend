"""
Centralized logging utility for the Veterinary Bloodwork Analyzer.

This module provides a standardized logging interface following Python's
logging best practices. It ensures consistent log formatting and handling
across all application components.

Last updated: 2025-06-17
Author: Bedirhan Gilgiler
"""

import logging
import sys
from typing import Optional


class ApplicationLogger:
    """
    Centralized logger class for the application.

    This class implements the singleton pattern to ensure consistent
    logging configuration across the entire application. It follows
    the principle: "There should be one-- and preferably only one
    --obvious way to do it."
    """

    _instance: Optional['ApplicationLogger'] = None
    _logger: Optional[logging.Logger] = None

    def __new__(cls) -> 'ApplicationLogger':
        """
        Implement singleton pattern for logger instance.

        Returns:
            ApplicationLogger: The singleton logger instance
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def setup_logging(cls, level: int = logging.INFO) -> logging.Logger:
        """
        Configure and return the central logger for the application.

        This method creates a logger named 'bloodwork_analyzer' with consistent
        formatting and output configuration. Subsequent calls return the same
        logger instance to maintain consistency.

        Args:
            level (int): Logging level (default: logging.INFO)

        Returns:
            logging.Logger: Configured logger instance

        Example:
            >>> from app.utils.logger_utils import ApplicationLogger
            >>> logger = ApplicationLogger.setup_logging()
            >>> module_logger = logger.getChild('my_module')
            >>> module_logger.info('Application started successfully')
        """
        if cls._logger is not None:
            return cls._logger

        # Create the root logger for the application
        cls._logger = logging.getLogger("bloodwork_analyzer")

        # Prevent adding multiple handlers if already configured
        if not cls._logger.handlers:
            cls._logger.setLevel(level)

            # Create console handler for stdout output
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)

            # Define log message format
            log_format = (
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            formatter = logging.Formatter(log_format)
            console_handler.setFormatter(formatter)

            # Attach handler to logger
            cls._logger.addHandler(console_handler)

            # Prevent propagation to avoid duplicate messages
            cls._logger.propagate = False

        return cls._logger

    @classmethod
    def get_logger(cls, module_name: str) -> logging.Logger:
        """
        Get a logger instance for a specific module.

        Args:
            module_name (str): Name of the module requesting the logger

        Returns:
            logging.Logger: Logger instance for the module
        """
        if cls._logger is None:
            cls.setup_logging()

        # Type guard to ensure _logger is not None
        assert cls._logger is not None, "Logger should be initialized"
        return cls._logger.getChild(module_name)
