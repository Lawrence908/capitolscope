/**
 * Logging utilities and helper functions
 */

import { logger, LogComponent, LogLevel } from '../core/logging';

/**
 * Utility to log performance metrics
 */
export const logPerformance = (name: string, startTime: number, additionalData?: Record<string, any>) => {
  const duration = performance.now() - startTime;
  logger.performance(name, duration, 'ms');
  
  if (additionalData) {
    logger.debug(LogComponent.PERFORMANCE, `Performance metric: ${name}`, {
      duration,
      ...additionalData,
    });
  }
};

/**
 * Utility to log user interactions with timing
 */
export const logUserInteraction = (
  action: string,
  element: string,
  startTime?: number,
  additionalData?: Record<string, any>
) => {
  const data: Record<string, any> = {
    action,
    element,
    ...additionalData,
  };

  if (startTime) {
    data.duration = performance.now() - startTime;
  }

  logger.userAction(action, element, data);
};

/**
 * Utility to log API calls with timing
 */
export const logApiCall = async <T>(
  method: string,
  url: string,
  apiCall: () => Promise<T>,
  additionalData?: Record<string, any>
): Promise<T> => {
  const startTime = performance.now();
  
  try {
    logger.apiRequest(method, url, additionalData);
    const result = await apiCall();
    const duration = performance.now() - startTime;
    
    logger.apiResponse(method, url, 200, { duration, ...additionalData });
    return result;
  } catch (error: any) {
    const duration = performance.now() - startTime;
    logger.apiError(method, url, { error, duration, ...additionalData });
    throw error;
  }
};

/**
 * Utility to log component lifecycle events
 */
export const logComponentLifecycle = {
  mount: (componentName: string, props?: any) => {
    logger.componentMount(componentName, props);
  },
  
  unmount: (componentName: string) => {
    logger.componentUnmount(componentName);
  },
  
  update: (componentName: string, prevProps?: any, nextProps?: any) => {
    logger.debug(LogComponent.COMPONENTS, `Component Updated: ${componentName}`, {
      prevProps,
      nextProps,
    });
  },
  
  render: (componentName: string, renderTime: number) => {
    logger.performance(`${componentName} render`, renderTime);
  },
};

/**
 * Utility to log navigation events
 */
export const logNavigation = {
  routeChange: (from: string, to: string, method: 'push' | 'replace' | 'back' | 'forward' = 'push') => {
    logger.navigation(from, to);
    logger.info(LogComponent.NAVIGATION, `Route change: ${from} → ${to}`, { method });
  },
  
  linkClick: (href: string, text?: string) => {
    logger.userAction('link_click', 'navigation', { href, text });
  },
  
  backButton: () => {
    logger.userAction('back_button', 'navigation');
  },
  
  forwardButton: () => {
    logger.userAction('forward_button', 'navigation');
  },
};

/**
 * Utility to log form interactions
 */
export const logFormInteraction = {
  submit: (formName: string, data?: any) => {
    logger.userAction('form_submit', formName, { data });
  },
  
  fieldChange: (formName: string, fieldName: string, value: any) => {
    logger.debug(LogComponent.INTERACTIONS, `Form field change: ${formName}.${fieldName}`, {
      fieldName,
      value: typeof value === 'string' ? value.substring(0, 100) : value, // Truncate long strings
    });
  },
  
  validationError: (formName: string, fieldName: string, error: string) => {
    logger.userAction('form_validation_error', formName, { fieldName, error });
  },
  
  reset: (formName: string) => {
    logger.userAction('form_reset', formName);
  },
};

/**
 * Utility to log search and filtering
 */
export const logSearchAndFilter = {
  search: (query: string, results: number, source: string = 'search') => {
    logger.userAction('search', source, { query, results });
  },
  
  filter: (filterType: string, value: any, results: number) => {
    logger.userAction('filter', filterType, { value, results });
  },
  
  sort: (field: string, direction: 'asc' | 'desc') => {
    logger.userAction('sort', 'data', { field, direction });
  },
  
  pagination: (page: number, perPage: number, total: number) => {
    logger.userAction('pagination', 'data', { page, perPage, total });
  },
};

/**
 * Utility to log data operations
 */
