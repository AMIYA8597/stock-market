'use client';

import { useEffect, useState } from 'react';
import { alertsApi } from '@/lib/api-client';
import type { AlertEvent } from '@neuroquant/types';

/**
 * AlertsFeed Component
 * 
 * Real-time WebSocket alert stream with:
 * - Severity color-coding (1-5)
 * - Time-relative display
 * - Scrollable list
 * - Alert type badges
 */

const AlertsFeed = (): JSX.Element => {
  const [alerts, setAlerts] = useState<AlertEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load(): Promise<void> {
      try {
        setLoading(true);
        setError(null);
        const data = await alertsApi.getHistory(20);
        if (!mounted) {
          return;
        }
        setAlerts(data);
        setLastUpdated(Date.now());
      } catch (fetchError) {
        if (!mounted) {
          return;
        }
        const message = fetchError instanceof Error ? fetchError.message : 'Unable to load alert history.';
        setError(message);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void load();
    const intervalId = setInterval(() => {
      void load();
    }, 15_000);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, []);

  const ageSeconds = lastUpdated ? Math.floor((Date.now() - lastUpdated) / 1000) : null;
  const freshness = error !== null ? 'degraded' : ageSeconds !== null && ageSeconds > 40 ? 'stale' : 'fresh';

  const getSeverityColor = (
    severity: 1 | 2 | 3 | 4 | 5
  ): { bg: string; text: string; label: string } => {
    switch (severity) {
      case 5:
        return { bg: '#FF3B3B', text: '#FFFFFF', label: 'Critical' };
      case 4:
        return { bg: '#FF7043', text: '#FFFFFF', label: 'High' };
      case 3:
        return { bg: '#FFB800', text: '#0A0B0E', label: 'Medium' };
      case 2:
        return { bg: '#80CBC4', text: '#0A0B0E', label: 'Low' };
      case 1:
        return { bg: '#00D4FF', text: '#0A0B0E', label: 'Info' };
    }
  };

  const getAlertTypeLabel = (
    type: 'price' | 'technical' | 'ml_signal' | 'sentiment' | 'anomaly' | 'news'
  ): string => {
    switch (type) {
      case 'price':
        return 'PRICE';
      case 'technical':
        return 'TECH';
      case 'ml_signal':
        return 'ML';
      case 'sentiment':
        return 'SENT';
      case 'anomaly':
        return 'ANOM';
      case 'news':
        return 'NEWS';
    }
  };

  const getTimeText = (timestamp: string): string => {
    const timestampMs = new Date(timestamp).getTime();
    const now = Date.now();
    const diffMs = now - timestampMs;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);

    if (diffSecs < 60) return `${diffSecs} seconds ago`;
    if (diffMins < 60) return `${diffMins} mins ago`;
    if (diffHours < 24) return `${diffHours} hours ago`;
    return 'Yesterday';
  };

  return (
    <div className="rounded-lg border border-[#1E2532] bg-[linear-gradient(180deg,#161B24,#111722)] p-4 sm:p-6 flex flex-col">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between gap-2">
        <h3 className="text-lg font-semibold text-[#E8EAED] font-clash">Alert Feed</h3>
        <span
          className={`rounded border px-2 py-0.5 text-[10px] uppercase tracking-[0.08em] sm:text-xs ${
            freshness === 'fresh'
              ? 'border-[rgba(0,230,118,0.35)] bg-[rgba(0,230,118,0.10)] text-[#00E676]'
              : freshness === 'stale'
                ? 'border-[rgba(255,184,0,0.35)] bg-[rgba(255,184,0,0.10)] text-[#FFB800]'
                : 'border-[rgba(255,59,92,0.35)] bg-[rgba(255,59,92,0.10)] text-[#FF3B5C]'
          }`}
        >
          {freshness}
          {ageSeconds !== null ? ` ${ageSeconds}s` : ''}
        </span>
        {error ? <span className="text-xs text-[#FF3B3B]">{error}</span> : null}
      </div>

      {/* Scrollable alerts list */}
      <div className="flex-1 overflow-y-auto space-y-2 max-h-64">
        {loading ? (
          Array.from({ length: 4 }, (_, i) => (
            <div key={`alert-skeleton-${i}`} className="h-14 animate-pulse rounded bg-[#0A0B0E]" />
          ))
        ) : alerts.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-center">
            <p className="text-[#8B9BB4] text-sm">
              No alerts yet. Check back soon!
            </p>
          </div>
        ) : (
          alerts.slice(0, 10).map((alert: AlertEvent) => {
            const severityStyle = getSeverityColor(alert.severity);
            const alertLabel = getAlertTypeLabel(alert.alert_type);

            return (
              <div
                key={alert.id}
                className="p-3 bg-[#0A0B0E] rounded border-l-4 hover:border-l-[#00D4FF] transition-all cursor-pointer group"
                style={{ borderLeftColor: severityStyle.bg }}
              >
                {/* Alert header */}
                <div className="flex items-start gap-3">
                  {/* Type & Severity */}
                  <div className="flex-shrink-0 flex items-center gap-2">
                    <span className="rounded border border-[#2A3345] px-1.5 py-0.5 text-[10px] font-semibold text-[#8B9BB4]">{alertLabel}</span>
                    <span
                      className="text-xs font-semibold px-2 py-1 rounded"
                      style={{
                        backgroundColor: severityStyle.bg,
                        color: severityStyle.text,
                      }}
                    >
                      {severityStyle.label}
                    </span>
                  </div>

                  {/* Message & Symbol */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-[#E8EAED] truncate">
                      {alert.message}
                    </p>
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-xs font-bold bg-[#1E2532] px-2 py-0.5 rounded text-[#00D4FF] font-clash">
                        {alert.symbol}
                      </span>
                      <span className="text-xs text-[#8B9BB4]">{alert.alert_name}</span>
                    </div>
                  </div>

                  {/* Time */}
                  <div className="flex-shrink-0 text-right">
                    <p className="text-xs text-[#8B9BB4]">
                      {getTimeText(alert.triggered_at)}
                    </p>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer */}
      {alerts.length > 10 && (
        <div className="mt-3 pt-3 border-t border-[#1E2532]">
          <button className="w-full py-2 text-center text-xs font-semibold text-[#00D4FF] hover:text-[#00E676] transition-colors">
            View all {alerts.length} alerts →
          </button>
        </div>
      )}
    </div>
  );
};

export default AlertsFeed;
