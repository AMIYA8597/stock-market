'use client';

import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';

/**
 * AISummaryPanel Component
 * 
 * Design Spec from prompt.txt:
 * - "NeuroQuant AI Market Pulse" — regenerates every 5 minutes
 * - LLM-generated 3-paragraph market analysis
 * - Regime indicator: animated badge (BULL/BEAR/SIDEWAYS) with confidence %
 * - Top 3 catalyst events (from news agent)
 * - Global risk gauge: Fear & Greed Index (animated radial chart)
 * - VIX level + Z-score
 */

interface MarketRegime {
  type: 'bull' | 'bear' | 'sideways';
  confidence: number;
}

interface CatalystEvent {
  title: string;
  impact: 'high' | 'medium' | 'low';
  timestamp: string;
}

interface AIAnalysis {
  summary: string;
  technicalView: string;
  fundamentalView: string;
  riskFactors: string;
  regime: MarketRegime;
  catalysts: CatalystEvent[];
  fearGreedIndex: number;
  vixLevel: number;
  vixZScore: number;
}

const AISummaryPanel = (): JSX.Element => {
  const { connectionStatus } = useWebSocket();
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Mock AI analysis data - in production, this would come from LangGraph multi-agent
  const mockAnalysis: AIAnalysis = {
    summary:
      'Markets show strong bull momentum with positive sectoral rotation. Tech and financials leading the rally. Crude oil weakness supporting margins across sectors. RBI policy stance remains accommodative, supporting equity valuations.',
    technicalView:
      'Nifty50 above 20-day SMA with bullish MACD crossover. RSI in 60-70 zone indicating strong momentum without overbought conditions. Support at 19,500 remaining intact. Breakout above 20,800 could trigger fresh longs.',
    fundamentalView:
      'Earnings growth acceleration expected in Q4 FY2024. Banks showing strong deposit growth and NIM expansion. IT services benefit from weak INR and strong deal flow. Valuations reasonable at 20x FY2025 earnings.',
    riskFactors:
      'Global geopolitical tensions impacting crude. Fed rate pause could strengthen USD. Domestic inflation monitoring continues. Q4 results could show margin compression in select sectors.',
    regime: {
      type: 'bull',
      confidence: 78,
    },
    catalysts: [
      {
        title: 'RBI MPC Meeting - Rate Decision Expected',
        impact: 'high',
        timestamp: '2 days',
      },
      {
        title: 'Q4 FY2024 Earnings Season Kickoff',
        impact: 'high',
        timestamp: '3 days',
      },
      {
        title: 'Fed FOMC Minutes Release',
        impact: 'medium',
        timestamp: '1 day',
      },
    ],
    fearGreedIndex: 72,
    vixLevel: 14.5,
    vixZScore: -0.8,
  };

  useEffect(() => {
    setIsLoading(true);
    // Simulate fetching AI analysis
    const timer = setTimeout(() => {
      setAiAnalysis(mockAnalysis);
      setIsLoading(false);
    }, 800);

    // Refresh every 5 minutes
    const refreshInterval = setInterval(() => {
      setIsLoading(true);
      setTimeout(() => {
        setAiAnalysis(mockAnalysis);
        setIsLoading(false);
      }, 800);
    }, 5 * 60 * 1000);

    return () => {
      clearTimeout(timer);
      clearInterval(refreshInterval);
    };
  }, []);

  const getRegimeColor = (
    regime: 'bull' | 'bear' | 'sideways'
  ): { bg: string; text: string; icon: string } => {
    switch (regime) {
      case 'bull':
        return { bg: '#00E676', text: '#0A0B0E', icon: '📈' };
      case 'bear':
        return { bg: '#FF3B3B', text: '#FFFFFF', icon: '📉' };
      case 'sideways':
        return { bg: '#FFB800', text: '#0A0B0E', icon: '➡️' };
    }
  };

  const renderFearGreedGauge = (value: number): JSX.Element => {
    const gaugeColor = value > 70 ? '#00E676' : value > 50 ? '#80CBC4' : value > 30 ? '#FFCC80' : '#FF3B3B';

    return (
      <div className="flex flex-col items-center gap-2">
        <div className="relative w-20 h-20">
          <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="40" fill="none" stroke="#1E2532" strokeWidth="4" />
            <circle
              cx="50"
              cy="50"
              r="40"
              fill="none"
              stroke={gaugeColor}
              strokeWidth="4"
              strokeDasharray={`${(value / 100) * 251.2} 251.2`}
              className="transition-all duration-700"
            />
            <text x="50" y="50" textAnchor="middle" dy="0.3em" className="font-bold text-xs fill-[#E8EAED]" fontSize="14">
              {value}
            </text>
          </svg>
        </div>
        <span className="text-xs text-[#8B9BB4]">Fear & Greed</span>
      </div>
    );
  };

  if (isLoading || !aiAnalysis) {
    return (
      <div className="bg-[#0A0B0E] border border-[#1E2532] rounded-lg p-6">
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="w-8 h-8 rounded-full border-2 border-[#1E2532] border-t-[#00D4FF] animate-spin mx-auto mb-4" />
            <p className="text-[#8B9BB4] text-sm">Analyzing market dynamics...</p>
          </div>
        </div>
      </div>
    );
  }

  const regimeStyle = getRegimeColor(aiAnalysis.regime.type);

  return (
    <div className="bg-[#0A0B0E] border border-[#1E2532] rounded-lg p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-start">
        <h2 className="text-xl font-semibold text-[#E8EAED] font-clash">
          NeuroQuant AI Market Pulse
        </h2>
        <div className="text-xs text-[#8B9BB4]">
          Updated {new Date().toLocaleTimeString()}
        </div>
      </div>

      {/* Regime Badge */}
      <div className="flex items-center gap-3">
        <div
          className="px-4 py-2 rounded-lg font-semibold flex items-center gap-2 transition-all duration-300"
          style={{
            backgroundColor: regimeStyle.bg,
            color: regimeStyle.text,
          }}
        >
          <span>{regimeStyle.icon}</span>
          <span>{aiAnalysis.regime.type.toUpperCase()}</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="w-24 bg-[#1E2532] rounded-full h-1.5 overflow-hidden">
            <div
              className="h-full transition-all duration-500"
              style={{
                width: `${aiAnalysis.regime.confidence}%`,
                backgroundColor: regimeStyle.bg,
              }}
            />
          </div>
          <span className="text-sm text-[#8B9BB4] font-jbmono">
            {aiAnalysis.regime.confidence}%
          </span>
        </div>
      </div>

      {/* Market Analysis Paragraphs */}
      <div className="space-y-3 text-sm text-[#E8EAED] leading-relaxed">
        <p>{aiAnalysis.summary}</p>
        <p className="text-[#8B9BB4]">{aiAnalysis.technicalView}</p>
        <p className="text-[#8B9BB4]">{aiAnalysis.fundamentalView}</p>
      </div>

      {/* Risk Factors */}
      <div className="bg-[#161B24] border border-[#1E2532] rounded p-3">
        <h3 className="text-xs font-semibold text-[#FFB800] mb-2 uppercase">⚠ Risk Factors</h3>
        <p className="text-xs text-[#8B9BB4]">{aiAnalysis.riskFactors}</p>
      </div>

      {/* Catalyst Events */}
      <div>
        <h3 className="text-xs font-semibold text-[#8B9BB4] mb-2 uppercase">Upcoming Catalysts</h3>
        <div className="space-y-2">
          {aiAnalysis.catalysts.map((catalyst, index) => (
            <div key={index} className="flex items-start gap-3 p-2 bg-[#161B24] rounded">
              <div
                className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                  catalyst.impact === 'high'
                    ? 'bg-[#FF3B3B]'
                    : catalyst.impact === 'medium'
                      ? 'bg-[#FFB800]'
                      : 'bg-[#00D4FF]'
                }`}
              />
              <div className="flex-1">
                <p className="text-xs font-semibold text-[#E8EAED]">{catalyst.title}</p>
                <p className="text-xs text-[#8B9BB4]">{catalyst.timestamp}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-[#1E2532]">
        {/* Fear & Greed Gauge */}
        <div className="flex justify-center">{renderFearGreedGauge(aiAnalysis.fearGreedIndex)}</div>

        {/* VIX Metrics */}
        <div className="flex flex-col justify-center space-y-3">
          <div>
            <p className="text-xs text-[#8B9BB4] uppercase">VIX Level</p>
            <p className="text-lg font-bold text-[#00D4FF] font-jbmono">
              {aiAnalysis.vixLevel.toFixed(2)}
            </p>
          </div>
          <div>
            <p className="text-xs text-[#8B9BB4] uppercase">Z-Score</p>
            <p
              className={`text-lg font-bold font-jbmono ${
                aiAnalysis.vixZScore > 0 ? 'text-[#FF3B3B]' : 'text-[#00E676]'
              }`}
            >
              {aiAnalysis.vixZScore > 0 ? '+' : ''}{aiAnalysis.vixZScore.toFixed(2)}
            </p>
          </div>
        </div>
      </div>

      {/* Connection Status */}
      {connectionStatus !== 'connected' && (
        <div className="text-xs text-[#FF3B3B] text-center pt-2 border-t border-[#1E2532]">
          {connectionStatus === 'reconnecting' ? 'Reconnecting...' : 'Disconnected'}
        </div>
      )}
    </div>
  );
};

export default AISummaryPanel;