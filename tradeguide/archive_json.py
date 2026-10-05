"""Archive tradeguide's daily 5-min output JSONs into json_output/archive/<data date>/ (nothing is deleted).
Data date = the date with the most snapshots in mainindex.json (ignores night / pre-open test runs).
optvwap.json and the ASGBOOM state files are left in place on purpose.
Usage: python archive_json.py [--dry-run]"""
import json, os, sys, shutil, collections, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'json_output')
FILES = ['banktop5', 'midcaptop5', 'nifty5min', 'niftytop10', 'premium', 'trend', 'mainindex', 'covering', 'sectors']
dry = '--dry-run' in sys.argv

mi = os.path.join(OUT, 'mainindex.json')
if not os.path.exists(mi):
    print('mainindex.json not found - nothing to archive.')
    sys.exit(0)
day = None
try:
    with open(mi) as f:
        data = json.load(f)
    c = collections.Counter(str(x.get('timestamp', ''))[:10] for x in data if isinstance(x, dict))
    c.pop('', None)
    if c:
        day = c.most_common(1)[0][0]
except Exception as e:
    print(f'Could not read mainindex.json ({e}); using file date.')
if not day:
    day = datetime.date.fromtimestamp(os.path.getmtime(mi)).isoformat()

dest = os.path.join(OUT, 'archive', day)
print(f'Data date: {day}  ->  {dest}' + ('  (dry run, nothing moved)' if dry else ''))
if not dry:
    os.makedirs(dest, exist_ok=True)
moved = 0
for name in FILES:
    src = os.path.join(OUT, name + '.json')
    if not os.path.exists(src):
        continue
    tgt = os.path.join(dest, name + '.json')
    k = 2
    while os.path.exists(tgt):                      # never overwrite an archived file
        tgt = os.path.join(dest, f'{name}_{k}.json'); k += 1
    print(f'  {name}.json -> {os.path.relpath(tgt, OUT)}')
    if not dry:
        shutil.move(src, tgt)
    moved += 1
print(f'{"Would archive" if dry else "Archived"} {moved} file(s).')
