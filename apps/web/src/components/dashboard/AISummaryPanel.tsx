'use client';

import { useEffect, useMemo, useState } from 'react';
import { contractsApi, type DriftItem, type ModelAccuracyItem, type RegimeCurrentResponse } from '@/lib/contracts-api';

interface AIAnalysis {
  summary: string;
  technicalView: string;
  fundamentalView: string;
  riskFactors: string;
  regime: {
    type: 'bull' | 'bear' | 'sideways' | 'crisis';
    confidence: number;
  };
  catalysts: Array<{ title: string; impact: 'high' | 'medium' | 'low'; timestamp: string }>;
  fearGreedIndex: number;
  vixLevel: number;
  vixZScore: number;
}

function toRegimeType(state: RegimeCurrentResponse['state']): 'bull' | 'bear' | 'sideways' | 'crisis' {
  if (state === 'BULL') return 'bull';
  if (state === 'BEAR') return 'bear';
  if (state === 'CRISIS') return 'crisis';
  return 'sideways';
}

const AISummaryPanel = (): JSX.Element => {
  const [aiAnalysis, setAiAnalysis] = useState<AIAnalysis | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);

  useEffect(() => {
    let mounted = true;

    async function loadAnalysis(): Promise<void> {
      try {
        setIsLoading(true);
        setError(null);

        const [regime, drifts, accuracy] = await Promise.all([
          contractsApi.getRegimeCurrent(),
          contractsApi.getDrift(),
          contractsApi.getModelAccuracy(),
        ]);

        if (!mounted) {
          return;
        }

        const driftDetected = drifts.filter((item: DriftItem) => item.drift_detected).length;
        const avgDirectionalAccuracy =
          accuracy.length > 0
            ? accuracy.reduce((sum: number, item: ModelAccuracyItem) => sum + item.directional_accuracy, 0) / accuracy.length
            : 0;

        const bullProb = regime.probs.BULL ?? 0;
        const bearProb = regime.probs.BEAR ?? 0;
        const confidence = Math.max(...Object.values(regime.probs)) * 100;
        const condVol = regime.cond_vol_21d * 100;

        const summary =
          regime.state === 'BULL'
            ? 'Risk-on posture remains dominant with broad participation and improving trend persistence.'
            : regime.state === 'BEAR'
              ? 'Defensive regime remains active with elevated downside clustering and reduced trend durability.'
              : regime.state === 'CRISIS'
                ? 'Crisis regime flagged with instability in transition probabilities and stressed volatility conditions.'
                : 'Sideways regime with rotational leadership and lower conviction directional moves.';

        const technicalView = `Bull probability ${bullProb.toFixed(2)}, Bear probability ${bearProb.toFixed(2)}, 21d conditional volatility ${condVol.toFixed(2)}%.`;
        const fundamentalView = `Ensemble directional accuracy averages ${(avgDirectionalAccuracy * 100).toFixed(1)}% across tracked models.`;
        const riskFactors = `${driftDetected} model${driftDetected === 1 ? '' : 's'} currently flagged by drift detectors.`;

        setAiAnalysis({
          summary,
          technicalView,
          fundamentalView,
          riskFactors,
          regime: {
            type: toRegimeType(regime.state),
            confidence,
          },
          catalysts: [
            { title: 'Regime transition matrix refreshed', impact: 'medium', timestamp: 'Live' },
            { title: `${driftDetected} drift alerts active`, impact: driftDetected > 0 ? 'high' : 'low', timestamp: 'Live' },
            { title: 'Model accuracy monitor synced', impact: 'medium', timestamp: 'Live' },
          ],
          fearGreedIndex: Math.round(confidence),
          vixLevel: Number((10 + condVol * 2.5).toFixed(2)),
          vixZScore: Number(((regime.cond_vol_5d - regime.cond_vol_21d) / Math.max(regime.cond_vol_21d, 0.0001)).toFixed(2)),
        });
        setLastUpdated(Date.now());
      } catch (fetchError) {
        if (!mounted) {
          return;
        }
        const message = fetchError instanceof Error ? fetchError.message : 'Failed to build AI market pulse.';
        setError(message);
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    void loadAnalysis();
    const refreshInterval = setInterval(() => {
      void loadAnalysis();
    }, 5 * 60 * 1000);

    return () => {
      mounted = false;
      clearInterval(refreshInterval);
    };
  }, []);

  const regimeStyle = useMemo(() => {
    if (!aiAnalysis) {
      return { bg: '#FFB800', text: '#0A0B0E', icon: '' };
    }
    switch (aiAnalysis.regime.type) {
      case 'bull':
        return { bg: '#00E676', text: '#0A0B0E', icon: '' };
      case 'bear':
        return { bg: '#FF3B3B', text: '#FFFFFF', icon: '' };
      case 'crisis':
        return { bg: '#FF7043', text: '#FFFFFF', icon: '!' };
      default:
        return { bg: '#FFB800', text: '#0A0B0E', icon: '' };
    }
  }, [aiAnalysis]);

  const ageSeconds = lastUpdated ? Math.floor((Date.now() - lastUpdated) / 1000) : null;
  const freshness = error !== null ? 'degraded' : ageSeconds !== null && ageSeconds > 360 ? 'stale' : 'fresh';

  const renderFearGreedGauge = (value: number): JSX.Element => {
    const gaugeColor = value > 70 ? '#00E676' : value > 50 ? '#80CBC4' : value > 30 ? '#FFCC80' : '#FF3B3B';

    return (
      <div className="flex flex-col items-center gap-2">
        <div className="relative h-20 w-20">
          <svg className="h-full w-full -rotate-90 transform" viewBox="0 0 100 100">
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
            <text x="50" y="50" textAnchor="middle" dy="0.3em" className="fill-[#E8EAED] text-xs font-bold" fontSize="14">
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
      <div className="rounded-lg border border-[#1E2532] bg-[#0A0B0E] p-6">
        <div className="flex h-64 items-center justify-center">
          <div className="text-center">
            <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-2 border-[#1E2532] border-t-[#00D4FF]" />
            <p className="text-sm text-[#8B9BB4]">Analyzing market dynamics...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4 rounded-lg border border-[#1E2532] bg-[#0A0B0E] p-4 sm:space-y-6 sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h2 className="font-clash text-lg font-semibold text-[#E8EAED] sm:text-xl">NeuroQuant AI Market Pulse</h2>
        <div className="flex items-center gap-2 text-xs text-[#8B9BB4]">
          <span
            className={`rounded border px-2 py-0.5 uppercase tracking-[0.08em] ${
              freshness === 'fresh'
                ? 'border-[rgba(0,230,118,0.35)] bg-[rgba(0,230,118,0.10)] text-[#00E676]'
                : freshness === 'stale'
                  ? 'border-[rgba(255,184,0,0.35)] bg-[rgba(255,184,0,0.10)] text-[#FFB800]'
                  : 'border-[rgba(255,59,92,0.35)] bg-[rgba(255,59,92,0.10)] text-[#FF3B5C]'
            }`}
          >
            {freshness}
          </span>
          <span>
            Updated {lastUpdated ? new Date(lastUpdated).toLocaleTimeString() : '--'}
            {ageSeconds !== null ? ` (${ageSeconds}s)` : ''}
          </span>
        </div>
      </div>

      {error ? <p className="text-xs text-[#FF3B3B]">{error}</p> : null}

      <div className="flex flex-wrap items-center gap-3">
        <div
          className="flex items-center gap-2 rounded-lg px-4 py-2 font-semibold transition-all duration-300"
          style={{
            backgroundColor: regimeStyle.bg,
            color: regimeStyle.text,
          }}
        >
          <span>{regimeStyle.icon}</span>
          <span>{aiAnalysis.regime.type.toUpperCase()}</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="h-1.5 w-24 overflow-hidden rounded-full bg-[#1E2532]">
            <div
              className="h-full transition-all duration-500"
              style={{
                width: `${aiAnalysis.regime.confidence}%`,
                backgroundColor: regimeStyle.bg,
              }}
            />
          </div>
          <span className="font-jbmono text-sm text-[#8B9BB4]">{aiAnalysis.regime.confidence.toFixed(1)}%</span>
        </div>
      </div>

      <div className="space-y-3 text-sm leading-relaxed text-[#E8EAED]">
        <p>{aiAnalysis.summary}</p>
        <p className="text-[#8B9BB4]">{aiAnalysis.technicalView}</p>
        <p className="text-[#8B9BB4]">{aiAnalysis.fundamentalView}</p>
      </div>

      <div className="rounded border border-[#1E2532] bg-[#161B24] p-3">
        <h3 className="mb-2 text-xs font-semibold uppercase text-[#FFB800]">Risk Factors</h3>
        <p className="text-xs text-[#8B9BB4]">{aiAnalysis.riskFactors}</p>
      </div>

      <div>
        <h3 className="mb-2 text-xs font-semibold uppercase text-[#8B9BB4]">Live Catalysts</h3>
        <div className="space-y-2">
          {aiAnalysis.catalysts.map((catalyst, index) => (
            <div key={`${catalyst.title}-${index}`} className="flex items-start gap-3 rounded bg-[#161B24] p-2">
              <div
                className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${
                  catalyst.impact === 'high' ? 'bg-[#FF3B3B]' : catalyst.impact === 'medium' ? 'bg-[#FFB800]' : 'bg-[#00D4FF]'
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

      <div className="grid grid-cols-1 gap-4 border-t border-[#1E2532] pt-4 sm:grid-cols-2">
        <div className="flex justify-center">{renderFearGreedGauge(aiAnalysis.fearGreedIndex)}</div>

        <div className="flex flex-col justify-center space-y-3">
          <div>
            <p className="text-xs uppercase text-[#8B9BB4]">VIX Level</p>
            <p className="font-jbmono text-lg font-bold text-[#00D4FF]">{aiAnalysis.vixLevel.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-xs uppercase text-[#8B9BB4]">Z-Score</p>
            <p className={`font-jbmono text-lg font-bold ${aiAnalysis.vixZScore > 0 ? 'text-[#FF3B3B]' : 'text-[#00E676]'}`}>
              {aiAnalysis.vixZScore > 0 ? '+' : ''}
              {aiAnalysis.vixZScore.toFixed(2)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AISummaryPanel;

