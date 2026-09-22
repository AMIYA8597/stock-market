import re

with open('backend/app/api/v1/models.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 6. Model monitor: remove the adwin_p = ks_p mislabel; rename to what is computed
content = re.sub(
    r'adwin_p = ks_p',
    '',
    content
)
content = re.sub(
    r'adwin_p_value=Decimal\(str\(round\(adwin_p, 6\)\)\),',
    '',
    content
)

with open('backend/app/api/v1/models.py', 'w', encoding='utf-8') as f:
    f.write(content)
