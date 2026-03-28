"use client";

import React from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import { AnimatePresence, motion } from 'framer-motion';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';

export function Modal({
  open,
  onOpenChange,
  title,
  description,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: React.ReactNode;
}): JSX.Element {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <AnimatePresence>
          {open ? (
            <>
              <Dialog.Overlay asChild>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm"
                />
              </Dialog.Overlay>
              <Dialog.Content asChild>
                <motion.div
                  initial={{ opacity: 0, y: 14, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.98 }}
                  transition={{ duration: 0.3 }}
                  className={cn(
                    'fixed left-1/2 top-1/2 z-50 w-[min(92vw,560px)] -translate-x-1/2 -translate-y-1/2',
                    'rounded-[var(--ds-radius-2xl)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-1)] p-5 shadow-[var(--ds-shadow-lg)]'
                  )}
                >
                  <div className="mb-4 flex items-start justify-between gap-3">
                    <div>
                      <Dialog.Title className="text-lg font-semibold text-[var(--ds-text-primary)]">{title}</Dialog.Title>
                      {description ? <Dialog.Description className="mt-1 text-sm text-[var(--ds-text-secondary)]">{description}</Dialog.Description> : null}
                    </div>
                    <Dialog.Close className="rounded-[var(--ds-radius-lg)] p-1.5 text-[var(--ds-text-secondary)] transition hover:bg-[var(--ds-surface-2)] hover:text-[var(--ds-text-primary)]">
                      <X className="h-4 w-4" />
                    </Dialog.Close>
                  </div>
                  {children}
                </motion.div>
              </Dialog.Content>
            </>
          ) : null}
        </AnimatePresence>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
