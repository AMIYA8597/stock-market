"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Bell,
  ChartNoAxesCombined,
  CheckCircle2,
  Eye,
  LayoutDashboard,
  Lock,
  Sparkles,
  TrendingUp,
  Workflow,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Input } from "@/components/ui/Input";
import { RangeSlider } from "@/components/ui/RangeSlider";
import { Select } from "@/components/ui/Select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/Tabs";
import { Button, Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle, StatCard } from "@/components/dashboard/premium";
import { Table, TableCell, TableHead, TableRow } from "@/components/ui/Table";

const kpiCards = [
  { title: "Users", value: "24.6K", delta: "+12.4%", trend: "up" as const, icon: LayoutDashboard },
  { title: "Revenue", value: "$3.42M", delta: "+9.8%", trend: "up" as const, icon: TrendingUp },
  { title: "Activity", value: "1,284", delta: "+4.1%", trend: "up" as const, icon: Bell },
  { title: "Latency", value: "42ms", delta: "-11ms", trend: "down" as const, icon: ChartNoAxesCombined },
];

const rows = [
  { symbol: "AAPL", side: "Long", qty: "420", pnl: "+$12,440", exposure: "$78,900" },
  { symbol: "NVDA", side: "Long", qty: "108", pnl: "+$9,188", exposure: "$54,210" },
  { symbol: "TSLA", side: "Long", qty: "190", pnl: "-$1,074", exposure: "$43,620" },
];

