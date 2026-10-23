import React, { useState, useEffect } from 'react';
import { AuthShell, AuthAlert, ButtonSpinner } from './AuthShell';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';

const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [validationErrors, setValidationErrors] = useState<{ password?: string; confirmPassword?: string }>({});
  const [token, setToken] = useState('');

  useEffect(() => {
    const tokenParam = searchParams.get('token');
    if (!tokenParam) {
      setError('Invalid reset link. Please request a new password reset.');
      return;
    }
    setToken(tokenParam);
  }, [searchParams]);

  const validateForm = (): boolean => {
    const errors: { password?: string; confirmPassword?: string } = {};

    if (!password) {
      errors.password = 'Password is required';
    } else if (password.length < 6) {
      errors.password = 'Password must be at least 6 characters long';
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(password)) {
      errors.password = 'Password must contain at least one uppercase letter, one lowercase letter, and one number';
    }

    if (!confirmPassword) {
      errors.confirmPassword = 'Please confirm your password';
    } else if (password !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setMessage('');

    if (!validateForm()) {
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api/v1/auth/reset-password-confirm`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          token,
          new_password: password 
        }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage('Password reset successful! You can now sign in with your new password.');
        // Redirect to login after 3 seconds
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      } else {
        setError(data.error?.message || 'Failed to reset password. Please try again.');
      }
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!token) {
    return (
      <AuthShell
        eyebrow="Account"
        title="Invalid reset link"
        subtitle="This password reset link is invalid or has expired."
      >
        <AuthAlert tone="error">The link could not be used. Request a fresh one below.</AuthAlert>
        <div className="mt-6">
          <Link to="/forgot-password" className="btn-secondary inline-block">
            Request a new password reset
          </Link>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      eyebrow="Account"
      title="Set new password"
      subtitle="Enter your new password below."
    >
      <form className="space-y-6" onSubmit={handleSubmit}>
          {/* Password Field */}
          <div>
            <label htmlFor="password" className="block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
              New password
            </label>
            <div className="mt-1">
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className={`input-field ${
                  validationErrors.password ? 'border-accent' : ''
                }`}
                placeholder="Enter your new password"
              />
            </div>
            {validationErrors.password && (
              <p className="mt-2 font-ui text-sm font-semibold text-accent">
                {validationErrors.password}
              </p>
            )}
          </div>

          {/* Confirm Password Field */}
          <div>
            <label htmlFor="confirmPassword" className="block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
              Confirm new password
            </label>
            <div className="mt-1">
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                className={`input-field ${
                  validationErrors.confirmPassword ? 'border-accent' : ''
                }`}
                placeholder="Confirm your new password"
              />
            </div>
            {validationErrors.confirmPassword && (
              <p className="mt-2 font-ui text-sm font-semibold text-accent">
                {validationErrors.confirmPassword}
              </p>
            )}
          </div>

          {/* Success Message */}
          {message && (
            <AuthAlert tone="success">{message}</AuthAlert>
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
                  Resetting password...
                </div>
              ) : (
                <div className="flex items-center justify-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Reset password
                </div>
              )}
            </button>
          </div>

          {/* Back to Login Link */}
          <div className="text-center">
            <p className="font-ui text-sm text-content-faint">
              Remember your password?{' '}
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

export default ResetPasswordPage; 