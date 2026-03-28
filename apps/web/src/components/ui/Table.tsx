import React from 'react';
import { cn } from '@/lib/utils';

export function Table({ className, ...props }: React.TableHTMLAttributes<HTMLTableElement>): JSX.Element {
  return <table className={cn('w-full border-separate border-spacing-0 text-sm', className)} {...props} />;
}

export function TableHead({ className, ...props }: React.HTMLAttributes<HTMLTableCellElement>): JSX.Element {
  return <th className={cn('bg-[var(--ds-surface-2)]/80 px-4 py-3 text-left text-xs font-semibold uppercase tracking-[0.08em] text-[var(--ds-text-secondary)] first:rounded-l-[var(--ds-radius-lg)] last:rounded-r-[var(--ds-radius-lg)]', className)} {...props} />;
}

export function TableRow({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>): JSX.Element {
  return <tr className={cn('border-b border-[var(--ds-border-subtle)] transition-all duration-300 hover:bg-[var(--ds-surface-2)]/60', className)} {...props} />;
}

export function TableCell({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>): JSX.Element {
  return <td className={cn('px-4 py-3 text-[var(--ds-text-primary)]', className)} {...props} />;
}
