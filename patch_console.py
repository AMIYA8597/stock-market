import re
import os

files_to_clean = [
    "apps/web/src/components/auth/AuthGuard.tsx",
    "apps/web/src/lib/api-client.ts",
    "apps/web/src/utils/chartFormatters.ts",
    "apps/web/src/hooks/useChartInstance.ts",
    "apps/web/src/components/charts/LightweightCandlestickChart.tsx",
    "apps/web/src/hooks/useTerminalData.ts"
]

for file_path in files_to_clean:
    if not os.path.exists(file_path):
        continue
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Simple regex to remove console.log and console.warn calls
    content = re.sub(r'^\s*console\.(log|warn)\(.*?\);\s*$', '', content, flags=re.MULTILINE)
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
