import pandas as pd

# -----------------------------
# LOAD + FIX DATETIME (ROBUST)
# -----------------------------
def load_data(file):
    df = pd.read_csv(file)

    # Try common datetime columns
    for col in df.columns:
        if "date" in col.lower():
            df["Datetime"] = pd.to_datetime(df[col])
            break
    else:
        # fallback: use first column
        df["Datetime"] = pd.to_datetime(df.iloc[:, 0])

    return df


nifty = load_data("nifty_5min.csv")
bank = load_data("banknifty_5min.csv")

# -----------------------------
# MERGE DATA
# -----------------------------
df = pd.merge(nifty, bank, on="Datetime", suffixes=("_n", "_b"))

df["Date"] = df["Datetime"].dt.date

# -----------------------------
# BACKTEST VARIABLES
# -----------------------------
wins = 0
losses = 0
trades = 0

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

    last_hl = None
    last_lh = None

    for i in range(5, len(day) - 5):

        row = day.iloc[i]
        prev = day.iloc[i - 1]

        bank_move = row["Close_b"] - row["Open_b"]

        # -----------------------------
        # SIMPLE HL / LH DETECTION
        # -----------------------------
        if prev["Low_n"] > day.iloc[i - 2]["Low_n"]:
            last_hl = prev["Low_n"]

        if prev["High_n"] < day.iloc[i - 2]["High_n"]:
            last_lh = prev["High_n"]

        # -----------------------------
        # LONG TRADE
        # -----------------------------
        if (
            row["Close_n"] > orh and
            bank_move >= 80 and
            last_hl is not None
        ):
            pb = prev["Close_n"] - prev["Open_n"]

            if -10 <= pb <= -3:
                entry = row["High_n"]
                target = entry + 10
                stop = entry - 10

                future = day.iloc[i + 1:i + 6]

                hit_target = (future["High_n"] >= target).any()
                hit_stop = (future["Low_n"] <= stop).any()

                trades += 1

                if hit_target and not hit_stop:
                    wins += 1
                else:
                    losses += 1

        # -----------------------------
        # SHORT TRADE
        # -----------------------------
        if (
            row["Close_n"] < orl and
            bank_move <= -80 and
            last_lh is not None
        ):
            pb = prev["Close_n"] - prev["Open_n"]

            if 3 <= pb <= 10:
                entry = row["Low_n"]
                target = entry - 10
                stop = entry + 10

                future = day.iloc[i + 1:i + 6]

                hit_target = (future["Low_n"] <= target).any()
                hit_stop = (future["High_n"] >= stop).any()

                trades += 1

                if hit_target and not hit_stop:
                    wins += 1
                else:
                    losses += 1


# -----------------------------
# RESULTS
# -----------------------------
if trades > 0:
    winrate = (wins / trades) * 100
else:
    winrate = 0

print("Trades:", trades)
print("Wins:", wins)
print("Losses:", losses)
print("Winrate:", round(winrate, 2), "%")