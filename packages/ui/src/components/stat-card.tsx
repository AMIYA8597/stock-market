"use client";

import * as React from "react";
import { cn, formatPercent, getPriceColor, getDirectionArrow } from "../lib/utils";
import { Card } from "./card";

interface StatCardProps {
  label: string;
  value: string;
  change?: number;
  changeLabel?: string;
  icon?: React.ReactNode;
  className?: string;
}

export function StatCard({ label, value, change, changeLabel, icon, className }: StatCardProps) {
  return (
    <Card className={cn("flex flex-col gap-2", className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-nq-text-secondary uppercase tracking-wider">
          {label}
        </span>
        {icon && (
          <div className="flex h-8 w-8 items-center justify-center rounded-nq bg-nq-bg-elevated text-nq-accent">
            {icon}
          </div>
        )}
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-2xl font-bold font-mono text-nq-text-primary">
          {value}
        </span>
        {change !== undefined && (
          <span className={cn("flex items-center gap-0.5 text-xs font-medium", getPriceColor(change))}>
            <span className="text-[10px]">{getDirectionArrow(change)}</span>
            {formatPercent(change)}
          </span>
        )}
      </div>
      {changeLabel && (
        <span className="text-xs text-nq-text-tertiary">{changeLabel}</span>
      )}
    </Card>
  );
}
