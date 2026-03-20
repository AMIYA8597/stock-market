'use client';

import { useEffect, useMemo, useState } from 'react';
import { contractsApi, type MarketIndex } from '@/lib/contracts-api';
import { marketApi } from '@/lib/api-client';
import { usePriceFeed } from '@/hooks/usePriceFeed';

interface TickerItem {
  label: string;
  symbol: string;
  price: number;
  changePct: number;
}

const TickerStrip = (): JSX.Element => {
  const [indices, setIndices] = useState<MarketIndex[]>([]);
  const [tickers, setTickers] = useState<TickerItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [sparklineMap, setSparklineMap] = useState<Record<string, number[]>>({});
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  const symbols = useMemo(() => {
    return indices.map((item) => item.ticker.toUpperCase());
  }, [indices]);

  const { ticks, status } = usePriceFeed(symbols);

  useEffect(() => {
    let mounted = true;

    async function loadIndices(): Promise<void> {
      try {
        setLoading(true);
        setError(null);
        const data = await contractsApi.getIndices();
        if (!mounted) {
          return;
        }
        setIndices(data);
        setTickers(
          data.map((item) => ({
            label: item.name,
            symbol: item.ticker,
            price: item.value,
            changePct: item.change_pct,
          }))
        );
        setLastUpdated(Date.now());
      } catch {
        if (!mounted) {
          return;
        }
        setError('Unable to load market index contracts.');
        setTickers([]);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void loadIndices();
    const intervalId = setInterval(() => {
      void loadIndices();
    }, 30_000);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, []);

  useEffect(() => {
    let mounted = true;

    async function loadSparklines(): Promise<void> {
      try {
        const responses = await Promise.all(
          tickers.map(async (item) => {
            try {
              const history = await marketApi.getHistory(item.symbol, '1D');
              return [item.symbol, history.bars.slice(-20).map((bar) => bar.close)] as const;
            } catch {
              return [item.symbol, []] as const;
            }
          })
        );

        if (!mounted) {
          return;
        }

        const nextMap: Record<string, number[]> = {};
        for (const [symbol, series] of responses) {
          nextMap[symbol] = Array.from(series);
        }
        setSparklineMap(nextMap);
      } catch {
        if (mounted) {
          setSparklineMap({});
        }
      }
    }

    void loadSparklines();
    const sparklineIntervalId = setInterval(() => {
      void loadSparklines();
    }, 120_000);

    return () => {
      mounted = false;
      clearInterval(sparklineIntervalId);
    };
  }, [tickers]);

  const contractAgeSeconds = lastUpdated ? Math.floor((Date.now() - lastUpdated) / 1000) : null;
  const contractState =
    error !== null ? 'degraded' : contractAgeSeconds !== null && contractAgeSeconds > 75 ? 'stale' : 'fresh';

  const renderSparkline = (data: number[]): JSX.Element => {
    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    const points = data
      .map((value, index) => {
        const x = (index / (data.length - 1)) * 60;
        const y = 12 - ((value - min) / range) * 12;
        return `${x.toFixed(2)},${y.toFixed(2)}`;
      })
      .join(' ');

    const first = data[0] ?? 0;
    const last = data.length > 0 ? (data[data.length - 1] ?? first) : first;
    const isPositive = last >= first;

    return (
      <svg className="h-6 w-16" viewBox="0 0 60 12" preserveAspectRatio="none">
        <polyline points={points} fill="none" stroke={isPositive ? '#00E676' : '#FF3B3B'} strokeWidth="0.5" />
      </svg>
    );
  };

  const formatPrice = (symbol: string, price: number): string => {
    const fractionDigits = symbol.includes('INR') || symbol.includes('USD') ? 4 : 2;
    return price.toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: fractionDigits,
    });
  };

  const mergedTickers = useMemo(() => {
    return tickers.map((item) => {
      const live = ticks.get(item.symbol.toUpperCase());
      return {
        ...item,
        price: live?.price ?? item.price,
        changePct: live?.change_pct ?? item.changePct,
      };
    });
  }, [tickers, ticks]);

  return (
    <div className="w-full border-b border-[#1E2532] bg-[linear-gradient(90deg,rgba(10,11,14,0.98),rgba(8,18,28,0.92),rgba(10,11,14,0.98))]">
      <div className="flex items-center justify-between px-3 py-2 text-[10px] text-[#8B9BB4] sm:px-4 sm:text-xs">
        <div className="flex items-center gap-2">
          <div className={`h-2 w-2 rounded-full ${status === 'connected' ? 'bg-[#00E676]' : status === 'reconnecting' ? 'bg-[#FFB800]' : 'bg-[#FF3B3B]'}`} />
          <span>{status === 'connected' ? 'Live' : status === 'reconnecting' ? 'Syncing...' : 'Disconnected'}</span>
        </div>
        <span
          className={`rounded border px-2 py-0.5 uppercase tracking-[0.08em] ${
            contractState === 'fresh'
              ? 'border-[rgba(0,230,118,0.35)] bg-[rgba(0,230,118,0.10)] text-[#00E676]'
              : contractState === 'stale'
                ? 'border-[rgba(255,184,0,0.35)] bg-[rgba(255,184,0,0.10)] text-[#FFB800]'
                : 'border-[rgba(255,59,92,0.35)] bg-[rgba(255,59,92,0.10)] text-[#FF3B5C]'
          }`}
        >
          contracts {contractState}
          {contractAgeSeconds !== null ? ` ${contractAgeSeconds}s` : ''}
        </span>
        {error ? <span className="text-[#FF3B3B]">{error}</span> : null}
      </div>

      <div className="overflow-x-auto scrollbar-hide">
        <div className="flex min-w-max gap-4 px-3 py-2.5 sm:gap-6 sm:px-4 sm:py-3">
          {mergedTickers.length > 0 ? (
            mergedTickers.map((ticker) => {
              const series = sparklineMap[ticker.symbol];
              const hasSparkline = Boolean(series && series.length > 1);
              return (
                <div key={ticker.symbol} className="group flex min-w-max cursor-pointer flex-col gap-1 transition-opacity hover:opacity-80">
                  <div className="font-clash text-[11px] font-semibold text-[#E8EAED] sm:text-sm">{ticker.label}</div>

                  <div className="flex items-center gap-2 font-jbmono">
                    <span className="text-sm text-[#00D4FF] sm:text-base">INR {formatPrice(ticker.symbol, ticker.price)}</span>
                    <div
                      className={`flex items-center gap-1 text-xs font-semibold sm:text-sm ${
                        ticker.changePct >= 0 ? 'text-[#00E676]' : 'text-[#FF3B3B]'
                      }`}
                    >
                      <span>{ticker.changePct >= 0 ? '+' : '-'}</span>
                      <span>{Math.abs(ticker.changePct).toFixed(2)}%</span>
                    </div>
                  </div>

                  <div className="opacity-70 transition-opacity group-hover:opacity-100">
                    {hasSparkline ? renderSparkline(series ?? []) : <div className="h-6 w-16 rounded bg-[rgba(255,255,255,0.08)]" />}
                  </div>
                </div>
              );
            })
          ) : (
            <div className="py-4 text-sm text-[#8B9BB4]">{loading ? 'Loading market data...' : 'No market symbols available.'}</div>
          )}
        </div>
      </div>

      <style jsx>{`
        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  );
};

export default TickerStrip;
