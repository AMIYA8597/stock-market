import { useEffect, useState } from "react";
import { createChart, ColorType, LineStyle, type IChartApi } from "lightweight-charts";

export interface LiveChartApi extends IChartApi {
  isAlive?: boolean;
}

interface UseChartInstanceProps {
  containerRef: React.RefObject<HTMLDivElement>;
  height?: number;
  activeSubPanes?: number;
}

export function useChartInstance({
  containerRef,
  height,
  activeSubPanes = 0,
}: UseChartInstanceProps) {
  const [chart, setChart] = useState<LiveChartApi | null>(null);

  const subPaneHeight = 110;
  const mainChartHeight = height ? Math.max(220, height - activeSubPanes * subPaneHeight) : undefined;

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const chartInstance = createChart(element, {
      autoSize: true,
      ...(mainChartHeight ? { height: mainChartHeight } : {}),
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8B97A8",
        fontFamily: "'JetBrains Mono', 'Courier New', monospace",
        fontSize: 11,
      },
      rightPriceScale: {
        borderColor: "rgba(255,255,255,0.08)",
        scaleMargins: { top: 0.08, bottom: 0.12 },
      },
      leftPriceScale: { visible: false },
      timeScale: {
        borderColor: "rgba(255,255,255,0.08)",
        timeVisible: true,
        secondsVisible: false,
        fixLeftEdge: false,
        fixRightEdge: false,
      },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)", style: LineStyle.Dotted },
        horzLines: { color: "rgba(255,255,255,0.04)", style: LineStyle.Dotted },
      },
      crosshair: {
        mode: 1,
        vertLine: { color: "rgba(0,212,245,0.4)", width: 1, style: LineStyle.Dashed, labelBackgroundColor: "#0a0e18" },
        horzLine: { color: "rgba(0,212,245,0.4)", width: 1, style: LineStyle.Dashed, labelBackgroundColor: "#0a0e18" },
      },
      handleScale: {
        axisPressedMouseMove: { time: true, price: true },
        mouseWheel: true,
        pinch: true,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
    }) as LiveChartApi;

    chartInstance.isAlive = true;
    setChart(chartInstance);

    return () => {
      chartInstance.isAlive = false;
      try { chartInstance.remove(); } catch { /* already removed */ }
      setChart(null);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [containerRef]);

  return {
    chart,
    mainChartHeight,
  };
}
