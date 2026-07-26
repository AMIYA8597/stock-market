"use client";

import { motion } from 'framer-motion';
import { ArrowDownRight, ArrowUpRight, type LucideIcon } from 'lucide-react';
import { Card, CardContent } from "./card";
import { cn } from "../lib/utils";

export interface StatCardProps {
  title: string;
  value: string;
  trend: React.ReactNode;
  icon: LucideIcon;
  delay?: number;
}

export function StatCard({ title, value, trend, icon: Icon, delay = 0 }: StatCardProps): JSX.Element {
  const isNumber = typeof trend === 'number';
  const positive = isNumber 
    ? (trend as number) >= 0 
    : (typeof trend === 'string' ? !trend.toLowerCase().includes('loss') : true);

  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay }}
      whileHover={{ y: -4, scale: 1.02 }}
    >
      <Card className="h-full bg-[var(--ds-surface-1)]/90">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.1em] text-[var(--ds-text-secondary)]">{title}</p>
              <p className="mt-2 text-3xl font-semibold leading-none">{value}</p>
              <div className={cn('mt-3 inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold', positive ? 'bg-[rgba(20,184,109,0.18)] text-[var(--ds-color-success-500)]' : 'bg-[rgba(221,53,93,0.18)] text-[var(--ds-color-danger-500)]')}>
                {isNumber ? (
                  <>
                    {positive ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
                    {positive ? '+' : ''}{(trend as number).toFixed(1)}%
                  </>
                ) : (
                  <span>{trend}</span>
                )}
              </div>
            </div>
            <div className={cn('rounded-[var(--ds-radius-lg)] p-2.5', positive ? 'bg-[var(--ds-color-primary-400)]/18' : 'bg-[var(--ds-color-danger-500)]/18')}>
              <Icon className={cn('h-5 w-5', positive ? 'text-[var(--ds-color-primary-300)]' : 'text-[var(--ds-color-danger-500)]')} />
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
