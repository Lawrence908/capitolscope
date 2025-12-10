import { useCallback, useEffect, useRef } from 'react';
import { logger, LogComponent, LogLevel } from '../core/logging';

/**
 * Hook for logging component lifecycle and interactions
 */
export const useLogger = (componentName: string) => {
  const mountTime = useRef<number>(Date.now());

  // Log component mount
  useEffect(() => {
    logger.componentMount(componentName);
    mountTime.current = Date.now();
    
    return () => {
      const mountDuration = Date.now() - mountTime.current;
      logger.debug(LogComponent.COMPONENTS, `Component ${componentName} unmounted after ${mountDuration}ms`);
    };
  }, [componentName]);

  // Logging methods for this component
  const logDebug = useCallback((message: string, data?: Record<string, any>) => {
    logger.debug(LogComponent.COMPONENTS, `[${componentName}] ${message}`, data);
  }, [componentName]);

  const logInfo = useCallback((message: string, data?: Record<string, any>) => {
    logger.info(LogComponent.COMPONENTS, `[${componentName}] ${message}`, data);
  }, [componentName]);

  const logWarning = useCallback((message: string, data?: Record<string, any>) => {
    logger.warning(LogComponent.COMPONENTS, `[${componentName}] ${message}`, data);
  }, [componentName]);

  const logError = useCallback((message: string, data?: Record<string, any>) => {
    logger.error(LogComponent.COMPONENTS, `[${componentName}] ${message}`, data);
  }, [componentName]);

  const logUserAction = useCallback((action: string, data?: Record<string, any>) => {
    logger.userAction(action, componentName, data);
  }, [componentName]);

  const logPerformance = useCallback((metric: string, value: number, unit?: string) => {
    logger.performance(`${componentName}: ${metric}`, value, unit);
  }, [componentName]);

  return {
    logDebug,
    logInfo,
    logWarning,
    logError,
    logUserAction,
    logPerformance,
  };
};

/**
 * Hook for logging API calls and data fetching
 */
export const useApiLogger = () => {
  const logRequest = useCallback((method: string, url: string, data?: any) => {
    logger.apiRequest(method, url, data);
  }, []);

  const logResponse = useCallback((method: string, url: string, status: number, data?: any) => {
    logger.apiResponse(method, url, status, data);
  }, []);

  const logError = useCallback((method: string, url: string, error: any) => {
    logger.apiError(method, url, error);
  }, []);

  return {
    logRequest,
    logResponse,
    logError,
  };
};

/**
 * Hook for logging user interactions
 */
export const useInteractionLogger = () => {
  const logClick = useCallback((element: string, data?: Record<string, any>) => {
    logger.userAction('click', element, data);
  }, []);

  const logFormSubmit = useCallback((formName: string, data?: Record<string, any>) => {
    logger.userAction('form_submit', formName, data);
  }, []);

  const logFormError = useCallback((formName: string, field: string, error: string) => {
    logger.userAction('form_error', formName, { field, error });
  }, []);

  const logNavigation = useCallback((from: string, to: string) => {
    logger.navigation(from, to);
  }, []);

  const logSearch = useCallback((query: string, results?: number) => {
    logger.userAction('search', 'search', { query, results });
  }, []);

  const logFilter = useCallback((filterType: string, value: any) => {
    logger.userAction('filter', filterType, { value });
  }, []);

  return {
    logClick,
    logFormSubmit,
    logFormError,
    logNavigation,
    logSearch,
    logFilter,
  };
};

/**
 * Hook for logging performance metrics
 */
export const usePerformanceLogger = () => {
  const startTiming = useCallback((operation: string) => {
    const startTime = performance.now();
    return () => {
      const duration = performance.now() - startTime;
      logger.performance(operation, duration);
    };
  }, []);

  const logMetric = useCallback((metric: string, value: number, unit?: string) => {
    logger.performance(metric, value, unit);
  }, []);

  const logRenderTime = useCallback((componentName: string, renderTime: number) => {
    logger.performance(`${componentName} render time`, renderTime);
  }, []);

  return {
    startTiming,
    logMetric,
    logRenderTime,
  };
};

/**
 * Hook for logging authentication events
 */
export const useAuthLogger = () => {
  const logLogin = useCallback((userId: string, method?: string) => {
    logger.info(LogComponent.AUTH, 'User login', { userId, method });
  }, []);

  const logLogout = useCallback((userId: string) => {
    logger.info(LogComponent.AUTH, 'User logout', { userId });
  }, []);

  const logAuthError = useCallback((error: string, context?: string) => {
    logger.error(LogComponent.AUTH, 'Authentication error', { error, context });
  }, []);

  const logTokenRefresh = useCallback((userId: string) => {
    logger.debug(LogComponent.AUTH, 'Token refresh', { userId });
  }, []);

  const logPermissionDenied = useCallback((resource: string, action: string) => {
    logger.warning(LogComponent.AUTH, 'Permission denied', { resource, action });
  }, []);

  return {
    logLogin,
    logLogout,
    logAuthError,
    logTokenRefresh,
    logPermissionDenied,
  };
};

/**
 * Hook for logging data operations
 */
export const useDataLogger = () => {
  const logDataFetch = useCallback((source: string, success: boolean, count?: number) => {
    logger.info(LogComponent.DATA, `Data fetch from ${source}`, { success, count });
  }, []);

  const logDataError = useCallback((source: string, error: string) => {
    logger.error(LogComponent.DATA, `Data error from ${source}`, { error });
  }, []);

  const logDataUpdate = useCallback((entity: string, action: string, success: boolean) => {
    logger.info(LogComponent.DATA, `Data update: ${entity} ${action}`, { success });
  }, []);

  const logCacheHit = useCallback((key: string) => {
    logger.debug(LogComponent.DATA, 'Cache hit', { key });
  }, []);

  const logCacheMiss = useCallback((key: string) => {
    logger.debug(LogComponent.DATA, 'Cache miss', { key });
  }, []);

  return {
    logDataFetch,
    logDataError,
    logDataUpdate,
    logCacheHit,
    logCacheMiss,
  };
};
