with open('app/api/v1/portfolio.py', 'r') as f:
    text = f.read()

import re
text = re.sub(r'select\(PaperWallet\.balance\)\.where\(PaperWallet\.user_id == uid\)[\s\)]*', 'select(PaperWallet.balance).where(PaperWallet.user_id == uid)\n        )\n', text)

with open('app/api/v1/portfolio.py', 'w') as f:
    f.write(text)
