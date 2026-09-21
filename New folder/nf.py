import yfinance as yf

df = yf.download(
    "NIFTY=F",
    interval="5m",
    period="7d",
    progress=False
)

print(df.tail())