with open('apps/web/src/components/terminal/panes/AlertsManager.tsx', 'r') as f:
    text = f.read()

text = text.replace('const token = localStorage.getItem("nq_access_token") || "";', 'const supabase = createClient(); const { data: { session } } = await supabase.auth.getSession(); const token = session?.access_token || "";')
with open('apps/web/src/components/terminal/panes/AlertsManager.tsx', 'w') as f:
    f.write(text)
