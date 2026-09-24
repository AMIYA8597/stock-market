with open('apps/web/src/lib/realtime.ts', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('import { createClient } from "@/lib/supabase/client";\n"use client";', '"use client";\nimport { createClient } from "@/lib/supabase/client";')
text = text.replace('import { createClient } from \'@/lib/supabase/client\';\n"use client";', '"use client";\nimport { createClient } from \'@/lib/supabase/client\';')

with open('apps/web/src/lib/realtime.ts', 'w', encoding='utf-8') as f:
    f.write(text)
print('Fixed realtime.ts')
