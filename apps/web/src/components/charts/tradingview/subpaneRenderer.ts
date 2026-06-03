import { createChart, ColorType, type IChartApi, type UTCTimestamp } from "lightweight-charts";
import { type IndicatorResult } from "@/utils/indicators";

export function drawSubPanes(
  charts: IChartApi[],
  indResults: IndicatorResult,
  subPaneHeight: number,
  rsi: boolean,
  rsiContainer: HTMLDivElement | null,
  rsiChartRef: React.MutableRefObject<IChartApi | null>,
  macd: boolean,
  macdContainer: HTMLDivElement | null,
  macdChartRef: React.MutableRefObject<IChartApi | null>,
  atr: boolean,
  atrContainer: HTMLDivElement | null,
  atrChartRef: React.MutableRefObject<IChartApi | null>
) {
  // A. RSI Sub-Pane
  if (rsi && rsiContainer) {
    const rsiChart = createChart(rsiContainer, {
      autoSize: false,
      height: subPaneHeight,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8B97A8",
      },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.12)" },
      timeScale: { visible: false, borderColor: "rgba(255,255,255,0.12)" },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      crosshair: {
        vertLine: { color: "rgba(0,212,245,0.45)", width: 1 },
        horzLine: { color: "rgba(0,212,245,0.45)", width: 1 },
      },
    });
    rsiChartRef.current = rsiChart;
    charts.push(rsiChart);

    const rsiSeries = rsiChart.addLineSeries({
      color: "#2196F3",
      lineWidth: 2,
      priceLineVisible: false,
      title: "RSI (14)"
    });
    if (indResults.rsi) {
      rsiSeries.setData(indResults.rsi.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.value })));
    }
    rsiSeries.createPriceLine({ price: 70, color: "rgba(255, 59, 92, 0.4)", lineWidth: 1, lineStyle: 2, title: "OB" });
    rsiSeries.createPriceLine({ price: 30, color: "rgba(0, 230, 118, 0.4)", lineWidth: 1, lineStyle: 2, title: "OS" });
  }

  // B. MACD Sub-Pane
  if (macd && macdContainer) {
    const macdChart = createChart(macdContainer, {
      autoSize: false,
      height: subPaneHeight,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8B97A8",
      },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.12)" },
      timeScale: { visible: false, borderColor: "rgba(255,255,255,0.12)" },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      crosshair: {
        vertLine: { color: "rgba(0,212,245,0.45)", width: 1 },
        horzLine: { color: "rgba(0,212,245,0.45)", width: 1 },
      },
    });
    macdChartRef.current = macdChart;
    charts.push(macdChart);

    const macdSeries = macdChart.addLineSeries({ color: "#2196F3", lineWidth: 2, priceLineVisible: false, title: "MACD" });
    const signalSeries = macdChart.addLineSeries({ color: "#FF9800", lineWidth: 2, priceLineVisible: false, title: "Signal" });
    const histSeries = macdChart.addHistogramSeries({
      priceFormat: { type: "custom", formatter: (v: number) => v.toFixed(2) },
      priceLineVisible: false
    });

    if (indResults.macd) {
      macdSeries.setData(indResults.macd.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.macd })));
      signalSeries.setData(indResults.macd.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.signal })));
      histSeries.setData(indResults.macd.map(pt => ({
        time: pt.time as UTCTimestamp,
        value: pt.histogram,
        color: pt.histogram >= 0 ? "rgba(0, 230, 118, 0.4)" : "rgba(255, 59, 92, 0.4)"
      })));
    }
  }

  // C. ATR Sub-Pane
  if (atr && atrContainer) {
    const atrChart = createChart(atrContainer, {
      autoSize: false,
      height: subPaneHeight,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#8B97A8",
      },
      rightPriceScale: { borderColor: "rgba(255,255,255,0.12)" },
      timeScale: { visible: false, borderColor: "rgba(255,255,255,0.12)" },
      grid: {
        vertLines: { color: "rgba(255,255,255,0.04)" },
        horzLines: { color: "rgba(255,255,255,0.04)" },
      },
      crosshair: {
        vertLine: { color: "rgba(0,212,245,0.45)", width: 1 },
        horzLine: { color: "rgba(0,212,245,0.45)", width: 1 },
      },
    });
    atrChartRef.current = atrChart;
    charts.push(atrChart);

    const atrSeries = atrChart.addLineSeries({ color: "#EC4899", lineWidth: 2, priceLineVisible: false, title: "ATR (14)" });
    if (indResults.atr) {
      atrSeries.setData(indResults.atr.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.value })));
    }
  }
}
