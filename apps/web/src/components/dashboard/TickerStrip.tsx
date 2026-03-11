'use client';

import { useWebSocket } from '@/hooks/useWebSocket';
import { TickData } from '@/types/market';

/**
 * TickerStrip Component
 * 
 * Design Spec from prompt.txt:
 * - WebSocket live price strip: Nifty50 | Sensex | S&P500 | NASDAQ | Gold | BTC | USD/INR
 * - Smooth horizontal scroll animation
 * - Color-coded +/- with sparkline mini-chart (SVG, 20-bar)
 * - Fonts: JetBrains Mono for prices, Clash Display for symbols
 * - Colors: Bull #00E676, Bear #FF3B3B, Primary #00D4FF
 */

const TickerStrip = (): JSX.Element => {
  const { ticks, connectionStatus } = useWebSocket([
    'NIFTY50',
    'SENSEX',
    'S&P500',
    'NASDAQ100',
    'GOLD',
    'BTC-USD',
    'USDINR',
  ]);

  const mockSparklineData = (symbol: string): number[] => {
    // Generate deterministic mock sparkline based on symbol
    // In production, this would come from WebSocket or API
    const seed = symbol.charCodeAt(0);
    return Array.from({ length: 20 }, (_, i) => {
      return 50 + (Math.sin((i + seed) * 0.5) * 30);
    });
  };

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

    const isPositive = data[data.length - 1] > data[0];

    return (
      <svg className="w-16 h-6" viewBox="0 0 60 12" preserveAspectRatio="none">
        <polyline
          points={points}
          fill="none"
          stroke={isPositive ? '#00E676' : '#FF3B3B'}
          strokeWidth="0.5"
        />
      </svg>
    );
  };

  const formatPrice = (price: number): string => {
    // Preserve trailing zeros and format with commas
    return price.toLocaleString('en-IN', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 4,
    });
  };

  const selectedTickers = Array.from(ticks.values()).slice(0, 7);

  return (
    <div className="w-full bg-[#0A0B0E] border-b border-[#1E2532]">
      {/* Status indicator */}
      <div className="flex items-center justify-between px-4 py-2 text-xs text-[#8B9BB4]">
        <div className="flex items-center gap-2">
          <div
            className={`w-2 h-2 rounded-full ${
              connectionStatus === 'connected' ? 'bg-[#00E676]' : 'bg-[#FF3B3B]'
            }`}
          />
          <span>
            {connectionStatus === 'connected' ? 'Live' : 'Reconnecting...'}
          </span>
        </div>
      </div>

      {/* Ticker scroll */}
      <div className="overflow-x-auto scrollbar-hide">
        <div className="flex gap-6 px-4 py-3 min-w-max animate-scroll">
          {selectedTickers.length > 0 ? (
            selectedTickers.map((ticker: TickData) => (
              <div
                key={ticker.symbol}
                className="flex flex-col gap-1 min-w-max group cursor-pointer hover:opacity-80 transition-opacity"
              >
                {/* Symbol */}
                <div className="text-sm font-semibold text-[#E8EAED] font-clash">
                  {ticker.symbol}
                </div>

                {/* Price and change */}
                <div className="flex items-center gap-2 font-jbmono">
                  <span className="text-base text-[#00D4FF]">
                    ₹{formatPrice(ticker.price)}
                  </span>
                  <div
                    className={`flex items-center gap-1 text-sm font-semibold ${
                      ticker.changePct >= 0 ? 'text-[#00E676]' : 'text-[#FF3B3B]'
                    }`}
                  >
                    <span>{ticker.changePct >= 0 ? '▲' : '▼'}</span>
                    <span>
                      {Math.abs(ticker.changePct).toFixed(2)}%
                    </span>
                  </div>
                </div>

                {/* Sparkline */}
                <div className="opacity-70 group-hover:opacity-100 transition-opacity">
                  {renderSparkline(mockSparklineData(ticker.symbol))}
                </div>
              </div>
            ))
          ) : (
            <div className="text-[#8B9BB4] text-sm py-4">
              Loading market data...
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        @keyframes scroll {
          0% {
            transform: translateX(0);
          }
          100% {
            transform: translateX(100px);
          }
        }

        .animate-scroll {
          animation: scroll 30s linear infinite;
        }

        .scrollbar-hide::-webkit-scrollbar {
          display: none;
        }
      `}</style>
    </div>
  );
};

export default TickerStrip;