export const logDataOperation = {
  fetch: (source: string, success: boolean, count?: number, error?: any) => {
    if (success) {
      logger.info(LogComponent.DATA, `Data fetch from ${source}`, { count });
    } else {
      logger.error(LogComponent.DATA, `Data fetch failed from ${source}`, { error });
    }
  },
  
  cache: (key: string, hit: boolean) => {
    if (hit) {
      logger.debug(LogComponent.DATA, 'Cache hit', { key });
    } else {
      logger.debug(LogComponent.DATA, 'Cache miss', { key });
    }
  },
  
  update: (entity: string, action: string, success: boolean, error?: any) => {
    if (success) {
      logger.info(LogComponent.DATA, `Data update: ${entity} ${action}`);
    } else {
      logger.error(LogComponent.DATA, `Data update failed: ${entity} ${action}`, { error });
    }
  },
};

/**
 * Utility to log authentication events
 */
export const logAuthEvent = {
  login: (userId: string, method: string = 'password') => {
    logger.info(LogComponent.AUTH, 'User login', { userId, method });
  },
  
  logout: (userId: string) => {
    logger.info(LogComponent.AUTH, 'User logout', { userId });
  },
  
  tokenRefresh: (userId: string) => {
    logger.debug(LogComponent.AUTH, 'Token refresh', { userId });
  },
  
  permissionDenied: (resource: string, action: string, userId?: string) => {
    logger.warning(LogComponent.AUTH, 'Permission denied', { resource, action, userId });
  },
  
  authError: (error: string, context?: string) => {
    logger.error(LogComponent.AUTH, 'Authentication error', { error, context });
  },
};

/**
 * Utility to log errors with context
 */
export const logError = (error: Error, context: string, additionalData?: Record<string, any>) => {
  logger.error(LogComponent.ERRORS, `Error in ${context}`, {
    error: {
      name: error.name,
      message: error.message,
      stack: error.stack,
    },
    context,
    ...additionalData,
  });
};

/**
 * Utility to log warnings with context
 */
export const logWarning = (message: string, context: string, additionalData?: Record<string, any>) => {
  logger.warning(LogComponent.GENERAL, `Warning in ${context}: ${message}`, {
    context,
    ...additionalData,
  });
};

/**
 * Utility to log info messages with context
 */
export const logInfo = (message: string, context: string, additionalData?: Record<string, any>) => {
  logger.info(LogComponent.GENERAL, `Info from ${context}: ${message}`, {
    context,
    ...additionalData,
  });
};

/**
 * Utility to log debug messages with context
 */
export const logDebug = (message: string, context: string, additionalData?: Record<string, any>) => {
  logger.debug(LogComponent.GENERAL, `Debug from ${context}: ${message}`, {
    context,
    ...additionalData,
  });
};

/**
 * Utility to create a performance timer
 */
export const createPerformanceTimer = (name: string) => {
  const startTime = performance.now();
  
  return {
    end: (additionalData?: Record<string, any>) => {
      logPerformance(name, startTime, additionalData);
    },
    
    checkpoint: (checkpointName: string, additionalData?: Record<string, any>) => {
      const currentTime = performance.now();
      const duration = currentTime - startTime;
      logger.performance(`${name} - ${checkpointName}`, duration, 'ms');
      
      if (additionalData) {
        logger.debug(LogComponent.PERFORMANCE, `Performance checkpoint: ${name} - ${checkpointName}`, {
          duration,
          ...additionalData,
        });
      }
    },
  };
};

/**
 * Utility to log memory usage (if available)
 */
export const logMemoryUsage = (context: string) => {
  if ('memory' in performance) {
    const memory = (performance as any).memory;
    logger.info(LogComponent.PERFORMANCE, 'Memory usage', {
      context,
      used: memory.usedJSHeapSize,
      total: memory.totalJSHeapSize,
      limit: memory.jsHeapSizeLimit,
    });
  }
};

export default {
  logPerformance,
  logUserInteraction,
  logApiCall,
  logComponentLifecycle,
  logNavigation,
  logFormInteraction,
  logSearchAndFilter,
  logDataOperation,
  logAuthEvent,
  logError,
  logWarning,
  logInfo,
  logDebug,
  createPerformanceTimer,
  logMemoryUsage,
};
