import re
with open("apps/web/src/types/intelligence.ts", "r", encoding="utf-8") as f:
    content = f.read()

# Replace all 
umber with 
umber | null inside models (except where not needed, but doing globally for number fields is easiest if we restrict to interfaces).
# It's better to just use a script to replace 
umber; with 
umber | null; and 
umber | undefined; with 
umber | null; in that file, or maybe just change asNumber to return ny for now? No, wait!

content = re.sub(r': number;', ': number | null;', content)
content = re.sub(r': number \s*\| \s*undefined;', ': number | null;', content)

with open("apps/web/src/types/intelligence.ts", "w", encoding="utf-8") as f:
    f.write(content)
