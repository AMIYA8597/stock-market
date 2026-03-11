'use client';

import { StatCardData } from '@/types/market';

/**
 * StatCard Component
 * 
 * Reusable card for displaying key metrics:
 * - Portfolio P&L Today | Active Signals | Model Accuracy (30d) | Alerts
 */

interface StatCardProps {
  data: StatCardData;
}

const StatCard = ({ data }: StatCardProps): JSX.Element => {
  const trendColor =
    data.trend === 'up'
      ? '#00E676'
      : data.trend === 'down'
        ? '#FF3B3B'
        : '#8B9BB4';

  const trendIcon =
    data.trend === 'up' ? '▲' : data.trend === 'down' ? '▼' : '→';

  return (
    <div className="bg-[#161B24] border border-[#1E2532] rounded-lg p-6 hover:border-[#00D4FF] transition-all duration-300">
      {/* Label */}
      <p className="text-xs font-semibold text-[#8B9BB4] uppercase mb-3">
        {data.label}
      </p>

      {/* Value */}
      <p className="text-2xl md:text-3xl font-bold text-[#E8EAED] font-jbmono mb-4">
        {typeof data.value === 'number'
          ? data.value.toLocaleString('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          })
          : data.value}
      </p>

      {/* Change indicator */}
      {data.changePct !== undefined && (
        <div className="flex items-center gap-2 text-sm font-semibold" style={{ color: trendColor }}>
          <span>{trendIcon}</span>
          <span>
            {data.changePct > 0 ? '+' : ''}
            {data.changePct.toFixed(2)}%
          </span>
          <span className="text-xs text-[#8B9BB4]">vs yesterday</span>
        </div>
      )}

      {/* Icon */}
      {data.icon && (
        <div className="absolute top-4 right-4 text-2xl opacity-20">
          {data.icon}
        </div>
      )}
    </div>
  );
};

export default StatCard;
