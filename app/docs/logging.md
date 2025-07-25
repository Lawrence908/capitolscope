# Logging Configuration Guide

This document describes the enhanced logging system for CapitolScope, which provides centralized control over log levels for different components.

## Overview

The logging system is designed to provide:
- **Component-specific log levels**: Different parts of the application can have different log levels
- **Environment-based configuration**: Different log levels for development vs production
- **Runtime control**: Ability to change log levels without restarting services
- **Structured logging**: JSON output in production, human-readable in development

## Components

The following components can have independent log levels:

- `api` - API endpoints and request handling
- `background_tasks` - Celery background tasks and workers
- `database` - Database operations and connections
- `congress_api` - Congress.gov API interactions
- `securities` - Stock data and securities operations
- `auth` - Authentication and authorization
- `general` - General application logging

## Default Configuration

### Development Environment
- `background_tasks`: DEBUG
- `congress_api`: DEBUG
- All others: INFO

### Production Environment
- `background_tasks`: INFO
- `congress_api`: WARNING
- All others: INFO

## Usage

### 1. View Current Configuration

```bash
# From the app directory
python scripts/logging_config.py show
```

Example output:
```
=== Current Logging Configuration ===

api                  | INFO     | Debug: False
background_tasks     | DEBUG    | Debug: True
database             | INFO     | Debug: False
congress_api         | DEBUG    | Debug: True
securities           | INFO     | Debug: False
auth                 | INFO     | Debug: False
general              | INFO     | Debug: False
```

### 2. Enable Debug Logging for Background Tasks

```bash
# Enable debug for background tasks only
python scripts/logging_config.py debug background_tasks

# Enable debug for Congress API only
python scripts/logging_config.py debug congress_api

# Enable debug for all components
python scripts/logging_config.py debug-all
```

### 3. Disable Debug Logging

```bash
# Disable debug for background tasks
python scripts/logging_config.py info background_tasks

# Disable debug for all components
python scripts/logging_config.py info-all
```

### 4. Set Custom Log Levels

```bash
# Set congress_api to WARNING level
python scripts/logging_config.py set congress_api WARNING

# Set database to DEBUG level
python scripts/logging_config.py set database DEBUG
```

## In Your Code

### Using Component-Specific Loggers

```python
from core.logging import (
    get_background_task_logger,
    get_congress_api_logger,
    get_database_logger,
    get_api_logger
)

# For background tasks
logger = get_background_task_logger(__name__)

# For Congress API operations
logger = get_congress_api_logger(__name__)

# For database operations
logger = get_database_logger(__name__)

# For API operations
logger = get_api_logger(__name__)
```

### Structured Logging

```python
# Instead of string formatting, use structured logging
logger.info("Processing member", member_id=123, name="John Doe", action="update")

# For errors with context
logger.error("Failed to sync member", 
           member_id=123, 
           error=str(exc), 
           exc_info=True)
```

## Environment Variables

You can control the environment by setting:

```bash
export ENVIRONMENT=development  # Default
export ENVIRONMENT=production
```

## Background Task Debugging

When debugging background tasks, you'll typically want to:

1. **Enable debug logging for background tasks**:
   ```bash
   python scripts/logging_config.py debug background_tasks
   ```

2. **Enable debug logging for Congress API** (if syncing members):
   ```bash
   python scripts/logging_config.py debug congress_api
   ```

3. **Trigger the task** and watch the logs:
   ```bash
   docker-compose -p capitolscope-dev logs -f worker
   ```

4. **Disable debug logging when done**:
   ```bash
   python scripts/logging_config.py info background_tasks
   python scripts/logging_config.py info congress_api
   ```

## Log Output Examples

### Development (Human-readable)
```
2025-07-10 18:46:09 [info     ] Starting congressional members sync action=sync-all kwargs={}
2025-07-10 18:46:11 [debug    ] Database manager not initialized, initializing now
2025-07-10 18:46:11 [debug    ] Database manager initialized successfully
2025-07-10 18:46:11 [debug    ] Creating sync database session
2025-07-10 18:46:11 [debug    ] Initializing repositories
2025-07-10 18:46:11 [debug    ] Initializing CongressAPIService
```

### Production (JSON)
```json
{
  "timestamp": "2025-07-10T18:46:09.592Z",
  "level": "info",
  "logger": "background.tasks",
  "component": "background_tasks",
  "event": "Starting congressional members sync",
  "action": "sync-all",
  "kwargs": {}
}
```

## Best Practices

1. **Use structured logging**: Pass data as keyword arguments instead of string formatting
2. **Include context**: Always include relevant IDs, counts, and parameters
3. **Use appropriate log levels**:
   - `DEBUG`: Detailed information for debugging
   - `INFO`: General information about program execution
   - `WARNING`: Something unexpected happened but the program can continue
   - `ERROR`: A serious problem occurred
4. **Include stack traces**: Use `exc_info=True` for error logging
5. **Keep debug logging minimal in production**: Only enable when troubleshooting

## Troubleshooting

### No Logs Appearing
- Check that the component's log level allows the message level
- Verify the logger is using the correct component-specific logger
- Check that the environment variable is set correctly

### Too Many Logs
- Disable debug logging for components you don't need to debug
- Use `info` level for normal operation
- Consider using `WARNING` level for noisy components in production

### Performance Impact
- Debug logging can impact performance, especially in production
- Disable debug logging when not needed
- Consider using sampling for high-volume debug logs 