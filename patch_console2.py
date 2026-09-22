import re
with open("apps/web/src/components/charts/LightweightCandlestickChart.tsx", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r'    console\.log\(\n.*?\]\n    \);', '', content, flags=re.DOTALL)
with open("apps/web/src/components/charts/LightweightCandlestickChart.tsx", "w", encoding="utf-8") as f:
    f.write(content)

with open("apps/web/src/components/charts/tradingview/useChartInstance.ts", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r'    console\.log\(.*?\);\n', '', content)
with open("apps/web/src/components/charts/tradingview/useChartInstance.ts", "w", encoding="utf-8") as f:
    f.write(content)
