import re
with open('app/api/v1/portfolio.py', 'r') as f:
    text = f.read()

text = text.replace("from app.models.payment import PaymentTransaction", "from app.models.paper_trading import PaperWallet")

pattern = r"select\(func\.coalesce\(func\.sum\(PaymentTransaction\.amount\),\s*0\)\)\.where\(\s*and_\(PaymentTransaction\.user_id == uid,\s*PaymentTransaction\.status == \"succeeded\"\)\s*\)"
replacement = "select(PaperWallet.balance).where(PaperWallet.user_id == uid)"
text = re.sub(pattern, replacement, text)

with open('app/api/v1/portfolio.py', 'w') as f:
    f.write(text)
