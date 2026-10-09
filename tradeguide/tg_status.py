"""tg_status.py - one-shot tradeguide status (reads files only, never calls Upstox, never changes anything).

Usage:  python tg_status.py [--date YYYY-MM-DD] [--time HH:MM] [--oi] [--sec] [--vwap] [--all]
  (no flags)  short summary for tg-check  (~12 lines)
  --oi        full strike-wise OI table   (tg-oi)
  --sec       full sector table           (tg-nifty-sec)
  --vwap      option VWAP breadth detail  (tg-opt-vwap)
  --all       summary + all three sections
  --date      day to report (default today); reads json_output/, else json_output/archive/<date>/
  --time      report "as of" this time (uses the last snapshot at or before it)
Sources: json_output/{mainindex,trend,sectors,optvwap}.json, tradelogger.log (OI, errors), asgboom.log, data.json.
Lines containing token / secret / authorization / bearer / code= are never printed."""
import json, os, re, sys, datetime

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'json_output')
BAD = re.compile(r'token|secret|authoriz|bearer|code=', re.I)
args = sys.argv[1:]


def opt(name, default=None):
    if name in args and args.index(name) + 1 < len(args):
        return args[args.index(name) + 1]
    return default


NOW = datetime.datetime.now()
TODAY = NOW.strftime('%Y-%m-%d')
DAY = opt('--date', TODAY)
ASOF = opt('--time', '23:59' if DAY == TODAY else '15:40')   # past days: ignore night test runs
SHOW_ALL = '--all' in args
SECTIONS = {s for s in ('--oi', '--sec', '--vwap') if s in args or SHOW_ALL}
SUMMARY = SHOW_ALL or not SECTIONS


def L(x):            # OI units -> lakh
    return x / 1e5


def hm(ts):
    return str(ts)[11:16]


def on_day(ts):
    return str(ts)[:10] == DAY and hm(ts) <= ASOF


def ts_of(x):
    return x.get('timestamp') or x.get('recdate') or x.get('vixts') or ''


def load(name):
    """Entries of DAY from json_output/<name>.json, else archive/<DAY>/<name>.json."""
    for p in (os.path.join(OUT, name + '.json'), os.path.join(OUT, 'archive', DAY, name + '.json')):
        if not os.path.exists(p):
            continue
        try:
            d = json.load(open(p))
        except Exception:
            continue
        if isinstance(d, list):
            r = [x for x in d if isinstance(x, dict) and on_day(ts_of(x))]
            if r:
                return r
        elif isinstance(d, dict):
            r = {k: [x for x in v if isinstance(x, dict) and on_day(ts_of(x))] for k, v in d.items() if isinstance(v, list)}
            if any(r.values()):
                return r
    return {} if name == 'trend' else []


def near(snaps, t, key='timestamp'):
    """last snapshot at or before HH:MM t (else the first one)"""
    c = [s for s in snaps if hm(s.get(key, '')) <= t]
    return c[-1] if c else (snaps[0] if snaps else None)


