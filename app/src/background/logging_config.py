"""
Production logging configuration for CapitolScope Celery tasks.

This module provides structured logging with proper formatting, rotation,
and different log levels for various components.
"""

import os
import logging
import logging.handlers
from datetime import datetime
from typing import Dict, Any

def setup_production_logging(log_level: str = "INFO", log_dir: str = "/var/log/capitolscope") -> Dict[str, Any]:
    """
    Setup production logging configuration for Celery workers.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files
        
    Returns:
        Dictionary with logging configuration
    """
    
    # Ensure log directory exists
    os.makedirs(log_dir, exist_ok=True)
    
    # Define log formats
    detailed_formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)8s] %(name)s.%(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    json_formatter = JsonFormatter()
    
    # Configure handlers
    handlers = {
        'console': {
            'class': 'logging.StreamHandler',
            'level': log_level,
            'formatter': 'simple',
            'stream': 'ext://sys.stdout'
        },
        'file_detailed': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'detailed',
            'filename': os.path.join(log_dir, 'celery-detailed.log'),
            'maxBytes': 50 * 1024 * 1024,  # 50MB
            'backupCount': 5,
            'encoding': 'utf-8'
        },
        'file_errors': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'ERROR',
            'formatter': 'detailed',
            'filename': os.path.join(log_dir, 'celery-errors.log'),
            'maxBytes': 20 * 1024 * 1024,  # 20MB
            'backupCount': 10,
            'encoding': 'utf-8'
        },
        'file_tasks': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'json',
            'filename': os.path.join(log_dir, 'celery-tasks.log'),
            'maxBytes': 100 * 1024 * 1024,  # 100MB
            'backupCount': 7,
            'encoding': 'utf-8'
        },
        'file_health': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'INFO',
            'formatter': 'simple',
            'filename': os.path.join(log_dir, 'celery-health.log'),
            'maxBytes': 10 * 1024 * 1024,  # 10MB
            'backupCount': 3,
            'encoding': 'utf-8'
        }
    }
    
    # Configure loggers
    loggers = {
        '': {  # Root logger
            'level': log_level,
            'handlers': ['console', 'file_detailed']
        },
        'celery': {
            'level': 'INFO',
            'handlers': ['console', 'file_detailed', 'file_errors'],
            'propagate': False
        },
        'celery.task': {
            'level': 'INFO',
            'handlers': ['file_tasks'],
            'propagate': True
        },
        'background': {
            'level': 'INFO',
            'handlers': ['console', 'file_detailed', 'file_errors'],
            'propagate': False
        },
        'background.tasks': {
            'level': 'INFO',
            'handlers': ['file_tasks'],
            'propagate': True
        },
        'background.health': {
            'level': 'INFO',
            'handlers': ['file_health'],
            'propagate': True
        },
        'domains.notifications': {
            'level': 'INFO',
            'handlers': ['file_tasks'],
            'propagate': True
        },
        'domains.congressional': {
            'level': 'INFO',
            'handlers': ['file_tasks'],
            'propagate': True
        },
        'domains.securities': {
            'level': 'INFO',
            'handlers': ['file_tasks'],
            'propagate': True
        }
    }
    
    return {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                '()': detailed_formatter.__class__,
                'fmt': detailed_formatter._fmt,
                'datefmt': detailed_formatter.datefmt
            },
            'simple': {
                '()': simple_formatter.__class__,
                'fmt': simple_formatter._fmt,
                'datefmt': simple_formatter.datefmt
            },
            'json': {
                '()': JsonFormatter,
            }
        },
        'handlers': handlers,
        'loggers': loggers
    }


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        import json
        
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'message': record.getMessage(),
            'process_id': record.process,
            'thread_id': record.thread
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, 'task_id'):
            log_data['task_id'] = record.task_id
        if hasattr(record, 'task_name'):
            log_data['task_name'] = record.task_name
        if hasattr(record, 'duration'):
            log_data['duration'] = record.duration
        
        return json.dumps(log_data, ensure_ascii=False)


class TaskLogger:
    """Enhanced logger for Celery tasks with additional context."""
    
    def __init__(self, task_name: str, task_id: str = None):
        self.logger = logging.getLogger(f'background.tasks.{task_name}')
        self.task_name = task_name
        self.task_id = task_id
        self.start_time = datetime.utcnow()
    
    def _add_context(self, extra: Dict[str, Any] = None) -> Dict[str, Any]:
        """Add task context to log records."""
        context = {
            'task_name': self.task_name,
            'task_id': self.task_id
        }
        if extra:
            context.update(extra)
        return context
    
    def info(self, message: str, **kwargs):
        """Log info message with task context."""
        self.logger.info(message, extra=self._add_context(kwargs))
    
    def warning(self, message: str, **kwargs):
        """Log warning message with task context."""
        self.logger.warning(message, extra=self._add_context(kwargs))
    
    def error(self, message: str, **kwargs):
        """Log error message with task context."""
        self.logger.error(message, extra=self._add_context(kwargs))
    
    def debug(self, message: str, **kwargs):
        """Log debug message with task context."""
        self.logger.debug(message, extra=self._add_context(kwargs))
    
    def task_started(self, **kwargs):
        """Log task start."""
        self.info(f"Task {self.task_name} started", **kwargs)
    
    def task_completed(self, result: Any = None, **kwargs):
        """Log task completion with duration."""
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        self.info(
            f"Task {self.task_name} completed successfully",
            duration=duration,
            result_summary=str(result)[:200] if result else None,
            **kwargs
        )
    
    def task_failed(self, error: Exception, **kwargs):
        """Log task failure."""
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        self.error(
            f"Task {self.task_name} failed: {str(error)}",
            duration=duration,
            error_type=error.__class__.__name__,
            **kwargs
        )


def get_task_logger(task_name: str, task_id: str = None) -> TaskLogger:
    """Get a task logger with context."""
    return TaskLogger(task_name, task_id)


def configure_celery_logging():
    """Configure Celery logging for production."""
    import logging.config
    
    # Get log level from environment
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    log_dir = os.getenv('LOG_DIR', '/var/log/capitolscope')
    
    # Setup logging configuration
    config = setup_production_logging(log_level, log_dir)
    logging.config.dictConfig(config)
    
    # Log configuration completion
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {log_level}, Directory: {log_dir}")


# Configure logging when module is imported
if os.getenv('CELERY_PRODUCTION', 'false').lower() == 'true':
    configure_celery_logging()



