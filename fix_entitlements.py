with open('apps/web/src/hooks/useEntitlements.ts', 'r') as f:
    text = f.read()

import_statement = "import { createClient } from '@/lib/supabase/client';\n"
if "import { createClient }" not in text:
    text = import_statement + text

text = text.replace('const token = localStorage.getItem("nq_access_token");', 'const supabase = createClient(); const { data: { session } } = await supabase.auth.getSession(); const token = session?.access_token || "";')
with open('apps/web/src/hooks/useEntitlements.ts', 'w') as f:
    f.write(text)
