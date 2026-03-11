'use client';

import { useWebSocket } from '@/hooks/useWebSocket';
import { AlertEvent } from '@/types/market';

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
  const { alerts } = useWebSocket();

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

  const getAlertTypeIcon = (
    type: 'price' | 'technical' | 'ml' | 'sentiment' | 'anomaly' | 'news'
  ): string => {
    switch (type) {
      case 'price':
        return '💹';
      case 'technical':
        return '📊';
      case 'ml':
        return '🤖';
      case 'sentiment':
        return '😊';
      case 'anomaly':
        return '⚠️';
      case 'news':
        return '📰';
    }
  };

  const getTimeText = (timestamp: number): string => {
    const now = Date.now();
    const diffMs = now - timestamp;
    const diffSecs = Math.floor(diffMs / 1000);
    const diffMins = Math.floor(diffSecs / 60);
    const diffHours = Math.floor(diffMins / 60);

    if (diffSecs < 60) return `${diffSecs} seconds ago`;
    if (diffMins < 60) return `${diffMins} mins ago`;
    if (diffHours < 24) return `${diffHours} hours ago`;
    return 'Yesterday';
  };

  return (
    <div className="bg-[#161B24] border border-[#1E2532] rounded-lg p-6 flex flex-col">
      {/* Header */}
      <h3 className="text-lg font-semibold text-[#E8EAED] font-clash mb-4">
        Alert Feed
      </h3>

      {/* Scrollable alerts list */}
      <div className="flex-1 overflow-y-auto space-y-2 max-h-64">
        {alerts.length === 0 ? (
          <div className="flex items-center justify-center h-40 text-center">
            <p className="text-[#8B9BB4] text-sm">
              No alerts yet. Check back soon!
            </p>
          </div>
        ) : (
          alerts.slice(0, 10).map((alert: AlertEvent) => {
            const severityStyle = getSeverityColor(alert.severity);
            const alertIcon = getAlertTypeIcon(alert.type);

            return (
              <div
                key={alert.id}
                className="p-3 bg-[#0A0B0E] rounded border-l-4 hover:border-l-[#00D4FF] transition-all cursor-pointer group"
                style={{ borderLeftColor: severityStyle.bg }}
              >
                {/* Alert header */}
                <div className="flex items-start gap-3">
                  {/* Icon & Severity */}
                  <div className="flex-shrink-0 flex items-center gap-2">
                    <span className="text-base">{alertIcon}</span>
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
                      <span className="text-xs text-[#8B9BB4]">
                        {alert.type.replace('_', ' ').toUpperCase()}
                      </span>
                    </div>
                  </div>

                  {/* Time */}
                  <div className="flex-shrink-0 text-right">
                    <p className="text-xs text-[#8B9BB4]">
                      {getTimeText(alert.triggeredAt)}
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
