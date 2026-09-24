import re

with open("apps/web/src/modules/dashboard/DashboardOverview.tsx", "r", encoding="utf-8") as f:
    text = f.read()

# Remove recharts imports
text = re.sub(r'import \{ Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis \} from "recharts";', 
              'import { createChart, ColorType, AreaSeries, LineSeries } from "lightweight-charts";\nimport { useRef, useEffect } from "react";', text)

# Rewrite the chart component
chart_code = """<div className="h-[320px]" ref={(node) => {
                if (node) {
                  // Only run once when the node mounts or data changes
                  if ((node as any)._chart) return;
                  const chart = createChart(node, {
                    layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: 'rgba(255,255,255,0.45)' },
                    grid: { vertLines: { color: 'rgba(255,255,255,0.08)' }, horzLines: { color: 'rgba(255,255,255,0.08)' } },
                    rightPriceScale: { borderVisible: false },
                    timeScale: { borderVisible: false, timeVisible: true }
                  });
                  (node as any)._chart = chart;

                  const benchmarkSeries = chart.addSeries(LineSeries, {
                    color: '#8B9BB4', lineWidth: 2
                  });
                  const portfolioSeries = chart.addSeries(AreaSeries, {
                    lineColor: '#00D4F5', topColor: 'rgba(0, 212, 245, 0.35)', bottomColor: 'rgba(0, 212, 245, 0.02)', lineWidth: 2.5
                  });
                  
                  const benchData = performanceSeries.map((d, i) => ({ time: i, value: d.benchmark }));
                  const portData = performanceSeries.map((d, i) => ({ time: i, value: d.value }));
                  benchmarkSeries.setData(benchData as any);
                  portfolioSeries.setData(portData as any);
                  chart.timeScale().fitContent();
                  
                  const resize = () => { chart.applyOptions({ width: node.clientWidth }); };
                  window.addEventListener('resize', resize);
                }
              }} />"""

old_chart = r"""<ResponsiveContainer width="100%" height="100%">.*?<\/ResponsiveContainer>"""
text = re.sub(old_chart, chart_code, text, flags=re.DOTALL)

with open("apps/web/src/modules/dashboard/DashboardOverview.tsx", "w", encoding="utf-8") as f:
    f.write(text)
print("Patched DashboardOverview.tsx")
