import yfinance as yf

# Nifty
nifty = yf.download("^NSEI", interval="5m", period="60d")
nifty.to_csv("nifty_5min.csv")

# Bank Nifty
bank = yf.download("^NSEBANK", interval="5m", period="60d")
bank.to_csv("banknifty_5min.csv")

print("Done")