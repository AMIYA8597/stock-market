import re

with open('apps/web/src/modules/dashboard/UserProfilePage.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('fallback="AK"', 'fallback={fullName ? fullName.substring(0, 2).toUpperCase() : "U"}')

with open('apps/web/src/modules/dashboard/UserProfilePage.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched AK')
