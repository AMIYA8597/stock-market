import re
with open("apps/web/src/components/terminal/Watchlist.tsx", "r", encoding="utf-8") as f:
    content = f.read()

replacement = '''                  }}
                  title={false ? "Live Broker Feed" : \ - \}
                >
                  {false ? "LIVE" : "DLY"}
'''

content = re.sub(r'                  \}\\}\n                  title=\{tick.source.toLowerCase\(\) === "nse" \? "NSE live" : \$\{tick.source\} \(delayed\)\}\n                >\n                  \{tick.source.toLowerCase\(\) === "nse" \? "LIVE" : "DLY"\}', replacement, content)

with open("apps/web/src/components/terminal/Watchlist.tsx", "w", encoding="utf-8") as f:
    f.write(content)
