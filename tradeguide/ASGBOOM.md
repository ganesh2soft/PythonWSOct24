# ASGBOOM – Common Alert Logic

Telegram alert bot for the ASG group. Watches **Nifty 50, Bank Nifty (BN) and Nifty Midcap Select (MID)** against the friend's due-level lists and sends alerts.

- Script: `asgboom.py` (runs separately from Flask, in its own terminal)
- Run: `tg-flask-venv\Scripts\python asgboom.py`  ·  test: `--test-send`  ·  print only: `--dry-run`
- Secrets: `asgboom.env` (`ASGBOOM_BOT_TOKEN`, `ASG_CHAT_ID`) – never share / never commit
- Price source: tradeguide `mainindex.json` (updated by the scheduler every 5 min) → tradeguide must be running and logged in
- Levels: `tgrepo/due_levels.json` (copy of project docs `tg-due-level-nifty / -bn / -mid`)
- Log: `asgboom.log`  ·  Day state: `tgrepo/asgboom_state.json`

## Daily window
- Active **09:17 → 15:12 IST**; stops by itself at 15:12.
- Polls every 30 s; acts only on a **new** `mainindex.json` snapshot.
- **Stale guard:** if the latest snapshot is older than **11 min** (max 2 missed 5-min schedules) → logs a warning, sends nothing.
- Restart-safe: state is kept per day, so a restart never resends the initial alert or already-alerted levels.

## 1. Initial alert (once per day)
First snapshot at/after 09:17 (normally the 09:16 data). Sets the day's references.

## 2. Move alert (rolling reference)
| Index | Step |
|---|---|
| NIFTY | 50 points |
| BN | 150 points |
| MID | 30 points |

Alert when an index moves ≥ step from its reference (any direction); the reference then resets to that price.

## 3. Near-level alert (once per level per day)
Alert when an index comes within its step (NIFTY 50 / BN 150 / MID 30) of any due level. Several levels in range are listed together.

### Level message format
```
ASGBOOM | Alert Time 09:26 | MID move -34
NIFTY Spot 22,520 | Nearest Category Yesterday | Level 23,021.53 (+502)
BN Spot 54,774 | NEAR Category Pending | Level 54,830.61 (+57) + Category Recent | Level 54,877 (+103)
MID Spot 13,632 | Nearest Category Yesterday | Level 13,794.14 (+162)
```
- First line = why it fired (`Initial`, `<INDEX> move ±x`, `<INDEX> near <level>`).
- **NEAR** = level within range; **Nearest** = closest level when none is in range.
- Bracket = level − spot (**+** level above spot, **−** below).

## Settings (top of asgboom.py)
| Setting | Value |
|---|---|
| START / STOP | 09:17 / 15:12 |
| POLL_SECONDS | 30 |
| STALE_MINUTES | 11 |
| Steps (INDICES) | NIFTY 50 · BN 150 · MID 30 |

## Limits
- Prices are 5-min snapshots: a quick touch between snapshots can be missed.
- Levels are the friend's list (received 29 Sep 2026); category labels (e.g. "Yesterday") are as given then. Update project docs and `due_levels.json` together when new levels arrive.

## Specific logics (separate files)
- `ASGBOOM_NiftyvsBN.md` – Nifty vs Bank Nifty convergence / divergence alert
