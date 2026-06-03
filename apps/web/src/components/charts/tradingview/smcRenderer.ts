import { type IChartApi } from "lightweight-charts";
import { type IndicatorResult } from "@/utils/indicators";
import { type PriceBar, toUtcTimestamp } from "@/utils/chartFormatters";

export function drawSMC(
  mainChart: IChartApi,
  indResults: IndicatorResult,
  bars: PriceBar[]
) {
  if (!indResults.smc) return;

  // 1. Order Blocks
  indResults.smc.orderBlocks.forEach((ob, idx) => {
    const color = ob.type === "bullish" ? "rgba(0, 230, 118, 0.45)" : "rgba(255, 59, 92, 0.45)";
    const label = ob.type === "bullish" ? `Bull OB ${idx+1}` : `Bear OB ${idx+1}`;
    const topSeries = mainChart.addLineSeries({ color, lineWidth: 1, lineStyle: 1, priceLineVisible: false, title: label });
    const bottomSeries = mainChart.addLineSeries({ color, lineWidth: 1, lineStyle: 1, priceLineVisible: false });
    
    const lastBar = bars[bars.length - 1];
    if (lastBar) {
      topSeries.setData([
        { time: toUtcTimestamp(ob.startTime as string), value: ob.top },
        { time: toUtcTimestamp(lastBar.timestamp), value: ob.top }
      ]);
      bottomSeries.setData([
        { time: toUtcTimestamp(ob.startTime as string), value: ob.bottom },
        { time: toUtcTimestamp(lastBar.timestamp), value: ob.bottom }
      ]);
    }
  });

  // 2. Fair Value Gaps
  indResults.smc.fairValueGaps.forEach((fvg, idx) => {
    const color = fvg.type === "bullish" ? "rgba(255, 179, 0, 0.35)" : "rgba(156, 39, 176, 0.35)";
    const label = fvg.type === "bullish" ? `Bull FVG ${idx+1}` : `Bear FVG ${idx+1}`;
    const topSeries = mainChart.addLineSeries({ color, lineWidth: 1, lineStyle: 2, priceLineVisible: false, title: label });
    const bottomSeries = mainChart.addLineSeries({ color, lineWidth: 1, lineStyle: 2, priceLineVisible: false });

    const lastBar = bars[bars.length - 1];
    if (lastBar) {
      topSeries.setData([
        { time: toUtcTimestamp(fvg.time as string), value: fvg.top },
        { time: toUtcTimestamp(lastBar.timestamp), value: fvg.top }
      ]);
      bottomSeries.setData([
        { time: toUtcTimestamp(fvg.time as string), value: fvg.bottom },
        { time: toUtcTimestamp(lastBar.timestamp), value: fvg.bottom }
      ]);
    }
  });

  // 3. Liquidity Zones
  indResults.smc.liquidityZones.forEach((liq) => {
    const color = liq.type === "bsl" ? "rgba(245, 0, 87, 0.4)" : "rgba(0, 229, 255, 0.4)";
    const style = liq.isSwept ? 2 : 0; // Swept is dashed, active is solid
    const title = liq.type === "bsl" ? "BSL" : "SSL";
    
    const lineSeries = mainChart.addLineSeries({
      color,
      lineWidth: 1,
      lineStyle: style,
      priceLineVisible: false,
      title,
    });

    const lastBar = bars[bars.length - 1];
    if (lastBar) {
      lineSeries.setData([
        { time: toUtcTimestamp(liq.time as string), value: liq.level },
        { time: toUtcTimestamp(lastBar.timestamp), value: liq.level }
      ]);
    }
  });
}
