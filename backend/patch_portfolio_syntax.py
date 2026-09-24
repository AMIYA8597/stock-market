with open('app/api/v1/portfolio.py', 'r') as f:
    content = f.read()

content = content.replace("select(PaperWallet.balance).where(PaperWallet.user_id == uid)\n        )\n    )", "select(PaperWallet.balance).where(PaperWallet.user_id == uid)\n    )")
content = content.replace("select(PaperWallet.balance).where(PaperWallet.user_id == uid)\n                )\n            )", "select(PaperWallet.balance).where(PaperWallet.user_id == uid)\n            )")
content = content.replace("select(PaperWallet.balance).where(PaperWallet.user_id == uid)\n                    )", "select(PaperWallet.balance).where(PaperWallet.user_id == uid)")
content = content.replace("select(PaperWallet.balance).where(PaperWallet.user_id == uid)\n        )", "select(PaperWallet.balance).where(PaperWallet.user_id == uid)")


with open('app/api/v1/portfolio.py', 'w') as f:
    f.write(content)
