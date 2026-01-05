"""
Logging and observability configuration for Rivet Pro.
Sets up structured logging with consistent formatting across all modules.
"""

import logging
import sys
from typing import Optional
from rivet_pro.config.settings import settings


def setup_logging(
    level: Optional[str] = None,
    log_format: Optional[str] = None
) -> logging.Logger:
    """
    Configure application-wide logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom log format string

    Returns:
        Configured root logger
    """
    log_level = level or settings.log_level

    # Default structured format
    if log_format is None:
        log_format = (
            "%(asctime)s | %(levelname)-8s | %(name)s | "
            "%(funcName)s:%(lineno)d | %(message)s"
        )

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Get root logger
    logger = logging.getLogger("rivet_pro")

    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.INFO)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)

    logger.info(
        f"Logging initialized | Level: {log_level} | Environment: {settings.environment}"
    )

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"rivet_pro.{name}")


# Initialize on import
root_logger = setup_logging()
