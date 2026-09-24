with open('apps/web/src/components/terminal/panes/SignalsTab.tsx', 'r', encoding='utf-8') as f:
    text = f.read()
import re
text = re.sub(r'₹\{pt\.predicted_price\.toLocaleString\([^)]*\)\}', r'{typeof pt.predicted_price === "number" ? `₹${pt.predicted_price.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "N/A"}', text)
with open('apps/web/src/components/terminal/panes/SignalsTab.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
print("Patched SignalsTab")
