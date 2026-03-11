'use client';

import { useWebSocket } from '@/hooks/useWebSocket';
import { TickData } from '@/types/market';

/**
 * TopHoldingsCard Component
 * 
 * Shows portfolio top 5 positions with:
 * - Symbol name
 * - Current price (live WebSocket)
 * - P&L with color coding
 * - Percentage change
 * - Sparkline chart per holding
 */

interface Holding {
  symbol: string;
  quantity: number;
  avgCost: number;
  currentPrice: number;
  pnl: number;
  pnlPct: number;
}

const TopHoldingsCard = (): JSX.Element => {
  const { ticks } = useWebSocket([
    'RELIANCE',
    'TCS',
    'INFY',
    'HDFC',
    'ICICI',
  ]);

  // Mock portfolio holdings
  const mockHoldings: Holding[] = [
    { symbol: 'RELIANCE', quantity: 10, avgCost: 2400, currentPrice: 2650, pnl: 2500, pnlPct: 10.4 },
    { symbol: 'TCS', quantity: 5, avgCost: 3200, currentPrice: 3580, pnl: 1900, pnlPct: 11.9 },
    { symbol: 'INFY', quantity: 20, avgCost: 1600, currentPrice: 1850, pnl: 5000, pnlPct: 15.6 },
    { symbol: 'HDFC', quantity: 8, avgCost: 2800, currentPrice: 2950, pnl: 1200, pnlPct: 5.4 },
    { symbol: 'ICICI', quantity: 12, avgCost: 1100, currentPrice: 1280, pnl: 2160, pnlPct: 16.4 },
  ];

  // Update prices from WebSocket
  const holdings = mockHoldings.map((h) => {
    const tickData = ticks.get(h.symbol);
    if (tickData) {
      return {
        ...h,
        currentPrice: tickData.price,
        pnlPct: tickData.changePct,
      };
    }
    return h;
  });

  const totalValue = holdings.reduce((sum, h) => sum + h.quantity * h.currentPrice, 0);
  const totalPnL = holdings.reduce((sum, h) => sum + h.pnl, 0);

  return (
    <div className="bg-[#161B24] border border-[#1E2532] rounded-lg p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-semibold text-[#E8EAED] font-clash">
          Top Holdings
        </h3>
        <div className="text-right">
          <p className="text-xs text-[#8B9BB4]">Portfolio Value</p>
          <p className="text-lg font-bold text-[#00D4FF] font-jbmono">
            ₹{totalValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
        </div>
      </div>

      {/* Holdings Table */}
      <div className="space-y-3">
        {holdings.slice(0, 5).map((holding) => {
          const isProfit = holding.pnlPct >= 0;
          const pnlColor = isProfit ? '#00E676' : '#FF3B3B';

          return (
            <div
              key={holding.symbol}
              className="flex items-center gap-4 p-3 bg-[#0A0B0E] rounded-lg hover:border-l-2 hover:border-[#00D4FF] transition-all cursor-pointer"
            >
              {/* Symbol */}
              <div className="min-w-fit">
                <p className="text-sm font-bold text-[#E8EAED] font-clash">
                  {holding.symbol}
                </p>
                <p className="text-xs text-[#8B9BB4]">
                  {holding.quantity} shares
                </p>
              </div>

              {/* Price & Change */}
              <div className="flex-1">
                <p className="text-sm font-jbmono text-[#00D4FF]">
                  ₹{holding.currentPrice.toFixed(2)}
                </p>
                <p className="text-xs text-[#8B9BB4]">
                  Avg: ₹{holding.avgCost.toFixed(2)}
                </p>
              </div>

              {/* P&L */}
              <div className="text-right">
                <p
                  className="text-sm font-bold font-jbmono"
                  style={{ color: pnlColor }}
                >
                  {isProfit ? '+' : ''}
                  ₹{holding.pnl.toLocaleString('en-IN', {
                    maximumFractionDigits: 0,
                  })}
                </p>
                <p
                  className="text-xs font-semibold"
                  style={{ color: pnlColor }}
                >
                  {isProfit ? '▲' : '▼'}{' '}
                  {Math.abs(holding.pnlPct).toFixed(2)}%
                </p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      <div className="mt-6 pt-4 border-t border-[#1E2532] flex justify-between items-center">
        <p className="text-xs text-[#8B9BB4]">Total P&L</p>
        <p
          className="text-lg font-bold font-jbmono"
          style={{ color: totalPnL >= 0 ? '#00E676' : '#FF3B3B' }}
        >
          {totalPnL >= 0 ? '+' : ''}
          ₹{totalPnL.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
        </p>
      </div>
    </div>
  );
};

export default TopHoldingsCard;
