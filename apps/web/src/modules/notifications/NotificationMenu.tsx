"use client";

import { Bell, CheckCheck, Clock3 } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Dropdown, DropdownContent, DropdownItem, DropdownLabel, DropdownSeparator, DropdownTrigger } from '@/components/ui/Dropdown';
import { useSignalAlerts } from '@/hooks/useSignalAlerts';
import { safeFormat } from '@/lib/formatters';

export function NotificationMenu(): JSX.Element {
  const { alerts, unread, markAllRead } = useSignalAlerts();

  // Helper to format time ago
  const formatTimeAgo = (timestampStr: string) => {
    try {
      const diffMs = Date.now() - new Date(timestampStr).getTime();
      const diffMin = Math.max(0, Math.floor(diffMs / 60000));
      if (diffMin < 1) return 'Just now';
      if (diffMin < 60) return `${diffMin}m`;
      const diffHr = Math.floor(diffMin / 60);
      if (diffHr < 24) return `${diffHr}h`;
      return `${Math.floor(diffHr / 24)}d`;
    } catch {
      return '';
    }
  };

  return (
    <Dropdown>
      <DropdownTrigger asChild>
        <button className="relative rounded-[var(--ds-radius-lg)] p-2 text-[var(--ds-text-secondary)] transition hover:bg-[var(--ds-surface-2)] hover:text-[var(--ds-text-primary)]">
          <Bell className="h-4.5 w-4.5" />
          {unread > 0 && (
            <span className="absolute -right-0.5 -top-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--ds-color-danger-500)] px-1 text-[10px] font-semibold text-white">
              {unread}
            </span>
          )}
        </button>
      </DropdownTrigger>
      <DropdownContent align="end" className="w-[340px]">
        <div className="flex items-center justify-between px-3 py-2">
          <DropdownLabel className="p-0 text-[10px]">Notifications</DropdownLabel>
          {unread > 0 && (
            <button
              onClick={markAllRead}
              className="inline-flex items-center gap-1 rounded-[var(--ds-radius-lg)] px-2 py-1 text-[11px] text-[var(--ds-text-secondary)] transition hover:bg-[var(--ds-surface-3)] hover:text-[var(--ds-text-primary)]"
            >
              <CheckCheck className="h-3.5 w-3.5" />
              Mark all read
            </button>
          )}
        </div>
        <DropdownSeparator />
        <div className="max-h-80 overflow-auto ds-scrollable">
          {alerts.map((item, idx) => {
            const key = `${item.symbol}-${item.timestamp}-${idx}`;
            const isBuy = item.direction.includes("BUY");
            const badgeVariant = isBuy ? "buy" : "sell";
            const timeAgo = formatTimeAgo(item.timestamp);
            const formattedPrice = item.current_price.toLocaleString("en-IN", {
              minimumFractionDigits: 2,
              maximumFractionDigits: 2,
            });
            const formattedConf = safeFormat(item.confidence * 100, 1) + "%";
            const patternsStr = item.patterns_detected && item.patterns_detected.length > 0
              ? item.patterns_detected.slice(0, 2).map(p => p.replace("CDL_", "").replace(/_/g, " ")).join(", ")
              : "-";

            return (
              <DropdownItem
                key={key}
                className="items-start gap-2 p-3 bg-[rgba(0,212,245,0.01)]"
              >
                <Clock3 className="mt-0.5 h-3.5 w-3.5 text-[var(--ds-text-muted)] shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-1">
                    <p className="text-xs font-semibold text-[var(--ds-text-primary)]">
                      {item.symbol}
                    </p>
                    <span className="text-[10px] text-[var(--ds-text-muted)] shrink-0">{timeAgo} ago</span>
                  </div>
                  <p className="text-[11px] text-[var(--ds-text-secondary)] mt-0.5 line-clamp-2">
                    {item.message}
                  </p>
                  
                  <div className="mt-1 flex flex-wrap gap-1">
                    <span className="text-[8px] text-[var(--nq-text-muted)] font-mono uppercase bg-[rgba(255,255,255,0.04)] px-1 rounded">
                      Patterns: {patternsStr}
                    </span>
                  </div>

                  <div className="mt-1.5 flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                      <Badge variant={badgeVariant} className="text-[9px] px-1.5 py-0">
                        {item.direction.replace("_", " ")}
                      </Badge>
                      <span className="text-[10px] font-mono text-[var(--ds-text-muted)]">
                        {formattedConf} conf
                      </span>
                    </div>
                    <span className="text-[10px] font-semibold text-[var(--ds-text-primary)]">
                      ₹{formattedPrice}
                    </span>
                  </div>
                </div>
              </DropdownItem>
            );
          })}
          {alerts.length === 0 && (
            <div className="py-6 text-center text-xs text-[var(--ds-text-muted)] italic">
              No live buy/sell alerts yet.
            </div>
          )}
        </div>
      </DropdownContent>
    </Dropdown>
  );
}
