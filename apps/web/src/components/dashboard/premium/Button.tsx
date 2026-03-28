"use client";

import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-xl text-sm font-medium transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--nq-accent)]/60 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        primary: "bg-[var(--nq-accent)] text-black shadow-[0_8px_24px_rgba(0,212,245,0.35)] hover:bg-[var(--nq-accent-hover)]",
        secondary: "border border-white/15 bg-white/5 text-[var(--nq-text-primary)] hover:bg-white/10",
        ghost: "text-[var(--nq-text-secondary)] hover:bg-white/8 hover:text-[var(--nq-text-primary)]",
      },
      size: {
        sm: "h-9 px-3",
        md: "h-10 px-4",
        lg: "h-11 px-5",
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
}

export function Button({ className, variant, size, leftIcon, rightIcon, children, ...props }: ButtonProps): JSX.Element {
  return (
    <button className={cn(buttonVariants({ variant, size }), "active:scale-[0.98] hover:scale-[1.01]", className)} {...props}>
      {leftIcon}
      {children}
      {rightIcon}
    </button>
  );
}
