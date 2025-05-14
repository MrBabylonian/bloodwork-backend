import logging
import sys


class Logger:
	@staticmethod
	def setup_logging(level: int = logging.INFO) -> logging.Logger:
		"""
        Configure and return a central logger for the application.

        This method:
        1. Creates (or retrieves) a logger named 'bloodwork'.
        2. Sets its logging level to the specified `level`.
        3. Adds a StreamHandler that writes log messages to stdout.
        4. Applies a clear, timestamped format for readability.

        Use example in other modules:
            from logging import getLogger
            logger = getLogger('bloodwork.your_module')
            logger.info('A useful message')

		:param level: logging level (default: logging.INFO)
		:return: logger: logging.Logger
		"""

		# Retrieve the root 'bloodwork' logger; subsequent calls return the
		# same looger
		logger = logging.getLogger("bloodwork")
		# Prevent adding multiple handlers if already set up
		if not logger.handlers:
			logger.setLevel(level)  # Minimum log level

			# Create a handler that sends messages to stdout
			handler = logging.StreamHandler(sys.stdout)

			# Log format
			fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
			handler.setFormatter(logging.Formatter(fmt))

			# Attach the handler to logger
			logger.addHandler(handler)
		return logger
