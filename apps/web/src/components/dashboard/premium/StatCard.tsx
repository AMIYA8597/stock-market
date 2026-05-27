"use client";

import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowUpRight, Minus } from "lucide-react";
import { motion } from "framer-motion";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
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
  const gradient = trend === "up" ? "from-[rgba(0,230,118,0.28)] to-[rgba(0,230,118,0.06)]" : trend === "down" ? "from-[rgba(255,59,92,0.28)] to-[rgba(255,59,92,0.06)]" : "from-white/18 to-white/6";

  return (
    <Card interactive className="p-5">
      <CardHeader className="mb-4">
        <div className="flex items-start gap-3">
          <div className="rounded-2xl border border-white/10 bg-[linear-gradient(135deg,rgba(255,255,255,0.12),rgba(255,255,255,0.03))] p-3 text-[var(--nq-accent)] shadow-[0_14px_24px_rgba(0,0,0,0.18)]">
            <Icon className="h-4.5 w-4.5" />
          </div>
          <div>
            <CardDescription>{title}</CardDescription>
            <CardTitle className="mt-1 text-2xl font-semibold tracking-tight sm:text-[2rem]">{value}</CardTitle>
          </div>
        </div>
        <Badge variant="outline" className="border-white/10 bg-white/[0.06] text-[10px] uppercase tracking-[0.16em] text-[var(--nq-text-secondary)]">
          Live
        </Badge>
      </CardHeader>

      <div className="space-y-3">
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(
            "inline-flex items-center gap-1 rounded-full border border-white/10 bg-gradient-to-r px-2.5 py-1 text-xs font-semibold",
            trendColor,
            gradient
          )}
        >
          {trend === "up" ? <ArrowUpRight className="h-3.5 w-3.5" /> : trend === "down" ? <ArrowDownRight className="h-3.5 w-3.5" /> : <Minus className="h-3.5 w-3.5" />}
          {delta}
        </motion.div>

        <div className="flex h-10 items-end gap-1.5 opacity-90">
          {[18, 32, 24, 40, 28, 46].map((height, index) => (
            <motion.span
              key={`${title}-${index}`}
              initial={{ scaleY: 0.5, opacity: 0.3 }}
              animate={{ scaleY: 1, opacity: 1 }}
              transition={{ duration: 0.35, delay: index * 0.04 }}
              className={cn("w-full rounded-full bg-gradient-to-t", gradient)}
              style={{ height, transformOrigin: "bottom" }}
            />
          ))}
        </div>
      </div>
    </Card>
  );
}
