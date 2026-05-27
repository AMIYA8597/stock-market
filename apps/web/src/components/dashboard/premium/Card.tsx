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
        "group relative overflow-hidden rounded-[1.5rem] border border-white/10 bg-[linear-gradient(180deg,rgba(255,255,255,0.085),rgba(255,255,255,0.02)_58%,rgba(255,255,255,0.012))] p-6 shadow-[0_18px_54px_rgba(0,0,0,0.32)] backdrop-blur-xl",
        "before:pointer-events-none before:absolute before:inset-0 before:bg-[radial-gradient(780px_180px_at_0%_0%,rgba(255,255,255,0.12),transparent_42%)] before:content-['']",
        interactive && "cursor-pointer transition-all duration-300 hover:-translate-y-1 hover:shadow-[0_26px_84px_rgba(0,0,0,0.42)] hover:before:bg-[radial-gradient(780px_180px_at_0%_0%,rgba(255,255,255,0.18),transparent_42%)]",
        glow && "ring-1 ring-[var(--nq-accent)]/35",
        "nq-soft-ring",
        className
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: React.HTMLAttributes<HTMLDivElement>): JSX.Element {
  return <div className={cn("mb-6 flex items-start justify-between gap-4", className)} {...props} />;
}

export function CardTitle({ className, ...props }: React.HTMLAttributes<HTMLHeadingElement>): JSX.Element {
  return <h3 className={cn("text-sm font-semibold tracking-tight text-[var(--nq-text-primary)] sm:text-base", className)} {...props} />;
}

export function CardDescription({ className, ...props }: React.HTMLAttributes<HTMLParagraphElement>): JSX.Element {
  return <p className={cn("text-xs leading-relaxed text-[var(--nq-text-secondary)]", className)} {...props} />;
}

export function CardContent({ className, ...props }: React.HTMLAttributes<HTMLDivElement>): JSX.Element {
  return <div className={cn("space-y-4", className)} {...props} />;
}

export function CardFooter({ className, ...props }: React.HTMLAttributes<HTMLDivElement>): JSX.Element {
  return <div className={cn("mt-6 flex items-center justify-between gap-3 border-t border-white/10 pt-4", className)} {...props} />;
}
