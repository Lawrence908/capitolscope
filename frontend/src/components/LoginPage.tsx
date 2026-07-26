import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { logger } from '../core/logging';
import { Eyebrow } from './ui';

const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login, isAuthenticated, isLoading, error, clearError } = useAuth();
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    remember_me: false,
  });
  
  const [validationErrors, setValidationErrors] = useState<{
    email?: string;
    password?: string;
  }>({});
  
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  // Clear errors when user starts typing
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => {
        clearError();
      }, 5000); // Clear error after 5 seconds
      
      return () => clearTimeout(timer);
    }
  }, [error, clearError]);

  const validateForm = (): boolean => {
    const errors: { email?: string; password?: string } = {};

    // Email validation
    if (!formData.email) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Please enter a valid email address';
    }

    // Password validation
    if (!formData.password) {
      errors.password = 'Password is required';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
    
    // Clear error when user starts typing
    if (error) {
      clearError();
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      logger.warn('Login form validation failed', { formData });
      return;
    }

    setIsSubmitting(true);
    logger.info('Login attempt started', { email: formData.email });
    
    try {
      await login(formData);
      logger.info('Login successful', { email: formData.email });
    } catch (error) {
      logger.error('Login error', { error, email: formData.email });
      console.error('Login error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-accent mx-auto"></div>
          <p className="mt-4 text-content-faint">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-surface py-12 px-4 sm:px-6 lg:px-8">
      {/* atmosphere: subtle verdigris glow from the top */}
      <div
        className="pointer-events-none fixed inset-x-0 top-0 h-64"
        style={{ background: 'radial-gradient(120% 60% at 50% 0%, rgba(67,168,151,0.08), transparent 70%)' }}
      />
      <div className="relative max-w-md w-full">
        {/* Header */}
        <div className="text-center">
          <img
            src="/capitol-scope-logo.png"
            alt="CapitolScope Logo"
            className="mx-auto mb-5 h-14 w-14 rounded-full"
          />
          <Eyebrow>CapitolScope · Oversight</Eyebrow>
          <h2 className="mt-2 font-display text-3xl font-medium tracking-[-0.01em] text-content">
            Welcome back
          </h2>
          <p className="mt-2 font-ui text-sm text-content-faint">
            Sign in to your account to continue
          </p>
        </div>

        {/* Login Form */}
        <form className="card mt-8 space-y-6 p-6 sm:p-8" onSubmit={handleSubmit}>
          <div className="space-y-4">
            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-content-muted">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={formData.email}
                onChange={handleInputChange}
                className={`mt-1 input-field ${
                  validationErrors.email 
                    ? 'border-error focus:ring-error focus:border-error' 
                    : ''
                }`}
                placeholder="Enter your email"
                aria-describedby={validationErrors.email ? "email-error" : undefined}
              />
              {validationErrors.email && (
                <p id="email-error" className="mt-1 text-sm text-error">
                  {validationErrors.email}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-content-muted">
                Password
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                value={formData.password}
                onChange={handleInputChange}
                className={`mt-1 input-field ${
                  validationErrors.password 
                    ? 'border-error focus:ring-error focus:border-error' 
                    : ''
                }`}
                placeholder="Enter your password"
                aria-describedby={validationErrors.password ? "password-error" : undefined}
              />
              {validationErrors.password && (
                <p id="password-error" className="mt-1 text-sm text-error">
                  {validationErrors.password}
                </p>
              )}
            </div>
          </div>

          {/* Remember Me & Forgot Password */}
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <input
                id="remember_me"
                name="remember_me"
                type="checkbox"
                checked={formData.remember_me}
                onChange={handleInputChange}
                className="h-4 w-4 text-accent focus:ring-accent border-accent rounded"
              />
              <label htmlFor="remember_me" className="ml-2 block text-sm text-content-muted">
                Remember me
              </label>
            </div>

            <div className="text-sm">
              <Link
                to="/forgot-password"
                className="font-medium text-accent hover:text-accent-strong"
              >
                Forgot your password?
              </Link>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div className="rounded-md bg-error/10 border border-error/20 p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-error" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-error">Error: {error}</p>
                </div>
              </div>
            </div>
          )}


          {/* Submit Button */}
          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary w-full"
            >
              {isSubmitting ? (
                <div className="flex items-center">
                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                  Signing in...
                </div>
              ) : (
                <div className="flex items-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                  </svg>
                  Sign in
                </div>
              )}
            </button>
          </div>

          {/* Sign Up Link */}
          <div className="text-center">
            <p className="text-sm text-content-faint">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="font-medium text-accent hover:text-accent-strong"
              >
                Sign up for free
              </Link>
            </p>
          </div>
        </form>

        {/* Demo Account Info */}
        <div className="mt-8 card p-4">
          <h3 className="text-sm font-medium text-accent mb-2">
            🚀 Beta Testing
          </h3>
          <p className="text-xs text-content-faint">
            CapitolScope is currently in beta. Sign up to get early access to congressional trading insights and help us improve the platform.
          </p>
        </div>
      </div>
    </div>
  );
};

export default LoginPage; 