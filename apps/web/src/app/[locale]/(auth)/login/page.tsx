'use client';
import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { useRouter } from '@/i18n/navigation';
import { createClient } from '@/lib/supabase/client';

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    const supabase = createClient();
    const { error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (signInError) {
      setError(signInError.message);
    } else {
      const next = searchParams.get('next');
      router.push(next || '/dashboard');
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <form onSubmit={handleLogin} className="flex flex-col gap-4 w-80">
        <h1 className="text-2xl font-bold">Login</h1>
        {error && <p className="text-red-500 text-sm">{error}</p>}
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
        <button type="submit" className="bg-blue-600 text-white p-2">
          Sign In
        </button>
      </form>
    </div>
  );
}
