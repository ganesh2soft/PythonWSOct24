"""jsonl_store.py - file storage that replaces tradeguide's MySQL tables (Options, Futures).   v2, 9 Oct 2026

Layout (inside tradeguide/db_migrate_json/, one sub-folder per underlying so BANKNIFTY / SENSEX can be added later):
  Current_Expiry/<UL>/options_<expiry>/<date>.jsonl   nearest expiry (data.json expiry1 for NIFTY)
  Current_Expiry/<UL>/futures/<SYMBOL>.jsonl          current futures contract, ONE file for the whole month, appended every run
  Next_Expiry/<UL>/options_<expiry>/<date>.jsonl      later expiries (expiry2, expiry3)
  Archived_All/<UL>/options_<expiry>/...              expired weeks   (deleted after RETAIN_OPT_DAYS)
  Archived_All/<UL>/futures/<SYMBOL>.jsonl            expired months  (deleted after RETAIN_FUT_DAYS)
Option line (one per run per expiry):
  {"ts": "...", "ul": "NIFTY", "expiry": "2026-10-13", "spot": .., "pcr": .., "cols": [...OPT_COLS...], "rows": [[...], ...]}
Futures line (one per run): {"ts": "...", "symbol": "NIFTY26OCTFUT", "key": .., "last_price": .., "average_price": .., "oi": ..,
  "volume": .., "total_buy_quantity": .., "total_sell_quantity": .., "result": .., "src_ts": ..}
Rolling (folders follow the expiry dates) runs automatically on the first write of each day; retention via retention().
Every write / roll / delete / error is logged to tradeguide/opt_fut_entry_logger.log (rotating, 5 MB x 3).
Readers getopt() / getfut() return the same shapes as db_read.getopt() / getfut().
"""
import json, os, datetime, shutil, logging
from logging.handlers import RotatingFileHandler
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))           # tradeguide/db_migrate_json
BASE = os.path.dirname(HERE)                                # tradeguide
CUR, NXT, ARC = 'Current_Expiry', 'Next_Expiry', 'Archived_All'
OPT_COLS = ['strike', 'c_oi', 'c_oi_prev', 'c_vol', 'c_ltp', 'c_iv', 'p_oi', 'p_oi_prev', 'p_vol', 'p_ltp', 'p_iv']
RETAIN_OPT_DAYS = 21          # options: 3 weeks after expiry
RETAIN_FUT_DAYS = 92          # futures: 3 months after the contract file stops being written
EXPIRY_KEY = {'NIFTY': 'expiry1'}     # data.json key that holds the nearest expiry, per underlying
ROOT = HERE                   # tests point this somewhere else
LOGFILE = os.path.join(BASE, 'opt_fut_entry_logger.log')

