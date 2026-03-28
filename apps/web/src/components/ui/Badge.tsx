import React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
  {
    variants: {
      variant: {
        default: 'border border-transparent bg-[var(--bg-elevated)] text-[var(--text-primary)]',
        secondary: 'border border-transparent bg-[var(--bg-overlay)] text-[var(--text-secondary)]',
        buy: 'border border-transparent bg-[rgba(0,230,118,0.2)] text-[var(--accent-green)]',
        sell: 'border border-transparent bg-[rgba(255,59,92,0.2)] text-[var(--accent-red)]',
        neutral: 'border border-transparent bg-[rgba(255,184,0,0.15)] text-[var(--accent-amber)]',
        bull: 'border border-transparent bg-[var(--regime-bull)] text-[var(--accent-green)]',
        bear: 'border border-transparent bg-[var(--regime-bear)] text-[var(--accent-red)]',
        sideways: 'border border-transparent bg-[var(--regime-side)] text-[var(--accent-amber)]',
        crisis: 'border border-transparent bg-[var(--regime-crisis)] text-red-300',
        outline: 'border border-[var(--border-strong)] text-[var(--text-primary)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
