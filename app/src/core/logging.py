"""
Structured logging configuration for CapitolScope.

This module configures structured logging using structlog for better
observability and debugging in both development and production.
"""

import sys
import logging
from typing import Dict, Any

import structlog
from structlog.stdlib import LoggerFactory

from core.config import settings


def configure_logging() -> structlog.stdlib.BoundLogger:
    """
    Configure structured logging for the application.
    
    Returns:
        Configured structlog logger instance.
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )
    
    # Determine processors based on environment
    if settings.is_development:
        # Development: human-readable console output
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    else:
        # Production: JSON output for log aggregation
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Return logger for the main application
    return structlog.get_logger("capitolscope")


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a configured logger for a specific module."""
    return structlog.get_logger(name) 