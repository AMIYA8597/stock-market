import yfinance as yf
news = yf.Ticker("RELIANCE.NS").news
print("Number of news items:", len(news))
if news:
    print("First news item structure:")
    import json
    print(json.dumps(news[0], indent=2))
