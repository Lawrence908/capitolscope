import React, { useState, useEffect } from 'react';
import { useLogger, useInteractionLogger, usePerformanceLogger } from '../hooks/useLogger';
import { createPerformanceTimer } from '../utils/logging';

/**
 * Example component demonstrating how to use the logging system
 * This component shows various logging patterns and can be used as a reference
 */
const LoggingExample: React.FC = () => {
  const [count, setCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  
  // Use the logging hooks
  const { logInfo, logError, logUserAction, logPerformance } = useLogger('LoggingExample');
  const { logClick, logFormSubmit } = useInteractionLogger();
  const { startTiming, logMetric } = usePerformanceLogger();

  // Log component mount
  useEffect(() => {
    logInfo('Component mounted');
    
    // Example of performance logging
    const timer = createPerformanceTimer('LoggingExample initialization');
    
    // Simulate some initialization work
    setTimeout(() => {
      timer.end({ message: 'Initialization complete' });
    }, 100);
  }, [logInfo]);

  const handleButtonClick = () => {
    const startTime = performance.now();
    
    // Log user interaction
    logClick('example-button', { count });
    logUserAction('button_click', { count });
    
    // Simulate some work
    setIsLoading(true);
    
    setTimeout(() => {
      const duration = performance.now() - startTime;
      logPerformance('button_click_processing', duration);
      
      setCount(prev => prev + 1);
      setIsLoading(false);
      
      logInfo('Count updated', { newCount: count + 1 });
    }, 500);
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    // Log form submission
    logFormSubmit('example-form', { count });
    logUserAction('form_submit', { count });
    
    logInfo('Form submitted', { count });
  };

  const handleError = () => {
    try {
      // Simulate an error
      throw new Error('This is a test error');
    } catch (error) {
      logError('Test error occurred', { error });
    }
  };

  const handlePerformanceTest = () => {
    const timer = startTiming('performance-test');
    
    // Simulate some work
    const startTime = performance.now();
    let result = 0;
    for (let i = 0; i < 1000000; i++) {
      result += Math.random();
    }
    
    const duration = performance.now() - startTime;
    logMetric('calculation', duration);
    timer();
    
    logInfo('Performance test completed', { result, duration });
  };

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h2 className="mb-4 font-display text-4xl font-extrabold leading-none text-content">Logging System Example</h2>
      
      <div className="space-y-4">
        <div className="section-rule py-4">
          <h3 className="mb-2 font-display text-xl font-extrabold leading-none text-content">Counter Example</h3>
          <p className="mb-2 font-ui text-sm text-content-muted">Count: {count}</p>
          <button
            onClick={handleButtonClick}
            disabled={isLoading}
            className="btn-primary disabled:opacity-50"
          >
            {isLoading ? 'Loading...' : 'Increment Counter'}
          </button>
        </div>

        <div className="section-rule py-4">
          <h3 className="mb-2 font-display text-xl font-extrabold leading-none text-content">Form Example</h3>
          <form onSubmit={handleFormSubmit} className="space-y-2">
            <input
              type="text"
              value={count.toString()}
              readOnly
              className="input-field"
            />
            <button
              type="submit"
              className="btn-secondary"
            >
              Submit Form
            </button>
          </form>
        </div>

        <div className="section-rule py-4">
          <h3 className="mb-2 font-display text-xl font-extrabold leading-none text-content">Error Example</h3>
          <button
            onClick={handleError}
            className="btn-primary"
          >
            Trigger Error
          </button>
        </div>

        <div className="section-rule py-4">
          <h3 className="mb-2 font-display text-xl font-extrabold leading-none text-content">Performance Example</h3>
          <button
            onClick={handlePerformanceTest}
            className="btn-secondary"
          >
            Run Performance Test
          </button>
        </div>

        <div className="border-l-4 border-content bg-surface-inset p-4">
          <h3 className="mb-2 font-display text-xl font-extrabold leading-none text-content">Logging Information</h3>
          <p className="font-ui text-sm text-content-muted">
            This component demonstrates various logging patterns. Check the browser console
            and developer tools to see the structured logging output.
          </p>
          <p className="font-ui text-sm text-content-muted mt-2">
            In development mode, logs are also stored in localStorage under 'capitolscope_logs'.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoggingExample;
