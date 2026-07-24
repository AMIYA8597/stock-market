"use client";

import { useEffect, useState } from "react";
import { BellRing, X } from "lucide-react";
import { useSignalAlerts } from "@/hooks/useSignalAlerts";
import { cn } from "@neuroquant/ui";
import { AnimatePresence, motion } from "framer-motion";

export function GlobalToast() {
  const { latestAlert } = useSignalAlerts();
  const [visibleAlert, setVisibleAlert] = useState<typeof latestAlert | null>(null);

  useEffect(() => {
    if (latestAlert) {
      setVisibleAlert(latestAlert);
      const timer = setTimeout(() => {
        setVisibleAlert(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [latestAlert]);

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      <AnimatePresence>
        {visibleAlert && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className={cn(
              "w-80 rounded-[var(--ds-radius-lg)] border bg-[var(--ds-surface-1)] p-4 shadow-[var(--ds-shadow-lg)]",
              visibleAlert.direction.includes("BUY") 
                ? "border-nq-bull text-nq-bull" 
                : visibleAlert.direction.includes("SELL")
                ? "border-nq-bear text-nq-bear"
                : "border-[var(--ds-border-subtle)] text-[var(--ds-text-primary)]"
            )}
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-2">
                <BellRing className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <p className="text-sm font-semibold">{visibleAlert.symbol} - {visibleAlert.direction}</p>
                  <p className="mt-1 text-xs text-[var(--ds-text-secondary)]">{visibleAlert.message}</p>
                </div>
              </div>
              <button 
                onClick={() => setVisibleAlert(null)}
                className="shrink-0 text-[var(--ds-text-tertiary)] hover:text-[var(--ds-text-primary)]"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
