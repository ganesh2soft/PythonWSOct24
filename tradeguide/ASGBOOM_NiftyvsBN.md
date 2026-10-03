# ASGBOOM – Nifty vs Bank Nifty (Convergence / Divergence)

Specific logic inside the common ASGBOOM alert (see `ASGBOOM.md` for the common rules). Sent as a **separate** ASGBOOM message.

## Logic
**Why 2.6, not 3.2:** 3.2 is the ratio of candle *sizes* (ATR). For *moving together*, the Jun–Sep 2026 5-min data gives **2.6 BN points per Nifty point** (correlation 0.81; price ratio ≈ 2.4).

Reference = day's 09:16 snapshot (same as the initial alert).
```
Nifty move   = Nifty now − Nifty 09:16
Expected BN  = 2.6 × Nifty move
Gap          = (BN now − BN 09:16) − Expected BN
```

| State | Rule |
|---|---|
| CONVERGED | \|gap\| < 100 |
| DIVERGENCE: BN stronger | gap ≥ +250 |
| DIVERGENCE: BN weaker | gap ≤ −250 |
| DIVERGENCE: OPPOSITE | Nifty ≥ ±25 **and** BN ≥ 80 in the other direction |

- One DIVERGENCE alert, then quiet while diverged.
- **RE-CONVERGED** alert when \|gap\| < 100 again (100–250 band = hysteresis, no flip-flop); after that a new divergence can alert again.
- Why 250: on Jun–Sep data the day's max |gap| reached 150 on 64% of days (too noisy), 250 on 27% (≈ 1 day in 4). Opposite-direction cases occurred on 21 of 81 days.

### Divergence message format
```
ASGBOOM | Alert Time 11:26 | DIVERGENCE: BN weaker
NIFTY +40 since 09:16 -> BN expected +104, actual -150 (gap -254)
NIFTY Spot 22,640 | BN Spot 54,350
```
```
ASGBOOM | Alert Time 12:41 | RE-CONVERGED
NIFTY +55 since 09:16 -> BN expected +143, actual +98 (gap -45)
NIFTY Spot 22,675 | BN Spot 54,916
```

## Settings (top of asgboom.py)
| Setting | Value |
|---|---|
| DIV_BETA | 2.6 |
| DIV_ON / DIV_OFF | 250 / 100 |
| OPP_N / OPP_B | 25 / 80 |

## Limits
- 5-min snapshots: divergence is detected within ≤5 min.
- Divergence is a heads-up, not a trade signal: one index often catches up with the other, but not always.
