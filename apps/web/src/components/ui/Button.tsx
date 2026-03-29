import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../../lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-[var(--ds-radius-lg)] text-sm font-semibold ring-offset-0 transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ds-color-primary-300)] active:translate-y-[1px] active:scale-[0.99] disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        primary: 'bg-[var(--ds-color-primary-400)] text-[var(--ds-text-invert)] shadow-[var(--ds-shadow-sm)] hover:translate-y-[-1px] hover:bg-[var(--ds-color-primary-300)]',
        default: 'bg-[var(--ds-color-primary-400)] text-[var(--ds-text-invert)] shadow-[var(--ds-shadow-sm)] hover:translate-y-[-1px] hover:bg-[var(--ds-color-primary-300)]',
        secondary: 'bg-[var(--ds-surface-2)] text-[var(--ds-text-primary)] border border-[var(--ds-border-subtle)] hover:bg-[var(--ds-surface-3)]',
        destructive: 'bg-[var(--ds-color-danger-500)] text-white shadow-[var(--ds-shadow-sm)] hover:translate-y-[-1px] hover:brightness-110',
        buy: 'bg-[var(--ds-color-success-500)] text-[var(--ds-text-invert)] shadow-[var(--ds-shadow-sm)] hover:translate-y-[-1px] hover:brightness-110',
        sell: 'bg-[var(--ds-color-danger-500)] text-white shadow-[var(--ds-shadow-sm)] hover:translate-y-[-1px] hover:brightness-110',
        neutral: 'bg-[var(--ds-color-warning-500)] text-[var(--ds-text-invert)] shadow-[var(--ds-shadow-sm)] hover:translate-y-[-1px] hover:brightness-110',
        ghost: 'text-[var(--ds-text-primary)] hover:bg-[var(--ds-surface-2)]',
        outline: 'border border-[var(--ds-border-strong)] bg-transparent text-[var(--ds-text-primary)] hover:bg-[var(--ds-surface-2)]',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-8 px-3 text-xs',
        lg: 'h-11 px-6 text-base',
        xl: 'h-12 px-8 text-base',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, isLoading, children, disabled, ...props }, ref) => (
    <button
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      disabled={disabled || isLoading}
      aria-busy={isLoading ? 'true' : undefined}
      {...props}
    >
      {isLoading ? (
        <div className="flex items-center gap-2">
          <div className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
          {children}
        </div>
      ) : (
        children
      )}
    </button>
  )
);
Button.displayName = 'Button';

export { Button, buttonVariants };
