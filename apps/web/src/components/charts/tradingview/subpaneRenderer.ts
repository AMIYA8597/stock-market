import { type IChartApi, type UTCTimestamp , LineSeries, HistogramSeries} from 'lightweight-charts';
import { type IndicatorResult } from "@/utils/indicators";

export function drawSubPanes(
  mainChart: IChartApi,
  indResults: IndicatorResult,
  rsi: boolean,
  macd: boolean,
  atr: boolean,
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  addedSeries: any[]
) {
  let currentPaneIndex = 1;

  // A. RSI Sub-Pane
  if (rsi && indResults.rsi) {
    const rsiSeries = mainChart.addSeries(LineSeries, {
      color: "#2196F3",
      lineWidth: 2,
      priceLineVisible: false,
      title: "RSI (14)"
    }, currentPaneIndex);
    
    rsiSeries.setData(indResults.rsi.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.value })));
    rsiSeries.createPriceLine({ price: 70, color: "rgba(255, 59, 92, 0.4)", lineWidth: 1, lineStyle: 2, title: "OB" });
    rsiSeries.createPriceLine({ price: 30, color: "rgba(0, 230, 118, 0.4)", lineWidth: 1, lineStyle: 2, title: "OS" });
    
    addedSeries.push(rsiSeries);
    currentPaneIndex++;
  }

  // B. MACD Sub-Pane
  if (macd && indResults.macd) {
    const macdSeries = mainChart.addSeries(LineSeries, { color: "#2196F3", lineWidth: 2, priceLineVisible: false, title: "MACD" }, currentPaneIndex);
    const signalSeries = mainChart.addSeries(LineSeries, { color: "#FF9800", lineWidth: 2, priceLineVisible: false, title: "Signal" }, currentPaneIndex);
    const histSeries = mainChart.addSeries(HistogramSeries, {
      priceFormat: { type: "custom", formatter: (v: number) => v.toFixed(2) },
      priceLineVisible: false
    }, currentPaneIndex);

    macdSeries.setData(indResults.macd.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.macd })));
    signalSeries.setData(indResults.macd.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.signal })));
    histSeries.setData(indResults.macd.map(pt => ({
      time: pt.time as UTCTimestamp,
      value: pt.histogram,
      color: pt.histogram >= 0 ? "rgba(0, 230, 118, 0.4)" : "rgba(255, 59, 92, 0.4)"
    })));

    addedSeries.push(macdSeries, signalSeries, histSeries);
    currentPaneIndex++;
  }

  // C. ATR Sub-Pane
  if (atr && indResults.atr) {
    const atrSeries = mainChart.addSeries(LineSeries, { color: "#EC4899", lineWidth: 2, priceLineVisible: false, title: "ATR (14)" }, currentPaneIndex);
    atrSeries.setData(indResults.atr.map(pt => ({ time: pt.time as UTCTimestamp, value: pt.value })));
    
    addedSeries.push(atrSeries);
    currentPaneIndex++;
  }
}

