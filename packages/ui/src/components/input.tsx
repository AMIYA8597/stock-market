"use client";

import * as React from "react";
import { cn } from "../lib/utils";

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: React.ReactNode;
  error?: string;
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, icon, error, ...props }, ref) => {
    return (
      <div className="relative w-full">
        {icon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-nq-text-tertiary">
            {icon}
          </div>
        )}
        <input
          type={type}
          className={cn(
            "flex h-9 w-full rounded-nq border bg-nq-bg-secondary px-3 py-1.5 text-sm text-nq-text-primary",
            "placeholder:text-nq-text-tertiary",
            "focus:outline-none focus:ring-2 focus:ring-nq-accent/50 focus:border-nq-accent",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "transition-all duration-150",
            error ? "border-nq-bear" : "border-nq-border",
            icon && "pl-9",
            className
          )}
          ref={ref}
          {...props}
        />
        {error && (
          <p className="mt-1 text-xs text-nq-bear">{error}</p>
        )}
      </div>
    );
  }
);
Input.displayName = "Input";

export { Input };
