"use client";

import { useEffect, useRef, useMemo } from "react";
import { createChart, type IChartApi, type ISeriesApi, ColorType } from "lightweight-charts";
import type { Timeframe, ChartType } from "@neuroquant/types";

interface TradingChartProps {
  symbol: string;
  timeframe: Timeframe;
  chartType: ChartType;
}

function generateSampleOHLCV(count: number): { time: string; open: number; high: number; low: number; close: number; }[] {
  const data: { time: string; open: number; high: number; low: number; close: number }[] = [];
  let price = 2700 + Math.random() * 200;
  const startDate = new Date("2024-01-01");

  for (let i = 0; i < count; i++) {
    const date = new Date(startDate);
    date.setDate(date.getDate() + i);
    if (date.getDay() === 0 || date.getDay() === 6) continue;

    const volatility = 15 + Math.random() * 25;
    const direction = Math.random() > 0.48 ? 1 : -1;
    const change = direction * (Math.random() * volatility);
    const open = price;
    const close = price + change;
    const high = Math.max(open, close) + Math.random() * volatility * 0.5;
    const low = Math.min(open, close) - Math.random() * volatility * 0.5;

    data.push({
      time: date.toISOString().split("T")[0]!,
      open: Number(open.toFixed(2)),
      high: Number(high.toFixed(2)),
      low: Number(low.toFixed(2)),
      close: Number(close.toFixed(2)),
    });

    price = close;
  }

  return data;
}

function generateVolumeData(ohlcv: { time: string; open: number; close: number }[]): { time: string; value: number; color: string }[] {
  return ohlcv.map((bar) => ({
    time: bar.time,
    value: Math.floor(5_000_000 + Math.random() * 15_000_000),
    color: bar.close >= bar.open ? "rgba(0, 230, 118, 0.3)" : "rgba(255, 59, 59, 0.3)",
  }));
}

export function TradingChart({ symbol, timeframe, chartType }: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  const ohlcvData = useMemo(() => generateSampleOHLCV(300), []);
  const volumeData = useMemo(() => generateVolumeData(ohlcvData), [ohlcvData]);

  useEffect(() => {
    if (!containerRef.current) return;

    const container = containerRef.current;

    // Clean up previous chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(container, {
      layout: {
        background: { type: ColorType.Solid, color: "#161B24" },
        textColor: "#8B9BB4",
        fontFamily: "var(--font-jetbrains)",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(30, 37, 50, 0.8)" },
        horzLines: { color: "rgba(30, 37, 50, 0.8)" },
      },
      crosshair: {
        mode: 0,
        vertLine: { color: "rgba(0, 212, 255, 0.3)", width: 1, style: 2, labelBackgroundColor: "#00D4FF" },
        horzLine: { color: "rgba(0, 212, 255, 0.3)", width: 1, style: 2, labelBackgroundColor: "#00D4FF" },
      },
      rightPriceScale: {
        borderColor: "#1E2532",
        scaleMargins: { top: 0.1, bottom: 0.2 },
      },
      timeScale: {
        borderColor: "#1E2532",
        timeVisible: true,
        secondsVisible: false,
      },
      width: container.clientWidth,
      height: container.clientHeight,
    });

    chartRef.current = chart;

    // Main series
    if (chartType === "candlestick") {
      const series = chart.addCandlestickSeries({
        upColor: "#00E676",
        downColor: "#FF3B3B",
        borderUpColor: "#00E676",
        borderDownColor: "#FF3B3B",
        wickUpColor: "#00E676",
        wickDownColor: "#FF3B3B",
      });
      series.setData(ohlcvData);

      // Add SMA20 overlay
      const sma20Data = ohlcvData.map((_, i, arr) => {
        if (i < 19) return null;
        const sum = arr.slice(i - 19, i + 1).reduce((s, b) => s + b.close, 0);
        return { time: arr[i]!.time, value: Number((sum / 20).toFixed(2)) };
      }).filter(Boolean) as { time: string; value: number }[];

      const sma20 = chart.addLineSeries({ color: "#00D4FF", lineWidth: 1, lineStyle: 0, priceLineVisible: false, lastValueVisible: false });
      sma20.setData(sma20Data);

      // Add SMA50 overlay
      const sma50Data = ohlcvData.map((_, i, arr) => {
        if (i < 49) return null;
        const sum = arr.slice(i - 49, i + 1).reduce((s, b) => s + b.close, 0);
        return { time: arr[i]!.time, value: Number((sum / 50).toFixed(2)) };
      }).filter(Boolean) as { time: string; value: number }[];

      const sma50 = chart.addLineSeries({ color: "#FFB800", lineWidth: 1, lineStyle: 0, priceLineVisible: false, lastValueVisible: false });
      sma50.setData(sma50Data);

    } else if (chartType === "line") {
      const series = chart.addLineSeries({ color: "#00D4FF", lineWidth: 2 });
      series.setData(ohlcvData.map((b) => ({ time: b.time, value: b.close })));
    } else if (chartType === "area") {
      const series = chart.addAreaSeries({
        topColor: "rgba(0, 212, 255, 0.3)",
        bottomColor: "rgba(0, 212, 255, 0.02)",
        lineColor: "#00D4FF",
        lineWidth: 2,
      });
      series.setData(ohlcvData.map((b) => ({ time: b.time, value: b.close })));
    }

    // Volume histogram
    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "volume",
    });
    volumeSeries.setData(volumeData);
    chart.priceScale("volume").applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    chart.timeScale().fitContent();

    // Resize observer
    const resizeObserver = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        chart.applyOptions({
          width: entry.contentRect.width,
          height: entry.contentRect.height,
        });
      }
    });
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, [ohlcvData, volumeData, chartType]);

  return <div ref={containerRef} className="h-full w-full" />;
}
