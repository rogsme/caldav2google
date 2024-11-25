"""Module for setting up logging configuration."""

import logging

# Configure logging format
LOGFORMAT = "%(asctime)s - %(levelname)s - %(message)s"
DATEFORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logger(name: str) -> logging.Logger:
    """Set up and return a logger instance with console output.

    Args:
        name: Name of the logger, typically __name__ from the calling module

    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(LOGFORMAT, DATEFORMAT)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger
