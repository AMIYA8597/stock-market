import re
with open("apps/web/src/components/terminal/SignalPanel.tsx", "r", encoding="utf-8") as f:
    content = f.read()

content = re.sub(r'    if \(tradingMode === "LIVE"\) \{\n      setTypedPhrase\(""\);\n      setShowConfirmModal\(true\);\n    \} else \{\n      void executePlaceOrder\(\);\n    \}', '    void executePlaceOrder();', content, flags=re.DOTALL)
content = re.sub(r'    if \(false\) \{\n      setTypedPhrase\(""\);\n      setShowConfirmModal\(true\);\n    \} else \{\n      void executePlaceOrder\(\);\n    \}', '    void executePlaceOrder();', content, flags=re.DOTALL)
content = re.sub(r'      setShowConfirmModal\(true\);', '', content)
content = re.sub(r'      setTypedPhrase\(""\);', '', content)

with open("apps/web/src/components/terminal/SignalPanel.tsx", "w", encoding="utf-8") as f:
    f.write(content)
