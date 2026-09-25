import re

with open('apps/web/src/components/terminal/panes/AlertsManager.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = re.sub(
    r'const supabase = createClient\(\); const \{ data: \{ session \} \} = await supabase\.auth\.getSession\(\); const token = session\?\.access_token \|\| "";\n?',
    '',
    text
)

text = re.sub(
    r'const supabase = createClient\(\);\n?\s*const \{ data: \{ session \} \} = await supabase\.auth\.getSession\(\);\n?\s*const token = session\?\.access_token \|\| "";\n?',
    '',
    text
)

with open('apps/web/src/components/terminal/panes/AlertsManager.tsx', 'w', encoding='utf-8') as f:
    f.write(text)
