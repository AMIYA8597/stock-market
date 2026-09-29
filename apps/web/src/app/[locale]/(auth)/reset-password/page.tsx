'use client';
import { Suspense, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { authApi, ApiError } from '@/lib/api-client';
import { useRouter, Link } from '@/i18n/navigation';

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [email, setEmail] = useState(searchParams.get('email') ?? '');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setSubmitting(true);
    try {
      await authApi.resetPassword({ email: email.trim(), otp: otp.trim(), new_password: newPassword });
      router.push('/login');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not reset password. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    setError('');
    setInfo('');
    setSubmitting(true);
    try {
      await authApi.resendOtp({ email: email.trim(), purpose: 'password_reset' });
      setInfo('A new reset code has been sent to your email.');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not send a new code. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4 w-80">
      <h1 className="text-2xl font-bold text-[var(--nq-text-primary)]">Reset Password</h1>
      {error && <p className="text-red-500 text-sm">{error}</p>}
      {info && <p className="text-green-500 text-sm">{info}</p>}
      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="border border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-2 text-[var(--nq-text-primary)] placeholder:text-[var(--nq-text-secondary)]"
      />
      <input
        type="text"
        inputMode="numeric"
        placeholder="6-digit reset code"
        value={otp}
        onChange={(e) => setOtp(e.target.value)}
        className="border border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-2 text-[var(--nq-text-primary)] placeholder:text-[var(--nq-text-secondary)]"
      />
      <input
        type="password"
        placeholder="New Password"
        value={newPassword}
        onChange={(e) => setNewPassword(e.target.value)}
        className="border border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-2 text-[var(--nq-text-primary)] placeholder:text-[var(--nq-text-secondary)]"
      />
      <input
        type="password"
        placeholder="Confirm New Password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        className="border border-[var(--nq-border)] bg-[var(--nq-bg-surface)] p-2 text-[var(--nq-text-primary)] placeholder:text-[var(--nq-text-secondary)]"
      />
      <p className="text-xs text-[var(--nq-text-secondary)]">
        At least 12 characters, with uppercase, lowercase, a number, and a special character.
      </p>
      <button type="submit" disabled={submitting} className="bg-blue-600 text-white p-2 disabled:opacity-50">
        {submitting ? 'Updating...' : 'Update Password'}
      </button>
      <div className="flex justify-between text-sm">
        <button type="button" onClick={handleResend} disabled={submitting} className="text-blue-500 disabled:opacity-50">
          Resend code
        </button>
        <Link href="/login" className="text-[var(--nq-text-secondary)]">Back to Sign In</Link>
      </div>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <Suspense fallback={null}>
        <ResetPasswordForm />
      </Suspense>
    </div>
  );
}
