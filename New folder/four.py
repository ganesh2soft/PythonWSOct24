import pandas as pd

# -----------------------------
# LOAD + CLEAN DATA
# -----------------------------
def load_data(file):
    df = pd.read_csv(file, header=[0,1])
    df.columns = df.columns.get_level_values(0)
    df.rename(columns={"Price": "Datetime"}, inplace=True)

    df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce")

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["Datetime"])
    return df


# -----------------------------
# LOAD FILES
# -----------------------------
nifty = load_data("nifty_5min.csv")
bank = load_data("banknifty_5min.csv")

df = pd.merge(nifty, bank, on="Datetime", suffixes=("_n", "_b"))
df["Date"] = df["Datetime"].dt.date

# -----------------------------
# BACKTEST VARIABLES
# -----------------------------
wins = 0
losses = 0
trades = 0
pnl_total = 0

# -----------------------------
# STRATEGY LOOP
# -----------------------------
for date, day in df.groupby("Date"):
    day = day.sort_values("Datetime").reset_index(drop=True)

    if len(day) < 30:
        continue

    # Opening Range (15 min)
    first3 = day.iloc[:3]
    orh = first3["High_n"].max()
    orl = first3["Low_n"].min()

    for i in range(3, len(day) - 5):

        row = day.iloc[i]
        prev = day.iloc[i - 1]

        bank_move = row["Close_b"] - row["Open_b"]

        # -----------------------------
        # LONG SETUP (IMPROVED)
        # -----------------------------
        if row["Close_n"] > orh and bank_move >= 60:

            # Pullback candle (red)
            if prev["Close_n"] < prev["Open_n"]:

                # Confirmation breakout
                if row["High_n"] > prev["High_n"]:

                    entry = prev["High_n"]
                    target = entry + 8
                    stop = entry - 8

                    future = day.iloc[i + 1:i + 6]

                    hit_target = (future["High_n"] >= target).any()
                    hit_stop = (future["Low_n"] <= stop).any()

                    trades += 1

                    if hit_target and not hit_stop:
                        wins += 1
                        pnl_total += 8
                    else:
                        losses += 1
                        pnl_total -= 8

        # -----------------------------
        # SHORT SETUP (IMPROVED)
        # -----------------------------
        if row["Close_n"] < orl and bank_move <= -60:

            # Pullback candle (green)
            if prev["Close_n"] > prev["Open_n"]:

                # Confirmation breakdown
                if row["Low_n"] < prev["Low_n"]:

                    entry = prev["Low_n"]
                    target = entry - 8
                    stop = entry + 8

                    future = day.iloc[i + 1:i + 6]

                    hit_target = (future["Low_n"] <= target).any()
                    hit_stop = (future["High_n"] >= stop).any()

                    trades += 1

                    if hit_target and not hit_stop:
                        wins += 1
                        pnl_total += 8
                    else:
                        losses += 1
                        pnl_total -= 8


# -----------------------------
# RESULTS
# -----------------------------
winrate = (wins / trades * 100) if trades > 0 else 0

print("Trades:", trades)
print("Wins:", wins)
print("Losses:", losses)
print("Winrate:", round(winrate, 2), "%")
print("Total PnL (points):", pnl_total)