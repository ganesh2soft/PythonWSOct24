# db_migrate_json — tradeguide without a database (v2, 9 Oct 2026)

User decisions (9 Oct 2026): no more MySQL; no export / no DB-vs-file comparison. Keep option data **3 weeks** after expiry and the Nifty futures as **one file per contract month**, appended every 5 min (a missed day is fine). Everything is logged to **`tradeguide/opt_fut_entry_logger.log`**.

## Folders (one sub-folder per underlying; BANKNIFTY / SENSEX can be added later via `EXPIRY_KEY` in jsonl_store.py)
```
db_migrate_json\
  Current_Expiry\NIFTY\options_<expiry1>\<date>.jsonl    nearest expiry (data.json expiry1), one file per day, one line per run
  Current_Expiry\NIFTY\futures\<SYMBOL>.jsonl            current contract, e.g. NIFTY26OCTFUT.jsonl, one line per run
  Next_Expiry\NIFTY\options_<expiry2|3>\<date>.jsonl     later expiries
  Archived_All\NIFTY\options_<expiry>\...                expired weeks   -> deleted 21 days after expiry
  Archived_All\NIFTY\futures\<SYMBOL>.jsonl              expired months  -> deleted 92 days after last write
```
Option line: ts, ul, expiry, spot, pcr, cols, rows = [strike, call OI, call prev OI, call vol, call LTP, call IV, put OI, put prev OI, put vol, put LTP, put IV].
Futures line: ts, symbol, key, last_price, average_price, oi, volume, total_buy_quantity, total_sell_quantity, result, src_ts.

## Rolling
- Option folders follow `data.json`: expiry passed -> `Archived_All`; equals expiry1 -> `Current_Expiry`; later -> `Next_Expiry`. Done on the first write of each day and by `retention.py`.
- Futures: a contract file not written today (old month) moves to `Archived_All` when the new contract is first written.

## Log: opt_fut_entry_logger.log (rotating 5 MB x 3, separate from tradelogger.log)
```
2026-10-09 13:46:05 INFO OPT NIFTY 2026-10-13 strikes=152 spot=22514.3 pcr=1.11 -> Current_Expiry/NIFTY/options_2026-10-13/2026-10-09.jsonl (+12.4 KB)
2026-10-09 13:46:06 INFO FUT NIFTY NIFTY26OCTFUT ltp=22571.5 oi=12345600 vol=800000 -> Current_Expiry/NIFTY/futures/NIFTY26OCTFUT.jsonl (+260 B)
2026-10-14 09:21:05 INFO ROLL NIFTY options_2026-10-13: Current_Expiry -> Archived_All
2026-11-10 15:40:00 INFO RETENTION deleted Archived_All/NIFTY/options_2026-10-13
```
Errors appear as `ERROR OPT/FUT ... write failed: ...` (the 5-min job continues).

## Files
| File | Purpose |
|---|---|
| `jsonl_store.py` | writers `write_optionchain()` / `write_futures()`, `roll()`, `retention()`, readers `getopt()` / `getfut()` (same shape as db_read) |
| `retention.py` | roll + delete past retention; `--dry-run` lists only. Called from `standalone_archive_script.bat` after `archive_json.py` |
| `test_jsonl_store.py` | offline test (temp folder): writes, roll on expiry, futures month change, retention, log lines — ALL PASS |
| `_to_delete/` | obsolete export/compare scripts (user decision) |

## Steps
1. ✅ Storage + logger + roll + retention (v2) — 9 Oct.
2. ✅ `app.py` `startrecord()` calls `write_optionchain(optbook.data)` and `write_futures(future_response.data)` after the MySQL writes (own try/except each; backup `app.py.bak_dbjson`). Active after the next Flask restart.
3. Switch `/api/futures`, `/options_analysis.html`, `/api/options` from `db_read` to `jsonl_store.getfut/getopt`.
4. Remove MySQL writes and `flask_sqlalchemy` / `db_config` from `app.py`; move `db_*.py`, `models.py`, `db_config.py` (plain-text DB password) to `_to_delete/`. Check `Trendone` and the Angular pages first.
5. ✅ `retention.py` added to `standalone_archive_script.bat` (backup `.bak_retention`).
