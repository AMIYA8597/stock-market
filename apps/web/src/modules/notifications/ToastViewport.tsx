"use client";

import { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { useToastStore } from '@/stores/toast-store';
import { useSignalAlerts } from '@/hooks/useSignalAlerts';

const toneIcon = {
  success: CheckCircle2,
  error: AlertTriangle,
  info: Info,
};

const toneClass = {
  success: 'text-[var(--ds-color-success-500)]',
  error: 'text-[var(--ds-color-danger-500)]',
  info: 'text-[var(--ds-color-primary-300)]',
};

export function ToastViewport(): JSX.Element {
  const { toasts, removeToast, addToast } = useToastStore();
  const { latestAlert } = useSignalAlerts();
  const lastSeenIdRef = useRef<string | null>(null);

  // useSignalAlerts already owns a single shared /ws/alerts connection (module-level
  // singleton) — this component just reacts to its latest alert instead of opening a
  // second raw socket to the same endpoint.
  useEffect(() => {
    if (!latestAlert) return;
    const id = `${latestAlert.symbol}-${latestAlert.timestamp}`;
    if (lastSeenIdRef.current === id) return;
    lastSeenIdRef.current = id;

    const isBuy = latestAlert.direction.includes('BUY');
    const isSell = latestAlert.direction.includes('SELL');
    const variant = isBuy ? 'success' : isSell ? 'destructive' : 'info';

    addToast({
      id,
      title: latestAlert.direction,
      description: latestAlert.message,
      variant,
      duration: 8000,
    });
  }, [latestAlert, addToast]);

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[60] w-[min(92vw,360px)] space-y-2">
      <AnimatePresence>
        {toasts.map((toast) => {
          const Icon = toneIcon[toast.tone];
          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              className="pointer-events-auto rounded-[var(--ds-radius-xl)] border border-[var(--ds-border-subtle)] bg-[var(--ds-surface-2)] p-3 shadow-[var(--ds-shadow-md)]"
            >
              <div className="flex items-start gap-2">
                <Icon className={`mt-0.5 h-4 w-4 ${toneClass[toast.tone]}`} />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-[var(--ds-text-primary)]">{toast.title}</p>
                  {toast.message ? <p className="mt-0.5 text-xs text-[var(--ds-text-secondary)]">{toast.message}</p> : null}
                </div>
                <button
                  type="button"
                  onClick={() => removeToast(toast.id)}
                  className="rounded-[var(--ds-radius-lg)] p-1 text-[var(--ds-text-muted)] transition hover:bg-[var(--ds-surface-3)] hover:text-[var(--ds-text-primary)]"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
