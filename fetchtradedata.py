import yfinance as yf

df = yf.download("^NSEI", interval="5m", period="60d")
df.to_csv("nifty_5min.csv")

print("Done")