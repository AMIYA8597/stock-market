import { type IChartApi, type UTCTimestamp } from "lightweight-charts";
import { type IndicatorResult } from "@/utils/indicators";
import { buildEma, buildSma, buildBollingerBands } from "@/utils/chartFormatters";

interface IndicatorsOptions {
  ema9?: boolean;
  ema21?: boolean;
  ema50?: boolean;
  ema200?: boolean;
  sma20?: boolean;
  sma50?: boolean;
  sma100?: boolean;
  bollingerBands?: boolean;
  superTrend?: boolean;
  ichimoku?: boolean;
  vwap?: boolean;
}

export function drawIndicators(
  mainChart: IChartApi,
  indicators: IndicatorsOptions,
  closes: number[],
  times: UTCTimestamp[],
  indResults: IndicatorResult,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  addedSeries: any[]
) {
  const {
    ema9,
    ema21,
    ema50,
    ema200,
    sma20,
    sma50,
    sma100,
    bollingerBands,
    superTrend,
    ichimoku,
    vwap,
  } = indicators;

  // 1. Moving Averages
  if (ema9) {
    const data = buildEma(closes, 9);
    const series = mainChart.addLineSeries({
      color: "#00D4F5",
      lineWidth: 1,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });
    series.setData(times.map((time, idx) => ({ time, value: data[idx] ?? closes[idx] ?? 0 })));
    addedSeries.push(series);
  }

  if (ema21) {
    const data = buildEma(closes, 21);
    const series = mainChart.addLineSeries({
      color: "#8B5CF6",
      lineWidth: 1,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });
    series.setData(times.map((time, idx) => ({ time, value: data[idx] ?? closes[idx] ?? 0 })));
    addedSeries.push(series);
  }

  if (ema50) {
    const data = buildEma(closes, 50);
    const series = mainChart.addLineSeries({
      color: "#FFB800",
      lineWidth: 1,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });
    series.setData(times.map((time, idx) => ({ time, value: data[idx] ?? closes[idx] ?? 0 })));
    addedSeries.push(series);
  }

  if (ema200) {
    const data = buildEma(closes, 200);
    const series = mainChart.addLineSeries({
      color: "#EC4899",
      lineWidth: 2,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });
    series.setData(times.map((time, idx) => ({ time, value: data[idx] ?? closes[idx] ?? 0 })));
    addedSeries.push(series);
  }

  if (sma20) {
    const data = buildSma(closes, 20);
    const series = mainChart.addLineSeries({
      color: "#3B82F6",
      lineWidth: 1,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });
    series.setData(times.map((time, idx) => ({ time, value: data[idx] ?? closes[idx] ?? 0 })));
    addedSeries.push(series);
  }

  if (sma50) {
    const data = buildSma(closes, 50);
    const series = mainChart.addLineSeries({
      color: "#EF4444",
      lineWidth: 1,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });
    series.setData(times.map((time, idx) => ({ time, value: data[idx] ?? closes[idx] ?? 0 })));
    addedSeries.push(series);
  }

  if (sma100) {
    const data = buildSma(closes, 100);
    const series = mainChart.addLineSeries({
      color: "#10B981",
      lineWidth: 1,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });
    series.setData(times.map((time, idx) => ({ time, value: data[idx] ?? closes[idx] ?? 0 })));
    addedSeries.push(series);
  }

  // 2. Bollinger Bands
  if (bollingerBands) {
    const bb = buildBollingerBands(closes, 20, 2);
    const bbUpperSeries = mainChart.addLineSeries({
      color: "rgba(0, 212, 245, 0.4)",
      lineWidth: 1,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });
    const bbBasisSeries = mainChart.addLineSeries({
      color: "rgba(0, 212, 245, 0.2)",
      lineWidth: 1,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });
    const bbLowerSeries = mainChart.addLineSeries({
      color: "rgba(0, 212, 245, 0.4)",
      lineWidth: 1,
      priceLineVisible: false,
      crosshairMarkerVisible: false,
    });

    bbUpperSeries.setData(times.map((time, idx) => ({ time, value: bb.upper[idx] ?? closes[idx] ?? 0 })));
    bbBasisSeries.setData(times.map((time, idx) => ({ time, value: bb.middle[idx] ?? closes[idx] ?? 0 })));
    bbLowerSeries.setData(times.map((time, idx) => ({ time, value: bb.lower[idx] ?? closes[idx] ?? 0 })));

    addedSeries.push(bbUpperSeries);
    addedSeries.push(bbBasisSeries);
    addedSeries.push(bbLowerSeries);
  }

  // 3. VWAP
  if (vwap && indResults.vwap) {
    const vwapSeries = mainChart.addLineSeries({
      color: "#F50057",
      lineWidth: 2,
      priceLineVisible: false,
      title: "VWAP",
    });
    vwapSeries.setData(indResults.vwap.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.value })));
    addedSeries.push(vwapSeries);
  }

  // 4. SuperTrend
  if (superTrend && indResults.superTrend) {
    const stSeries = mainChart.addLineSeries({
      color: "#FF9800",
      lineWidth: 2,
      priceLineVisible: false,
      title: "SuperTrend",
    });
    stSeries.setData(indResults.superTrend.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.value })));
    addedSeries.push(stSeries);
  }

  // 5. Ichimoku Cloud
  if (ichimoku && indResults.ichimoku) {
    const tenkanSeries = mainChart.addLineSeries({ color: "#2196F3", lineWidth: 1, priceLineVisible: false, title: "Tenkan" });
    const kijunSeries = mainChart.addLineSeries({ color: "#FF1744", lineWidth: 1, priceLineVisible: false, title: "Kijun" });
    const senkouASeries = mainChart.addLineSeries({ color: "#4CAF50", lineWidth: 1, lineStyle: 2, priceLineVisible: false, title: "Senkou A" });
    const senkouBSeries = mainChart.addLineSeries({ color: "#FF5722", lineWidth: 1, lineStyle: 2, priceLineVisible: false, title: "Senkou B" });

    tenkanSeries.setData(indResults.ichimoku.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.tenkan })));
    kijunSeries.setData(indResults.ichimoku.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.kijun })));
    senkouASeries.setData(indResults.ichimoku.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.senkouA })));
    senkouBSeries.setData(indResults.ichimoku.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.senkouB })));

    addedSeries.push(tenkanSeries);
    addedSeries.push(kijunSeries);
    addedSeries.push(senkouASeries);
    addedSeries.push(senkouBSeries);
  }
}


