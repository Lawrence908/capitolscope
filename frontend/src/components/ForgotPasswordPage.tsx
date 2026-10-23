import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { AuthShell, AuthAlert, AuthNote, ButtonSpinner } from './AuthShell';

const ForgotPasswordPage: React.FC = () => {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [validationErrors, setValidationErrors] = useState<{ email?: string }>({});

  const validateForm = (): boolean => {
    const errors: { email?: string } = {};

    if (!email) {
      errors.email = 'Email is required';
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      errors.email = 'Please enter a valid email address';
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
      const response = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8001'}/api/v1/auth/reset-password`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email }),
      });

      const data = await response.json();

      if (response.ok) {
        setMessage(data.data?.message || 'If an account exists with this email, a password reset link has been sent.');
      } else {
        setError(data.error?.message || 'Failed to send reset email. Please try again.');
      }
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthShell
      eyebrow="Account"
      title="Reset your password"
      subtitle="Enter your email address and we'll send you a link to reset your password."
      note={
        <AuthNote title="Need help?">
          If you don't receive an email within a few minutes, check your spam folder. The reset link will expire in 24 hours.
        </AuthNote>
      }
    >
      <form className="space-y-6" onSubmit={handleSubmit}>
          {/* Email Field */}
          <div>
            <label htmlFor="email" className="block font-ui text-[11px] font-bold uppercase tracking-[0.08em] text-content-faint">
              Email address
            </label>
            <div className="mt-1">
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={`input-field ${
                  validationErrors.email ? 'border-accent' : ''
                }`}
                placeholder="Enter your email address"
              />
            </div>
            {validationErrors.email && (
              <p className="mt-2 font-ui text-sm font-semibold text-accent">
                {validationErrors.email}
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
                  Sending reset email...
                </div>
              ) : (
                <div className="flex items-center justify-center">
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                  Send reset email
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

export default ForgotPasswordPage; 