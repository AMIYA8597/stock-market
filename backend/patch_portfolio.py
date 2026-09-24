import re

with open('app/api/v1/portfolio.py', 'r') as f:
    content = f.read()

content = content.replace("from app.models.payment import PaymentTransaction", "from app.models.paper_trading import PaperWallet")

pattern = r"select\(func\.coalesce\(func\.sum\(PaymentTransaction\.amount\),\s*0\)\)\.where\([\s\S]*?status\s*==\s*\"succeeded\"[\s\S]*?\)"

content = re.sub(pattern, "select(PaperWallet.balance).where(PaperWallet.user_id == uid)", content)

with open('app/api/v1/portfolio.py', 'w') as f:
    f.write(content)
