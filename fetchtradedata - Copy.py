import yfinance as yf

df = yf.download("^NSEBANK", interval="5m", period="60d")
df.to_csv("banknifty_5min.csv")

print("Done")