/* eslint-disable @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars, prefer-const, react-hooks/exhaustive-deps, react/no-unescaped-entities, react/display-name */
"use client";

import { AuthGuard } from "@/components/auth/AuthGuard";
import { useAuth } from "@/hooks/useAuth";
import { Card, CardContent, CardHeader, CardTitle, CardDescription, Button } from "@neuroquant/ui";
import { Settings, Moon, Sun, Monitor, Bell, ShieldAlert } from "lucide-react";
import { useState } from "react";

export default function SettingsPage() {
  const { user } = useAuth();
  const [theme, setTheme] = useState<"dark" | "light" | "system">("dark");
  const [notifications, setNotifications] = useState(true);

  return (
    <AuthGuard>
      <div className="mx-auto max-w-4xl p-4 sm:p-6 lg:p-8">
        <div className="mb-8 flex items-center gap-3">
          <Settings className="h-6 w-6 text-[var(--nq-accent)]" />
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-[var(--nq-text-primary)]">Settings</h1>
            <p className="text-sm text-[var(--nq-text-secondary)]">Manage your application preferences and integrations.</p>
          </div>
        </div>

        <div className="grid gap-6">
          {/* Theme Settings */}
          <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
            <CardHeader>
              <CardTitle className="text-lg">Appearance</CardTitle>
              <CardDescription>Customize the look and feel of your terminal.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-4">
                <Button 
                  variant={theme === "light" ? "default" : "outline"}
                  onClick={() => setTheme("light")}
                  className={theme === "light" ? "bg-[var(--nq-accent)] text-black" : ""}
                >
                  <Sun className="mr-2 h-4 w-4" /> Light
                </Button>
                <Button 
                  variant={theme === "dark" ? "default" : "outline"}
                  onClick={() => setTheme("dark")}
                  className={theme === "dark" ? "bg-[var(--nq-accent)] text-black" : ""}
                >
                  <Moon className="mr-2 h-4 w-4" /> Dark
                </Button>
                <Button 
                  variant={theme === "system" ? "default" : "outline"}
                  onClick={() => setTheme("system")}
                  className={theme === "system" ? "bg-[var(--nq-accent)] text-black" : ""}
                >
                  <Monitor className="mr-2 h-4 w-4" /> System
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Notifications */}
          <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
            <CardHeader>
              <CardTitle className="text-lg">Notifications</CardTitle>
              <CardDescription>Configure how you want to be alerted about market events.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] p-4">
                <div className="flex items-center gap-4">
                  <Bell className="h-5 w-5 text-[var(--nq-text-secondary)]" />
                  <div>
                    <p className="font-medium text-[var(--nq-text-primary)]">Trade Alerts</p>
                    <p className="text-xs text-[var(--nq-text-secondary)]">Receive push notifications for AI signals.</p>
                  </div>
                </div>
                <Button 
                  variant={notifications ? "default" : "outline"}
                  onClick={() => setNotifications(!notifications)}
                  className={notifications ? "bg-[var(--nq-bull)] text-black" : ""}
                >
                  {notifications ? "Enabled" : "Disabled"}
                </Button>
              </div>
              <div className="flex items-center justify-between rounded-lg border border-[var(--border-subtle)] p-4">
                <div className="flex items-center gap-4">
                  <ShieldAlert className="h-5 w-5 text-[var(--nq-text-secondary)]" />
                  <div>
                    <p className="font-medium text-[var(--nq-text-primary)]">Risk Warnings</p>
                    <p className="text-xs text-[var(--nq-text-secondary)]">Mandatory alerts when positions exceed limits.</p>
                  </div>
                </div>
                <Button variant="outline" disabled>
                  Always On
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* API Keys */}
          <Card className="bg-[var(--bg-surface)] border-[var(--border-subtle)]">
            <CardHeader>
              <CardTitle className="text-lg">API & Broker Integrations</CardTitle>
              <CardDescription>Manage keys to execute real trades securely.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="rounded-md bg-white/5 p-4 border border-[var(--border-subtle)]">
                <p className="text-sm text-[var(--nq-text-secondary)] mb-4">
                  Your account is currently in Paper Trading mode. To enable live trading, add your broker API keys below.
                </p>
                <Button variant="outline">Add Broker Integration</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </AuthGuard>
  );
}
