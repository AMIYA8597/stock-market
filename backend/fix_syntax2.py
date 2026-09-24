with open('app/api/v1/portfolio.py', 'r') as f:
    text = f.read()

import re
text = re.sub(r'select\(PaperWallet\.balance\)\.where\(PaperWallet\.user_id == uid\)\n        \)\ninitial_cap', 'select(PaperWallet.balance).where(PaperWallet.user_id == uid)\n    )\n    initial_cap', text)
text = re.sub(r'select\(PaperWallet\.balance\)\.where\(PaperWallet\.user_id == uid\)\n        \)\ntotal_deposits', 'select(PaperWallet.balance).where(PaperWallet.user_id == uid)\n        )\n        total_deposits', text)
text = re.sub(r'select\(PaperWallet\.balance\)\.where\(PaperWallet\.user_id == uid\)\n        \)\ntotal_funds_added', 'select(PaperWallet.balance).where(PaperWallet.user_id == uid)\n        )\n        total_funds_added', text)

# Just in case, fix indentation of initial_cap anywhere
text = re.sub(r'\ninitial_cap =', '\n    initial_cap =', text)
text = re.sub(r'\ntotal_deposits =', '\n        total_deposits =', text)
text = re.sub(r'\ntotal_funds_added =', '\n        total_funds_added =', text)


with open('app/api/v1/portfolio.py', 'w') as f:
    f.write(text)
