"""
Structured logging configuration for CapitolScope.

This module configures structured logging using structlog for better
observability and debugging in both development and production.
"""

import sys
import logging
import os
from typing import Optional
from enum import Enum
from pathlib import Path

from core.config import settings


class LogLevel(Enum):
    """Log level enumeration for different components."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogComponent(Enum):
    """Logging components that can have different log levels."""
    API = "api"
    BACKGROUND_TASKS = "background_tasks"
    DATABASE = "database"
    CONGRESS_API = "congress_api"
    SECURITIES = "securities"
    AUTH = "auth"
    GENERAL = "general"


# Centralized logging configuration (kept for compatibility, but not used by stdlib logging)
LOGGING_CONFIG = {
    # Default log levels for different components
    LogComponent.API: LogLevel.INFO,
    LogComponent.BACKGROUND_TASKS: LogLevel.INFO,
    LogComponent.DATABASE: LogLevel.INFO,
    LogComponent.CONGRESS_API: LogLevel.DEBUG,
    LogComponent.SECURITIES: LogLevel.INFO,
    LogComponent.AUTH: LogLevel.INFO,
    LogComponent.GENERAL: LogLevel.INFO,
    
    # Environment-specific overrides
    "development": {
        LogComponent.BACKGROUND_TASKS: LogLevel.DEBUG,
        LogComponent.CONGRESS_API: LogLevel.DEBUG,
    },
    "production": {
        LogComponent.BACKGROUND_TASKS: LogLevel.INFO,
        LogComponent.CONGRESS_API: LogLevel.WARNING,
    }
}


def setup_file_logging():
    """Set up file and stdout logging handlers."""
    logs_dir = Path(os.environ.get("LOG_DIR", "logs"))
    logs_dir.mkdir(exist_ok=True)

    # File handler
    app_handler = logging.FileHandler(logs_dir / "app.log")
    app_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    app_handler.setFormatter(formatter)

    # Stream handler (stdout for Docker)
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(formatter)

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    # Avoid duplicate handlers
    if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
        root_logger.addHandler(app_handler)
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        root_logger.addHandler(stream_handler)


def configure_logging():
    """
    Configure standard logging for the application.
    """
    setup_file_logging()
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL.upper()),
    )


def get_logger(name: str) -> logging.Logger:
    """Get a standard logger by name."""
    return logging.getLogger(name)


# The following functions are now no-ops or compatibility stubs

def get_component_log_level(component: LogComponent) -> LogLevel:
    """
    Get the log level for a specific component.
    
    Args:
        component: The logging component
        
    Returns:
        The configured log level for the component
    """
    # Check environment-specific overrides first
    env = os.getenv("ENVIRONMENT", "development")
    if env in LOGGING_CONFIG:
        env_config = LOGGING_CONFIG[env]
        if component in env_config:
            return env_config[component]
    
    # Fall back to default configuration
    return LOGGING_CONFIG.get(component, LogLevel.INFO)


def is_debug_enabled(component: LogComponent) -> bool:
    """
    Check if debug logging is enabled for a component.
    
    Args:
        component: The logging component
        
    Returns:
        True if debug logging is enabled
    """
    return get_component_log_level(component) == LogLevel.DEBUG


# Convenience function to update log levels at runtime
def update_log_level(component: LogComponent, level: LogLevel):
    """
    Update the log level for a component at runtime.
    
    Args:
        component: The logging component
        level: The new log level
    """
    LOGGING_CONFIG[component] = level


# Convenience function to enable debug logging for all components
def enable_debug_logging():
    """Enable debug logging for all components."""
    for component in LogComponent:
        LOGGING_CONFIG[component] = LogLevel.DEBUG


# Convenience function to disable debug logging for all components
def disable_debug_logging():
    """Disable debug logging for all components."""
    for component in LogComponent:
        LOGGING_CONFIG[component] = LogLevel.INFO 