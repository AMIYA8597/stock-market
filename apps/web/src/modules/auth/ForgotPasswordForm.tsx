"use client";

import Link from 'next/link';
import { useState } from 'react';
import { MailCheck, ShieldCheck } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { authApi } from '@/lib/api-client';
import { useToastStore } from '@/stores/toast-store';

export function ForgotPasswordForm(): JSX.Element {
  const pushToast = useToastStore((state) => state.pushToast);
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);

  return (
    <Card className="border-[var(--ds-border-subtle)] bg-[var(--ds-surface-1)]/92">
      <CardHeader>
        <CardTitle>Reset your password</CardTitle>
        <CardDescription>Enter your work email. We will send a secure reset link.</CardDescription>
      </CardHeader>
      <CardContent>
        {sent ? (
          <div className="rounded-[var(--ds-radius-lg)] border border-[var(--ds-color-success-500)]/40 bg-[var(--ds-color-success-500)]/10 p-3 text-sm text-[var(--ds-color-success-500)]">
            <p className="inline-flex items-center gap-2"><MailCheck className="h-4 w-4" />Reset link sent to {email}</p>
          </div>
        ) : null}
        <form
          className="space-y-3"
          onSubmit={async (event) => {
            event.preventDefault();
            if (!email.includes('@')) {
              return;
            }
            try {
              setLoading(true);
              await authApi.forgotPassword(email);
              setSent(true);
              pushToast({ tone: 'info', title: 'Reset email queued', message: 'Check your inbox for the reset token.' });
            } finally {
              setLoading(false);
            }
          }}
        >
          <div>
            <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">Email address</label>
            <Input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="you@company.com"
              required
            />
          </div>
          <Button type="submit" className="w-full" isLoading={loading}>Send reset link</Button>
        </form>
        <p className="mt-4 flex items-center gap-1 text-xs text-[var(--ds-text-muted)]"><ShieldCheck className="h-3.5 w-3.5" /> Enterprise-grade secure flow</p>
        <p className="mt-2 text-xs text-[var(--ds-text-secondary)]">Remembered your password? <Link href="/login" className="text-[var(--ds-color-primary-300)] hover:underline">Back to sign in</Link></p>
      </CardContent>
    </Card>
  );
}
