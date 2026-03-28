import React from 'react';
import { cn } from '@/lib/utils';

const Select = React.forwardRef<
  HTMLSelectElement,
  React.SelectHTMLAttributes<HTMLSelectElement> & { children: React.ReactNode }
>(({ className, children, ...props }, ref) => (
  <select
    ref={ref}
    className={cn(
      'flex h-10 w-full rounded-md border border-[var(--border-muted)] bg-[var(--bg-elevated)] px-3 py-2',
      'text-sm text-[var(--text-primary)] transition-colors',
      'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-cyan)]',
      'disabled:cursor-not-allowed disabled:opacity-50',
      className
    )}
    {...props}
  >
    {children}
  </select>
));
Select.displayName = 'Select';

export { Select };
