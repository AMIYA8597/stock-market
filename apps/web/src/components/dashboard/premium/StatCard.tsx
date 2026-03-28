"use client";

import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/Badge";
import { Card, CardDescription, CardHeader, CardTitle } from "./Card";

interface StatCardProps {
  title: string;
  value: string;
  delta: string;
  trend: "up" | "down" | "flat";
  icon: LucideIcon;
}

export function StatCard({ title, value, delta, trend, icon: Icon }: StatCardProps): JSX.Element {
  const trendColor = trend === "up" ? "text-[var(--nq-bull)]" : trend === "down" ? "text-[var(--nq-bear)]" : "text-[var(--nq-text-secondary)]";

  return (
    <Card interactive className="p-5">
      <CardHeader className="mb-3">
        <div className="rounded-xl border border-white/10 bg-white/5 p-2.5 text-[var(--nq-accent)]">
          <Icon className="h-4 w-4" />
        </div>
        <Badge variant="outline" className="text-[10px] uppercase tracking-wide text-[var(--nq-text-secondary)]">
          Live
        </Badge>
      </CardHeader>

      <div className="space-y-2">
        <CardDescription>{title}</CardDescription>
        <CardTitle className="text-2xl font-semibold">{value}</CardTitle>
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className={`inline-flex items-center gap-1 text-xs font-semibold ${trendColor}`}>
          {trend === "up" ? <ArrowUpRight className="h-3.5 w-3.5" /> : trend === "down" ? <ArrowDownRight className="h-3.5 w-3.5" /> : <Minus className="h-3.5 w-3.5" />}
          {delta}
        </motion.div>
      </div>
    </Card>
  );
}
