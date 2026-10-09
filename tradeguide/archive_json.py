"""Archive tradeguide's 5-min output JSONs into json_output/archive/<date>/, one folder per day (nothing is deleted).

Each file's entries are split by their own timestamp (timestamp / recdate / vixts), so a file holding
6, 7 and 8 Oct goes to archive/2026-10-06, archive/2026-10-07 and archive/2026-10-08.
If an archived file for that day already exists, the new entries are merged into it (duplicates skipped).

Today's entries:
  - before 15:35 (market still running) they stay in json_output so the dashboard and scheduler keep working;
  - from 15:35 onwards they are archived too.
  --all       archive today's entries even before 15:35
  --dry-run   show what would happen, change nothing

optvwap.json and the ASGBOOM state files are left in place on purpose.
Usage: python archive_json.py [--dry-run] [--all]"""
import json, os, sys, datetime, tempfile, collections

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'json_output')
ARCH = os.path.join(OUT, 'archive')
FILES = ['banktop5', 'midcaptop5', 'nifty5min', 'niftytop10', 'premium', 'trend', 'mainindex', 'covering', 'sectors']
TS_KEYS = ('timestamp', 'recdate', 'vixts')
dry = '--dry-run' in sys.argv
now = datetime.datetime.now()
today = now.date().isoformat()
keep_today = ('--all' not in sys.argv) and now.strftime('%H:%M') < '15:35'


def day_of(item):
    if isinstance(item, dict):
        for k in TS_KEYS:
            v = item.get(k)
            if v:
                return str(v)[:10]
    return None


def split(entries):
    """entries -> {date: [entries]}; entries without a date stay with today's (kept/archived with today)."""
    out = collections.OrderedDict()
    for e in entries:
        out.setdefault(day_of(e) or today, []).append(e)
    return out


def write_json(path, data):
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix='.tmp')
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)                       # atomic swap, Flask never sees a half-written file


def merge(old, new):
    seen = {json.dumps(x, sort_keys=True) for x in old}
    return old + [x for x in new if json.dumps(x, sort_keys=True) not in seen]


print(f'Now {now:%Y-%m-%d %H:%M} - today\'s entries are '
      + ('KEPT in json_output (market hours; use --all to override)' if keep_today else 'archived too')
      + ('   [dry run, nothing changed]' if dry else ''))
totals = collections.Counter()
for name in FILES:
    src = os.path.join(OUT, name + '.json')
    if not os.path.exists(src):
        continue
    try:
        with open(src) as f:
            data = json.load(f)
    except Exception as e:
        print(f'  {name}.json: could not read ({e}) - skipped')
        continue

    # Shape 1: a list of snapshots.  Shape 2: a dict of lists (premium: premium_set; trend: vix_set + pcr_set).
    if isinstance(data, list):
        parts = {None: split(data)}
    elif isinstance(data, dict) and all(isinstance(v, list) for v in data.values()):
        parts = {k: split(v) for k, v in data.items()}
    else:
        print(f'  {name}.json: unknown layout - skipped')
        continue

    days = sorted({d for p in parts.values() for d in p})
    go = [d for d in days if not (keep_today and d == today)]
    stay = [d for d in days if d not in go]
    if not go:
        print(f'  {name}.json: only today\'s data - nothing to archive')
        continue

    for d in go:
        if data.__class__ is list:
            chunk = parts[None].get(d, [])
            n = len(chunk)
        else:
            chunk = {k: p.get(d, []) for k, p in parts.items()}
            n = sum(len(v) for v in chunk.values())
        tgt = os.path.join(ARCH, d, name + '.json')
        note = ''
        if os.path.exists(tgt):
            try:
                with open(tgt) as f:
                    old = json.load(f)
                if isinstance(chunk, list) and isinstance(old, list):
                    chunk = merge(old, chunk)
                elif isinstance(chunk, dict) and isinstance(old, dict):
                    chunk = {k: merge(old.get(k, []), chunk.get(k, [])) for k in set(old) | set(chunk)}
                else:
                    raise ValueError('layout differs')
                note = ' (merged into existing)'
            except Exception as e:
                base, k = tgt[:-5], 2
                while os.path.exists(f'{base}_{k}.json'):
                    k += 1
                tgt = f'{base}_{k}.json'
                note = f' (existing file not mergeable: {e})'
        print(f'  {name}.json: {n:4d} entries of {d} -> {os.path.relpath(tgt, OUT)}{note}')
        totals[d] += n
        if not dry:
            write_json(tgt, chunk)

    if not dry:
        if stay:
            rest = parts[None].get(today, []) if isinstance(data, list) else {k: p.get(today, []) for k, p in parts.items()}
            write_json(src, rest)
        else:
            os.remove(src)
    print(f'  {name}.json: ' + (f'keeps {", ".join(stay)} in json_output' if stay else 'removed from json_output (all archived)'))

print('Summary: ' + (', '.join(f'{d}: {n} entries' for d, n in sorted(totals.items())) or 'nothing to archive'))
