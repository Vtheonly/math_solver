"""
Logging configuration for the equation solving engine.

Provides a centralized logging system with configurable levels,
structured output, and module-specific loggers. Every component
in the engine uses this module for all logging needs.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional


_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s"
_DATE_FORMAT = "%H:%M:%S"

_logging_configured = False


def configure_logging(
    level: int = logging.DEBUG,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
) -> None:
    """
    Configure the global logging system.

    Args:
        level: The logging level (e.g., logging.DEBUG, logging.INFO).
        log_file: Optional file path to write logs to. If None, logs go to stderr only.
        log_format: Custom log format string. If None, uses the default format.
    """
    global _logging_configured

    if _logging_configured:
        return

    fmt = log_format or _LOG_FORMAT
    formatter = logging.Formatter(fmt, datefmt=_DATE_FORMAT)

    handlers = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    handlers.append(console_handler)

    # File handler (optional)
    if log_file:
        file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        handlers.append(file_handler)

    # Root logger for the engine namespace
    engine_logger = logging.getLogger("engine")
    engine_logger.setLevel(logging.DEBUG)
    engine_logger.propagate = False

    # Remove existing handlers to avoid duplicates
    engine_logger.handlers.clear()

    for handler in handlers:
        engine_logger.addHandler(handler)

    _logging_configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.

    Args:
        name: The module name (typically __name__ of the caller).

    Returns:
        A configured Logger instance under the 'engine' namespace.
    """
    if not _logging_configured:
        configure_logging()

    if not name.startswith("engine."):
        name = f"engine.{name}"

    return logging.getLogger(name)
