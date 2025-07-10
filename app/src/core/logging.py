"""
Structured logging configuration for CapitolScope.

This module configures structured logging using structlog for better
observability and debugging in both development and production.
"""

import sys
import logging
import os
from typing import Dict, Any, Optional
from enum import Enum
from pathlib import Path

import structlog
from structlog.stdlib import LoggerFactory

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


# Centralized logging configuration
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


def setup_file_logging():
    """Set up file logging handlers."""
    # Create logs directory
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Main application log
    app_handler = logging.FileHandler(logs_dir / "app.log")
    app_handler.setLevel(logging.DEBUG)
    
    # Background tasks log
    tasks_handler = logging.FileHandler(logs_dir / "background_tasks.log")
    tasks_handler.setLevel(logging.DEBUG)
    
    # Congress API log
    api_handler = logging.FileHandler(logs_dir / "congress_api.log")
    api_handler.setLevel(logging.DEBUG)
    
    # Set formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    app_handler.setFormatter(formatter)
    tasks_handler.setFormatter(formatter)
    api_handler.setFormatter(formatter)
    
    # Get root logger and add handlers
    root_logger = logging.getLogger()
    root_logger.addHandler(app_handler)
    
    # Add specific handlers for components
    tasks_logger = logging.getLogger("background_tasks")
    tasks_logger.addHandler(tasks_handler)
    
    api_logger = logging.getLogger("congress_api")
    api_logger.addHandler(api_handler)


def configure_logging() -> structlog.stdlib.BoundLogger:
    """
    Configure structured logging for the application.
    
    Returns:
        Configured structlog logger instance.
    """
    # Set up file logging first
    setup_file_logging()
    
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


def get_logger(name: str, component: Optional[LogComponent] = None) -> structlog.stdlib.BoundLogger:
    """
    Get a configured logger for a specific module.
    
    Args:
        name: The logger name (usually __name__)
        component: Optional component for log level configuration
        
    Returns:
        Configured structlog logger
    """
    logger = structlog.get_logger(name)
    
    # Add component context if specified
    if component:
        logger = logger.bind(component=component.value)
    
    return logger


def get_background_task_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger specifically configured for background tasks.
    
    Args:
        name: The logger name (usually __name__)
        
    Returns:
        Configured logger for background tasks
    """
    return get_logger(name, LogComponent.BACKGROUND_TASKS)


def get_congress_api_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger specifically configured for Congress API operations.
    
    Args:
        name: The logger name (usually __name__)
        
    Returns:
        Configured logger for Congress API operations
    """
    return get_logger(name, LogComponent.CONGRESS_API)


def get_database_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger specifically configured for database operations.
    
    Args:
        name: The logger name (usually __name__)
        
    Returns:
        Configured logger for database operations
    """
    return get_logger(name, LogComponent.DATABASE)


def get_api_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger specifically configured for API operations.
    
    Args:
        name: The logger name (usually __name__)
        
    Returns:
        Configured logger for API operations
    """
    return get_logger(name, LogComponent.API)


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