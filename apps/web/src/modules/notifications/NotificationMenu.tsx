"use client";

import { Bell, CheckCheck, Clock3 } from 'lucide-react';
import { Badge } from '@/components/ui/Badge';
import { Dropdown, DropdownContent, DropdownItem, DropdownLabel, DropdownSeparator, DropdownTrigger } from '@/components/ui/Dropdown';

const notifications = [
  { id: 1, title: 'AAPL crossed target zone', tone: 'buy', time: '2m' },
  { id: 2, title: 'Model drift warning on momentum-v4', tone: 'neutral', time: '11m' },
  { id: 3, title: 'Order partially filled: RELIANCE', tone: 'default', time: '24m' },
  { id: 4, title: 'Weekly portfolio digest is ready', tone: 'secondary', time: '1h' },
] as const;

export function NotificationMenu(): JSX.Element {
  return (
    <Dropdown>
      <DropdownTrigger asChild>
        <button className="relative rounded-[var(--ds-radius-lg)] p-2 text-[var(--ds-text-secondary)] transition hover:bg-[var(--ds-surface-2)] hover:text-[var(--ds-text-primary)]">
          <Bell className="h-4.5 w-4.5" />
          <span className="absolute -right-0.5 -top-0.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--ds-color-danger-500)] px-1 text-[10px] font-semibold text-white">
            {notifications.length}
          </span>
        </button>
      </DropdownTrigger>
      <DropdownContent align="end" className="w-[320px]">
        <div className="flex items-center justify-between px-3 py-2">
          <DropdownLabel className="p-0 text-[10px]">Notifications</DropdownLabel>
          <button className="inline-flex items-center gap-1 rounded-[var(--ds-radius-lg)] px-2 py-1 text-[11px] text-[var(--ds-text-secondary)] transition hover:bg-[var(--ds-surface-3)] hover:text-[var(--ds-text-primary)]">
            <CheckCheck className="h-3.5 w-3.5" />
            Mark all read
          </button>
        </div>
        <DropdownSeparator />
        <div className="max-h-80 overflow-auto">
          {notifications.map((item) => (
            <DropdownItem key={item.id} className="items-start gap-2">
              <Clock3 className="mt-0.5 h-3.5 w-3.5 text-[var(--ds-text-muted)]" />
              <div className="flex-1">
                <p className="text-xs text-[var(--ds-text-primary)]">{item.title}</p>
                <div className="mt-1 flex items-center gap-2">
                  <Badge variant={item.tone} className="text-[9px]">live</Badge>
                  <span className="text-[10px] text-[var(--ds-text-muted)]">{item.time} ago</span>
                </div>
              </div>
            </DropdownItem>
          ))}
        </div>
      </DropdownContent>
    </Dropdown>
  );
}
