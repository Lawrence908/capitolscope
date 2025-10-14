/**
 * Structured logging configuration for CapitolScope Frontend.
 *
 * This module configures structured logging for better
 * observability and debugging in both development and production.
 */

export enum LogLevel {
  DEBUG = 'DEBUG',
  INFO = 'INFO',
  WARNING = 'WARNING',
  ERROR = 'ERROR',
  CRITICAL = 'CRITICAL',
}

export enum LogComponent {
  /** API requests and responses */
  API = 'api',
  /** Authentication and user management */
  AUTH = 'auth',
  /** Component lifecycle and rendering */
  COMPONENTS = 'components',
  /** Data fetching and state management */
  DATA = 'data',
  /** User interactions and events */
  INTERACTIONS = 'interactions',
  /** Navigation and routing */
  NAVIGATION = 'navigation',
  /** Performance monitoring */
  PERFORMANCE = 'performance',
  /** Error boundaries and error handling */
  ERRORS = 'errors',
  /** General application logging */
  GENERAL = 'general',
}

export interface LogEntry {
  timestamp: string;
  level: LogLevel;
  component: LogComponent;
  message: string;
  data?: Record<string, any>;
  userId?: string;
  sessionId?: string;
  userAgent?: string;
  url?: string;
}

// Centralized logging configuration
export const LOGGING_CONFIG = {
  // Default log levels for different components
  [LogComponent.API]: LogLevel.INFO,
  [LogComponent.AUTH]: LogLevel.INFO,
  [LogComponent.COMPONENTS]: LogLevel.INFO,
  [LogComponent.DATA]: LogLevel.INFO,
  [LogComponent.INTERACTIONS]: LogLevel.INFO,
  [LogComponent.NAVIGATION]: LogLevel.INFO,
  [LogComponent.PERFORMANCE]: LogLevel.INFO,
  [LogComponent.ERRORS]: LogLevel.ERROR,
  [LogComponent.GENERAL]: LogLevel.INFO,
  
  // Environment-specific overrides
  development: {
    [LogComponent.API]: LogLevel.DEBUG,
    [LogComponent.COMPONENTS]: LogLevel.DEBUG,
    [LogComponent.DATA]: LogLevel.DEBUG,
    [LogComponent.INTERACTIONS]: LogLevel.DEBUG,
    [LogComponent.PERFORMANCE]: LogLevel.DEBUG,
  },
  production: {
    [LogComponent.API]: LogLevel.INFO,
    [LogComponent.COMPONENTS]: LogLevel.WARNING,
    [LogComponent.DATA]: LogLevel.INFO,
    [LogComponent.INTERACTIONS]: LogLevel.WARNING,
    [LogComponent.PERFORMANCE]: LogLevel.WARNING,
  }
};

class Logger {
  private sessionId: string;
  private userId?: string;
  private environment: string;

