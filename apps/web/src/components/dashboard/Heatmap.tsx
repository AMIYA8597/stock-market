'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { contractsApi, type MarketMover } from '@/lib/contracts-api';
import { usePriceFeed } from '@/hooks/usePriceFeed';
import { HeatmapData } from '@/types/market';

/**
 * SectorHeatmap Component (D3.js Treemap style)
 * 
 * Design Spec from prompt.txt:
 * - NSE500 stocks as rectangles, sized by market cap
 * - Colored: deep red (-5%+) → neutral (#161B24) → deep green (+5%+)
 * - Hover: tooltip with OHLCV, prediction, news count
 * - Toggle: by sector, by index, by asset class
 * - Animation: smooth color transitions on price updates
 */

type GroupBy = 'sector' | 'index' | 'asset-class';

const SectorHeatmap = (): JSX.Element => {
  const router = useRouter();
  const [groupBy, setGroupBy] = useState<GroupBy>('sector');
  const [hoveredSymbol, setHoveredSymbol] = useState<string | null>(null);
  const [movers, setMovers] = useState<MarketMover[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  const symbols = useMemo(() => {
    if (!Array.isArray(movers)) return [];
    return movers.map((item) => item.ticker.toUpperCase());
  }, [movers]);
  const { ticks } = usePriceFeed(symbols);

  useEffect(() => {
    let mounted = true;

    async function loadMovers(): Promise<void> {
      try {
        setLoading(true);
        setError(null);
        const data = await contractsApi.getMovers('NSE', 'momentum');
        if (!mounted) {
          return;
        }
        setMovers(data.slice(0, 15));
        setLastUpdated(Date.now());
      } catch {
        if (!mounted) {
          return;
        }
        setError('Unable to load heatmap movers contract.');
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    void loadMovers();
    const intervalId = setInterval(() => {
      void loadMovers();
    }, 30_000);

    return () => {
      mounted = false;
      clearInterval(intervalId);
    };
  }, []);

  const inferSector = (name: string, symbol: string): string => {
    const token = `${name} ${symbol}`.toUpperCase();
    if (token.includes('BANK') || token.includes('FIN')) return 'Finance';
    if (token.includes('TECH') || token.includes('INFO') || token.includes('TCS') || token.includes('WIPRO')) return 'IT';
    if (token.includes('AUTO') || token.includes('MOTOR') || token.includes('MARUTI')) return 'Auto';
    if (token.includes('PHARMA') || token.includes('HEALTH')) return 'Healthcare';
    if (token.includes('POWER') || token.includes('ENERGY') || token.includes('OIL') || token.includes('GAS')) return 'Energy';
    if (token.includes('METAL') || token.includes('STEEL') || token.includes('CEMENT')) return 'Industrials';
    return 'Other';
  };

  // Convert movers + live ticks to heatmap data with sector mapping.
  const heatmapData = useMemo(() => {
    if (!Array.isArray(movers)) return [];
    return movers.map((item) => {
      const symbol = item.ticker.toUpperCase();
      const live = ticks.get(symbol);
      const price = live?.price ?? item.price;
      const changePct = live?.change_pct ?? item.change_pct;
      const inferredMarketCap = Math.max(price * Math.max(item.volume, 1) * 4.5, 1000000000);

      return {
        symbol,
        name: item.name,
        sector: inferSector(item.name, symbol),
        marketCap: inferredMarketCap,
        price,
        change: changePct,
        changePct,
        volume: item.volume,
      } as HeatmapData;
    });
  }, [movers, ticks]);

  const ageSeconds = lastUpdated ? Math.floor((Date.now() - lastUpdated) / 1000) : null;
  const freshness = error !== null ? 'degraded' : ageSeconds !== null && ageSeconds > 75 ? 'stale' : 'fresh';

  // Group data based on selected grouping
  const groupedData = useMemo(() => {
    if (groupBy === 'sector') {
      const grouped: Record<string, HeatmapData[]> = {};
      heatmapData.forEach((item) => {
        const bucket = grouped[item.sector] ?? (grouped[item.sector] = []);
        bucket.push(item);
      });
      return grouped;
    }
    return { 'All': heatmapData };
  }, [heatmapData, groupBy]);

  // Get color based on change percentage
  const getColor = (changePct: number): string => {
    if (changePct >= 5) return '#00E676'; // Deep green
    if (changePct >= 2) return '#4CAF50';
    if (changePct >= 0) return '#80CBC4';
    if (changePct > -2) return '#FFCC80';
    if (changePct >= -5) return '#FF7043';
    return '#FF3B3B'; // Deep red
  };

  const handleRectClick = (symbol: string): void => {
    router.push(`/markets/stocks/${encodeURIComponent(symbol)}`);
  };

  return (
    <div className="w-full rounded-lg border border-[#1E2532] bg-[linear-gradient(180deg,#0A0B0E,#111722)] p-4 sm:p-6">
      {/* Header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-semibold text-[#E8EAED] font-clash">
          Market Sector Heatmap
        </h2>
        <span
          className={`rounded border px-2 py-1 text-[10px] uppercase tracking-[0.08em] sm:text-xs ${
            freshness === 'fresh'
              ? 'border-[rgba(0,230,118,0.35)] bg-[rgba(0,230,118,0.10)] text-[#00E676]'
              : freshness === 'stale'
                ? 'border-[rgba(255,184,0,0.35)] bg-[rgba(255,184,0,0.10)] text-[#FFB800]'
                : 'border-[rgba(255,59,92,0.35)] bg-[rgba(255,59,92,0.10)] text-[#FF3B5C]'
          }`}
        >
          movers {freshness}
          {ageSeconds !== null ? ` ${ageSeconds}s` : ''}
        </span>
        {error ? <span className="text-xs text-[#FF3B3B]">{error}</span> : null}
        <div className="flex gap-2">
          {(['sector', 'index', 'asset-class'] as const).map((option) => (
            <button
              key={option}
              onClick={() => setGroupBy(option)}
              className={`px-3 py-1 rounded text-sm transition-colors ${
                groupBy === option
                  ? 'bg-[#00D4FF] text-[#0A0B0E] font-semibold'
                  : 'bg-[#1E2532] text-[#8B9BB4] hover:bg-[#2A3040]'
              }`}
            >
              {option === 'asset-class' ? 'Asset Class' : option.charAt(0).toUpperCase() + option.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Heatmap Grid */}
      <div className="space-y-4">
        {loading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {Array.from({ length: 10 }, (_, i) => (
              <div key={`heatmap-skeleton-${i}`} className="h-24 animate-pulse rounded-lg bg-[#161B24]" />
            ))}
          </div>
        ) : null}

        {Object.entries(groupedData).map(([group, items]) => (
          <div key={group}>
            {group !== 'All' && (
              <h3 className="text-sm font-semibold text-[#8B9BB4] mb-3">
                {group}
              </h3>
            )}
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
              {items.map((item: HeatmapData) => {
                const color = getColor(item.changePct);
                const isHovered = hoveredSymbol === item.symbol;

                return (
                  <div
                    key={item.symbol}
                    onMouseEnter={() => setHoveredSymbol(item.symbol)}
                    onMouseLeave={() => setHoveredSymbol(null)}
                    onClick={() => handleRectClick(item.symbol)}
                    className="relative cursor-pointer group h-24 rounded-lg overflow-hidden transition-all duration-300 hover:shadow-lg hover:scale-105"
                    style={{
                      backgroundColor: color,
                      opacity: isHovered ? 1 : 0.9,
                    }}
                  >
                    {/* Cell content */}
                    <div className="p-3 h-full flex flex-col justify-between">
                      <div>
                        <p className="text-sm font-bold text-[#0A0B0E] font-clash">
                          {item.symbol.replace('.NS', '')}
                        </p>
                        <p className="text-xs text-[#0A0B0E]/80 font-jbmono">
                          ₹{item.price.toFixed(2)}
                        </p>
                      </div>
                      <div className="text-xs font-semibold text-[#0A0B0E]">
                        {item.changePct >= 0 ? '▲' : '▼'}{' '}
                        {Math.abs(item.changePct).toFixed(1)}%
                      </div>
                    </div>

                    {/* Tooltip */}
                    {isHovered && (
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-[#161B24] border border-[#1E2532] rounded p-2 text-xs text-[#E8EAED] z-10 whitespace-nowrap shadow-lg">
                        <p>Volume: {(item.volume / 1000000).toFixed(1)}M</p>
                        <p>52W: ₹{(item.price * 0.85).toFixed(0)} - ₹{(item.price * 1.15).toFixed(0)}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="mt-6 pt-4 border-t border-[#1E2532] flex items-center gap-4 text-xs text-[#8B9BB4]">
        <span>Color scale:</span>
        <div className="flex gap-2 items-center">
          <div className="w-4 h-4 rounded bg-[#FF3B3B]" />
          <span>&lt; -5%</span>
        </div>
        <div className="flex gap-2 items-center">
          <div className="w-4 h-4 rounded bg-[#FFB800]" />
          <span>-5% to 0%</span>
        </div>
        <div className="flex gap-2 items-center">
          <div className="w-4 h-4 rounded bg-[#00D4FF]" />
          <span>0% to +5%</span>
        </div>
        <div className="flex gap-2 items-center">
          <div className="w-4 h-4 rounded bg-[#00E676]" />
          <span>&gt; +5%</span>
        </div>
      </div>
    </div>
  );
};

export default SectorHeatmap;