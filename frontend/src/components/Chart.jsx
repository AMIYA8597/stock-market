import React, { useEffect, useRef } from 'react';
import { createChart } from 'lightweight-charts';

function Chart({ candles, indicators }) {
  const chartContainerRef = useRef();
  const chartRef = useRef();
  const candleSeriesRef = useRef();
  const smaSeriesRef = useRef();
  const emaSeriesRef = useRef();

  // Initialize chart on mount
  useEffect(() => {
    const chart = createChart(chartContainerRef.current, {
      width: chartContainerRef.current.clientWidth,
      height: 500,
      layout: {
        background: { type: 'solid', color: '#0f0f0f' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2A2E39' },
        horzLines: { color: '#2A2E39' },
      },
      crossHair: { mode: 0 },
      rightPriceScale: { borderColor: '#555' },
      timeScale: { borderColor: '#555', timeVisible: true },
    });
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderDownColor: '#ef5350',
      borderUpColor: '#26a69a',
      wickDownColor: '#ef5350',
      wickUpColor: '#26a69a',
    });
    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    // Create placeholder line series for SMA and EMA
    smaSeriesRef.current = chart.addLineSeries({ color: '#ffd54f', lineWidth: 1, title: 'SMA 20' });
    emaSeriesRef.current = chart.addLineSeries({ color: '#4fc3f7', lineWidth: 1, title: 'EMA 20' });
    // Cleanup on unmount
    return () => chart.remove();
  }, []);

  // Update candle data
  useEffect(() => {
    if (candleSeriesRef.current && candles.length) {
      candleSeriesRef.current.setData(candles);
    }
  }, [candles]);

  // Update indicator series
  useEffect(() => {
    if (!chartRef.current) return;
    if (indicators.length) {
      const smaData = indicators.map(ind => ({
        time: Math.floor(new Date(ind.time).getTime() / 1000),
        value: ind.SMA_20,
      }));
      const emaData = indicators.map(ind => ({
        time: Math.floor(new Date(ind.time).getTime() / 1000),
        value: ind.EMA_20,
      }));
      smaSeriesRef.current.setData(smaData);
      emaSeriesRef.current.setData(emaData);
    }
  }, [indicators]);

  return <div ref={chartContainerRef} className="chart-container" />;
}

export default Chart;
