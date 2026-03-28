import React from 'react';
import { cn } from '@/lib/utils';

const Input = React.forwardRef<
  HTMLInputElement,
  React.InputHTMLAttributes<HTMLInputElement>
>(({ className, type, ...props }, ref) => (
  <input
    type={type}
    className={cn(
      'flex h-10 w-full rounded-[var(--ds-radius-lg)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)] px-3 py-2',
      'text-sm text-[var(--ds-text-primary)] placeholder:text-[var(--ds-text-muted)]',
      'shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] transition-all duration-300 focus-visible:-translate-y-[1px] focus-visible:border-[var(--ds-color-primary-300)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--ds-color-primary-400)]/25',
      'disabled:cursor-not-allowed disabled:opacity-50',
      className
    )}
    ref={ref}
    {...props}
  />
));
Input.displayName = 'Input';

export { Input };
