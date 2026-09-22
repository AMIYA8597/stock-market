import re

with open("apps/web/src/components/terminal/SignalPanel.tsx", "r", encoding="utf-8") as f:
    content = f.read()

# Remove useAuditLogsQuery import
content = re.sub(r'import \{ useAuditLogsQuery \} from "@/hooks/queries/useTrading";\n', '', content)

# Remove auditLogsData hook
content = re.sub(r'  const \{ data: auditLogsData, refetch: fetchAuditLogs \} = useAuditLogsQuery\(\);\n', '', content)
content = re.sub(r'  const auditLogs = auditLogsData\?.logs \?\? \[\];\n', '', content)

# Remove showConfirmModal and typedPhrase
content = re.sub(r'  const \[showConfirmModal, setShowConfirmModal\] = useState<boolean>\(false\);\n', '', content)
content = re.sub(r'  const \[typedPhrase, setTypedPhrase\] = useState<string>\(""\);\n', '', content)

# Remove LIVE block in handlePlaceOrder
content = re.sub(r'    if \(false\) \{\n      setTypedPhrase\(""\);\n      setShowConfirmModal\(true\);\n    \} else \{\n      void executePlaceOrder\(\);\n    \}', '    void executePlaceOrder();', content)

# Remove Live Audit Log Console UI
content = re.sub(r'      <div className="mt-3 rounded border border-\[var\(--nq-border\)\].*?<div className="text-center opacity-60 py-4 font-mono text-\[9px\]">No trading activity logged in this session.</div>\n          \)\}\n        </div>\n      </div>', '', content, flags=re.DOTALL)

# Remove Confirm Modal UI
content = re.sub(r'      \{showConfirmModal && \(\n        <div className="fixed inset-0 z-50.*?</div>\n        </div>\n      \)\}', '', content, flags=re.DOTALL)


with open("apps/web/src/components/terminal/SignalPanel.tsx", "w", encoding="utf-8") as f:
    f.write(content)
