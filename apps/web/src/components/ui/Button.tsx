import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
  {
    variants: {
      variant: {
        default: 'bg-[var(--accent-cyan)] text-black hover:bg-[#33DDFF]',
        secondary: 'bg-[var(--bg-elevated)] text-[var(--text-primary)] border border-[var(--border-muted)] hover:bg-[var(--bg-overlay)]',
        destructive: 'bg-[var(--accent-red)] text-white hover:bg-[#FF5B7D]',
        buy: 'bg-[var(--accent-green)] text-black hover:bg-[#00FF88]',
        sell: 'bg-[var(--accent-red)] text-white hover:bg-[#FF5B7D]',
        neutral: 'bg-[var(--accent-amber)] text-black hover:bg-[#FFD133]',
        ghost: 'hover:bg-[var(--bg-elevated)] text-[var(--text-primary)]',
        outline: 'border border-[var(--border-strong)] bg-transparent text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]',
      },
      size: {
        default: 'h-10 px-4 py-2',
        sm: 'h-9 rounded-md px-3 text-xs',
        lg: 'h-11 rounded-md px-8',
        xl: 'h-12 rounded-md px-8 text-base',
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
  asChild?: boolean;
  isLoading?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, isLoading, children, disabled, ...props }, ref) => (
    <button
      className={cn(buttonVariants({ variant, size, className }))}
      ref={ref}
      disabled={disabled || isLoading}
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