  constructor() {
    this.sessionId = this.generateSessionId();
    this.environment = import.meta.env.MODE || 'development';
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  setUserId(userId: string): void {
    this.userId = userId;
  }

  clearUserId(): void {
    this.userId = undefined;
  }

  private shouldLog(component: LogComponent, level: LogLevel): boolean {
    const envConfig = LOGGING_CONFIG[this.environment as keyof typeof LOGGING_CONFIG];
    const componentLevel = envConfig?.[component] || LOGGING_CONFIG[component];
    
    const levelPriority = {
      [LogLevel.DEBUG]: 0,
      [LogLevel.INFO]: 1,
      [LogLevel.WARNING]: 2,
      [LogLevel.ERROR]: 3,
      [LogLevel.CRITICAL]: 4,
    };

    return levelPriority[level] >= levelPriority[componentLevel];
  }

  private createLogEntry(
    level: LogLevel,
    component: LogComponent,
    message: string,
    data?: Record<string, any>
  ): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      component,
      message,
      data,
      userId: this.userId,
      sessionId: this.sessionId,
      userAgent: navigator.userAgent,
      url: window.location.href,
    };
  }

  private log(level: LogLevel, component: LogComponent, message: string, data?: Record<string, any>): void {
    if (!this.shouldLog(component, level)) {
      return;
    }

    const logEntry = this.createLogEntry(level, component, message, data);

    // Console output with styling
    const style = this.getConsoleStyle(level);
    const prefix = `[${logEntry.timestamp}] [${level}] [${component.toUpperCase()}]`;
    
    if (data) {
      console.log(`%c${prefix} ${message}`, style, data);
    } else {
      console.log(`%c${prefix} ${message}`, style);
    }

    // In development, also log to localStorage for debugging
    if (this.environment === 'development') {
      this.logToStorage(logEntry);
    }

    // Send to external logging service in production
    if (this.environment === 'production' && level >= LogLevel.ERROR) {
      this.sendToExternalService(logEntry);
    }
  }

  private getConsoleStyle(level: LogLevel): string {
    const styles = {
      [LogLevel.DEBUG]: 'color: #6B7280; font-weight: normal;',
      [LogLevel.INFO]: 'color: #3B82F6; font-weight: normal;',
      [LogLevel.WARNING]: 'color: #F59E0B; font-weight: bold;',
      [LogLevel.ERROR]: 'color: #EF4444; font-weight: bold;',
      [LogLevel.CRITICAL]: 'color: #DC2626; font-weight: bold; background: #FEF2F2;',
    };
    return styles[level];
  }

  private logToStorage(logEntry: LogEntry): void {
    try {
      const logs = JSON.parse(localStorage.getItem('capitolscope_logs') || '[]');
      logs.push(logEntry);
      
      // Keep only last 100 logs
      if (logs.length > 100) {
        logs.splice(0, logs.length - 100);
      }
      
      localStorage.setItem('capitolscope_logs', JSON.stringify(logs));
    } catch (error) {
      console.warn('Failed to store log entry:', error);
    }
  }

  private async sendToExternalService(logEntry: LogEntry): Promise<void> {
    try {
      // In a real application, you would send this to your logging service
      // For now, we'll just log it to console in production
      console.log('External logging service:', logEntry);
    } catch (error) {
      console.warn('Failed to send log to external service:', error);
    }
  }

  // Public logging methods
  debug(component: LogComponent, message: string, data?: Record<string, any>): void {
    this.log(LogLevel.DEBUG, component, message, data);
  }

  info(component: LogComponent, message: string, data?: Record<string, any>): void {
    this.log(LogLevel.INFO, component, message, data);
  }

  warning(component: LogComponent, message: string, data?: Record<string, any>): void {
    this.log(LogLevel.WARNING, component, message, data);
  }

  error(component: LogComponent, message: string, data?: Record<string, any>): void {
    this.log(LogLevel.ERROR, component, message, data);
  }

  critical(component: LogComponent, message: string, data?: Record<string, any>): void {
    this.log(LogLevel.CRITICAL, component, message, data);
  }

  // Convenience methods for common logging patterns
  apiRequest(method: string, url: string, data?: any): void {
    this.info(LogComponent.API, `API Request: ${method.toUpperCase()} ${url}`, { data });
  }

  apiResponse(method: string, url: string, status: number, data?: any): void {
    this.info(LogComponent.API, `API Response: ${method.toUpperCase()} ${url} - ${status}`, { data });
  }

  apiError(method: string, url: string, error: any): void {
    this.error(LogComponent.API, `API Error: ${method.toUpperCase()} ${url}`, { error });
  }

  userAction(action: string, component: string, data?: any): void {
    this.info(LogComponent.INTERACTIONS, `User Action: ${action}`, { component, ...data });
  }

  componentMount(componentName: string, props?: any): void {
    this.debug(LogComponent.COMPONENTS, `Component Mounted: ${componentName}`, { props });
  }

  componentUnmount(componentName: string): void {
    this.debug(LogComponent.COMPONENTS, `Component Unmounted: ${componentName}`);
  }

  navigation(from: string, to: string): void {
    this.info(LogComponent.NAVIGATION, `Navigation: ${from} → ${to}`);
  }

  performance(metric: string, value: number, unit: string = 'ms'): void {
    this.info(LogComponent.PERFORMANCE, `Performance: ${metric}`, { value, unit });
  }

  // Utility methods
  getStoredLogs(): LogEntry[] {
    try {
      return JSON.parse(localStorage.getItem('capitolscope_logs') || '[]');
    } catch {
      return [];
    }
  }

  clearStoredLogs(): void {
    localStorage.removeItem('capitolscope_logs');
  }

  exportLogs(): string {
    return JSON.stringify(this.getStoredLogs(), null, 2);
  }
}

// Create and export singleton instance
export const logger = new Logger();

// Export convenience functions
export const log = {
  debug: (component: LogComponent, message: string, data?: Record<string, any>) => 
    logger.debug(component, message, data),
  info: (component: LogComponent, message: string, data?: Record<string, any>) => 
    logger.info(component, message, data),
  warning: (component: LogComponent, message: string, data?: Record<string, any>) => 
    logger.warning(component, message, data),
  error: (component: LogComponent, message: string, data?: Record<string, any>) => 
    logger.error(component, message, data),
  critical: (component: LogComponent, message: string, data?: Record<string, any>) => 
    logger.critical(component, message, data),
};

// Export component-specific loggers for convenience
export const apiLogger = {
  request: (method: string, url: string, data?: any) => logger.apiRequest(method, url, data),
  response: (method: string, url: string, status: number, data?: any) => logger.apiResponse(method, url, status, data),
  error: (method: string, url: string, error: any) => logger.apiError(method, url, error),
};

export const authLogger = {
  login: (userId: string) => logger.info(LogComponent.AUTH, 'User login', { userId }),
  logout: (userId: string) => logger.info(LogComponent.AUTH, 'User logout', { userId }),
  tokenRefresh: (userId: string) => logger.debug(LogComponent.AUTH, 'Token refresh', { userId }),
  authError: (error: string) => logger.error(LogComponent.AUTH, 'Authentication error', { error }),
};

export const componentLogger = {
  mount: (componentName: string, props?: any) => logger.componentMount(componentName, props),
  unmount: (componentName: string) => logger.componentUnmount(componentName),
  render: (componentName: string, props?: any) => logger.debug(LogComponent.COMPONENTS, `Component Render: ${componentName}`, { props }),
};

export const navigationLogger = {
  navigate: (from: string, to: string) => logger.navigation(from, to),
  routeChange: (route: string) => logger.info(LogComponent.NAVIGATION, `Route change: ${route}`),
};

export const performanceLogger = {
  metric: (metric: string, value: number, unit?: string) => logger.performance(metric, value, unit),
  timing: (operation: string, startTime: number) => {
    const duration = performance.now() - startTime;
    logger.performance(operation, duration);
  },
};

export default logger;
