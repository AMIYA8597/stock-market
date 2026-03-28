"use client";

import React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

export function Drawer({
  open,
  onOpenChange,
  title,
  children,
  side = 'right',
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: React.ReactNode;
  side?: 'left' | 'right';
}): JSX.Element {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/45 backdrop-blur-sm" />
        <Dialog.Content
          className={cn(
            'fixed top-0 z-50 h-screen w-[min(92vw,420px)] border-[var(--ds-border-subtle)] bg-[var(--ds-surface-1)] p-4 shadow-[var(--ds-shadow-lg)]',
            side === 'right' ? 'right-0 border-l' : 'left-0 border-r'
          )}
        >
          <div className="mb-4 flex items-center justify-between">
            <Dialog.Title className="text-base font-semibold text-[var(--ds-text-primary)]">{title}</Dialog.Title>
            <Dialog.Close className="rounded-[var(--ds-radius-lg)] p-1.5 text-[var(--ds-text-secondary)] transition hover:bg-[var(--ds-surface-2)] hover:text-[var(--ds-text-primary)]">
              <X className="h-4 w-4" />
            </Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
