"use client";

import { useEffect, useState } from 'react';
import { Camera, KeyRound, MapPin, User2 } from 'lucide-react';
import { Avatar } from '@/components/ui/Avatar';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { usersApi } from '@/lib/api-client';
import { useToastStore } from '@/stores/toast-store';

export function UserProfilePage(): JSX.Element {
  const pushToast = useToastStore((state) => state.pushToast);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    let mounted = true;
    usersApi.getProfile().then((profile) => {
      if (!mounted) return;
      setFullName(profile.full_name ?? '');
      setEmail(profile.email);
    }).catch(() => {
      if (!mounted) return;
      pushToast({ tone: 'error', title: 'Profile load failed' });
    });
    return () => {
      mounted = false;
    };
  }, [pushToast]);

  return (
    <div className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
      <Card className="bg-[var(--ds-surface-1)]/90">
        <CardHeader>
          <CardTitle>User Profile</CardTitle>
          <CardDescription>Manage account details and workspace identity.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-4">
            <div className="relative">
              <Avatar className="h-16 w-16" fallback="AK" />
              <button className="absolute -right-1 -bottom-1 rounded-full border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)] p-1.5 text-[var(--ds-text-secondary)] hover:text-[var(--ds-text-primary)]">
                <Camera className="h-3.5 w-3.5" />
              </button>
            </div>
            <div>
              <p className="font-semibold">Aarav Kapoor</p>
              <p className="text-xs text-[var(--ds-text-secondary)]">Lead Quant Analyst</p>
            </div>
          </div>

          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">First name</label>
              <Input value={fullName.split(' ')[0] ?? ''} readOnly />
            </div>
            <div>
              <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">Last name</label>
              <Input value={fullName.split(' ').slice(1).join(' ')} readOnly />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">Email</label>
              <Input value={email} readOnly />
            </div>
            <div className="sm:col-span-2">
              <label className="mb-1 block text-xs text-[var(--ds-text-secondary)]">Display name</label>
              <Input value={fullName} onChange={(event) => setFullName(event.target.value)} />
            </div>
          </div>

          <Button
            isLoading={loading}
            onClick={async () => {
              try {
                setLoading(true);
                await usersApi.updateProfile(fullName.trim());
                pushToast({ tone: 'success', title: 'Profile updated' });
              } catch {
                pushToast({ tone: 'error', title: 'Update failed' });
              } finally {
                setLoading(false);
              }
            }}
          >
            Save changes
          </Button>
        </CardContent>
      </Card>

      <div className="space-y-4">
        <Card className="bg-[var(--ds-surface-1)]/90">
          <CardHeader>
            <CardTitle className="text-base">Security</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-[var(--ds-text-secondary)]">
            <p className="inline-flex items-center gap-2"><KeyRound className="h-4 w-4" /> Password last changed 18 days ago</p>
            <Button variant="secondary" className="w-full">Update password</Button>
          </CardContent>
        </Card>
        <Card className="bg-[var(--ds-surface-1)]/90">
          <CardHeader>
            <CardTitle className="text-base">Workspace</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-[var(--ds-text-secondary)]">
            <p className="inline-flex items-center gap-2"><User2 className="h-4 w-4" /> Role: Admin Analyst</p>
            <p className="inline-flex items-center gap-2"><MapPin className="h-4 w-4" /> Region: APAC</p>
            <Button variant="outline" className="w-full">Manage team membership</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
