"use client";

import { useEffect, useRef, useState } from "react";
import {
  ChartCanvas,
  Chart,
  CandlestickSeries,
  XAxis,
  YAxis,
  timeFormat,
  discontinuousTimeScaleProviderBuilder,
} from "react-financial-charts";
import type { OHLCVBar } from "@neuroquant/types";

// Imported directly above

interface FinancialCandlestickChartProps {
  bars: OHLCVBar[];
  height?: number;
  width?: number;
}

export function FinancialCandlestickChart({
  bars,
  height = 400,
  width,
}: FinancialCandlestickChartProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [containerWidth, setContainerWidth] = useState<number>(width || 800);

  // ResizeObserver for responsive width when width not provided
  useEffect(() => {
    if (width) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const cr = entry.contentRect;
        setContainerWidth(Math.floor(cr.width));
      }
    });
    if (containerRef.current) observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, [width]);

  // Transform OHLCV data to chart-friendly format
  const chartData = bars.map((b) => ({
    date: new Date(b.timestamp),
    open: b.open,
    high: b.high,
    low: b.low,
    close: b.close,
    volume: b.volume,
  }));

  const yExtents = (data: any) => [data.high, data.low];

  return (
    <div ref={containerRef} className="w-full h-full">
      {(() => {
        const scaleProvider = discontinuousTimeScaleProviderBuilder()
          .inputDateAccessor((d) => d.date);
        const { data, xScale, xAccessor, displayXAccessor } = scaleProvider(chartData);
        return (
          <ChartCanvas
            height={height}
            width={containerWidth}
            ratio={1}
            seriesName="OHLC"
            data={data}
            xScale={xScale}
            xAccessor={xAccessor}
            displayXAccessor={displayXAccessor}
            xExtents={[data[0]?.date, data[data.length - 1]?.date]}
          >
        <Chart id={1} yExtents={yExtents}>
          <XAxis axisAt="bottom" orient="bottom" ticks={6} />
          <YAxis axisAt="right" orient="right" ticks={5} />
          <CandlestickSeries />
          </Chart>
        </ChartCanvas>
        );
        })()}</div>
  );
}
