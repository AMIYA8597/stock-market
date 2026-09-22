import re
with open("apps/web/src/components/terminal/SignalPanel.tsx", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r'    setShowConfirmModal\(false\);\n', '', content)
content = re.sub(r'    if \(false\) \{\n.*?setShowConfirmModal\(true\);\n.*?\n      void executePlaceOrder\(\);\n    \}', '    void executePlaceOrder();', content, flags=re.DOTALL)
content = re.sub(r'  const expectedPhrase = \$\{side\} \$\{signal\?.symbol \? signal.symbol.split\("\."\)\[0\]\?.toUpperCase\(\) : "STOCK"\} \$\{quantity\};', '', content)

with open("apps/web/src/components/terminal/SignalPanel.tsx", "w", encoding="utf-8") as f:
    f.write(content)
