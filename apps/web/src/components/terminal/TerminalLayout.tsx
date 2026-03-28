'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs';
import { cn } from '@/lib/utils';
import { useTerminalStore } from '@/stores/terminalStore';
import { formatTime } from '@/lib/formatters';

interface Watchlist {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePercent: number;
  volume: number;
  signal?: {
    direction: string;
    confidence: number;
  };
  regime?: string;
}

const mockWatchlist: Watchlist[] = [
  {
    symbol: 'RELIANCE.NS',
    name: 'Reliance Industries',
    price: 2847.50,
    change: 45.25,
    changePercent: 1.62,
    volume: 45234500,
    signal: { direction: 'BUY', confidence: 0.78 },
    regime: 'BULL',
  },
  {
    symbol: 'TCS.NS',
    name: 'Tata Consultancy Services',
    price: 3456.75,
    change: -12.50,
    changePercent: -0.36,
    volume: 23456789,
    signal: { direction: 'NEUTRAL', confidence: 0.45 },
    regime: 'BEAR',
  },
  {
    symbol: 'INFY.NS',
    name: 'Infosys Limited',
    price: 1895.40,
    change: 28.90,
    changePercent: 1.55,
    volume: 34567890,
    signal: { direction: 'STRONG_BUY', confidence: 0.85 },
    regime: 'BULL',
  },
];

function TopBar() {
  const { setSelectedSymbol } = useTerminalStore();
  const [searchInput, setSearchInput] = React.useState('');

  return (
    <div className="col-span-3 row-span-1 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)] px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-bold text-[var(--text-primary)]">NeuroQuant</h1>
        <Badge variant="bull">BULL</Badge>
        <span className="text-xs text-[var(--text-secondary)]">{formatTime(new Date())}</span>
      </div>

      <Input
        placeholder="Search symbol (Cmd+K)..."
        className="w-64"
        value={searchInput}
        onChange={(e) => {
          setSearchInput(e.target.value);
          if (e.target.value.length > 0) {
            setSelectedSymbol(e.target.value.toUpperCase());
          }
        }}
      />

      <div className="flex items-center gap-4">
        <div className="text-right">
          <div className="text-sm font-semibold text-[var(--text-primary)]">₹1,234,567.89</div>
          <div className="text-xs text-[var(--accent-green)]">+₹12,345 (+1.00%)</div>
        </div>
      </div>
    </div>
  );
}

function WatchlistRow({ item, isSelected, onSelect }: { item: Watchlist; isSelected: boolean; onSelect: () => void }) {
  const signalColor =
    item.signal?.direction === 'BUY' || item.signal?.direction === 'STRONG_BUY'
      ? 'text-[var(--accent-green)]'
      : item.signal?.direction === 'SELL' || item.signal?.direction === 'STRONG_SELL'
      ? 'text-[var(--accent-red)]'
      : 'text-[var(--accent-amber)]';

  const regimeColor =
    item.regime === 'BULL'
      ? 'bg-[var(--regime-bull)]'
      : item.regime === 'BEAR'
      ? 'bg-[var(--regime-bear)]'
      : item.regime === 'SIDEWAYS'
      ? 'bg-[var(--regime-side)]'
      : 'bg-[var(--regime-crisis)]';

  return (
    <div
      onClick={onSelect}
      className={cn(
        'flex items-center gap-2 px-4 py-3 border-b border-[var(--border-subtle)] cursor-pointer transition-colors hover:bg-[var(--bg-elevated)]',
        isSelected && 'bg-[var(--bg-elevated)]'
      )}
    >
      <div className={cn('h-2 w-2 rounded-full', regimeColor)} />
      <div className="flex-1 min-w-0">
        <div className="text-xs font-bold text-[var(--text-primary)]">{item.symbol}</div>
        <div className="text-xs text-[var(--text-secondary)]">{item.name}</div>
      </div>
      <div className="text-right flex-shrink-0">
        <div className="text-sm font-bold text-[var(--text-primary)]">₹{item.price.toFixed(2)}</div>
        <div className={cn('text-xs', item.change >= 0 ? 'text-[var(--accent-green)]' : 'text-[var(--accent-red)]')}>
          {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)} ({item.changePercent.toFixed(2)}%)
        </div>
      </div>
      {item.signal && (
        <div className={cn('text-xs font-bold', signalColor)}>
          {item.signal.direction === 'BUY' || item.signal.direction === 'STRONG_BUY' ? '↑' : '↓'}
        </div>
      )}
    </div>
  );
}

