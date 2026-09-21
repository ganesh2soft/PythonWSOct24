# Scheduler Design Notes

Two different scheduling approaches exist in this project's history. This file
captures both so the reasoning isn't lost, now that only one remains as code.

## 1. scheduler.py (currently active)

- An explicit list of ~90 fixed daily times (`schedule_job_times()`), each
  scheduled individually via `schedule.every().day.at(time_str).do(job, ...)`.
- A custom catch-up loop in `run_scheduler()`: every second it checks whether
  `current_time > job.next_run`, and if so force-runs that job immediately and
  cancels it — so a job due at, say, 09:21 still fires even if the server only
  started at 09:22.
- A global `scheduler_running` flag prevents duplicate scheduler threads on
  reload.
- The access token is captured once when the scheduler starts and reused by
  every job scheduled in that run.
- The times list mixes genuine market-hours entries (~09:15-15:41, roughly
  5-minute cadence) with off-hours dev/testing entries (23:00, 01:10,
  08:10-08:55) used to trigger and validate runs outside market hours during
  development.

## 2. The alternate approach (previously `scheduler copy.py` / `scheduler_alt.py`, now removed as code)

```python
import time
import schedule
import threading
import os
import json
from datetime import datetime, time as datetime_time
from flask import session, current_app

data_file = "data.json"

def read_data_from_file():
    if os.path.exists(data_file):
        with open(data_file, 'r') as f:
            data = json.load(f)
            return data.get('expiry1', ''), data.get('expiry2', ''), data.get('expiry3', ''), data.get('instrumentkey', '')
    else:
        return '', '', '', ""

def job(access_token):
    from app import app
    with app.app_context():
        print('Reached job ')
        if access_token:
            expiry1, expiry2, expiry3, instrumentkey = read_data_from_file()
            now = datetime.now()

            start_time = datetime_time(0, 10)
            end_time = datetime_time(23, 50)

            if start_time <= now.time() <= end_time:
                from app import startrecord
                startrecord(expiry1, expiry2, expiry3, instrumentkey, access_token)
            else:
                print("Outside of scheduled time window.")
        else:
            print("No access token found. Skipping job.")

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

def start_scheduler():
    access_token = session.get('access_token', None)
    if access_token:
        schedule.every(10).minutes.do(lambda: job(access_token))
        scheduler_thread = threading.Thread(target=run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
    else:
        print("No access token found, skipping scheduler startup.")
```

- A simple recurring interval — `schedule.every(10).minutes.do(...)` — instead
  of a hand-maintained list of exact times.
- A guard *inside* `job()` itself: it only actually runs `startrecord()` if
  the current time falls within a configured window (`start_time`/`end_time`),
  otherwise it logs "Outside of scheduled time window" and skips.
- No catch-up logic, no exact-time list, no `scheduler_running` flag.
- Simpler to read and reason about, but less precise — it fires whenever the
  10-minute tick happens to land, not at specific chosen times. As written,
  the window (00:10-23:50) covers almost the entire day, so in practice the
  interval alone drives the real cadence.

## Trade-off summary

| | scheduler.py (active) | alternate approach |
|---|---|---|
| Precision | Exact, hand-picked times | Approximate, interval-driven |
| Maintenance | ~90 times to edit by hand | One interval + one window |
| Missed-run handling | Explicit catch-up logic | None — just waits for the next tick |
| Readability | Long, repetitive | Short, easy to follow |
| Market-hours vs. dev-time | Same list handles both (easy to mix up) | Would need a separate window/interval per mode |

## Why this matters going forward

Neither design is a great long-term fit once the planned websocket-based live
strike tracking (5 call + 5 put: 1 ATM, 1 OTM, 3 ITM) is built — that shifts
the core data flow to a continuously-updated push feed rather than a periodic
poll, so most of `startrecord()`'s current polling cadence becomes unnecessary
for the strikes tracked live via websocket.

Whatever polling *does* remain (VIX, PCR, top-N lists, and anything else not
covered by the websocket feed) would likely benefit more from the simpler
interval + time-window pattern above than from a hand-maintained list of ~90
exact times — and real market-hours scheduling should probably be kept
separate from ad-hoc dev/testing triggers rather than mixed into one list, as
they are today.

## Status

The alternate implementation's code is captured above for reference. The
`scheduler_alt.py` / `scheduler copy.py` file has been removed from the
project so there's only one active scheduler implementation (`scheduler.py`)
going forward.