def minus(t, mins):
    h, m = map(int, t.split(':'))
    x = max(h * 60 + m - mins, 0)
    return '%02d:%02d' % (x // 60, x % 60)


# ---------------- OI + errors from tradelogger.log ----------------
def parse_log():
    snaps, spot, errs, cur = [], {}, [], None
    p = os.path.join(BASE, 'tradelogger.log')
    if not os.path.exists(p):
        return snaps, errs
    with open(p, 'r', errors='ignore') as f:
        for l in f:
            l = l.rstrip('\r\n')
            if l[:10] == DAY:
                t = l[11:16]
                if t > ASOF and cur is None:
                    continue
                if re.search(r' - (ERROR|CRITICAL) - |Traceback|Error in |Exception', l) and not BAD.search(l):
                    errs.append(l[:160])
                m = re.search(r'IVIX: ([\d.]+), Nifty50: ([\d.]+), Nifty Futures: ([\d.]+)', l)
                if m:
                    spot[t] = (float(m.group(1)), float(m.group(2)), float(m.group(3)))
                if 'Filtered DataFrame with Relevant Data' in l and t <= ASOF:
                    cur = {'t': t, 'rows': {}}
                    continue
                if 'End of Few Strikes Dataframe' in l and cur is not None:
                    if cur['rows']:
                        snaps.append(cur)
                    cur = None
                continue
            if cur is not None:
                q = l.split()
                if len(q) == 8:
                    try:
                        cur['rows'][int(float(q[1]))] = dict(coi=float(q[2]), poi=float(q[3]), cl=float(q[6]), pl=float(q[7]))
                    except ValueError:
                        pass
    for s in snaps:
        s['vix'], s['spot'], s['fut'] = spot.get(s['t'], (None, None, None))
    return snaps, errs


def oi_base(snaps):
    for t in ('09:21', '09:26'):
        for s in snaps:
            if s['t'] == t:
                return s
    return snaps[0] if snaps else None


def pcr(s, keys=None):
    ks = list(keys) if keys is not None else list(s['rows'].keys())
    c = sum(s['rows'][k]['coi'] for k in ks if k in s['rows'])
    p = sum(s['rows'][k]['poi'] for k in ks if k in s['rows'])
    return p / c if c else 0.0


def idx(snap, name):
    for i in (snap or {}).get('main_index', []):
        if i.get('index') == name:
            return i.get('ltp')
    return None


ANCH = {1: 'low', -1: 'high', 0: 'start'}

# ---------------- load ----------------
MI = load('mainindex')
TR = load('trend')
SEC = load('sectors')
OV = load('optvwap')
OI, ERRS = parse_log()
lines = []
P = lines.append

if not (MI or OV or OI):
    print('tg_status %s: no tradeguide data for this day (Flask not run yet, or a holiday).' % DAY)
    sys.exit(0)

last = MI[-1] if MI else None
t_last = hm(last['timestamp']) if last else (OI[-1]['t'] if OI else '09:15')
t30 = minus(t_last, 30)

# ---------------- SUMMARY (tg-check) ----------------
if SUMMARY:
    h = ['last run ' + t_last]
    if DAY == TODAY and last and '--time' not in args:
        age = (NOW - datetime.datetime.strptime(last['timestamp'][:19], '%Y-%m-%d %H:%M:%S')).total_seconds() / 60
        if '09:15' <= NOW.strftime('%H:%M') <= '15:45':
            h.append('OK' if age <= 11 else 'STALE (%.0f min old)' % age)
        else:
            h.append('%.0f min ago' % age)
    h.append('errors %d' % len(ERRS))
    try:
        e1 = json.load(open(os.path.join(BASE, 'data.json'))).get('expiry1')
        h.append('expiry1 %s%s' % (e1, '  ** EXPIRED - update data.json **' if e1 and e1 < DAY else ''))
    except Exception:
        pass
    asg_last, asg_alerts = None, []
    ap = os.path.join(BASE, 'asgboom.log')
    if os.path.exists(ap):
        for l in open(ap, errors='ignore'):
            l = l.rstrip('\r\n')
            if l[:10] != DAY or l[11:16] > ASOF or BAD.search(l):
                continue
            if 'Sent:' in l:
                msg = l.split('Sent:', 1)[1].strip()
                asg_alerts.append(l[11:16] + ' ' + (msg.split('|')[-1].strip() if msg.startswith('ASGBOOM') else msg[:60]))
            elif re.search(r'started|stopped|rror', l):
                asg_last = l[11:].strip()[:70]
    h.append('ASGBOOM: ' + (asg_last or 'no status line'))
    P('== tg_status %s (as of %s) ==' % (DAY, t_last))
    P('Health : ' + ' | '.join(h))

    first = next((m for m in MI if hm(m['timestamp']) >= '09:16'), MI[0] if MI else None)
    n, bn, mid = idx(last, 'NIFTY 50'), idx(last, 'BANK NIFTY'), idx(last, 'MIDCAP')
    s_last = SEC[-1] if SEC else None
    ov_last = OV[-1] if OV else None
    px = 'Nifty %s' % n
    if s_last:
        nn = s_last['nifty']
        px += ' (%+.2f%% vs prev close, %+.2f%% vs %s)' % (nn['chg_prev_pct'], nn['chg_base_pct'], nn['base_ref'])
    if ov_last:
        px += ' | day H %s L %s' % (ov_last['nifty']['day_high'], ov_last['nifty']['day_low'])
    m30 = near(MI, t30)
    if m30 and n is not None and idx(m30, 'NIFTY 50') is not None:
        px += ' | 30m %+.0f' % (n - idx(m30, 'NIFTY 50'))
    P('Price  : ' + px)
    bnf = idx(first, 'BANK NIFTY')
    s = 'BN/MID : BN %s' % bn
    if bn and bnf:
        s += ' (%s 09:16 %s, %+.0f)' % ('above' if bn >= bnf else 'below', bnf, bn - bnf)
    P(s + ' | MID %s' % mid)
    vs = TR.get('vix_set', []) if isinstance(TR, dict) else []
    if vs:
        v0 = next((v for v in vs if hm(v['vixts']) >= '09:16'), vs[0])
        v1, v30 = vs[-1], near(vs, t30, 'vixts')
        P('VIX    : %s (09:16 %s, %s open; 30m %+.2f)' % (v1['ivix'], v0['ivix'], 'ABOVE' if v1['ivix'] > v0['ivix'] else 'below', v1['ivix'] - v30['ivix']))
    if ov_last:
        sc, sg, an = ov_last['scores'], ov_last['signal'], ov_last['anchor']
        chg = None
        for a, b in zip(OV, OV[1:]):
            if a['signal']['verdict'] != b['signal']['verdict']:
                chg = hm(b['timestamp'])
        okk = 'CALL ok' if sg['call_ok'] else 'PUT ok' if sg['put_ok'] else 'no side ok'
        P('OptVWAP: %s | %s | day %+d (CE %d/PE %d) | anchor %s@%s score %+d hold %s%s' % (
            sg['verdict'], okk, sc['day_score'], sc['ce_day'], sc['pe_day'], ANCH.get(an.get('dir'), '?'), an.get('time'),
            sc['anc_score'], sc['anc_hold'], (' | verdict since ' + chg) if chg else ''))
    if OI:
        b, s = oi_base(OI), OI[-1]
        s30 = next((x for x in reversed(OI) if x['t'] <= t30), OI[0])
        common = [k for k in s['rows'] if k in b['rows']]
        sp = s['spot'] or n or 0
        cw = max([k for k in s['rows'] if k >= sp] or [None], key=lambda k: s['rows'][k]['coi'] if k else 0)
        pw = max([k for k in s['rows'] if k <= sp] or [None], key=lambda k: s['rows'][k]['poi'] if k else 0)
        ch = []
        for k in s['rows']:
            if k in s30['rows']:
                dc = s['rows'][k]['coi'] - s30['rows'][k]['coi']
                dp = s['rows'][k]['poi'] - s30['rows'][k]['poi']
                ch.append((abs(dc), '%dC %+.0fL' % (k, L(dc))))
                ch.append((abs(dp), '%dP %+.0fL' % (k, L(dp))))
        ch = [c[1] for c in sorted(ch, reverse=True)[:3]]
        txt = 'OI %s : PCR(9 strikes) %s %.2f -> %.2f' % (s['t'], b['t'], pcr(b), pcr(s))
        if cw:
            txt += ' | call wall %d (%.0fL)' % (cw, L(s['rows'][cw]['coi']))
        if pw:
            txt += ' | put wall %d (%.0fL)' % (pw, L(s['rows'][pw]['poi']))
        P(txt + ' | 30m: ' + ', '.join(ch))
    ps = TR.get('pcr_set', []) if isinstance(TR, dict) else []
    if ps:
        e1 = min(x['expiry'] for x in ps if x['expiry'] >= DAY) if any(x['expiry'] >= DAY for x in ps) else ps[-1]['expiry']
        e1p = [p for p in ps if p['expiry'] == e1][-1]
        P('PCR    : expiry %s %.2f %s' % (e1p['expiry'], e1p['tpcr'], e1p['pcrtrend']))
    if s_last:
        sm = s_last['summary']['since_base']
        its = sorted(s_last['items'], key=lambda i: i['nifty_pts_base'])
        nd = s_last['nifty']['chg_base_pct']
        drv = its[:2] if nd < 0 else its[::-1][:2]
        res = its[-1] if nd < 0 else its[0]
        w = sm['weight_with_nifty_pct']
        P('Sectors: %s%% weight with Nifty (%s), %+.0f pts since base | drivers %s %+.0f, %s %+.0f | resister %s %+.0f' % (
            w, 'broad' if w >= 70 else 'narrow' if w <= 40 else 'mixed', sm['pts_total'],
            drv[0]['name'], drv[0]['nifty_pts_base'], drv[1]['name'], drv[1]['nifty_pts_base'], res['name'], res['nifty_pts_base']))
    if asg_alerts:
        P('Alerts : ' + ' ; '.join(asg_alerts[-3:]))
    for e in ERRS[-3:]:
        P('ERROR  : ' + e)

# ---------------- --oi (tg-oi) ----------------
if '--oi' in SECTIONS and OI:
    b, s = oi_base(OI), OI[-1]
    s30 = next((x for x in reversed(OI) if x['t'] <= t30), OI[0])
    P('')
    P('== OI (lakh) base %s | 30m ref %s | now %s | spot %s VIX %s (base spot %s VIX %s) ==' % (b['t'], s30['t'], s['t'], s['spot'], s['vix'], b['spot'], b['vix']))
    P('%7s %7s %6s %6s %7s %6s %6s %7s %7s' % ('strike', 'callOI', 'dBase', 'd30m', 'putOI', 'dBase', 'd30m', 'C ltp', 'P ltp'))
    nc = npu = 0.0

    def d(r, rr, f):
        return '%+6.1f' % L(r[f] - rr[f]) if rr else '   new'
    for k in sorted(s['rows']):
        r, rb, r3 = s['rows'][k], b['rows'].get(k), s30['rows'].get(k)
        if rb:
            nc += r['coi'] - rb['coi']
            npu += r['poi'] - rb['poi']
        P('%7d %7.1f %s %s %7.1f %s %s %7.1f %7.1f' % (k, L(r['coi']), d(r, rb, 'coi'), d(r, r3, 'coi'), L(r['poi']), d(r, rb, 'poi'), d(r, r3, 'poi'), r['cl'], r['pl']))
    common = [k for k in s['rows'] if k in b['rows']]
    P('net dOI since base (common strikes): calls %+.1fL  puts %+.1fL | PCR base %.2f -> now %.2f (all 9: %.2f)' % (L(nc), L(npu), pcr(b, common), pcr(s, common), pcr(s)))
    tl = ['%s %.0f/%.2f' % (x['t'], x['spot'], pcr(x)) for x in OI if x['spot'] and (x['t'][-2:] in ('16', '46') or x is OI[-1])]
    P('timeline (time spot/PCR): ' + '  '.join(tl))

# ---------------- --sec (tg-nifty-sec) ----------------
if '--sec' in SECTIONS and SEC:
    s = SEC[-1]
    s30 = near(SEC, t30)
    nn = s['nifty']
    P('')
    P('== Sectors %s | Nifty %s base %s %s (%+.2f%%), vs prev close %+.2f%% ==' % (hm(s['timestamp']), nn['ltp'], nn['base_ref'], nn['base'], nn['chg_base_pct'], nn['chg_prev_pct']))
    P('%-22s %-18s %5s %6s %6s %6s %6s  dir' % ('sector', 'tracked as', 'wt', '%base', '%prev', 'pts', 'pts30m'))
    old = {i['name']: i for i in (s30 or s)['items']}
    for i in sorted(s['items'], key=lambda i: i['nifty_pts_base']):
        al = 'with' if (i['chg_base_pct'] > 0) == (nn['chg_base_pct'] > 0) else 'AGAINST'
        d30 = i['nifty_pts_base'] - old.get(i['name'], i)['nifty_pts_base']
        P('%-22s %-18s %5.2f %+6.2f %+6.2f %+6.1f %+6.1f  %s' % (i['sector'][:22], i['name'][:18], i['weight'], i['chg_base_pct'], i['chg_prev_pct'], i['nifty_pts_base'], d30, al))
    for k, v in s['summary'].items():
        P('%s: weight up %s%% | with Nifty %s%% | tracked pts %+.1f' % (k, v['weight_up_pct'], v['weight_with_nifty_pct'], v['pts_total']))
    bad = [i['name'] for i in s['items'] if i.get('ltp') is None]
    if bad:
        P('MISSING ltp: ' + ', '.join(bad))

# ---------------- --vwap (tg-opt-vwap) ----------------
if '--vwap' in SECTIONS and OV:
    P('')
    P('== OptVWAP %d snapshots %s-%s ==' % (len(OV), hm(OV[0]['timestamp']), hm(OV[-1]['timestamp'])))
    P('%5s %8s %6s CE PE %4s %11s %4s hold ok    verdict' % ('time', 'nifty', 'atm', 'day', 'anchor', 'anc'))
    prev = None
    for i, x in enumerate(OV):
        v, t = x['signal']['verdict'], hm(x['timestamp'])
        if t[-2:] in ('16', '46') or v != prev or i == len(OV) - 1:
            sc, sg, an = x['scores'], x['signal'], x['anchor']
            ok = 'CALL' if sg['call_ok'] else 'PUT ' if sg['put_ok'] else '-   '
            P('%5s %8s %6s %2s %2s %+4d %11s %+4d %4s %s  %s%s' % (
                t, x['nifty']['ltp'], x['nifty']['atm'], sc['ce_day'], sc['pe_day'], sc['day_score'],
                ANCH.get(an.get('dir'), '?') + '@' + str(an.get('time')), sc['anc_score'], sc['anc_hold'], ok, v,
                '  [preopen]' if x.get('preopen') else ''))
        prev = v
    x = OV[-1]
    P('strikes at %s (ltp / vwap / anchored vwap, ^ above vwap, vol5 vs avg):' % hm(x['timestamp']))
    for r in x['strikes']:
        c, p = r['CE'], r['PE']
        P('  %s CE %-4s %s/%s/%s %s vol %.1fx | PE %-4s %s/%s/%s %s vol %.1fx' % (
            r['strike'], c['role'], c['ltp'], c['vwap'], c['anc_vwap'], '^' if c['above_vwap'] else 'v', c['vol5'] / max(c['vol5_avg'] or 1, 1),
            p['role'], p['ltp'], p['vwap'], p['anc_vwap'], '^' if p['above_vwap'] else 'v', p['vol5'] / max(p['vol5_avg'] or 1, 1)))
    if x.get('reversal'):
        P('reversal latch: ' + json.dumps(x['reversal'])[:200])

print('\n'.join(l for l in lines if not BAD.search(l)))
