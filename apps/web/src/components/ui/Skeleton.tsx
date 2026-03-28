import React from 'react';
import { cn } from '@/lib/utils';

const Skeleton = ({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn('animate-pulse rounded-[var(--ds-radius-lg)] bg-[var(--ds-surface-2)]/90', className)}
    {...props}
  />
);

export { Skeleton };
