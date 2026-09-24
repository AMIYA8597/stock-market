'use client';
import { useState } from 'react';
import { createClient } from '@/lib/supabase/client';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const supabase = createClient();
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email);
    if (resetError) {
      setError(resetError.message);
    } else {
      setSuccess(true);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <form onSubmit={handleReset} className="flex flex-col gap-4 w-80">
        <h1 className="text-2xl font-bold">Reset Password</h1>
        {error && <p className="text-red-500 text-sm">{error}</p>}
        {success && <p className="text-green-500 text-sm">Check your email for reset link</p>}
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="border p-2 text-black"
        />
        <button type="submit" className="bg-blue-600 text-white p-2">
          Send Reset Link
        </button>
      </form>
    </div>
  );
}
