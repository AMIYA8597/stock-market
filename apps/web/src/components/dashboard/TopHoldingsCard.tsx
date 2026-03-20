'use client';

import { useEffect, useMemo, useState } from 'react';
import { contractsApi, type PortfolioHolding } from '@/lib/contracts-api';
import { usePriceFeed } from '@/hooks/usePriceFeed';

interface HoldingView {
  symbol: string;
  quantity: number;
  avgCost: number;
  currentPrice: number;
  pnl: number;
  pnlPct: number;
}

const TopHoldingsCard = (): JSX.Element => {
  const [holdings, setHoldings] = useState<PortfolioHolding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const symbols = useMemo(() => holdings.map((h) => h.symbol.toUpperCase()), [holdings]);
  const { ticks } = usePriceFeed(symbols);

  useEffect(() => {
    let mounted = true;

    async function loadHoldings(): Promise<void> {
      try {
        setLoading(true);
        setError(null);
        const response = await contractsApi.getPortfolioHoldings();
        if (!mounted) {
          return;
        }
        setHoldings(response.holdings);
      } catch (fetchError) {
        if (!mounted) {
          return;
        }
        const message = fetchError instanceof Error ? fetchError.message : 'Failed to load holdings';
        setError(message);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void loadHoldings();
    return () => {
      mounted = false;
    };
  }, []);

  const normalized = useMemo<HoldingView[]>(() => {
    return holdings.map((holding) => {
      const live = ticks.get(holding.symbol.toUpperCase());
      const currentPrice = live?.price ?? holding.ltp;
      const invested = holding.quantity * holding.avg_buy_price;
      const currentValue = holding.quantity * currentPrice;
      const pnl = currentValue - invested;
      const pnlPct = invested > 0 ? (pnl / invested) * 100 : 0;

      return {
        symbol: holding.symbol,
        quantity: holding.quantity,
        avgCost: holding.avg_buy_price,
        currentPrice,
        pnl,
        pnlPct,
      };
    });
  }, [holdings, ticks]);

  const totalValue = normalized.reduce((sum, h) => sum + h.quantity * h.currentPrice, 0);
  const totalPnL = normalized.reduce((sum, h) => sum + h.pnl, 0);

  return (
    <div className="rounded-lg border border-[#1E2532] bg-[#161B24] p-4 sm:p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 sm:mb-6">
        <h3 className="font-clash text-base font-semibold text-[#E8EAED] sm:text-lg">Top Holdings</h3>
        <div className="text-right">
          <p className="text-xs text-[#8B9BB4]">Portfolio Value</p>
          <p className="font-jbmono text-base font-bold text-[#00D4FF] sm:text-lg">
            ₹{totalValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
          </p>
        </div>
      </div>

      {error ? <p className="mb-3 text-xs text-[#FF3B3B]">{error}</p> : null}

      <div className="space-y-2.5 sm:space-y-3">
        {(loading ? [] : normalized.slice(0, 5)).map((holding) => {
          const isProfit = holding.pnlPct >= 0;
          const pnlColor = isProfit ? '#00E676' : '#FF3B3B';

          return (
            <div
              key={holding.symbol}
              className="flex items-center gap-3 rounded-lg bg-[#0A0B0E] p-3 transition-all hover:border-l-2 hover:border-[#00D4FF]"
            >
              <div className="min-w-fit">
                <p className="font-clash text-sm font-bold text-[#E8EAED]">{holding.symbol}</p>
                <p className="text-xs text-[#8B9BB4]">{holding.quantity} shares</p>
              </div>

              <div className="flex-1">
                <p className="font-jbmono text-sm text-[#00D4FF]">₹{holding.currentPrice.toFixed(2)}</p>
                <p className="text-xs text-[#8B9BB4]">Avg: ₹{holding.avgCost.toFixed(2)}</p>
              </div>

              <div className="text-right">
                <p className="font-jbmono text-sm font-bold" style={{ color: pnlColor }}>
                  {isProfit ? '+' : ''}
                  ₹{holding.pnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                </p>
                <p className="text-xs font-semibold" style={{ color: pnlColor }}>
                  {isProfit ? '▲' : '▼'} {Math.abs(holding.pnlPct).toFixed(2)}%
                </p>
              </div>
            </div>
          );
        })}

        {loading
          ? Array.from({ length: 3 }, (_, i) => (
              <div key={`holding-skeleton-${i}`} className="h-16 animate-pulse rounded-lg bg-[#0A0B0E]" />
            ))
          : null}
      </div>

      <div className="mt-4 flex items-center justify-between border-t border-[#1E2532] pt-4 sm:mt-6">
        <p className="text-xs text-[#8B9BB4]">Total P&L</p>
        <p className="font-jbmono text-base font-bold sm:text-lg" style={{ color: totalPnL >= 0 ? '#00E676' : '#FF3B3B' }}>
          {totalPnL >= 0 ? '+' : ''}
          ₹{totalPnL.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
        </p>
      </div>
    </div>
  );
};

export default TopHoldingsCard;