export default function ComponentShowcasePage(): JSX.Element {
  const [rangeValue, setRangeValue] = useState<[number, number]>([20, 80]);

  return (
    <main className="relative min-h-screen overflow-hidden px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-[1600px] space-y-8">
        <motion.section initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35 }}>
          <Card glow className="relative overflow-hidden">
            <div className="absolute inset-0 bg-[radial-gradient(1100px_520px_at_0%_0%,rgba(0,212,245,0.16),transparent_45%),radial-gradient(800px_420px_at_100%_0%,rgba(139,92,246,0.14),transparent_45%)]" />
            <div className="relative grid gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
              <div className="space-y-5">
                <Badge variant="bull" className="px-3 py-1.5 text-[10px] uppercase tracking-[0.16em]">Design system showcase</Badge>
                <h1 className="text-4xl font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-5xl">
                  Premium UI primitives, dashboard panels, and data-heavy controls.
                </h1>
                <p className="max-w-2xl text-sm leading-7 text-[var(--nq-text-secondary)] sm:text-base">
                  This page is built to verify the new card-based visual language, spacing scale, responsive layout behavior, and component polish locally.
                </p>
                <div className="flex flex-wrap gap-3">
                  <Button rightIcon={<ArrowRight className="h-4 w-4" />}>Primary action</Button>
                  <Button variant="secondary">Secondary action</Button>
                  <Button variant="ghost" leftIcon={<Eye className="h-4 w-4" />}>Preview mode</Button>
                </div>
              </div>

              <div className="grid gap-3 sm:grid-cols-2">
                {[
                  { label: "System health", value: "98.4%" },
                  { label: "Model confidence", value: "92%" },
                  { label: "Open alerts", value: "17" },
                  { label: "Theme mode", value: "Dark" },
                ].map((item) => (
                  <div key={item.label} className="rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
                    <p className="text-xs uppercase tracking-[0.14em] text-[var(--nq-text-secondary)]">{item.label}</p>
                    <p className="mt-2 text-2xl font-semibold tracking-tight text-[var(--nq-text-primary)]">{item.value}</p>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </motion.section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {kpiCards.map((item) => (
            <StatCard key={item.title} title={item.title} value={item.value} delta={item.delta} trend={item.trend} icon={item.icon} />
          ))}
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Controls</CardTitle>
                <CardDescription>Common inputs, buttons, and interactive states.</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-4 md:grid-cols-2">
                <Input placeholder="Search symbols or pages" />
                <Select>
                  <option>All assets</option>
                  <option>Stocks</option>
                  <option>Crypto</option>
                </Select>
              </div>

              <div className="grid gap-3 sm:grid-cols-3">
                <Button leftIcon={<Sparkles className="h-4 w-4" />}>Primary</Button>
                <Button variant="secondary" leftIcon={<Workflow className="h-4 w-4" />}>Secondary</Button>
                <Button variant="ghost" leftIcon={<Lock className="h-4 w-4" />}>Ghost</Button>
              </div>

              <div className="space-y-3 rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
                <div className="flex items-center justify-between text-sm text-[var(--nq-text-secondary)]">
                  <span>Allocation range</span>
                  <span>{rangeValue[0]} - {rangeValue[1]}</span>
                </div>
                <RangeSlider min={0} max={100} step={5} value={rangeValue} onChange={(value) => Array.isArray(value) && setRangeValue(value)} />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>Tabbed workspace</CardTitle>
                <CardDescription>Responsive composition and container spacing.</CardDescription>
              </div>
            </CardHeader>
            <CardContent>
              <Tabs defaultValue="overview">
                <TabsList>
                  <TabsTrigger value="overview">Overview</TabsTrigger>
                  <TabsTrigger value="signals">Signals</TabsTrigger>
                  <TabsTrigger value="risk">Risk</TabsTrigger>
                </TabsList>
                <TabsContent value="overview" className="mt-4 rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-sm text-[var(--nq-text-secondary)]">A premium dashboard layout should always preserve hierarchy, depth, and breathing room.</p>
                </TabsContent>
                <TabsContent value="signals" className="mt-4 rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-sm text-[var(--nq-text-secondary)]">Signals belong in cards, not flat panels.</p>
                </TabsContent>
                <TabsContent value="risk" className="mt-4 rounded-[1.25rem] border border-white/10 bg-white/5 p-4">
                  <p className="text-sm text-[var(--nq-text-secondary)]">Risk controls should be visible, legible, and easy to act on.</p>
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <Card>
            <CardHeader>
              <div>
                <CardTitle>Portfolio table</CardTitle>
                <CardDescription>Readable row spacing, premium borders, and clear P&amp;L contrast.</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="overflow-hidden">
              <div className="overflow-x-auto rounded-[1.25rem] border border-white/10 bg-white/[0.04] p-2">
                <Table>
                  <thead>
                    <TableRow>
                      <TableHead>Symbol</TableHead>
                      <TableHead>Side</TableHead>
                      <TableHead>Qty</TableHead>
                      <TableHead>P&amp;L</TableHead>
                      <TableHead>Exposure</TableHead>
                    </TableRow>
                  </thead>
                  <tbody>
                    {rows.map((row) => (
                      <TableRow key={row.symbol}>
                        <TableCell className="font-semibold">{row.symbol}</TableCell>
                        <TableCell>{row.side}</TableCell>
                        <TableCell>{row.qty}</TableCell>
                        <TableCell className={row.pnl.startsWith("-") ? "text-[var(--nq-bear)]" : "text-[var(--nq-bull)]"}>{row.pnl}</TableCell>
                        <TableCell>{row.exposure}</TableCell>
                      </TableRow>
                    ))}
                  </tbody>
                </Table>
              </div>
            </CardContent>
            <CardFooter>
              <Badge variant="outline" className="border-white/10 bg-white/[0.06] text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">
                Responsive, scalable, clean
              </Badge>
            </CardFooter>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardTitle>Visual checklist</CardTitle>
                <CardDescription>Useful for local QA of the redesign.</CardDescription>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                "Card-based layout",
                "Soft shadows and glow",
                "Rounded corners and spacing",
                "Premium color contrast",
                "Motion-ready structure",
              ].map((item) => (
                <div key={item} className="flex items-center gap-3 rounded-[1.15rem] border border-white/10 bg-white/5 px-4 py-3">
                  <CheckCircle2 className="h-4.5 w-4.5 text-[var(--nq-bull)]" />
                  <span className="text-sm text-[var(--nq-text-secondary)]">{item}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </section>
      </div>
    </main>
  );
}