import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { AuthShell, AuthAlert, AuthNote, ButtonSpinner } from './AuthShell';

const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register, isAuthenticated, isLoading, error, clearError } = useAuth();
  
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: '',
    username: '',
    terms_accepted: false,
  });
  
  const [validationErrors, setValidationErrors] = useState<{
    email?: string;
    password?: string;
    confirmPassword?: string;
    first_name?: string;
    last_name?: string;
    username?: string;
    terms_accepted?: string;
  }>({});
  
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Redirect if already authenticated
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  // Clear errors when form data changes
  useEffect(() => {
    if (error) {
      clearError();
    }
  }, [formData, clearError, error]);

  const validateForm = (): boolean => {
    const errors: typeof validationErrors = {};

    // Email validation
    if (!formData.email) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      errors.email = 'Please enter a valid email address';
    }

    // Password validation
    if (!formData.password) {
      errors.password = 'Password is required';
    } else if (formData.password.length < 8) {
      errors.password = 'Password must be at least 8 characters long';
    } else if (!/(?=.*[a-z])/.test(formData.password)) {
      errors.password = 'Password must contain at least one lowercase letter';
    } else if (!/(?=.*[A-Z])/.test(formData.password)) {
      errors.password = 'Password must contain at least one uppercase letter';
    } else if (!/(?=.*\d)/.test(formData.password)) {
      errors.password = 'Password must contain at least one number';
    } else if (!/(?=.*[!@#$%^&*])/.test(formData.password)) {
      errors.password = 'Password must contain at least one special character (!@#$%^&*)';
    }

    // Confirm password validation
    if (!formData.confirmPassword) {
      errors.confirmPassword = 'Please confirm your password';
    } else if (formData.password !== formData.confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }

    // Name validation
    if (formData.first_name && formData.first_name.length > 100) {
      errors.first_name = 'First name must be less than 100 characters';
    }
    if (formData.last_name && formData.last_name.length > 100) {
      errors.last_name = 'Last name must be less than 100 characters';
    }

    // Username validation
    if (formData.username) {
      if (formData.username.length < 3) {
        errors.username = 'Username must be at least 3 characters long';
      } else if (formData.username.length > 50) {
        errors.username = 'Username must be less than 50 characters';
      } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
        errors.username = 'Username can only contain letters, numbers, underscores, and hyphens';
      }
    }

    // Terms validation
    if (!formData.terms_accepted) {
      errors.terms_accepted = 'You must accept the terms and conditions';
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
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);
    
    try {
      const registerData = {
        email: formData.email,
        password: formData.password,
        first_name: formData.first_name || undefined,
        last_name: formData.last_name || undefined,
        username: formData.username || undefined,
        terms_accepted: formData.terms_accepted,
      };
      
      await register(registerData);
    } catch (error) {
      console.error('Registration error:', error);
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
      eyebrow="Create account"
      title="Join CapitolScope"
      subtitle="Create your account to get started."
      note={
        <AuthNote title="Free tier includes">
          <ul className="list-inside list-disc space-y-0.5">
            <li>Access to congressional trading data</li>
            <li>Basic search and filtering</li>
            <li>Member profiles and trade history</li>
            <li>Email notifications for major trades</li>
            <li>Community discussions</li>
          </ul>
          <p className="mt-2">
            Premium features coming soon: advanced analytics, real-time alerts, portfolio tracking and more.
          </p>
        </AuthNote>
      }
    >
      <form className="space-y-6" onSubmit={handleSubmit}>
          <div className="space-y-4">
            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
                Email address *
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

            {/* Name Fields */}
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="first_name" className="block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
                  First name
                </label>
                <input
                  id="first_name"
                  name="first_name"
                  type="text"
                  autoComplete="given-name"
                  value={formData.first_name}
                  onChange={handleInputChange}
                  className={`mt-1 input-field ${
                    validationErrors.first_name 
                      ? 'border-accent' 
                      : ''
                  }`}
                  placeholder="First name"
                  aria-describedby={validationErrors.first_name ? "first-name-error" : undefined}
                />
                {validationErrors.first_name && (
                  <p id="first-name-error" className="mt-1 font-ui text-sm font-semibold text-accent">
                    {validationErrors.first_name}
                  </p>
                )}
              </div>

              <div>
                <label htmlFor="last_name" className="block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
                  Last name
                </label>
                <input
                  id="last_name"
                  name="last_name"
                  type="text"
                  autoComplete="family-name"
                  value={formData.last_name}
                  onChange={handleInputChange}
                  className={`mt-1 input-field ${
                    validationErrors.last_name 
                      ? 'border-accent' 
                      : ''
                  }`}
                  placeholder="Last name"
                  aria-describedby={validationErrors.last_name ? "last-name-error" : undefined}
                />
                {validationErrors.last_name && (
                  <p id="last-name-error" className="mt-1 font-ui text-sm font-semibold text-accent">
                    {validationErrors.last_name}
                  </p>
                )}
              </div>
            </div>

            {/* Username Field */}
            <div>
              <label htmlFor="username" className="block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
                Username (optional)
              </label>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                value={formData.username}
                onChange={handleInputChange}
                className={`mt-1 input-field ${
                  validationErrors.username 
                    ? 'border-accent' 
                    : ''
                }`}
                placeholder="Choose a username"
                aria-describedby={validationErrors.username ? "username-error" : undefined}
              />
              {validationErrors.username && (
                <p id="username-error" className="mt-1 font-ui text-sm font-semibold text-accent">
                  {validationErrors.username}
                </p>
              )}
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
                Password *
              </label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                value={formData.password}
                onChange={handleInputChange}
                className={`mt-1 input-field ${
                  validationErrors.password 
                    ? 'border-accent' 
                    : ''
                }`}
                placeholder="Create a strong password"
                aria-describedby={validationErrors.password ? "password-error" : undefined}
              />
              {validationErrors.password && (
                <p id="password-error" className="mt-1 font-ui text-sm font-semibold text-accent">
                  {validationErrors.password}
                </p>
              )}
            </div>

            {/* Confirm Password Field */}
            <div>
              <label htmlFor="confirmPassword" className="block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
                Confirm password *
              </label>
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                required
                value={formData.confirmPassword}
                onChange={handleInputChange}
                className={`mt-1 input-field ${
                  validationErrors.confirmPassword 
                    ? 'border-accent' 
                    : ''
                }`}
                placeholder="Confirm your password"
                aria-describedby={validationErrors.confirmPassword ? "confirm-password-error" : undefined}
              />
              {validationErrors.confirmPassword && (
                <p id="confirm-password-error" className="mt-1 font-ui text-sm font-semibold text-accent">
                  {validationErrors.confirmPassword}
                </p>
              )}
            </div>
          </div>

          {/* Terms and Conditions */}
          <div className="flex items-center">
            <input
              id="terms_accepted"
              name="terms_accepted"
              type="checkbox"
              checked={formData.terms_accepted}
              onChange={handleInputChange}
              className="h-4 w-4 accent-[var(--accent)]"
              aria-describedby={validationErrors.terms_accepted ? "terms-error" : undefined}
            />
            <label htmlFor="terms_accepted" className="ml-2 block font-ui text-sm text-content-muted">
              I agree to the{' '}
              <Link
                to="/terms"
                className="font-semibold text-accent hover:text-accent-strong hover:underline underline-offset-2"
              >
                Terms of Service
              </Link>{' '}
              and{' '}
              <Link
                to="/privacy"
                className="font-semibold text-accent hover:text-accent-strong hover:underline underline-offset-2"
              >
                Privacy Policy
              </Link>
            </label>
          </div>
          {validationErrors.terms_accepted && (
            <p id="terms-error" className="font-ui text-sm font-semibold text-accent">
              {validationErrors.terms_accepted}
            </p>
          )}

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
                  Creating account...
                </div>
              ) : (
                <div className="flex items-center justify-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                  </svg>
                  Create account
                </div>
              )}
            </button>
          </div>

          {/* Sign In Link */}
          <div className="text-center">
            <p className="font-ui text-sm text-content-faint">
              Already have an account?{' '}
              <Link
                to="/login"
                className="font-semibold text-accent hover:text-accent-strong hover:underline underline-offset-2"
              >
                Sign in
              </Link>
            </p>
          </div>
        </form>
    </AuthShell>
  );
};

export default RegisterPage; 