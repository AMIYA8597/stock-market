"use client";

import { cn } from "@/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  interactive?: boolean;
  glow?: boolean;
}

export function Card({ className, interactive = false, glow = false, ...props }: CardProps): JSX.Element {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.085),rgba(255,255,255,0.02)_55%,rgba(255,255,255,0.012))] p-6 shadow-[0_14px_44px_rgba(0,0,0,0.30)] backdrop-blur-sm",
        "before:pointer-events-none before:absolute before:inset-0 before:bg-[radial-gradient(600px_140px_at_0%_0%,rgba(255,255,255,0.10),transparent_45%)] before:content-['']",
        interactive && "cursor-pointer transition duration-300 hover:-translate-y-1 hover:scale-[1.004] hover:shadow-[0_22px_70px_rgba(0,0,0,0.40)]",
        glow && "ring-1 ring-[var(--nq-accent)]/35",
        "nq-soft-ring",
        className
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>): JSX.Element {
  return <div className={cn("mb-6 flex items-center justify-between", className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>): JSX.Element {
  return <h3 className={cn("text-sm font-semibold text-[var(--nq-text-primary)]", className)} {...props} />;
}

export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>): JSX.Element {
  return <p className={cn("text-xs text-[var(--nq-text-secondary)]", className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>): JSX.Element {
  return <div className={cn("space-y-4", className)} {...props} />;
}
