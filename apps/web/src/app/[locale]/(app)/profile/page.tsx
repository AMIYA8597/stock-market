"use client";

import { AuthGuard } from "@/components/auth/AuthGuard";
import { useAuth } from "@/hooks/useAuth";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, Button, Badge } from "@neuroquant/ui";
import { User, Mail, Shield, CreditCard, LogOut } from "lucide-react";

export default function ProfilePage() {
  const { user, logout } = useAuth();

  return (
    <AuthGuard>
      <div className="mx-auto max-w-4xl p-4 sm:p-6 lg:p-8">
        <div className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight text-[var(--nq-text-primary)]">Profile</h1>
          <p className="text-sm text-[var(--nq-text-secondary)]">Manage your account settings and preferences.</p>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          {/* Personal Information */}
          <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
            <CardHeader>
              <CardTitle className="text-lg">Personal Information</CardTitle>
              <CardDescription>Your personal details and identity.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--nq-accent)]/10 text-[var(--nq-accent)]">
                  <User className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-[var(--nq-text-tertiary)]">Full Name</p>
                  <p className="font-medium text-[var(--nq-text-primary)]">{user?.full_name || "User"}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--nq-bull)]/10 text-[var(--nq-bull)]">
                  <Mail className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-[var(--nq-text-tertiary)]">Email Address</p>
                  <p className="font-medium text-[var(--nq-text-primary)]">{user?.email}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-[var(--ds-color-purple-500)]/10 text-[var(--ds-color-purple-500)]">
                  <Shield className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-[var(--nq-text-tertiary)]">Role</p>
                  <div className="mt-1">
                    <Badge variant="outline" className="text-[10px] uppercase">
                      {user?.role || "USER"}
                    </Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Subscription / Plan */}
          <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
            <CardHeader>
              <CardTitle className="text-lg">Subscription & Entitlements</CardTitle>
              <CardDescription>Manage your active plan and billing details.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white/5 text-[var(--nq-text-secondary)]">
                  <CreditCard className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-xs uppercase tracking-wider text-[var(--nq-text-tertiary)]">Current Plan</p>
                  <div className="mt-1 flex items-center gap-2">
                    <Badge variant="default" className="text-[10px] uppercase bg-[var(--nq-accent)] text-black font-bold">
                      FREE
                    </Badge>
                    <span className="text-xs text-[var(--nq-text-secondary)]">Active</span>
                  </div>
                </div>
              </div>
              <p className="text-sm text-[var(--nq-text-secondary)]">
                Upgrade to PRO for AI signals, real-time data, and advanced portfolio analytics.
              </p>
              <Button variant="outline" className="w-full">
                Manage Billing
              </Button>
            </CardContent>
          </Card>

          {/* Session Management */}
          <Card className="md:col-span-2 bg-[var(--bg-surface)] border-[var(--border-subtle)]">
            <CardHeader>
              <CardTitle className="text-lg text-[var(--nq-bear)]">Session Management</CardTitle>
              <CardDescription>Sign out of your account on this device.</CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="destructive" onClick={logout} className="flex items-center gap-2">
                <LogOut className="h-4 w-4" />
                Sign Out
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </AuthGuard>
  );
}
