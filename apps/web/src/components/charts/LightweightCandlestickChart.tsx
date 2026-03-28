"use client";

import { useEffect, useRef } from "react";
import {
  createChart,
  ColorType,
  type IChartApi,
  type CandlestickData,
  type HistogramData,
  type UTCTimestamp,
} from "lightweight-charts";

interface PriceBar {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface LightweightCandlestickChartProps {
  bars: PriceBar[];
  height?: number;
}

function toUtcTimestamp(value: string): UTCTimestamp {
  return Math.floor(new Date(value).getTime() / 1000) as UTCTimestamp;
}

function buildEma(values: number[], period: number): number[] {
  if (values.length === 0) {
    return [];
  }

  const k = 2 / (period + 1);
  const ema: number[] = [values[0] ?? 0];

  for (let i = 1; i < values.length; i += 1) {
    ema.push((values[i] ?? 0) * k + (ema[i - 1] ?? 0) * (1 - k));
  }

  return ema;
}

export function LightweightCandlestickChart({ bars, height = 340 }: LightweightCandlestickChartProps): JSX.Element {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!rootRef.current) {
      return;
    }

    const chart = createChart(rootRef.current, {
      autoSize: true,
      height,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8B97A8",
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.12)",
      },
      timeScale: {
        borderColor: "rgba(255,255,255,0.12)",
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      crosshair: {
        vertLine: { color: "rgba(0,212,245,0.45)", width: 1 },
        horzLine: { color: "rgba(0,212,245,0.45)", width: 1 },
      },
    });

    chartRef.current = chart;

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#00E676",
      downColor: "#FF3B5C",
      wickUpColor: "#00E676",
      wickDownColor: "#FF3B5C",
      borderVisible: false,
    });

    const volumeSeries = chart.addHistogramSeries({
      priceScaleId: "",
      priceFormat: { type: "volume" },
      color: "rgba(0,212,245,0.45)",
    });

    volumeSeries.priceScale().applyOptions({
      scaleMargins: {
        top: 0.82,
        bottom: 0,
      },
    });

    const ema9Series = chart.addLineSeries({
      color: "#00D4F5",
      lineWidth: 2,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });

    const ema21Series = chart.addLineSeries({
      color: "#8B5CF6",
      lineWidth: 2,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });

    const candleData: CandlestickData[] = bars.map((bar) => ({
      time: toUtcTimestamp(bar.timestamp),
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }));

    const volumeData: HistogramData[] = bars.map((bar) => ({
      time: toUtcTimestamp(bar.timestamp),
      value: bar.volume,
      color: bar.close >= bar.open ? "rgba(0,230,118,0.4)" : "rgba(255,59,92,0.4)",
    }));

    const closes = bars.map((bar) => bar.close);
    const ema9 = buildEma(closes, 9);
    const ema21 = buildEma(closes, 21);

    candleSeries.setData(candleData);
    volumeSeries.setData(volumeData);
    ema9Series.setData(candleData.map((bar, idx) => ({ time: bar.time, value: ema9[idx] ?? bar.close })));
    ema21Series.setData(candleData.map((bar, idx) => ({ time: bar.time, value: ema21[idx] ?? bar.close })));

    chart.timeScale().fitContent();

    const observer = new ResizeObserver(() => {
      if (!rootRef.current || !chartRef.current) {
        return;
      }
      chartRef.current.applyOptions({ width: rootRef.current.clientWidth });
    });

    observer.observe(rootRef.current);

    return () => {
      observer.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [bars, height]);

  return <div ref={rootRef} className="h-full w-full" />;
}
