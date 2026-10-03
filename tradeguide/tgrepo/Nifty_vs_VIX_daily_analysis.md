# Nifty 50 vs India VIX - daily alignment (1 Jan - 1 Oct 2026, 186 days)

Source files: tgrepo/NIFTY 50 daily.xlsx, tgrepo/hist_india_vix_daywise.xlsx

## 1. Direction: they move opposite

| | VIX down | VIX up |
|---|---|---|
| Nifty down | 30 | 66 |
| Nifty up | 68 | 21 |

- Opposite direction on 72% of days. Correlation of daily changes is -0.80 (strong inverse link).
- Nifty falls of more than 1%: VIX rose on 26 of 27 days.
- Nifty rises of more than 1%: VIX fell on 17 of 19 days.
- Over the period Nifty fell 14% (26,147 -> 22,422) while VIX rose from 9.2 to 14.5.

## 2. Size: higher VIX means bigger days

Yesterday's VIX close against today's Nifty high-low range:

| VIX level | Days | Avg Nifty day range | Avg close-to-close move |
|---|---|---|---|
| 10-11 | 10 | 185 | 126 |
| 11-12 | 35 | 182 | 123 |
| 12-13 | 28 | 199 | 121 |
| 13-14 | 32 | 252 | 152 |
| Above 14 | 77 | 288 | 220 |

- Above 13, Nifty's days get clearly bigger. Below 13 they are fairly similar.
- VIX "expected daily move" = Nifty x VIX / 100 / sqrt(252): median about 206 points in this period. Nifty's actual close-to-close move stayed within it on 75% of days.
- March: VIX averaged 22, Nifty fell 11%, average day range 362. August: VIX 11.5, smallest range (150).

## 3. Yesterday's VIX change and today's Nifty: almost no link

| | Days | Avg range | Nifty up days |
|---|---|---|---|
| After VIX fell | 98 | 231 | 46% |
| After VIX rose | 86 | 253 | 50% |

Yesterday's VIX direction does not predict today's Nifty direction or size by itself. So the strong ACE "Rule C" result (trading only after VIX fell) is not explained by Nifty simply moving more on those days. It may be specific to how ACE's levels behave after a calm day, or partly luck from a small sample (44 trades). Paper-track Rule C on new data.

## Practical use

- Rising VIX during the day almost always comes with Nifty falling: supportive for PE trades, a warning for CE.
- VIX above 13-14: expect wider days (250-290 points); wider stop-losses, bigger targets possible.
- VIX below 12: quieter days (about 180 points); keep targets modest.
- VIX and NSE turnover move together (correlation 0.54): higher fear brings heavier trading.

Information only, not trading advice.
