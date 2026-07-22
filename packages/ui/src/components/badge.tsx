import React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold tracking-wide transition-colors focus:outline-none",
  {
    variants: {
      variant: {
        default:
          "border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)] text-[var(--ds-text-primary)]",
        secondary:
          "border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-3)] text-[var(--ds-text-secondary)]",
        buy: "border border-transparent bg-[rgba(20,184,109,0.2)] text-[var(--ds-color-success-500)]",
        sell: "border border-transparent bg-[rgba(221,53,93,0.2)] text-[var(--ds-color-danger-500)]",
        neutral:
          "border border-transparent bg-[rgba(210,139,16,0.18)] text-[var(--ds-color-warning-500)]",
        bull: "border border-transparent bg-[rgba(20,184,109,0.18)] text-[var(--ds-color-success-500)]",
        bear: "border border-transparent bg-[rgba(221,53,93,0.18)] text-[var(--ds-color-danger-500)]",
        sideways:
          "border border-transparent bg-[rgba(210,139,16,0.16)] text-[var(--ds-color-warning-500)]",
        crisis:
          "border border-transparent bg-[var(--regime-crisis)] text-red-300",
        outline:
          "border border-[var(--ds-border-strong)] text-[var(--ds-text-primary)]",
        accent:
          "border border-transparent bg-[var(--ds-color-accent-500)] bg-opacity-20 text-[var(--ds-color-accent-500)]",
        warning:
          "border border-transparent bg-[rgba(210,139,16,0.18)] text-[var(--ds-color-warning-500)]",
        severity1: "border border-transparent bg-red-500/20 text-red-500",
        severity2: "border border-transparent bg-orange-500/20 text-orange-500",
        severity3: "border border-transparent bg-yellow-500/20 text-yellow-500",
        severity4: "border border-transparent bg-blue-500/20 text-blue-500",
        severity5: "border border-transparent bg-gray-500/20 text-gray-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends
    React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
