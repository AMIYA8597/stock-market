'use client';
import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';
import { authApi, ApiError } from '@/lib/api-client';
import { Link } from '@/i18n/navigation';

type Step = 'email' | 'password' | 'unverified';

export default function LoginPage() {
  const [step, setStep] = useState<Step>('email');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [otp, setOtp] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setInfo('');
    if (!email.trim()) return;
    setSubmitting(true);
    try {
      const { exists } = await authApi.checkEmail(email.trim());
      if (!exists) {
        setError('Account not found. Please register your account first.');
      } else {
        setStep('password');
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const establishSessionAndRedirect = async (accessToken: string, refreshToken: string | null) => {
    const supabase = createClient();
    // login()/verify-signup-otp() authenticate against OUR backend (so its
    // lockout + email-verification gates apply), not supabase-js directly -
    // but the Next.js middleware that guards every protected route reads a
    // Supabase session cookie, which only supabase-js's own client sets.
    // setSession() with the tokens our backend already validated re-derives
    // that cookie without a second round-trip to Supabase.
    await supabase.auth.setSession({ access_token: accessToken, refresh_token: refreshToken ?? '' });
    // Full navigation (not router.push) so middleware re-runs with the
    // now-valid session and reads the nq_next cookie to send us back to
    // wherever we were headed before login.
    const nextCookie = document.cookie.split('; ').find(c => c.startsWith('nq_next='));
    const nextPath = nextCookie ? decodeURIComponent(nextCookie.split('=')[1] ?? '/dashboard') : '/dashboard';
    window.location.href = nextPath;
  };

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setInfo('');
    setSubmitting(true);
    try {
      const tokens = await authApi.login({ email: email.trim(), password });
      await establishSessionAndRedirect(tokens.access_token, tokens.refresh_token);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setStep('unverified');
        setError('Please verify your email before signing in.');
      } else if (err instanceof ApiError && err.status === 429) {
        setError(err.message);
      } else if (err instanceof ApiError && err.status === 401) {
        setError('Incorrect password.');
      } else {
        setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleResendOtp = async () => {
    setError('');
    setInfo('');
    setSubmitting(true);
    try {
      await authApi.resendOtp({ email: email.trim(), purpose: 'signup' });
      setInfo('A new verification code has been sent to your email.');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not send a new code. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleVerifySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      const tokens = await authApi.verifySignupOtp({ email: email.trim(), otp: otp.trim(), password });
      await establishSessionAndRedirect(tokens.access_token, tokens.refresh_token);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Verification failed. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      {step === 'email' && (
        <form onSubmit={handleEmailSubmit} className="flex flex-col gap-4 w-80">
          <h1 className="text-2xl font-bold">Sign In</h1>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <input
            type="email"
            placeholder="Email"
            autoFocus
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="border border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-2 text-[var(--nq-text-primary)] placeholder:text-[var(--nq-text-secondary)]"
          />
          <button type="submit" disabled={submitting} className="bg-blue-600 text-white p-2 disabled:opacity-50">
            {submitting ? 'Checking...' : 'Continue'}
          </button>
          <p className="text-sm text-[var(--nq-text-secondary)]">
            Don&apos;t have an account? <Link href="/register" className="text-blue-500">Register</Link>
          </p>
        </form>
      )}

      {step === 'password' && (
        <form onSubmit={handlePasswordSubmit} className="flex flex-col gap-4 w-80">
          <h1 className="text-2xl font-bold">Sign In</h1>
          <p className="text-sm text-[var(--nq-text-secondary)]">{email}</p>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <input
            type="password"
            placeholder="Password"
            autoFocus
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="border border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-2 text-[var(--nq-text-primary)] placeholder:text-[var(--nq-text-secondary)]"
          />
          <button type="submit" disabled={submitting} className="bg-blue-600 text-white p-2 disabled:opacity-50">
            {submitting ? 'Signing in...' : 'Sign In'}
          </button>
          <div className="flex justify-between text-sm">
            <button type="button" onClick={() => setStep('email')} className="text-[var(--nq-text-secondary)]">
              Use a different email
            </button>
            <Link href="/forgot-password" className="text-blue-500">Forgot Password?</Link>
          </div>
        </form>
      )}

      {step === 'unverified' && (
        <form onSubmit={handleVerifySubmit} className="flex flex-col gap-4 w-80">
          <h1 className="text-2xl font-bold">Verify Your Email</h1>
          <p className="text-sm text-[var(--nq-text-secondary)]">
            Enter the verification code sent to {email}, or request a new one.
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
            {submitting ? 'Verifying...' : 'Verify & Sign In'}
          </button>
          <button type="button" onClick={handleResendOtp} disabled={submitting} className="text-sm text-blue-500 disabled:opacity-50">
            Resend code
          </button>
        </form>
      )}
    </div>
  );
}
