'use client';
import { useState } from 'react';
import { useLocale } from 'next-intl';
import { authApi, ApiError } from '@/lib/api-client';
import { createClient } from '@/lib/supabase/client';
import { Link } from '@/i18n/navigation';
import { registerSchema } from '@/lib/validations/auth';

type Step = 'form' | 'otp';

interface StructuredErrorBody {
  error?: { details?: Array<{ message: string }> };
}

function extractErrorDetails(err: unknown): string[] | null {
  if (!(err instanceof ApiError)) return null;
  const details = (err.body as StructuredErrorBody | null)?.error?.details;
  if (!Array.isArray(details) || details.length === 0) return null;
  return details.map((d) => d.message);
}

export default function RegisterPage() {
  const locale = useLocale();
  const [step, setStep] = useState<Step>('form');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [fieldErrors, setFieldErrors] = useState<string[]>([]);
  const [info, setInfo] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setFieldErrors([]);

    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    const parsed = registerSchema.safeParse({ full_name: fullName, email, password });
    if (!parsed.success) {
      setFieldErrors(parsed.error.issues.map((i) => i.message));
      return;
    }

    setSubmitting(true);
    try {
      const result = await authApi.register({ email, password, full_name: fullName });
      if (result && 'access_token' in result) {
        // No-OTP path: backend auto-verified and returned tokens directly
        const supabase = createClient();
        await supabase.auth.setSession({
          access_token: result.access_token,
          refresh_token: result.refresh_token ?? '',
        });
        // Full navigation so the middleware sees the new session cookie.
        window.location.href = `/${locale}/dashboard`;
        return;
      }
      if (result && 'login_required' in result && result.login_required) {
        // Account was created and verified, but the automatic sign-in did
        // not go through. Send the user to the login page with their email
        // filled in instead of leaving them on this form.
        const params = new URLSearchParams({ registered: '1', email });
        window.location.href = `/${locale}/login?${params.toString()}`;
        return;
      }
      setStep('otp');
    } catch (err) {
      const details = extractErrorDetails(err);
      if (details) {
        setFieldErrors(details);
      } else {
        setError(err instanceof ApiError ? err.message : 'Registration failed. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const tokens = await authApi.verifySignupOtp({ email, otp: otp.trim(), password });
      const supabase = createClient();
      await supabase.auth.setSession({ access_token: tokens.access_token, refresh_token: tokens.refresh_token ?? '' });
      window.location.href = `/${locale}/dashboard`;
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Verification failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    setError('');
    setInfo('');
    setSubmitting(true);
    try {
      await authApi.resendOtp({ email, purpose: 'signup' });
      setInfo('A new verification code has been sent to your email.');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not send a new code. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (step === 'otp') {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center p-24">
        <form onSubmit={handleVerify} className="flex flex-col gap-4 w-80">
          <h1 className="text-2xl font-bold text-[var(--nq-text-primary)]">Verify Your Email</h1>
          <p className="text-sm text-[var(--nq-text-secondary)]">
            We sent a verification code to {email}. Enter it below to activate your account.
          </p>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          {info && <p className="text-green-500 text-sm">{info}</p>}
          <input
            type="text"
            inputMode="numeric"
            placeholder="6-digit code"
            autoFocus
            value={otp}
            onChange={(e) => setOtp(e.target.value)}
            className="border border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-2 text-[var(--nq-text-primary)] placeholder:text-[var(--nq-text-secondary)]"
          />
          <button type="submit" disabled={submitting} className="bg-blue-600 text-white p-2 disabled:opacity-50">
            {submitting ? 'Verifying...' : 'Verify & Continue'}
          </button>
          <button type="button" onClick={handleResend} disabled={submitting} className="text-sm text-blue-500 disabled:opacity-50">
            Resend code
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <form onSubmit={handleRegister} className="flex flex-col gap-4 w-80">
        <h1 className="text-2xl font-bold text-[var(--nq-text-primary)]">Register</h1>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        {fieldErrors.length > 0 && (
          <ul className="text-red-500 text-sm list-disc pl-4">
            {fieldErrors.map((msg) => (
              <li key={msg}>{msg}</li>
            ))}
          </ul>
        )}
        <input
          type="text"
          placeholder="Full Name"
          value={fullName}
          onChange={(e) => setFullName(e.target.value)}
          className="border border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-2 text-[var(--nq-text-primary)] placeholder:text-[var(--nq-text-secondary)]"
        />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="border border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-2 text-[var(--nq-text-primary)] placeholder:text-[var(--nq-text-secondary)]"
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="border border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-2 text-[var(--nq-text-primary)] placeholder:text-[var(--nq-text-secondary)]"
        />
        <input
          type="password"
          placeholder="Confirm Password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className="border border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-2 text-[var(--nq-text-primary)] placeholder:text-[var(--nq-text-secondary)]"
        />
        <p className="text-xs text-[var(--nq-text-secondary)]">
          At least 12 characters, with uppercase, lowercase, a number, and a special character.
        </p>
        <button type="submit" disabled={submitting} className="bg-blue-600 text-white p-2 disabled:opacity-50">
          {submitting ? 'Registering...' : 'Sign Up'}
        </button>
        <p className="text-sm text-[var(--nq-text-secondary)]">
          Already have an account? <Link href="/login" className="text-blue-500">Sign In</Link>
        </p>
      </form>
    </div>
  );
}
