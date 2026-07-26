import React, { Component, ErrorInfo, ReactNode } from 'react';
import { logger, LogComponent } from '../core/logging';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
}

/**
 * Error Boundary component with integrated logging
 * 
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI instead of the
 * component tree that crashed.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error with detailed information
    logger.critical(LogComponent.ERRORS, 'React Error Boundary caught an error', {
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
      },
      errorInfo: {
        componentStack: errorInfo.componentStack,
      },
      userAgent: navigator.userAgent,
      url: window.location.href,
      timestamp: new Date().toISOString(),
    });

    // Update state with error info
    this.setState({
      error,
      errorInfo,
    });

    // Call custom error handler if provided
    if (this.props.onError) {
      this.props.onError(error, errorInfo);
    }
  }

  render() {
    if (this.state.hasError) {
      // Custom fallback UI
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default fallback UI
      return (
        <div className="flex min-h-screen items-center justify-center bg-surface px-4">
          <div className="card w-full max-w-md p-6">
            <div className="mb-4 flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-8 w-8 text-sev-flag"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
                  />
                </svg>
              </div>
              <div className="ml-3">
                <h3 className="font-display text-lg font-medium text-content">Something went wrong</h3>
              </div>
            </div>
            <div className="mb-4">
              <p className="font-ui text-sm text-content-muted">
                We're sorry, but something unexpected happened. Our team has been notified
                and is working to fix the issue.
              </p>
            </div>
            <div className="flex space-x-3">
              <button onClick={() => window.location.reload()} className="btn-primary text-sm">
                Reload Page
              </button>
              <button
                onClick={() => this.setState({ hasError: false, error: undefined, errorInfo: undefined })}
                className="btn-secondary text-sm"
              >
                Try Again
              </button>
            </div>
            {process.env.NODE_ENV === 'development' && this.state.error && (
              <details className="mt-4">
                <summary className="cursor-pointer font-data text-[11px] uppercase tracking-[0.12em] text-content-faint">
                  Error Details (Development)
                </summary>
                <div className="mt-2 rounded-md border border-line bg-surface-inset p-3">
                  <pre className="whitespace-pre-wrap font-data text-xs text-content-muted">
                    {this.state.error.toString()}
                    {this.state.errorInfo?.componentStack}
                  </pre>
                </div>
              </details>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

/**
 * Higher-order component for wrapping components with error boundary
 */
export const withErrorBoundary = <P extends object>(
  Component: React.ComponentType<P>,
  fallback?: ReactNode,
  onError?: (error: Error, errorInfo: ErrorInfo) => void
) => {
  const WrappedComponent = (props: P) => (
    <ErrorBoundary fallback={fallback} onError={onError}>
      <Component {...props} />
    </ErrorBoundary>
  );

  WrappedComponent.displayName = `withErrorBoundary(${Component.displayName || Component.name})`;
  
  return WrappedComponent;
};

/**
 * Hook for manually logging errors in functional components
 */
export const useErrorLogger = () => {
  const logError = (error: Error, context?: string, additionalData?: Record<string, any>) => {
    logger.error(LogComponent.ERRORS, `Error in ${context || 'component'}`, {
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
      },
      context,
      ...additionalData,
    });
  };

  const logAsyncError = (error: Error, operation: string, additionalData?: Record<string, any>) => {
    logger.error(LogComponent.ERRORS, `Async operation failed: ${operation}`, {
      error: {
        name: error.name,
        message: error.message,
        stack: error.stack,
      },
      operation,
      ...additionalData,
    });
  };

  return {
    logError,
    logAsyncError,
  };
};

export default ErrorBoundary;
