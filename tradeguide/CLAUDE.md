# tradeguide — project guide for AI assistants (Claude, ChatGPT, others) and new developers

Last updated: 10 Oct 2026. Owner: ganesh2soft (GitHub repo `PythonWSOct24`, this folder = `tradeguide/`).
Read this whole file before changing anything. It explains what the app does, where every file lives,
how data flows, and the rules that must not be broken.

---

## 1. What this project is

tradeguide is a **Python Flask app** that collects Indian market data from the **Upstox API (v2)** every
5 minutes during market hours and turns it into analysis for an **intraday Nifty 50 option buyer**
(buys CE/PE, does not sell options).

It produces:
- JSON snapshots (indices, sectors, top stocks, option VWAP breadth, PCR/trend, premium) in `json_output/`
- the full option chain (3 expiries) and Nifty futures as JSON Lines files in `db_migrate_json/`
- strike-wise OI lines in `tradelogger.log`
- **Telegram alerts** to the friend's "ASG" group: entry alerts (`tg_alerts.py`) and index move alerts (`asgboom.py`)
- a web dashboard (Flask templates) and JSON APIs for an Angular frontend (`ng-futopt`, separate repo/folder)

There is **no database**. MySQL was removed on 10 Oct 2026; all storage is files (JSON / JSONL / logs).

Platform: Windows PC, Python virtualenv `tg-flask-venv`, timezone IST (Asia/Kolkata).
Market hours: 09:15–15:30 IST, Monday–Friday.

---

## 2. How to run

```
cd D:\PythonWSOct24\tradeguide
tg-flask-venv\Scripts\activate
python app.py                       # Flask on http://127.0.0.1:5000
```
1. Open http://127.0.0.1:5000 and log in to Upstox (the `/authorize` → Upstox login → `/callback` flow).
   The access token is kept in the Flask session; it is valid for one day, so log in every morning.
2. After login the scheduler (`scheduler.py`) starts and calls `startrecord()` at fixed times.
3. In a second terminal: `python asgboom.py` (Telegram move alerts, 09:17–15:12). `--dry-run` prints only.
4. Status at any time (read-only, never calls Upstox): `python tg_status.py` (or `tg_status.bat`).
   Flags: `--oi`, `--sec`, `--vwap`, `--all`, `--date YYYY-MM-DD`, `--time HH:MM`.
