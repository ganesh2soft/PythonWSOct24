import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Data
buy_change = [-67050, 75450, 31800, 27675, -66150, 38325, 38700, 13650, 6525, -39375,
              6975, 4650, 33675, -13725, -42600, 19875, 20775, -7200, -18225, 10950,
              -5475, 21525, -19950, 375, 9975, 1875, 3750, -9750, 3600, -450,
              6300, -300, -11100, -3000, 4200, -3975, 5100, 14400, 6300, -14400,
              12375, -15300, -11325, 7575, 2925, 1200, 22125, 3075, -11025, -7950,
              17625, -8625, 16575, -17625, 35925, -29550, 5550, 0, -4275, 10425,
              8175, -33750, -11925, -26475, 19350, -19350, 14925, -16650, 9750, 16575,
              -36300, 37725, -24825, 15975, 1275, -24375, -79950]

sell_change = [-251100, 28500, 419025, 18600, 3450, 138375, 2850, -750, 22350, -825,
               -16950, -150, 14025, -1350, 30900, 2175, -1275, -10950, 14400, -3225,
               23175, -13275, -2025, 7200, 49575, -13500, -5325, 22350, 42450, 12975,
               7650, -10050, 18000, 15450, -8400, 14100, -2550, -5250, -6900, 4500,
               -15300, 19650, 12600, -975, -5700, 12900, -30450, 12150, -13275, 8550,
               1425, -75, -7650, -1575, -12075, 13200, -4800, 17850, -10875, 6525,
               3075, 21375, -3675, -26175, 53175, -3750, 11475, 4500, -4050, -5100,
               6075, -5550, 0, -47925, -375, -10650, -37050]

nifty_change = [-55, 10, -35, -14, -23, -11, 6, 5, -13, -10,
                3, 8, -1, -10, -20, -12, 17, -5, -12, 7,
                -13, -1, -5, 21, 1, -18, 9, 8, 7, -5,
                6, 1, 3, 0, 1, 1, -8, -17, 1, -1,
                9, 1, -13, 2, 11, -4, -6, -4, 4, 6,
                -3, 15, -3, 14, -1, -5, -3, 1, -13, -7,
                10, -15, -8, -13, 11, -20, -1, 1, -2, 13,
                -17, 5, -6, 8, 1, -6, -8]

# Create DataFrame
df = pd.DataFrame({
    'Change in Buy Qty': buy_change,
    'Change in Sell Qty': sell_change,
    'Change in Nifty 50 Fut': nifty_change
})

# Correlation matrix
correlation_matrix = df.corr()

# Plot correlation heatmap
plt.figure(figsize=(8, 6))
sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt=".2f")
plt.title("Correlation Matrix")
plt.show()

# Summary statistics
summary_stats = df.describe()

# Correlation matrix
correlation_matrix = df.corr()

# Identify strongest correlations with Nifty Futures
strongest_corr = correlation_matrix["Change in Nifty 50 Fut"].sort_values(ascending=False)

# Plot patterns
plt.figure(figsize=(15, 5))

# Buy vs Nifty
plt.subplot(1, 2, 1)
sns.scatterplot(x='Change in Buy Qty', y='Change in Nifty 50 Fut', data=df)
plt.title('Buy Qty vs Nifty 50 Futures')

# Sell vs Nifty
plt.subplot(1, 2, 2)
sns.scatterplot(x='Change in Sell Qty', y='Change in Nifty 50 Fut', data=df)
plt.title('Sell Qty vs Nifty 50 Futures')

plt.tight_layout()
plt.show()

# Print stats and correlations
print("Summary Statistics:\n", summary_stats)
print("\nStrongest Correlations with Nifty Futures:\n", strongest_corr)
