'use client';
import { useState } from 'react';
import { authApi, ApiError } from '@/lib/api-client';
import { useRouter } from '@/i18n/navigation';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!email.trim()) return;
    setSubmitting(true);
    try {
      // Always responds the same way whether or not the email is
      // registered, so this can't be used to enumerate accounts - the user
      // finds out for certain only by checking their inbox.
      await authApi.forgotPassword(email.trim());
      router.push(`/reset-password?email=${encodeURIComponent(email.trim())}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <form onSubmit={handleSubmit} className="flex flex-col gap-4 w-80">
        <h1 className="text-2xl font-bold text-[var(--nq-text-primary)]">Forgot Password</h1>
        <p className="text-sm text-[var(--nq-text-secondary)]">
          Enter your account email and we&apos;ll send you a password reset code.
        </p>
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
          {submitting ? 'Sending...' : 'Send Reset Code'}
        </button>
      </form>
    </div>
  );
}
