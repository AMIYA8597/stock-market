with open('apps/web/src/components/terminal/panes/PaperTradePanel.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

old_str = 'Est. Value: ₹{((orderType === "MARKET" ? (liveTick?.price || 0) : Number(price)) * Number(quantity) || 0).toLocaleString()}'
new_str = 'Est. Value: { (orderType === "MARKET" && typeof liveTick?.price === "number" || orderType === "LIMIT" && Number(price) > 0) ? `₹${(((orderType === "MARKET" ? liveTick!.price! : Number(price)) * Number(quantity)) || 0).toLocaleString()}` : "N/A" }'

if old_str in text:
    text = text.replace(old_str, new_str)
    with open('apps/web/src/components/terminal/panes/PaperTradePanel.tsx', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Patched Est. Value")
else:
    print("Not found!")
