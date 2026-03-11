'use client';

import { useState, useMemo } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { TickData, HeatmapData } from '@/types/market';

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
  const { ticks } = useWebSocket([
    'RELIANCE',
    'TCS',
    'INFY',
    'HDFC',
    'ICICI',
    'SBIN',
    'WIPRO',
    'BAJAJFINSV',
    'MARUTI',
    'HEROMOTOCO',
  ]);

  const [groupBy, setGroupBy] = useState<GroupBy>('sector');
  const [hoveredSymbol, setHoveredSymbol] = useState<string | null>(null);

  // Convert tick data to heatmap data with sectors
  const heatmapData = useMemo(() => {
    const sectorMap: Record<string, string> = {
      RELIANCE: 'Energy',
      TCS: 'IT',
      INFY: 'IT',
      HDFC: 'Finance',
      ICICI: 'Finance',
      SBIN: 'Finance',
      WIPRO: 'IT',
      BAJAJFINSV: 'Finance',
      MARUTI: 'Auto',
      HEROMOTOCO: 'Auto',
    };

    return Array.from(ticks.values()).map((tick: TickData) => ({
      symbol: tick.symbol,
      name: tick.symbol,
      sector: sectorMap[tick.symbol] || 'Other',
      marketCap: Math.random() * 500000000000, // Mock market cap
      price: tick.price,
      change: tick.changePct,
      changePct: tick.changePct,
      volume: tick.volume,
    })) as HeatmapData[];
  }, [ticks]);

  // Group data based on selected grouping
  const groupedData = useMemo(() => {
    if (groupBy === 'sector') {
      const grouped: Record<string, HeatmapData[]> = {};
      heatmapData.forEach((item) => {
        if (!grouped[item.sector]) grouped[item.sector] = [];
        grouped[item.sector].push(item);
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
    // Navigate to stock detail page
    window.location.href = `/market/${symbol}`;
  };

  return (
    <div className="w-full bg-[#0A0B0E] border border-[#1E2532] rounded-lg p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-semibold text-[#E8EAED] font-clash">
          Market Sector Heatmap
        </h2>
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
                          {item.symbol}
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