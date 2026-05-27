"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-[1rem] text-sm font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nq-accent)]/60 disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]",
  {
    variants: {
      variant: {
        primary: "bg-[linear-gradient(135deg,var(--nq-accent),#69f5ff)] text-black shadow-[0_12px_28px_rgba(0,212,245,0.30)] hover:-translate-y-0.5 hover:shadow-[0_18px_40px_rgba(0,212,245,0.40)]",
        secondary: "border border-white/[0.12] bg-white/[0.06] text-[var(--nq-text-primary)] hover:-translate-y-0.5 hover:bg-white/[0.12]",
        ghost: "text-[var(--nq-text-secondary)] hover:bg-white/[0.08] hover:text-[var(--nq-text-primary)]",
        outline: "border border-white/[0.14] bg-transparent text-[var(--nq-text-primary)] hover:border-white/20 hover:bg-white/[0.08]",
      },
      size: {
        sm: "h-9 px-3.5",
        md: "h-10 px-4.5",
        lg: "h-11 px-5.5",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
  isLoading?: boolean;
}

export function Button({ className, variant, size, leftIcon, rightIcon, children, isLoading = false, disabled, ...props }: ButtonProps): JSX.Element {
  return (
    <button className={cn(buttonVariants({ variant, size }), className)} disabled={disabled || isLoading} aria-busy={isLoading ? "true" : undefined} {...props}>
      {isLoading ? (
        <span className="inline-flex items-center gap-2">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
          {children}
        </span>
      ) : (
        <>
          {leftIcon}
          {children}
          {rightIcon}
        </>
      )}
    </button>
  );
}
