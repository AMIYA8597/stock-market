with open('apps/web/src/components/terminal/panes/PaperTradePanel.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

old_price = 'const parsedPrice = orderType === "MARKET" ? (liveTick?.price || 0) : Number(price);'
new_price = '''
    const parsedPrice = orderType === "MARKET" ? liveTick?.price : Number(price);
    if (orderType === "MARKET" && typeof parsedPrice !== "number") {
      setMessage({ type: "error", text: "Cannot place MARKET order: Live price unavailable." });
      return;
    }
'''

if old_price in text:
    text = text.replace(old_price, new_price)
    with open('apps/web/src/components/terminal/panes/PaperTradePanel.tsx', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Patched parsedPrice")
else:
    print("Not found parsedPrice")
