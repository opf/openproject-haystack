"""Logging configuration for the OpenProject Haystack application."""

import logging
import sys
from typing import Optional


def setup_logging(log_level: str = "INFO", log_format: Optional[str] = None) -> None:
    """Configure logging for the application.
    
    Args:
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom log format string. If None, uses default format.
    """
    # Default log format with timestamp, level, module name, and message
    if log_format is None:
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,  # Ensure logs go to stdout for Docker
        force=True  # Override any existing configuration
    )
    
    # Set specific loggers to appropriate levels
    # Reduce noise from external libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    
    # Log the configuration
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name.
    
    Args:
        name: The logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
