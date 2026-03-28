"use client";

import { useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  ArrowUpRight,
  BellDot,
  DollarSign,
  Gauge,
  Sparkles,
  Users,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Skeleton } from '@/components/ui/Skeleton';
import { StatCard } from '@/components/ui/StatCard';
import { Table, TableCell, TableHead, TableRow } from '@/components/ui/Table';

const kpis = [
  { title: 'Users', value: '24.6K', trend: 12.4, icon: Users },
  { title: 'Revenue', value: '$3.42M', trend: 9.8, icon: DollarSign },
  { title: 'Growth', value: '38.1%', trend: 4.6, icon: ArrowUpRight },
  { title: 'Activity', value: '1,284', trend: -1.7, icon: Activity },
] as const;

const revenueSeries = [
  { day: 'Mon', revenue: 220 },
  { day: 'Tue', revenue: 246 },
  { day: 'Wed', revenue: 238 },
  { day: 'Thu', revenue: 272 },
  { day: 'Fri', revenue: 286 },
  { day: 'Sat', revenue: 274 },
  { day: 'Sun', revenue: 301 },
];

const conversionSeries = [
  { day: 'Mon', rate: 2.9 },
  { day: 'Tue', rate: 3.2 },
  { day: 'Wed', rate: 3.1 },
  { day: 'Thu', rate: 3.4 },
  { day: 'Fri', rate: 3.7 },
  { day: 'Sat', rate: 3.5 },
  { day: 'Sun', rate: 3.9 },
];

const activities = [
  { id: 'evt-1', icon: BellDot, title: 'Alert rule triggered for AAPL', description: 'Threshold breakout detected in pre-market feed', time: '2m' },
  { id: 'evt-2', icon: Sparkles, title: 'Model forecast refreshed', description: 'Ensemble confidence updated across growth basket', time: '18m' },
  { id: 'evt-3', icon: Gauge, title: 'Risk profile normalized', description: 'Portfolio drawdown recovered by 2.1%', time: '36m' },
];

const positions = [
  { symbol: 'AAPL', side: 'Long', quantity: '420', pnl: '+$12,440', exposure: '$78,900' },
  { symbol: 'NVDA', side: 'Long', quantity: '108', pnl: '+$9,188', exposure: '$54,210' },
  { symbol: 'TSLA', side: 'Long', quantity: '190', pnl: '-$1,074', exposure: '$43,620' },
  { symbol: 'MSFT', side: 'Long', quantity: '210', pnl: '+$3,904', exposure: '$64,880' },
  { symbol: 'AMZN', side: 'Long', quantity: '330', pnl: '+$5,217', exposure: '$58,110' },
];

export function DashboardOverview(): JSX.Element {
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 700);
    return () => clearTimeout(timer);
  }, []);

  const pnlColor = useMemo(
    () => (value: string) => (value.startsWith('-') ? 'text-[var(--ds-color-danger-500)]' : 'text-[var(--ds-color-success-500)]'),
    []
  );

  if (loading) {
    return (
      <div className="space-y-5">
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => (
            <Skeleton key={index} className="h-[132px]" />
          ))}
        </div>
        <div className="grid gap-4 xl:grid-cols-[1.55fr_1fr]">
          <Skeleton className="h-[320px]" />
          <Skeleton className="h-[320px]" />
        </div>
        <Skeleton className="h-[290px]" />
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35 }} className="space-y-5">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {kpis.map((item, index) => (
          <StatCard
            key={item.title}
            title={item.title}
            value={item.value}
            trend={item.trend}
            icon={item.icon}
            delay={0.03 * index}
          />
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.55fr_1fr]">
        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay: 0.08 }}>
          <Card className="h-full bg-[var(--ds-surface-1)]/90">
            <CardHeader>
              <CardTitle>Revenue Performance</CardTitle>
              <CardDescription>Weekly trend with smooth growth trajectory.</CardDescription>
            </CardHeader>
            <CardContent className="grid gap-4 pb-6 lg:grid-cols-2">
              <div className="h-[240px] rounded-[var(--ds-radius-xl)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)]/60 p-3">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={revenueSeries}>
                    <defs>
                      <linearGradient id="revFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#54d5ff" stopOpacity={0.55} />
                        <stop offset="100%" stopColor="#54d5ff" stopOpacity={0.05} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                    <XAxis dataKey="day" stroke="var(--ds-text-muted)" fontSize={11} />
                    <YAxis stroke="var(--ds-text-muted)" fontSize={11} />
                    <Tooltip />
                    <Area type="monotone" dataKey="revenue" stroke="#54d5ff" strokeWidth={2.2} fill="url(#revFill)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="h-[240px] rounded-[var(--ds-radius-xl)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)]/60 p-3">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={conversionSeries}>
                    <CartesianGrid stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                    <XAxis dataKey="day" stroke="var(--ds-text-muted)" fontSize={11} />
                    <YAxis stroke="var(--ds-text-muted)" fontSize={11} />
                    <Tooltip />
                    <Line type="monotone" dataKey="rate" stroke="#1fb987" strokeWidth={2.4} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay: 0.14 }}>
          <Card className="h-full bg-[var(--ds-surface-1)]/90">
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Live operational feed from your workspace.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 pb-6">
              {activities.map((item, idx) => {
                const Icon = item.icon;
                return (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, x: 10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.18 + idx * 0.06, duration: 0.3 }}
                    whileHover={{ scale: 1.02 }}
                    className="rounded-[var(--ds-radius-xl)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)]/65 p-3"
                  >
                    <div className="flex items-start gap-2">
                      <div className="rounded-[var(--ds-radius-lg)] bg-[var(--ds-color-primary-400)]/18 p-1.5">
                        <Icon className="h-4 w-4 text-[var(--ds-color-primary-300)]" />
                      </div>
                      <div className="flex-1">
                        <p className="text-sm font-medium">{item.title}</p>
                        <p className="mt-1 text-xs text-[var(--ds-text-secondary)]">{item.description}</p>
                      </div>
                      <span className="text-[11px] text-[var(--ds-text-muted)]">{item.time}</span>
                    </div>
                  </motion.div>
                );
              })}
            </CardContent>
          </Card>
        </motion.div>
      </section>

      <motion.section initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, delay: 0.2 }}>
        <Card className="bg-[var(--ds-surface-1)]/90">
          <CardHeader>
            <CardTitle>Open Positions</CardTitle>
            <CardDescription>Interactive portfolio table with clean spacing and hover states.</CardDescription>
          </CardHeader>
          <CardContent className="overflow-hidden pb-6">
            <div className="overflow-x-auto rounded-[var(--ds-radius-xl)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-1)]/70 p-2">
              <Table>
                <thead>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Side</TableHead>
                    <TableHead>Quantity</TableHead>
                    <TableHead>P&amp;L</TableHead>
                    <TableHead>Exposure</TableHead>
                  </TableRow>
                </thead>
                <tbody>
                  {positions.map((row) => (
                    <TableRow key={row.symbol}>
                      <TableCell className="font-semibold">{row.symbol}</TableCell>
                      <TableCell>{row.side}</TableCell>
                      <TableCell>{row.quantity}</TableCell>
                      <TableCell className={pnlColor(row.pnl)}>{row.pnl}</TableCell>
                      <TableCell>{row.exposure}</TableCell>
                    </TableRow>
                  ))}
                </tbody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </motion.section>
    </motion.div>
  );
}
