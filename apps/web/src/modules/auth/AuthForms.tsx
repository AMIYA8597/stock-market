"use client";

import Link from 'next/link';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { CheckCircle2, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { authApi, setAuthTokens } from '@/lib/api-client';
import { useToastStore } from '@/stores/toast-store';

function StatusBanner({ type, message }: { type: 'success' | 'error'; message: string }): JSX.Element {
  return (
    <div className={`mb-4 flex items-center gap-2 rounded-[var(--ds-radius-lg)] border px-3 py-2 text-xs ${type === 'success' ? 'border-[var(--ds-color-success-500)]/40 bg-[var(--ds-color-success-500)]/10 text-[var(--ds-color-success-500)]' : 'border-[var(--ds-color-danger-500)]/40 bg-[var(--ds-color-danger-500)]/10 text-[var(--ds-color-danger-500)]'}`}>
      {type === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
      <span>{message}</span>
    </div>
  );
}

export function LoginForm(): JSX.Element {
  const router = useRouter();
  const pushToast = useToastStore((state) => state.pushToast);
  const [status, setStatus] = useState<'idle' | 'error' | 'success'>('idle');
  const [loading, setLoading] = useState(false);

  return (
    <Card className="border-[var(--ds-border-subtle)] bg-[var(--ds-surface-1)]/92">
      <CardHeader>
        <CardTitle>Welcome back</CardTitle>
        <CardDescription>Sign in to your workspace and continue where your team left off.</CardDescription>
      </CardHeader>
      <CardContent>
        {status === 'error' ? <StatusBanner type="error" message="Please provide a valid email and password." /> : null}
        {status === 'success' ? <StatusBanner type="success" message="Signed in successfully. Redirecting to dashboard..." /> : null}
        <form
          className="space-y-3"
          onSubmit={async (event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const email = String(form.get('email') ?? '');
            const password = String(form.get('password') ?? '');
            if (!email.includes('@') || password.length < 8) {
              setStatus('error');
              return;
            }
            try {
              setLoading(true);
              const tokens = await authApi.login(email, password);
              setAuthTokens(tokens);
              setStatus('success');
              pushToast({ tone: 'success', title: 'Signed in', message: 'Redirecting to dashboard...' });
              router.push('/dashboard');
            } catch {
              setStatus('error');
            } finally {
              setLoading(false);
            }
          }}
        >
          <div>
            <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">Email</label>
            <Input name="email" placeholder="you@company.com" />
          </div>
          <div>
            <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">Password</label>
            <Input name="password" type="password" placeholder="Enter your password" />
          </div>
          <Button className="w-full" type="submit" isLoading={loading}>Sign in</Button>
        </form>
        <p className="mt-2 text-right text-xs">
          <Link href="/forgot-password" className="text-[var(--ds-color-primary-300)] hover:underline">Forgot password?</Link>
        </p>
        <p className="mt-4 text-xs text-[var(--ds-text-secondary)]">New to NeuroQuant? <Link href="/register" className="text-[var(--ds-color-primary-300)] hover:underline">Create an account</Link></p>
      </CardContent>
    </Card>
  );
}

export function RegisterForm(): JSX.Element {
  const router = useRouter();
  const pushToast = useToastStore((state) => state.pushToast);
  const [status, setStatus] = useState<'idle' | 'error' | 'success'>('idle');
  const [loading, setLoading] = useState(false);

  return (
    <Card className="border-[var(--ds-border-subtle)] bg-[var(--ds-surface-1)]/92">
      <CardHeader>
        <CardTitle>Create your account</CardTitle>
        <CardDescription>Set up your organization workspace in under two minutes.</CardDescription>
      </CardHeader>
      <CardContent>
        {status === 'error' ? <StatusBanner type="error" message="Use a valid work email and a password with at least 8 characters." /> : null}
        {status === 'success' ? <StatusBanner type="success" message="Account created. Verify your email to continue." /> : null}
        <form
          className="space-y-3"
          onSubmit={async (event) => {
            event.preventDefault();
            const form = new FormData(event.currentTarget);
            const name = String(form.get('name') ?? '');
            const email = String(form.get('email') ?? '');
            const password = String(form.get('password') ?? '');
            if (name.length < 2 || !email.includes('@') || password.length < 8) {
              setStatus('error');
              return;
            }
            try {
              setLoading(true);
              await authApi.register({ email, password, full_name: name });
              setStatus('success');
              pushToast({ tone: 'success', title: 'Account created', message: 'You can now sign in.' });
              router.push('/login');
            } catch {
              setStatus('error');
            } finally {
              setLoading(false);
            }
          }}
        >
          <div>
            <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">Full name</label>
            <Input name="name" placeholder="Your name" />
          </div>
          <div>
            <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">Work email</label>
            <Input name="email" type="email" placeholder="you@company.com" />
          </div>
          <div>
            <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">Password</label>
            <Input name="password" type="password" placeholder="Create a password" />
          </div>
          <Button className="w-full" type="submit" isLoading={loading}>Create account</Button>
        </form>
        <p className="mt-4 text-xs text-[var(--ds-text-secondary)]">Already have an account? <Link href="/login" className="text-[var(--ds-color-primary-300)] hover:underline">Sign in</Link></p>
      </CardContent>
    </Card>
  );
}
