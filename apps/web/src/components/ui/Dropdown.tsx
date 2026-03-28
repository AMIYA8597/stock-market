"use client";

import React from 'react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import { cn } from '@/lib/utils';

export const Dropdown = DropdownMenu.Root;
export const DropdownTrigger = DropdownMenu.Trigger;

export function DropdownContent({ className, ...props }: DropdownMenu.DropdownMenuContentProps): JSX.Element {
  return (
    <DropdownMenu.Portal>
      <DropdownMenu.Content
        sideOffset={8}
        className={cn(
          'z-50 min-w-[180px] rounded-[var(--ds-radius-xl)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)] p-1 shadow-[var(--ds-shadow-md)]',
          className
        )}
        {...props}
      />
    </DropdownMenu.Portal>
  );
}

export function DropdownItem({ className, ...props }: DropdownMenu.DropdownMenuItemProps): JSX.Element {
  return (
    <DropdownMenu.Item
      className={cn(
        'flex cursor-pointer select-none items-center rounded-[var(--ds-radius-lg)] px-3 py-2 text-sm text-[var(--ds-text-secondary)] outline-none transition hover:bg-[var(--ds-surface-3)] hover:text-[var(--ds-text-primary)]',
        className
      )}
      {...props}
    />
  );
}

export function DropdownLabel({ className, ...props }: DropdownMenu.DropdownMenuLabelProps): JSX.Element {
  return <DropdownMenu.Label className={cn('px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--ds-text-muted)]', className)} {...props} />;
}

export function DropdownSeparator({ className, ...props }: DropdownMenu.DropdownMenuSeparatorProps): JSX.Element {
  return <DropdownMenu.Separator className={cn('my-1 h-px bg-[var(--ds-border-subtle)]', className)} {...props} />;
}
