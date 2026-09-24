import React, { useEffect, useRef } from 'react';
import { createChart, LineSeries, AreaSeries, ColorType } from 'lightweight-charts';

export interface LineAreaPoint {
  label: string;
  value: number;
}

interface SimpleLineAreaChartProps {
  data: LineAreaPoint[];
  mode?: 'area' | 'line';
  stroke?: string;
  fill?: string;
  yTickFormatter?: (value: number) => string;
}

export function SimpleLineAreaChart({
  data,
  mode = 'area',
  stroke = 'var(--nq-accent-cyan)',
  fill = 'rgba(0, 212, 245, 0.25)',
  yTickFormatter,
}: SimpleLineAreaChartProps): JSX.Element {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartInstanceRef = useRef<any>(null);

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: 'var(--nq-text-tertiary)',
      },
      grid: {
        vertLines: { color: 'rgba(255,255,255,0.06)' },
        horzLines: { color: 'rgba(255,255,255,0.06)' },
      },
      rightPriceScale: {
        borderVisible: false,
      },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
      },
      crosshair: {
        mode: 0,
      }
    });
    
    chartInstanceRef.current = chart;

    let series: any;
    if (mode === 'line') {
      series = chart.addSeries(LineSeries, {
        color: stroke.replace('var(--nq-accent-cyan)', '#00D4F5').replace('var(--nq-accent-purple)', '#8F66FF'),
        lineWidth: 2,
      });
    } else {
      series = chart.addSeries(AreaSeries, {
        lineColor: stroke.replace('var(--nq-accent-cyan)', '#00D4F5'),
        topColor: fill.replace('var(--nq-accent-cyan)', '#00D4F5'),
        bottomColor: 'transparent',
        lineWidth: 2,
      });
    }

    if (yTickFormatter && series.applyOptions) {
      series.applyOptions({
        priceFormat: {
          type: 'custom',
          formatter: yTickFormatter,
        }
      });
    }

    const formattedData = data.map((d, i) => ({
      time: i as any, // Using index as mock time if it's not a valid date string
      value: d.value,
    }));
    
    series.setData(formattedData);
    chart.timeScale().fitContent();

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };
    
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [data, mode, stroke, fill]);

  return <div ref={chartContainerRef} style={{ width: '100%', height: '100%' }} />;
}