5. After 15:35: run `standalone_archive_script.bat` (archives today's JSON, then storage roll + retention).

---

## 3. Folder map

```
tradeguide/
├── app.py                    Flask app: routes, all data-collection functions, startrecord()
├── scheduler.py              5-min scheduler (times list, job() -> startrecord)
├── upstoxapiservices.py      thin wrappers around the Upstox SDK/REST (quotes, option chain, orders)
├── tokengen.py               Upstox OAuth code -> access token   (contains API secret: never print/share)
├── logoutuser.py             Upstox logout
├── optvwap.py                option VWAP breadth logic (5 CE + 5 PE) -> json_output/optvwap.json
├── tg_alerts.py              entry alerts (CE / PE / reversal / sideways) -> Telegram via asgboom.send
├── tg_status.py / .bat       one-shot status summary for humans and AI assistants (read-only)
├── asgboom.py                separate process: Nifty / BankNifty / Midcap move + divergence alerts -> Telegram
├── asgboom.env               Telegram bot token + chat id            (SECRET: never open, print or commit)
├── asgboom.env.example       template for asgboom.env (safe)
├── archive_json.py           moves each day's JSON entries into json_output/archive/<date>/
├── standalone_archive_script.bat  end-of-day: archive_json.py + db_migrate_json/retention.py
├── clearstaledata.py         removes stale expiry entries from trend.json
├── data.json                 current expiries + futures instrument key (edit weekly, see §6)
├── symbolnamemapping.json    instrument key <-> symbol names
├── tg_nifty_sec.json         config: sectors / heavyweights tracked for tg-nifty-sec (weights, keys)
├── tg_opt_vwap.json          config: optvwap settings (read every run, no restart needed)
├── ASGBOOM.md, ASGBOOM_NiftyvsBN.md   older notes on ASGBOOM (project notes are the latest)
├── tradelogger.log           main app log (also holds strike-wise OI blocks from fewstrikes())
├── opt_fut_entry_logger.log  log of every option-chain / futures file write (db_migrate_json)
├── asgboom.log               ASGBOOM + tg_alerts "Sent:" lines (fresh from 12 Oct 2026)
├── json_output/              5-minute snapshot files (see §5)
│   └── archive/<YYYY-MM-DD>/ one folder per past trading day
├── db_migrate_json/          option chain + futures storage, replaces MySQL (see §5)
├── templates/, static/       Flask HTML pages (mainboard, options_analysis, optionchainlive, ...)
├── tgrepo/                   research data: Nifty/BN/VIX 5-min history (xlsx/csv), backtests, due_levels.json
├── charts/, Claude outputs/  generated images (analysis output, not used by the app)
├── asgboom_old/              ASGBOOM log/state up to 9 Oct 2026 (kept for reference)
├── claude_bak_del_later/     backups made by AI assistants: <date>/<file>.bak_<reason>; reference/ = NSE contract list
├── _to_delete/               old MySQL code (db_config.py has a plain-text DB password: never open/print)
└── tg-flask-venv/            Python virtualenv (do not edit)
```
Git ignores: `*.log`, `__pycache__/`, `_to_delete/`, `claude_bak_del_later/`, `db_migrate_json/Archived_All/`.

---

## 4. The 5-minute cycle — `startrecord()` in app.py

Scheduler times (IST): 09:11, 09:16, then every 5 minutes 09:21 … 15:41 (14:40 instead of 14:41).
The list in `scheduler.py` may also contain night "test" slots (00:40, 01:00, 02:10 …) used for testing
outside market hours; they run on the last available (Friday-close) data.

Each run, in order (each step has its own try/except so one failure does not stop the rest):

| Step | Function | Output |
|---|---|---|
| 1 | `indiavixcalc` | India VIX → `json_output/trend.json` |
| 2 | `findbanktop`, `findniftytop`, `findmidcaptop` | `banktop5.json`, `niftytop10.json`, `midcaptop5.json` |
| 3 | `findpremium` | `premium.json` |
| 4 | `mainindexfun` | `mainindex.json` (Nifty 50, Bank Nifty, Midcap Select LTP) |
| 5 | `sectorsfun` | `sectors.json` (config `tg_nifty_sec.json`) |
| 6 | `optvwapfun` (uses `optvwap.py`) | `optvwap.json` (config `tg_opt_vwap.json`) |
| 7 | `fewstrikes` | strike-wise OI (ATM ±400) written to `tradelogger.log`; `covering.json` |
| 8 | `tg_alerts.live()` | Telegram entry alerts; state in `json_output/tg_alerts_state.json` |
| 9 | option chain for expiry1/2/3 → `processpcr` | PCR/trend → `trend.json`; full chain → `db_migrate_json` (`write_optionchain`) |
| 10 | Nifty futures quote | `db_migrate_json` (`write_futures`) |

`asgboom.py` is NOT called by startrecord; it runs on its own and polls `json_output/mainindex.json` every 30 s.

---

## 5. Data files

### json_output/ (today's snapshots; each file is a JSON list, one entry per run)
| File | Content | Main readers |
|---|---|---|
| mainindex.json | Nifty 50 / Bank Nifty / Midcap LTP per run (`timestamp`, `main_index[]`) | asgboom, tg_status, dashboard |
| trend.json | PCR sets per expiry, India VIX | /api/trend, tg_status |
| sectors.json | sector indices + heavyweights | tg-nifty-sec, tg_status --sec |
| optvwap.json | per-strike option price vs VWAP, CALL ok / PUT ok / REVERSAL verdicts | tg_alerts, tg_status --vwap |
| covering.json | short-covering data near ATM | tg_alerts, dashboard |
| niftytop10.json, banktop5.json, midcaptop5.json | top constituents | dashboard APIs |
| premium.json, nifty5min.json | option premium samples, Nifty 5-min OHLC | dashboard APIs |
| options_api.json | copy of the last `/api/options` response (calls/puts, 3 expiries) — for the Angular rewrite | Angular (future) |
| tg_alerts_state.json | alert state (open alerts, cooldowns) | tg_alerts |
| history_market_cues.json | daily news-based market bias history (separate "market-cues" analysis; never uses Upstox data) | AI assistant |
| archive/<date>/ | past days, same file names | tg_status --date, backtests |

### db_migrate_json/ (option chain + futures, JSON Lines = one JSON object per line, append-only)
```
Current_Expiry/NIFTY/options_<expiry1>/<date>.jsonl   all strikes of the nearest expiry, one line per run
Next_Expiry/NIFTY/options_<expiry>/<date>.jsonl       expiry2 and expiry3
Current_Expiry/NIFTY/futures/<SYMBOL>.jsonl           one file per futures contract (e.g. NIFTY26OCTFUT)
Archived_All/...                                      expired data (git-ignored)
```
- Option line: `{ts, ul, expiry, spot, pcr, cols, rows}`; `cols` = `strike, c_oi, c_oi_prev, c_vol, c_ltp, c_iv, p_oi, p_oi_prev, p_vol, p_ltp, p_iv`; `pcr` = total put OI / total call OI.
- Futures line: `{ts, symbol, key, last_price, average_price, oi, volume, total_buy_quantity, total_sell_quantity, result, src_ts}`.
- Code: `db_migrate_json/jsonl_store.py` — writers `write_optionchain`, `write_futures`; readers `getopt(expiry)`, `getfut()` (same shape the old MySQL readers returned; app.py imports it as `db_read`); `roll()` moves folders when the expiry in data.json changes; `retention()` deletes options older than 21 days after expiry and futures older than 92 days.
- Test: `python db_migrate_json/test_jsonl_store.py` (uses a temp folder, prints ALL PASS).

### Logs
- `tradelogger.log` — app log + OI blocks. `opt_fut_entry_logger.log` — one line per file write (`OPT NIFTY <exp> strikes=.. spot=.. pcr=..`, `FUT ...`, `ROLL`, `RETENTION`). `asgboom.log` — `Sent:` lines for every Telegram message.

---

## 6. Weekly / daily maintenance
- **Every morning:** start app.py, log in to Upstox, start asgboom.py.
- **After each weekly expiry (Tuesday):** update `data.json` (`expiry1`, `expiry2`, `expiry3`; `instrumentkey` when the futures contract changes). The storage roll happens automatically on the next write.
- **After 15:35:** `standalone_archive_script.bat`.
- **Monthly:** refresh weights in `tg_nifty_sec.json` from the NSE Nifty 50 factsheet.

---

## 7. Alert logic (summary)

**tg_alerts.py** (entries only 09:21–14:45, sideways until 15:00; never sends alerts older than 10 min)
- CE SETUP: optvwap "CALL ok" confirmed (2 runs) + Bank Nifty above its 09:16 value + India VIX ≥ its 09:16 value + put writing ≥ 40 lakh in 30 min at strikes ≤ spot+50.
- PE SETUP: mirror image (PUT ok, BN below 09:16, VIX ≥ 09:16, call writing ≥ 40 lakh at strikes ≥ spot−50).
- REVERSAL: optvwap verdict "REVERSAL UP/DOWN – confirmed". NEAR WALL warning only while an alert is open and in profit.
- Stop / target = nearest of the two biggest OI walls; stop checked on 5-min close; 30-min cooldown; one open alert per side.
- Sideways: `sideways-alert-covering` and `sideways-covering-wall-broken` (naming rule: `sideways-alert-<approach>`, `sideways-<approach>-wall-broken`).
- Settings are in the `CFG` dict at the top of tg_alerts.py.

**asgboom.py** (09:17–15:12)
- Initial alert at 09:17 with spot of Nifty / BN / Midcap.
- BIG move: index moves ≥ Nifty 75 / BN 200 / Midcap 60 points **within 15 minutes** (vs the 15-min low/high); window restarts after each alert.
- Nifty vs Bank Nifty divergence / re-convergence alert (BN expected ≈ 2.6 × Nifty move; alert at gap ≥ 250, re-converged < 100).
- Due-level alerts are switched OFF (`SHOW_LEVELS = False`, since 10 Oct 2026); the code stays.
- Message format: `ASGBOOM | Alert Time 10:06 | NIFTY BIG move -79` + one line of spots.

---

## 8. Web routes (Flask)
Pages: `/`, `/mainboard`, `/options_analysis.html`, `/optionchainlive`, `/capturedata.html`, `/feedindicators`, `/orders`, `/positions`, `/login`, `/logout_user`.
JSON APIs (used by the Angular app): `/api/trend`, `/api/options`, `/api/futures`, `/api/getmainindex`, `/api/gettopnifty10`, `/api/gettopbank5`, `/api/gettopmidcap5`, `/api/getpremium`, `/api/getniftyhl`, `/api/get-expiry-dates`, `/data.json`, `/api/postorder/orderitems` (POST, places orders — do not call in tests).

---

## 9. Rules for any AI assistant or developer (must follow)

1. **Secrets — never open, print, copy or commit:** `asgboom.env`, `tokengen.py` (API secret), `_to_delete/db_config.py` (DB password), Upstox access tokens, `readme.md` login URLs. When showing log lines, filter out lines containing token, secret, authorization, bearer or `code=`.
2. **Backups:** before editing a file, copy it to `claude_bak_del_later/<YYYY-MM-DD>/<file>.bak_<reason>`. Never create `.bak` files next to the code. Never delete files; move unwanted files into `claude_bak_del_later/` and tell the owner.
3. **No database.** Do not add MySQL/SQLAlchemy back. Store data as JSON / JSONL in the existing folders.
4. **Do not break the 5-minute cycle:** every new step inside `startrecord()` gets its own `try/except` that logs the error and continues. Keep the same function signatures and file names; tg_status, tg_alerts, asgboom and the skills read them.
5. **Read-only analysis by default.** Status/analysis tasks read files only; never call Upstox order APIs or `/api/postorder/...`.
6. **Telegram:** do not send test messages to the ASG group without the owner's OK; use `--dry-run`.
7. **Restart needed:** changes to `app.py`, `scheduler.py`, `tg_alerts.py` need a Flask restart; `asgboom.py` changes need an asgboom restart; `tg_*.json` configs are read every run.
8. **Market-cues** (news-based bias, `history_market_cues.json`) must stay independent: it uses websites only, never Upstox/tradeguide data.
9. **Time zone:** all times are IST. When checking "is the app alive", the latest `mainindex.json` timestamp should be ≤ 11 minutes old during market hours.
10. Trading output is information, not financial advice. The owner/friend decides trades.

---

## 10. Quick health check (for any assistant)
```
python tg_status.py                       # summary: last run, errors, PCR, sectors, optvwap, alerts
tail opt_fut_entry_logger.log             # option/futures writes every 5 min
python -c "import json;print(json.load(open('json_output/mainindex.json'))[-1]['timestamp'])"
```
Healthy = last run within 11 minutes (market hours), `errors 0`, three OPT lines + one FUT line per run.

---

## 11. Pending / planned
- Rewrite the Angular (`ng-futopt`) pages to read the new JSON files (`options_api.json`, `db_migrate_json`) instead of the old MySQL-based APIs.
- Optional: tg_status / tg_alerts to read OI from `db_migrate_json` instead of parsing `tradelogger.log`.
- Optional: remove Flask-SQLAlchemy / PyMySQL from `requirements.txt` (file is UTF-16 encoded).
