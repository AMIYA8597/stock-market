"use client";

import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-nq-bg-elevated text-nq-text-secondary border border-nq-border",
        accent: "bg-nq-accent-muted text-nq-accent border border-nq-accent/20",
        bull: "bg-nq-bull-bg text-nq-bull border border-nq-bull/20",
        bear: "bg-nq-bear-bg text-nq-bear border border-nq-bear/20",
        warning: "bg-nq-warning-muted text-nq-warning border border-nq-warning/20",
        severity1: "bg-nq-bg-elevated text-nq-text-secondary",
        severity2: "bg-blue-500/10 text-blue-400",
        severity3: "bg-nq-warning-muted text-nq-warning",
        severity4: "bg-orange-500/10 text-orange-400",
        severity5: "bg-nq-bear-bg text-nq-bear",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
