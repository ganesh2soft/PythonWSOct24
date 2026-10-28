"""ace_levels.py - track Senthil's ACE MASTERLEVEL levels inside tradeguide (28 Oct 2026).

capture(access_token)  called from app.startrecord() every run; does real work only until the
                       day's data is saved:
  * first 5-min candle 09:15-09:20 of Nifty 50 (exact OHLC from Upstox 5-min candles; v3 API,
    fallback v2 1-minute candles aggregated 09:15-09:19)
  * previous trading day: 15:10-15:15 candle close (ACE "pre-CAS 15:15" reference close),
    last candle (15:25) open/close for Concept 2, day high / low
  Saved to json_output/ace_levels.json  {date: {...}}. Never prints or stores the token.

levels(day, hi, lo)    ACE formulas (master level script v6.6w, Concept 1 + Concept 2 original method):
  ET  = first open +/- |first open - ref close|                         (Concept 1 only)
  50% = running extreme + (ET - extreme) x 0.50 ; 75% = x 0.75          (UP from today's low, DN from today's high)
  EET = first body edge +/- 2 x liquidity  (liquidity per SETTINGS)     EET 50% / 75% same running-extreme method
  Concept 2 when yesterday's last candle open AND close are inside today's first-candle body.
status_line(day, ov)   one line for tg_status.

Liquidity (ACE "Liquidity Meter") is Senthil's setting - fill SETTINGS once he tells us.
RULE (user, 28 Oct 2026): ACE output is NEVER sent to Telegram (no asgboom.send, no tg_alerts use). It is printed only
in tg_status / "check now" - ACE logic is experimental here and must not confuse the ASG group.
"""
import os, json, datetime, logging, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, 'json_output')
FILE = os.path.join(OUT, 'ace_levels.json')
KEY = 'NSE_INDEX|Nifty 50'
log = logging.getLogger('app')

SETTINGS = {
    'LIQ_MODE': 'manual',      # 'manual' | 'first5_body' | 'first5_full'   (ACE: Manual / Today First 5-min Body / Full Candle)
    'LIQ_VALUE': None,         # manual liquidity value in Nifty points (None = not known yet -> EET shown for body/full only)
    'LIQ_FROM': 'Body',        # 'Body' (first candle open/close) | 'Edge' (first candle high/low)
}


