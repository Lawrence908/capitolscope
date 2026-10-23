import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { logger, LogComponent } from '../core/logging';
import { AuthShell, AuthAlert, AuthNote, ButtonSpinner } from './AuthShell';

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
      logger.warning(LogComponent.AUTH, 'Login form validation failed', { formData });
      return;
    }

    setIsSubmitting(true);
    logger.info(LogComponent.AUTH, 'Login attempt started', { email: formData.email });

    try {
      await login(formData);
      logger.info(LogComponent.AUTH, 'Login successful', { email: formData.email });
    } catch (error) {
      logger.error(LogComponent.AUTH, 'Login error', { error, email: formData.email });
      console.error('Login error:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-surface">
        <div className="text-center">
          <div className="mx-auto h-10 w-10 animate-spin rounded-full border-[3px] border-line border-t-accent"></div>
          <p className="mt-4 font-ui text-[11px] font-semibold uppercase tracking-[0.14em] text-content-faint">Loading</p>
        </div>
      </div>
    );
  }

  return (
    <AuthShell
      eyebrow="Sign in"
      title="Welcome back"
      subtitle="Sign in to your account to continue."
      note={
        <AuthNote title="Beta">
          CapitolScope is currently in beta. Sign up to get early access to congressional trading insights and help us improve the platform.
        </AuthNote>
      }
    >
      <form className="space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
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
                    ? 'border-accent' 
                    : ''
                }`}
                placeholder="Enter your email"
                aria-describedby={validationErrors.email ? "email-error" : undefined}
              />
              {validationErrors.email && (
                <p id="email-error" className="mt-1 font-ui text-sm font-semibold text-accent">
                  {validationErrors.email}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
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
                    ? 'border-accent' 
                    : ''
                }`}
                placeholder="Enter your password"
                aria-describedby={validationErrors.password ? "password-error" : undefined}
              />
              {validationErrors.password && (
                <p id="password-error" className="mt-1 font-ui text-sm font-semibold text-accent">
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
                className="h-4 w-4 accent-[var(--accent)]"
              />
              <label htmlFor="remember_me" className="ml-2 block font-ui text-sm text-content-muted">
                Remember me
              </label>
            </div>

            <div className="text-sm">
              <Link
                to="/forgot-password"
                className="font-semibold text-accent hover:text-accent-strong hover:underline underline-offset-2"
              >
                Forgot your password?
              </Link>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <AuthAlert tone="error">{error}</AuthAlert>
          )}


          {/* Submit Button */}
          <div>
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary w-full disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSubmitting ? (
                <div className="flex items-center justify-center">
                  <ButtonSpinner />
                  Signing in...
                </div>
              ) : (
                <div className="flex items-center justify-center">
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
            <p className="font-ui text-sm text-content-faint">
              Don't have an account?{' '}
              <Link
                to="/register"
                className="font-semibold text-accent hover:text-accent-strong hover:underline underline-offset-2"
              >
                Sign up for free
              </Link>
            </p>
          </div>
        </form>
    </AuthShell>
  );
};

export default LoginPage; 