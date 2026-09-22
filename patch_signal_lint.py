import re
with open("apps/web/src/components/terminal/SignalPanel.tsx", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r'  const \{ orders, addOrder, clearOrders \} = useOrderHistory\(\);\n', '  const { addOrder } = useOrderHistory();\n', content)
content = re.sub(r'  const feedStatus = usePriceFeed\(\["\^NSEI"\]\).status;\n', '', content)
content = re.sub(r'  const expectedPhrase = \$\{side\} \$\{signal\?.symbol \? signal.symbol.split\("\."\)\[0\]\?.toUpperCase\(\) : "STOCK"\} \$\{quantity\};\n', '', content)

with open("apps/web/src/components/terminal/SignalPanel.tsx", "w", encoding="utf-8") as f:
    f.write(content)