def _get(url, token):
    req = urllib.request.Request(url, headers={'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (tradeguide)', 'Api-Version': '2.0', 'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode('utf-8'))


def _sdk(token):
    import upstox_client   # same SDK (v2 HistoryApi) the rest of tradeguide uses
    cfg = upstox_client.Configuration()
    cfg.access_token = token
    return upstox_client.HistoryApi(upstox_client.ApiClient(cfg))


def _sdk_candles(resp):
    data = getattr(resp, 'data', None)
    cs = getattr(data, 'candles', None) if data is not None else None
    if cs is None and isinstance(resp, dict):
        cs = (resp.get('data') or {}).get('candles')
    return _candles({'data': {'candles': cs or []}})


def _candles(resp):
    out = []
    for c in (resp or {}).get('data', {}).get('candles', []) or []:
        ts = str(c[0])
        out.append({'d': ts[:10], 't': ts[11:16], 'o': float(c[1]), 'h': float(c[2]), 'l': float(c[3]), 'c': float(c[4])})
    return sorted(out, key=lambda x: (x['d'], x['t']))


def _agg(cs):
    return {'o': cs[0]['o'], 'h': max(c['h'] for c in cs), 'l': min(c['l'] for c in cs), 'c': cs[-1]['c']}


def _first5(token, day):
    k = urllib.parse.quote(KEY, safe='')
    try:   # SDK v2 intraday 1-minute candles, 09:15-09:19 combined
        cs = [c for c in _sdk_candles(_sdk(token).get_intra_day_candle_data(KEY, '1minute', '2.0'))
              if c['d'] == day and '09:15' <= c['t'] <= '09:19']
        if len(cs) == 5:
            return dict(_agg(cs), src='upstox sdk v2 1min x5')
    except Exception as e:
        log.info('ACE first5 sdk failed: %s' % str(e)[:120])
    try:   # v3: native 5-minute candles
        cs = [c for c in _candles(_get('https://api.upstox.com/v3/historical-candle/intraday/%s/minutes/5' % k, token)) if c['d'] == day]
        f = next((c for c in cs if c['t'] == '09:15'), None)
        if f:
            return dict(_agg([f]), src='upstox v3 5min')
    except Exception as e:
        log.info('ACE first5 v3 failed: %s' % str(e)[:120])
    cs = [c for c in _candles(_get('https://api.upstox.com/v2/historical-candle/intraday/%s/1minute' % k, token))
          if c['d'] == day and '09:15' <= c['t'] <= '09:19']
    if len(cs) == 5:
        return dict(_agg(cs), src='upstox v2 1min x5')
    return None


def _prev(token, day):
    k = urllib.parse.quote(KEY, safe='')
    d0 = datetime.date.fromisoformat(day)
    to_d, fr_d = (d0 - datetime.timedelta(days=1)).isoformat(), (d0 - datetime.timedelta(days=10)).isoformat()
    cs, src = [], ''
    try:   # SDK v2 historical 1-minute candles
        cs = _sdk_candles(_sdk(token).get_historical_candle_data1(KEY, '1minute', to_d, (d0 - datetime.timedelta(days=6)).isoformat(), '2.0')); src = 'upstox sdk v2 1min'
    except Exception as e:
        log.info('ACE prev sdk failed: %s' % str(e)[:120])
    if not cs:
      try:
        cs = _candles(_get('https://api.upstox.com/v3/historical-candle/%s/minutes/5/%s/%s' % (k, to_d, fr_d), token)); src = 'upstox v3 5min'
      except Exception as e:
        log.info('ACE prev v3 failed: %s' % str(e)[:120])
    if not cs:
        cs = _candles(_get('https://api.upstox.com/v2/historical-candle/%s/1minute/%s/%s' % (k, to_d, fr_d), token)); src = 'upstox v2 1min'
    cs = [c for c in cs if c['d'] < day]
    if not cs:
        return None
    pd_ = cs[-1]['d']
    dc = [c for c in cs if c['d'] == pd_ and '09:15' <= c['t'] <= '15:29']
    five = '5min' in src
    c1510 = [c for c in dc if ('15:10' <= c['t'] <= '15:14')] if not five else [c for c in dc if c['t'] == '15:10']
    last = [c for c in dc if ('15:25' <= c['t'] <= '15:29')] if not five else [c for c in dc if c['t'] == '15:25']
    return {'date': pd_, 'close1515': c1510[-1]['c'] if c1510 else None,
            'last_o': _agg(last)['o'] if last else None, 'last_c': _agg(last)['c'] if last else None,
            'high': max(c['h'] for c in dc), 'low': min(c['l'] for c in dc), 'src': src}


def load_all():
    try:
        return json.load(open(FILE))
    except Exception:
        return {}


def capture(access_token, now=None):
    """Called every scheduler run. Fetches once per day after 09:20:30; retries on later runs if it failed."""
    now = now or datetime.datetime.now()
    day = now.strftime('%Y-%m-%d')
    if now.strftime('%H:%M:%S') < '09:20:30' or not access_token:
        return 'too early'
    allx = load_all()
    rec = allx.get(day, {})
    if rec.get('first5') and rec.get('prev'):
        return 'have'
    try:
        if not rec.get('first5'):
            f = _first5(access_token, day)
            if f:
                rec['first5'] = f
        if not rec.get('prev'):
            p = _prev(access_token, day)
            if p:
                rec['prev'] = p
    except Exception as e:
        log.error('ACE capture failed: %s' % str(e)[:160])
    rec['fetched_at'] = now.strftime('%H:%M:%S')
    allx = {k: v for k, v in allx.items() if k >= (now.date() - datetime.timedelta(days=60)).isoformat()}
    allx[day] = rec
    json.dump(allx, open(FILE, 'w'), indent=1)
    log.info('ACE levels: first5 %s, prev %s' % ('ok' if rec.get('first5') else 'MISSING', 'ok' if rec.get('prev') else 'MISSING'))
    return 'saved'


def _liq(f):
    m, v = SETTINGS['LIQ_MODE'], SETTINGS['LIQ_VALUE']
    if m == 'first5_body':
        return abs(f['c'] - f['o']), 'first5 body'
    if m == 'first5_full':
        return f['h'] - f['l'], 'first5 full'
    return (v, 'manual') if v else (None, 'not set')


def levels(day, hi=None, lo=None, rec=None):
    rec = rec or load_all().get(day) or {}
    f, p = rec.get('first5'), rec.get('prev') or {}
    if not f:
        return None
    hi = max(f['h'], hi if hi is not None else f['h'])
    lo = min(f['l'], lo if lo is not None else f['l'])
    bl, bh = min(f['o'], f['c']), max(f['o'], f['c'])
    c2 = p.get('last_o') is not None and p.get('last_c') is not None and bl <= p['last_o'] <= bh and bl <= p['last_c'] <= bh
    L = {'concept': 2 if c2 else 1, 'first5': f, 'ref_close': p.get('close1515'), 'hi': hi, 'lo': lo}
    if not c2 and p.get('close1515'):
        em = abs(f['o'] - p['close1515'])
        L.update(up_et=f['o'] + em, dn_et=f['o'] - em, gap=em)
        L.update(up_50=lo + (L['up_et'] - lo) * 0.5, up_75=lo + (L['up_et'] - lo) * 0.75,
                 dn_50=hi - (hi - L['dn_et']) * 0.5, dn_75=hi - (hi - L['dn_et']) * 0.75)
    liq, liq_src = _liq(f)
    L['liq'], L['liq_src'] = liq, liq_src
    ub, lb = (bh, bl) if SETTINGS['LIQ_FROM'] == 'Body' else (f['h'], f['l'])
    if liq:
        L.update(up_eet=ub + 2 * liq, dn_eet=lb - 2 * liq)
        L.update(up_eet50=lo + (L['up_eet'] - lo) * 0.5, up_eet75=lo + (L['up_eet'] - lo) * 0.75,
                 dn_eet50=hi - (hi - L['dn_eet']) * 0.5, dn_eet75=hi - (hi - L['dn_eet']) * 0.75)
        if c2:   # Concept 2 original method: 50% measured to EET
            L['up_50'] = f['c'] + (L['up_eet'] - f['c']) * 0.5 if f['c'] > f['o'] else lo + (L['up_eet'] - lo) * 0.5
            L['dn_50'] = f['c'] - (f['c'] - L['dn_eet']) * 0.5 if f['c'] < f['o'] else hi - (hi - L['dn_eet']) * 0.5
    else:   # liquidity unknown: show EET for the two first-candle modes as a guide
        for nm, lq in (('body', abs(f['c'] - f['o'])), ('full', f['h'] - f['l'])):
            L['eet_if_' + nm] = (ub + 2 * lq, lb - 2 * lq)
    return L


def status_line(day, ov=None):
    """'ACE    : ...' line for tg_status. ov = optvwap snapshots of the day (for the running high / low)."""
    snaps = [x for x in (ov or []) if not x.get('preopen') and str(x.get('timestamp', ''))[11:16] >= '09:15']
    hi = max((x['nifty']['day_high'] for x in snaps if x['nifty'].get('day_high')), default=None)
    lo = min((x['nifty']['day_low'] for x in snaps if x['nifty'].get('day_low')), default=None)
    spot = snaps[-1]['nifty']['ltp'] if snaps else None
    L = levels(day, hi, lo)
    if not L:
        return 'ACE    : first 5-min candle not captured yet (fetched after 09:20 by ace_levels.capture)'
    f = L['first5']
    s = 'ACE    : C%d | first5 O %.1f H %.1f L %.1f C %.1f | ref close %s' % (L['concept'], f['o'], f['h'], f['l'], f['c'], '%.2f' % L['ref_close'] if L['ref_close'] else 'n/a')

    def fm(k):
        v = L.get(k)
        return '%.1f' % v if v is not None else 'n/a'
    if 'up_et' in L or L['concept'] == 2:
        s += ' || UP 50%% %s 75%% %s ET %s | DN 50%% %s 75%% %s ET %s' % (fm('up_50'), fm('up_75'), fm('up_et'), fm('dn_50'), fm('dn_75'), fm('dn_et'))
    if L.get('liq'):
        s += ' || EET (%s %.1f) UP %s [50%% %s 75%% %s] DN %s [50%% %s 75%% %s]' % (
            L['liq_src'], L['liq'], fm('up_eet'), fm('up_eet50'), fm('up_eet75'), fm('dn_eet'), fm('dn_eet50'), fm('dn_eet75'))
    else:
        b, fu = L['eet_if_body'], L['eet_if_full']
        s += ' || EET liquidity not set (if body: UP %.0f / DN %.0f; if full: UP %.0f / DN %.0f)' % (b[0], b[1], fu[0], fu[1])
    if spot is not None:
        s += ' | spot %.0f' % spot
    return s
