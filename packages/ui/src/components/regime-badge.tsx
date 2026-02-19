"use client";

import * as React from "react";
import { cn } from "../lib/utils";

type Regime = "bull" | "bear" | "sideways";

interface RegimeBadgeProps {
  regime: Regime;
  confidence?: number;
  animated?: boolean;
  className?: string;
}

const regimeConfig: Record<Regime, { label: string; dotClass: string; bgClass: string; textClass: string }> = {
  bull: {
    label: "BULL",
    dotClass: "bg-nq-bull",
    bgClass: "bg-nq-bull-bg border-nq-bull/20",
    textClass: "text-nq-bull",
  },
  bear: {
    label: "BEAR",
    dotClass: "bg-nq-bear",
    bgClass: "bg-nq-bear-bg border-nq-bear/20",
    textClass: "text-nq-bear",
  },
  sideways: {
    label: "SIDEWAYS",
    dotClass: "bg-nq-warning",
    bgClass: "bg-nq-warning-muted border-nq-warning/20",
    textClass: "text-nq-warning",
  },
};

export function RegimeBadge({ regime, confidence, animated = true, className }: RegimeBadgeProps) {
  const config = regimeConfig[regime];

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1",
        config.bgClass,
        className
      )}
    >
      <span className="relative flex h-2 w-2">
        {animated && (
          <span
            className={cn(
              "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
              config.dotClass
            )}
          />
        )}
        <span className={cn("relative inline-flex h-2 w-2 rounded-full", config.dotClass)} />
      </span>
      <span className={cn("text-xs font-bold tracking-wider", config.textClass)}>
        {config.label}
      </span>
      {confidence !== undefined && (
        <span className={cn("text-[10px] font-mono", config.textClass)}>
          {confidence.toFixed(0)}%
        </span>
      )}
    </div>
  );
}
