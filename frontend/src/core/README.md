# CapitolScope Frontend Logging System

This directory contains the structured logging system for the CapitolScope frontend application, designed to match the backend logging style and provide comprehensive observability.

## Overview

The logging system provides:
- **Structured logging** with consistent format across all components
- **Component-based logging** with different log levels per component
- **Environment-specific configuration** (development vs production)
- **React hooks** for easy integration with components
- **Error boundary integration** for automatic error logging
- **Performance monitoring** capabilities
- **User interaction tracking**

## Core Files

### `logging.ts`
The main logging configuration and logger class. Provides:
- `LogLevel` enum (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- `LogComponent` enum for different application areas
- `Logger` class with singleton instance
- Environment-specific log level configuration
- Console output with styling
- Local storage logging in development
- External service integration for production

### `useLogger.ts` (hooks/)
React hooks for logging integration:
- `useLogger(componentName)` - Basic component logging
- `useApiLogger()` - API call logging
- `useInteractionLogger()` - User interaction logging
- `usePerformanceLogger()` - Performance metrics
- `useAuthLogger()` - Authentication events
- `useDataLogger()` - Data operations

### `ErrorBoundary.tsx` (components/)
React error boundary with integrated logging:
- Catches JavaScript errors in component tree
- Logs errors with full context
- Provides fallback UI
- HOC wrapper for easy integration

### `logging.ts` (utils/)
Utility functions for common logging patterns:
- Performance timing utilities
- User interaction helpers
- API call wrappers
- Form interaction logging
- Navigation tracking
- Data operation logging

## Usage Examples

### Basic Component Logging

```typescript
import { useLogger } from '../hooks/useLogger';

const MyComponent = () => {
  const { logInfo, logError, logUserAction } = useLogger('MyComponent');
  
  useEffect(() => {
    logInfo('Component mounted');
  }, []);
  
  const handleClick = () => {
    logUserAction('button_click', 'MyComponent', { buttonId: 'submit' });
  };
  
  return <button onClick={handleClick}>Click me</button>;
};
```

### API Logging

```typescript
import { useApiLogger } from '../hooks/useLogger';

const MyComponent = () => {
  const { logRequest, logResponse, logError } = useApiLogger();
  
  const fetchData = async () => {
    try {
      logRequest('GET', '/api/data');
      const response = await api.get('/api/data');
      logResponse('GET', '/api/data', response.status, response.data);
    } catch (error) {
      logError('GET', '/api/data', error);
    }
  };
};
```

### Performance Logging

```typescript
import { usePerformanceLogger } from '../hooks/useLogger';

const MyComponent = () => {
  const { startTiming, logMetric } = usePerformanceLogger();
  
  const performOperation = () => {
    const timer = startTiming('data-processing');
    
    // Perform work...
    
    timer(); // Logs the duration
  };
};
```

### Error Boundary Integration

```typescript
import { ErrorBoundary } from '../components/ErrorBoundary';

const App = () => (
  <ErrorBoundary>
    <MyComponent />
  </ErrorBoundary>
);
```

## Configuration

### Environment-Specific Log Levels

The system automatically adjusts log levels based on the environment:

**Development:**
- API: DEBUG
- Components: DEBUG
- Data: DEBUG
- Interactions: DEBUG
- Performance: DEBUG

**Production:**
- API: INFO
- Components: WARNING
- Data: INFO
- Interactions: WARNING
- Performance: WARNING

### Custom Log Levels

You can override log levels at runtime:

```typescript
import { logger, LogComponent, LogLevel } from '../core/logging';

// Enable debug logging for a specific component
logger.updateLogLevel(LogComponent.API, LogLevel.DEBUG);

// Enable debug logging for all components
logger.enableDebugLogging();
```

## Log Output

### Console Output
Logs are displayed in the browser console with color-coded styling:
- **DEBUG**: Gray text
- **INFO**: Blue text
- **WARNING**: Orange text
- **ERROR**: Red text
- **CRITICAL**: Red text with background

### Development Storage
In development mode, logs are stored in localStorage under `capitolscope_logs` (last 100 entries).

### Production Integration
In production, ERROR and CRITICAL logs are sent to external logging services.

## Log Entry Structure

Each log entry contains:
```typescript
{
  timestamp: string;           // ISO timestamp
  level: LogLevel;            // Log level
  component: LogComponent;    // Component that generated the log
  message: string;            // Log message
  data?: Record<string, any>; // Additional data
  userId?: string;            // Current user ID (if authenticated)
  sessionId: string;          // Session identifier
  userAgent: string;          // Browser user agent
  url: string;                // Current page URL
}
```

## Best Practices

1. **Use appropriate log levels:**
   - DEBUG: Detailed information for debugging
   - INFO: General information about application flow
   - WARNING: Potentially harmful situations
   - ERROR: Error events that might still allow the application to continue
   - CRITICAL: Very severe errors that might cause the application to abort

2. **Include relevant context:**
   ```typescript
   logger.info(LogComponent.API, 'User data fetched', {
     userId: user.id,
     dataCount: data.length,
     duration: 150
   });
   ```

3. **Use component-specific loggers:**
   ```typescript
   // Good
   logger.info(LogComponent.AUTH, 'User login', { userId });
   
   // Avoid
   logger.info(LogComponent.GENERAL, 'User login', { userId });
   ```

4. **Log user interactions for analytics:**
   ```typescript
   const { logClick, logFormSubmit } = useInteractionLogger();
   
   const handleSubmit = () => {
     logFormSubmit('contact-form', { fieldCount: 5 });
   };
   ```

5. **Monitor performance:**
   ```typescript
   const { startTiming } = usePerformanceLogger();
   
   const processData = () => {
     const timer = startTiming('data-processing');
     // ... work ...
     timer();
   };
   ```

## Integration with Backend

The frontend logging system is designed to complement the backend logging system:

- **Consistent log levels** across frontend and backend
- **Structured data format** for easy correlation
- **Session tracking** for request tracing
- **User context** for authentication correlation

## Debugging

### View Stored Logs
```typescript
import { logger } from '../core/logging';

// Get all stored logs
const logs = logger.getStoredLogs();

// Export logs as JSON
const logsJson = logger.exportLogs();

// Clear stored logs
logger.clearStoredLogs();
```

### Development Tools
The system includes a `LoggingExample` component that demonstrates various logging patterns and can be used for testing and debugging.

## Migration from console.log

Replace existing console.log statements:

```typescript
// Before
console.log('User clicked button', { buttonId: 'submit' });
console.error('API error:', error);

// After
import { useLogger } from '../hooks/useLogger';

const { logInfo, logError } = useLogger('MyComponent');
logInfo('User clicked button', { buttonId: 'submit' });
logError('API error', { error });
```

This logging system provides comprehensive observability for the CapitolScope frontend application while maintaining consistency with the backend logging approach.