log = logging.getLogger('opt_fut_entry')
if not log.handlers:
    log.setLevel(logging.INFO)
    log.propagate = False                                   # keep these lines out of tradelogger.log
    try:
        h = RotatingFileHandler(LOGFILE, maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
        h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', '%Y-%m-%d %H:%M:%S'))
        log.addHandler(h)
    except Exception:
        log.addHandler(logging.NullHandler())


# ------------------------------------------------------------------ helpers
def _g(obj, path, default=0):
    cur = obj
    for part in path.split('.'):
        if cur is None:
            return default
        cur = cur.get(part) if isinstance(cur, dict) else getattr(cur, part, None)
    return default if cur is None else cur


def _num(x):
    try:
        f = float(x)
    except (TypeError, ValueError):
        return 0
    return int(f) if f.is_integer() else round(f, 4)


def _iso(x):
    if isinstance(x, (datetime.datetime, datetime.date)):
        return x.isoformat()[:10] if isinstance(x, datetime.date) and not isinstance(x, datetime.datetime) else x.isoformat()
    return str(x) if x is not None else None


def _rel(p):
    return os.path.relpath(p, ROOT)


def _append(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    line = json.dumps(obj, separators=(',', ':'), default=str) + '\n'
    with open(path, 'a', encoding='utf-8') as f:            # one write per line keeps lines whole
        f.write(line)
        f.flush()
    return len(line)


def current_expiry(ul='NIFTY'):
    try:
        with open(os.path.join(BASE, 'data.json')) as f:
            return str(json.load(f).get(EXPIRY_KEY.get(ul, 'expiry1')))[:10]
    except Exception:
        return None


# ------------------------------------------------------------------ rolling + retention
_rolled = {}


def roll(ul='NIFTY', today=None, cur_exp=None):
    """Move option folders between tiers to match the expiry dates. Safe to call often (does real work once a day)."""
    today = today or datetime.date.today().isoformat()
    cur_exp = cur_exp or current_expiry(ul)
    if _rolled.get(ul) == (today, cur_exp):
        return
    for tier in (CUR, NXT):
        d = os.path.join(ROOT, tier, ul)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.startswith('options_'):
                continue
            exp = name[8:18]
            if exp < today:
                dest = ARC
            elif cur_exp and exp == cur_exp:
                dest = CUR
            else:
                dest = NXT
            if dest != tier:
                src, dst = os.path.join(d, name), os.path.join(ROOT, dest, ul, name)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if os.path.exists(dst):                      # merge day files, never overwrite
                    for f in os.listdir(src):
                        t = os.path.join(dst, f)
                        if not os.path.exists(t):
                            shutil.move(os.path.join(src, f), t)
                    if not os.listdir(src):
                        os.rmdir(src)
                else:
                    shutil.move(src, dst)
                log.info('ROLL %s %s: %s -> %s', ul, name, tier, dest)
    _rolled[ul] = (today, cur_exp)


def retention(dry_run=False, today=None):
    """Delete expired data in Archived_All: option folders > RETAIN_OPT_DAYS after expiry, futures files idle > RETAIN_FUT_DAYS."""
    today = datetime.date.fromisoformat(today) if today else datetime.date.today()
    out = []
    arc = os.path.join(ROOT, ARC)
    if not os.path.isdir(arc):
        return out
    for ul in sorted(os.listdir(arc)):
        d = os.path.join(arc, ul)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if name.startswith('options_'):
                try:
                    age = (today - datetime.date.fromisoformat(name[8:18])).days
                except ValueError:
                    continue
                if age > RETAIN_OPT_DAYS:
                    out.append(p)
                    if not dry_run:
                        shutil.rmtree(p)
            elif name == 'futures':
                for f in sorted(os.listdir(p)):
                    fp = os.path.join(p, f)
                    age = (today - datetime.date.fromtimestamp(os.path.getmtime(fp))).days
                    if age > RETAIN_FUT_DAYS:
                        out.append(fp)
                        if not dry_run:
                            os.remove(fp)
    for p in out:
        log.info('RETENTION %s %s', 'would delete' if dry_run else 'deleted', _rel(p))
    return out


# ------------------------------------------------------------------ writers
def write_optionchain(rows, ul='NIFTY', now=None):
    """rows = optbook.data (Upstox option-chain rows). Returns number of strikes written."""
    try:
        if not isinstance(rows, list) or not rows:
            log.warning('OPT %s nothing to write (empty or not a list)', ul)
            return 0
        now = now or datetime.datetime.now()
        today = now.date().isoformat()
        cur_exp = current_expiry(ul)
        roll(ul, today, cur_exp)
        groups = {}
        for r in rows:
            groups.setdefault(_iso(_g(r, 'expiry', None)), []).append(r)
        n = 0
        for exp, rs in groups.items():
            exp = (exp or 'unknown')[:10]
            tier = CUR if exp == cur_exp else NXT
            line = {'ts': now.isoformat(timespec='seconds'), 'ul': ul, 'expiry': exp,
                    'spot': _num(_g(rs[0], 'underlying_spot_price')), 'pcr': _num(_g(rs[0], 'pcr')), 'cols': OPT_COLS, 'rows': []}
            for r in rs:
                line['rows'].append([
                    _num(_g(r, 'strike_price')),
                    _num(_g(r, 'call_options.market_data.oi')), _num(_g(r, 'call_options.market_data.prev_oi')),
                    _num(_g(r, 'call_options.market_data.volume')), _num(_g(r, 'call_options.market_data.ltp')),
                    _num(_g(r, 'call_options.option_greeks.iv')),
                    _num(_g(r, 'put_options.market_data.oi')), _num(_g(r, 'put_options.market_data.prev_oi')),
                    _num(_g(r, 'put_options.market_data.volume')), _num(_g(r, 'put_options.market_data.ltp')),
                    _num(_g(r, 'put_options.option_greeks.iv'))])
            line['rows'].sort(key=lambda x: x[0])
            tc = sum(r[1] for r in line['rows']); tp = sum(r[6] for r in line['rows'])
            line['pcr'] = round(tp / tc, 4) if tc else 0      # chain PCR (Upstox row 'pcr' is per strike, not the chain)
            path = os.path.join(ROOT, tier, ul, 'options_' + exp, today + '.jsonl')
            nb = _append(path, line)
            log.info('OPT %s %s strikes=%d spot=%s pcr=%s -> %s (+%.1f KB)', ul, exp, len(rs), line['spot'], line['pcr'], _rel(path), nb / 1024)
            n += len(rs)
        return n
    except Exception as e:
        log.error('OPT %s write failed: %s: %s', ul, type(e).__name__, str(e)[:200])
        raise


def write_futures(data, ul='NIFTY', now=None):
    """data = future_response.data (dict key -> quote). One file per contract symbol, appended every run."""
    try:
        if not isinstance(data, dict) or not data:
            log.warning('FUT %s nothing to write (empty or not a dict)', ul)
            return 0
        now = now or datetime.datetime.now()
        try:
            from db_write import fut_senti
        except Exception:
            fut_senti = None
        fdir = os.path.join(ROOT, CUR, ul, 'futures')
        written = set()
        for key, q in data.items():
            sym = str(_g(q, 'symbol', '') or str(key).split(':')[-1].split('|')[-1]).strip() or 'UNKNOWN'
            tb, tsq = _g(q, 'total_buy_quantity'), _g(q, 'total_sell_quantity')
            res = None
            if fut_senti:
                try:
                    res = fut_senti(tb, tsq)
                except Exception:
                    res = None
            line = {'ts': now.isoformat(timespec='seconds'), 'symbol': sym, 'key': key,
                    'last_price': _num(_g(q, 'last_price')), 'average_price': _num(_g(q, 'average_price')), 'oi': _num(_g(q, 'oi')),
                    'volume': _num(_g(q, 'volume')), 'total_buy_quantity': _num(tb), 'total_sell_quantity': _num(tsq),
                    'result': res, 'src_ts': _iso(_g(q, 'timestamp', None))}
            path = os.path.join(fdir, sym + '.jsonl')
            nb = _append(path, line)
            written.add(sym + '.jsonl')
            log.info('FUT %s %s ltp=%s oi=%s vol=%s -> %s (+%d B)', ul, sym, line['last_price'], line['oi'], line['volume'], _rel(path), nb)
        # a contract file that was not written today belongs to an expired month -> Archived_All
        today = now.date()
        for f in os.listdir(fdir):
            fp = os.path.join(fdir, f)
            if f not in written and f.endswith('.jsonl') and datetime.date.fromtimestamp(os.path.getmtime(fp)) < today:
                dst = os.path.join(ROOT, ARC, ul, 'futures', f)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                if not os.path.exists(dst):
                    shutil.move(fp, dst)
                    log.info('ROLL %s futures %s: %s -> %s', ul, f, CUR, ARC)
        return len(written)
    except Exception as e:
        log.error('FUT %s write failed: %s: %s', ul, type(e).__name__, str(e)[:200])
        raise


# ------------------------------------------------------------------ readers
def iter_lines(path):
    if not os.path.exists(path):
        return
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for raw in f:
            raw = raw.strip()
            if raw:
                try:
                    yield json.loads(raw)
                except ValueError:
                    continue          # half-written line after a crash


def option_dir(expiry, ul='NIFTY'):
    exp = _iso(expiry)[:10]
    for tier in (CUR, NXT, ARC):
        d = os.path.join(ROOT, tier, ul, 'options_' + exp)
        if os.path.isdir(d):
            return d
    return None


def read_optionchain(expiry, day=None, ul='NIFTY'):
    d = option_dir(expiry, ul)
    if not d:
        return []
    days = sorted(f[:-6] for f in os.listdir(d) if f.endswith('.jsonl'))
    if day is None and days:
        day = days[-1]
    return list(iter_lines(os.path.join(d, str(day) + '.jsonl')))


def getopt(expirydate, ul='NIFTY'):
    """Same shape as db_read.getopt(): dicts for the last two available days of this expiry."""
    d = option_dir(expirydate, ul)
    if not d:
        return []
    days = sorted(f[:-6] for f in os.listdir(d) if f.endswith('.jsonl'))[-2:]
    if days and days[-1] != datetime.date.today().isoformat():
        print(f"Alert: The most recent available data is from {days[-1]}, not today!")
    out, lid = [], 0
    for day in days:
        for l in iter_lines(os.path.join(d, day + '.jsonl')):
            ts = datetime.datetime.fromisoformat(l['ts'])
            ix = {c: i for i, c in enumerate(l['cols'])}
            ed = datetime.date.fromisoformat(l['expiry'][:10])
            for r in l['rows']:
                lid += 1
                out.append({'ledger_id': lid, 'date_entry': ts,
                            'call_writer_oi': r[ix['c_oi']], 'call_wri_oi_prev': r[ix['c_oi_prev']], 'call_volume': r[ix['c_vol']],
                            'call_ltp': r[ix['c_ltp']], 'call_iv': r[ix['c_iv']], 'expiry_date': ed, 'strike_price': r[ix['strike']],
                            'put_writer_oi': r[ix['p_oi']], 'put_wri_oi_prev': r[ix['p_oi_prev']], 'put_volume': r[ix['p_vol']],
                            'put_ltp': r[ix['p_ltp']], 'put_iv': r[ix['p_iv']], 'nifty_spot_price': l.get('spot'), 'pcr': l.get('pcr')})
    return out


def getfut(ul='NIFTY'):
    """Same shape as db_read.getfut(): Futures-like objects for the last available day of the current contract file(s)."""
    fdir = os.path.join(ROOT, CUR, ul, 'futures')
    if not os.path.isdir(fdir):
        return []
    lines = [l for f in sorted(os.listdir(fdir)) if f.endswith('.jsonl') for l in iter_lines(os.path.join(fdir, f))]
    if not lines:
        return []
    last_day = max(l['ts'][:10] for l in lines)
    if last_day != datetime.date.today().isoformat():
        print(f"Alert: The most recent available data is from {last_day}, not today!")
    out = []
    for i, l in enumerate([l for l in lines if l['ts'][:10] == last_day], 1):
        out.append(SimpleNamespace(symid=i, ts=datetime.datetime.fromisoformat(l['ts']), average_price=l.get('average_price'),
                                   instrument_token=l.get('key'), last_price=l.get('last_price'), oi=l.get('oi'), symbol=l.get('symbol'),
                                   total_buy_quantity=l.get('total_buy_quantity'), total_sell_quantity=l.get('total_sell_quantity'),
                                   volume=l.get('volume'), result=l.get('result')))
    return out
