import re

def add_import(file, imp):
    with open(file, 'r', encoding='utf-8') as f:
        text = f.read()
    if imp not in text:
        text = imp + "\n" + text
        with open(file, 'w', encoding='utf-8') as f:
            f.write(text)

add_import("apps/web/src/components/terminal/panes/AlertsManager.tsx", "import { createClient } from '@/lib/supabase/client';")
add_import("apps/web/src/lib/contracts-api.ts", "import { createClient } from '@/lib/supabase/client';")

with open("apps/web/src/hooks/useSignalAlerts.ts", "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace("direction?: string;", "direction: string;")
text = text.replace("signal_score?: number;", "signal_score: number;")
text = text.replace("confidence?: number;", "confidence: number;")
text = text.replace("current_price?: number;", "current_price: number;")
text = text.replace("timestamp?: string;", "timestamp: string;")
text = text.replace("message?: string;", "message: string;")
with open("apps/web/src/hooks/useSignalAlerts.ts", "w", encoding="utf-8") as f:
    f.write(text)

with open("apps/web/src/modules/dashboard/DashboardOverview.tsx", "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace("lineWidth: 2.5", "lineWidth: 2")
with open("apps/web/src/modules/dashboard/DashboardOverview.tsx", "w", encoding="utf-8") as f:
    f.write(text)
    
with open("apps/web/src/components/terminal/panes/PaperTradePanel.tsx", "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace('limit_price: orderType === "LIMIT" ? parsedPrice : undefined,', 'limit_price: orderType === "LIMIT" ? (parsedPrice as number) : undefined,')
with open("apps/web/src/components/terminal/panes/PaperTradePanel.tsx", "w", encoding="utf-8") as f:
    f.write(text)

with open("apps/web/src/components/common/global-toast.tsx", "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace('visibleAlert.direction', 'visibleAlert.direction!')
with open("apps/web/src/components/common/global-toast.tsx", "w", encoding="utf-8") as f:
    f.write(text)

print("Fixed type errors")