function ChartSection() {
  const { selectedSymbol } = useTerminalStore();
  const selected = mockWatchlist.find((w) => w.symbol === selectedSymbol);

  return (
    <div className="flex flex-col gap-4 p-4">
      {/* Chart Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-[var(--text-primary)]">{selected?.name}</h2>
          <div className="flex gap-4 text-sm text-[var(--text-secondary)]">
            <span>{selected?.symbol}</span>
            <span>NSE</span>
            <Badge variant="outline" className="text-xs">{selected?.regime}</Badge>
          </div>
        </div>
        <div className="text-right">
          <div className="text-2xl font-bold text-[var(--text-primary)]">₹{selected?.price.toFixed(2)}</div>
          <div className="text-[var(--accent-green)]">+{selected?.change.toFixed(2)} (+{selected?.changePercent.toFixed(2)}%)</div>
        </div>
      </div>

      {/* Chart Placeholder */}
      <Card className="flex-1 min-h-[400px]">
        <CardContent className="h-full flex items-center justify-center text-[var(--text-secondary)]">
          Chart Component - TradingView Lightweight Charts
        </CardContent>
      </Card>

      {/* Indicator Tabs */}
      <Tabs defaultValue="volume">
        <TabsList>
          <TabsTrigger value="volume">Volume</TabsTrigger>
          <TabsTrigger value="indicators">Indicators</TabsTrigger>
          <TabsTrigger value="signals">Signals</TabsTrigger>
        </TabsList>
        <TabsContent value="volume" className="min-h-[150px]">
          <div className="text-center text-[var(--text-secondary)]">Volume chart here</div>
        </TabsContent>
        <TabsContent value="indicators" className="min-h-[150px]">
          <div className="text-center text-[var(--text-secondary)]">RSI, MACD, Stochastic charts here</div>
        </TabsContent>
        <TabsContent value="signals" className="min-h-[150px]">
          <div className="text-center text-[var(--text-secondary)]">Model signals here</div>
        </TabsContent>
      </Tabs>
    </div>
  );
}

function SignalPanel() {
  const { selectedSymbol } = useTerminalStore();
  const selected = mockWatchlist.find((w) => w.symbol === selectedSymbol);

  return (
    <div className="flex flex-col gap-4 p-4 overflow-y-auto">
      {/* Ensemble Signal */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Ensemble Signal</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Badge variant={selected?.signal?.direction === 'BUY' ? 'buy' : 'sell'} className="text-base px-3 py-1">
              {selected?.signal?.direction}
            </Badge>
          </div>
          <div>
            <div className="text-xs text-[var(--text-secondary)] mb-1">Confidence</div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-2 bg-[var(--bg-elevated)] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[var(--accent-cyan)]"
                  style={{ width: `${(selected?.signal?.confidence || 0) * 100}%` }}
                />
              </div>
              <span className="text-xs font-bold text-[var(--text-primary)]">
                {((selected?.signal?.confidence || 0) * 100).toFixed(0)}%
              </span>
            </div>
          </div>
          <div>
            <div className="text-xs text-[var(--text-secondary)] mb-1">Kelly Fraction</div>
            <div className="text-sm font-bold text-[var(--text-primary)]">2.5%</div>
          </div>
        </CardContent>
      </Card>

      {/* Model Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Model Breakdown</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {['TFT', 'HMM', 'LSTM', 'XGBoost'].map((model) => (
            <div key={model} className="flex justify-between">
              <span className="text-xs text-[var(--text-secondary)]">{model}</span>
              <div className="flex gap-2">
                <div className="w-16 h-4 bg-[var(--bg-elevated)] rounded text-xs flex items-center justify-center text-[var(--text-muted)]">
                  +0.5%
                </div>
                <Badge variant="outline" className="text-xs">15%</Badge>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* News Feed */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Latest News</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {[
            { title: 'Positive Q3 earnings expected', sentiment: 'positive' },
            { title: 'Market correction expected soon', sentiment: 'negative' },
            { title: 'Sector rotation ongoing', sentiment: 'neutral' },
          ].map((news, i) => (
            <div key={i} className="text-xs">
              <div className="flex gap-2">
                <Badge
                  variant={
                    news.sentiment === 'positive' ? 'buy' : news.sentiment === 'negative' ? 'sell' : 'neutral'
                  }
                  className="px-2 py-0 text-xs flex-shrink-0"
                >
                  {news.sentiment === 'positive' ? '✓' : news.sentiment === 'negative' ? '✗' : '○'}
                </Badge>
                <span className="text-[var(--text-secondary)]">{news.title}</span>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

export default function TerminalLayout() {
  const { selectedSymbol, setSelectedSymbol } = useTerminalStore();

  return (
    <div className="h-screen bg-[var(--bg-base)] flex flex-col">
      <TopBar />

      <div className="flex-1 grid grid-cols-[280px_1fr_320px] gap-0 overflow-hidden">
        {/* Watchlist */}
        <div className="flex flex-col border-r border-[var(--border-subtle)] bg-[var(--bg-surface)]">
          <div className="p-4 border-b border-[var(--border-subtle)]">
            <Tabs defaultValue="watchlist">
              <TabsList className="w-full">
                <TabsTrigger value="watchlist" className="flex-1 text-xs">My Watchlist</TabsTrigger>
                <TabsTrigger value="market" className="flex-1 text-xs">Market</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
          <div className="flex-1 overflow-y-auto">
            {mockWatchlist.map((item) => (
              <WatchlistRow
                key={item.symbol}
                item={item}
                isSelected={selectedSymbol === item.symbol}
                onSelect={() => setSelectedSymbol(item.symbol)}
              />
            ))}
          </div>
        </div>

        {/* Chart Area */}
        <div className="border-r border-[var(--border-subtle)] bg-[var(--bg-base)] overflow-y-auto">
          <ChartSection />
        </div>

        {/* Signal Panel */}
        <div className="border-l border-[var(--border-subtle)] bg-[var(--bg-surface)]">
          <SignalPanel />
        </div>
      </div>
    </div>
  );
}
