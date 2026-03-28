"use client";

import { useEffect, useState } from 'react';
import { BellRing, Filter, MessagesSquare } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/Tabs';
import { notificationsApi } from '@/lib/api-client';
import { useToastStore } from '@/stores/toast-store';

const seedRows = [
  { id: 'N-883', title: 'AAPL target reached', detail: 'Take-profit condition met at $218.2', tone: 'buy', time: '2m ago' },
  { id: 'N-884', title: 'Model drift warning', detail: 'momentum-v4 confidence dropped by 8.2%', tone: 'neutral', time: '10m ago' },
  { id: 'N-885', title: 'Order failed', detail: 'Insufficient margin for NIFTY option spread', tone: 'sell', time: '31m ago' },
];

export function NotificationCenterPage(): JSX.Element {
  const pushToast = useToastStore((state) => state.pushToast);
  const [rows, setRows] = useState(seedRows);

  useEffect(() => {
    let mounted = true;
    notificationsApi.list().then((data) => {
      if (!mounted) return;
      setRows(
        data.items.map((item) => ({
          id: item.id,
          title: item.title,
          detail: item.message,
          tone: item.level === 'error' ? 'sell' : item.level === 'warning' ? 'neutral' : 'buy',
          time: new Date(item.created_at).toLocaleTimeString(),
        }))
      );
    }).catch(() => {
      if (!mounted) return;
      pushToast({ tone: 'error', title: 'Notifications unavailable' });
    });

    return () => {
      mounted = false;
    };
  }, [pushToast]);

  return (
    <Card className="bg-[var(--ds-surface-1)]/90">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <CardTitle>Notification Center</CardTitle>
            <CardDescription>Unified panel for alerts, platform events, and collaboration updates.</CardDescription>
          </div>
          <Button variant="secondary" size="sm"><Filter className="mr-1 h-4 w-4" /> Filter</Button>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="all">
          <TabsList>
            <TabsTrigger value="all">All</TabsTrigger>
            <TabsTrigger value="alerts">Alerts</TabsTrigger>
            <TabsTrigger value="messages">Messages</TabsTrigger>
          </TabsList>
          <TabsContent value="all" className="mt-4 space-y-2">
            {rows.map((item) => (
              <div key={item.id} className="flex items-start justify-between gap-3 rounded-[var(--ds-radius-lg)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)] p-3">
                <div className="flex items-start gap-2">
                  <BellRing className="mt-0.5 h-4 w-4 text-[var(--ds-color-primary-300)]" />
                  <div>
                    <p className="text-sm font-medium">{item.title}</p>
                    <p className="text-xs text-[var(--ds-text-secondary)]">{item.detail}</p>
                  </div>
                </div>
                <div className="text-right">
                  <Badge variant={item.tone as 'buy' | 'sell' | 'neutral'}>{item.id}</Badge>
                  <p className="mt-1 text-[11px] text-[var(--ds-text-muted)]">{item.time}</p>
                </div>
              </div>
            ))}
          </TabsContent>
          <TabsContent value="alerts" className="mt-4 text-sm text-[var(--ds-text-secondary)]">Signal and risk alerts are shown here.</TabsContent>
          <TabsContent value="messages" className="mt-4">
            <div className="rounded-[var(--ds-radius-lg)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)] p-5 text-sm text-[var(--ds-text-secondary)] inline-flex items-center gap-2">
              <MessagesSquare className="h-4 w-4" /> Team messages will appear here.
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}
