import re

with open('apps/web/src/modules/payments/PaymentPages.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

# Remove sub_mock handling
text = re.sub(r'if \(res\.subscription_id\.startsWith\("sub_mock_"\)\) \{.*?return;\s*\}', '', text, flags=re.DOTALL)

with open('apps/web/src/modules/payments/PaymentPages.tsx', 'w', encoding='utf-8') as f:
    f.write(text)

print('Patched PaymentPages.tsx')
