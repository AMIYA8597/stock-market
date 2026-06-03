import { useEffect, useState } from "react";
import { createChart, ColorType, type IChartApi } from "lightweight-charts";

export interface LiveChartApi extends IChartApi {
  isAlive?: boolean;
}

interface UseChartInstanceProps {
  containerRef: React.RefObject<HTMLDivElement>;
  height: number;
  activeSubPanes: number;
}

export function useChartInstance({
  containerRef,
  height,
  activeSubPanes,
}: UseChartInstanceProps) {
  const [chart, setChart] = useState<LiveChartApi | null>(null);

  const subPaneHeight = 110;
  const mainChartHeight = Math.max(220, height - activeSubPanes * subPaneHeight);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const chartInstance = createChart(element, {
      autoSize: false,
      height: mainChartHeight,
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
    }) as LiveChartApi;

    chartInstance.isAlive = true;
    setChart(chartInstance);

    return () => {
      chartInstance.isAlive = false;
      chartInstance.remove();
      setChart(null);
    };
  }, [containerRef, mainChartHeight]);

  return {
    chart,
    mainChartHeight,
  };
}
