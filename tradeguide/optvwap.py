"""
tg-opt-vwap: option VWAP breadth for Nifty (5 CE + 5 PE: 2 ITM, ATM, 2 OTM each side).

Rules (decided 4 Oct 2026):
- Reference = exchange VWAP of each option (Upstox full quote 'average_price', from 09:15).
- Moving ATM: every run ATM is re-picked from the options' forward price; each strike is compared
  with ITS OWN VWAP. A wider band of strikes (ATM +/- track_each_side) is stored every run so that
  strikes are ready when ATM shifts.
- CALL ok when 5/5 CE are above their VWAP; PUT ok when 5/5 PE are above their VWAP.
- Anchored VWAP is re-set at every new Nifty day low / day high. Anchored VWAP from snapshot a to now:
  (VWAP_now*Vol_now - VWAP_a*Vol_a) / (Vol_now - Vol_a).
- Reversal confirmed when the anchored score (CE above - PE above) holds >= min_score for hold_bars
  runs (default 4 x 5 min) against the day trend, with ATM volume above its 10-bar average.

Pure functions only (no Flask / Upstox imports) so the logic can be tested offline.
"""

DEFAULT_CFG = {'strike_step': 50, 'track_each_side': 6, 'use_each_side': 2,
               'hold_bars': 4, 'min_score': 4, 'vol_avg_bars': 10}


def pick_atm(chain, spot, step):
    """chain: {strike: {'ce_ltp','pe_ltp',...}}. ATM from synthetic forward (K + C - P) at the strike nearest spot."""
    strikes = sorted(k for k in chain if k % step == 0)
    if not strikes or spot is None:
        return None, None
    k0 = min(strikes, key=lambda k: abs(k - spot))
    c, p = chain[k0].get('ce_ltp'), chain[k0].get('pe_ltp')
    fwd = k0 + c - p if (c and p) else spot
    return int(round(fwd / step) * step), round(fwd, 2)


def anchored_vwap(cur, ref):
    """cur/ref: [ltp, vwap, cum_volume]. Returns VWAP of trades after the anchor, or None."""
    if not cur or not ref:
        return None
    _, vw1, v1 = cur
    _, vw0, v0 = ref
    if None in (vw1, v1, vw0, v0) or v1 <= v0:
        return None
    return round((vw1 * v1 - vw0 * v0) / (v1 - v0), 2)


def build_snapshot(chain, spot, quotes, nifty_q, todays, cfg, ts, hhmm):
    """
    chain   : {strike(int): {'ce_key','pe_key','ce_ltp','pe_ltp'}}
    spot    : Nifty spot from the chain
    quotes  : {instrument_key: {'ltp','vwap','volume'}} for option keys
    nifty_q : {'ltp','high','low','open'} for Nifty 50 (day OHLC)
    todays  : list of today's earlier snapshots (oldest first)
    Returns the snapshot dict to append to json_output/optvwap.json.
    """
    c = dict(DEFAULT_CFG)
    c.update(cfg or {})
    step, trk, use = int(c['strike_step']), int(c['track_each_side']), int(c['use_each_side'])
    hold, minsc, vavg = int(c['hold_bars']), int(c['min_score']), int(c['vol_avg_bars'])
    nuse = 2 * use + 1

    atm, fwd = pick_atm(chain, spot, step)
    if atm is None:
        return None
    track = [atm + i * step for i in range(-trk, trk + 1) if (atm + i * step) in chain]

    # cumulative data for every tracked strike: key '22300CE' -> [ltp, vwap, cum_volume]
    cum = {}
    for k in track:
        for side in ('CE', 'PE'):
            qq = quotes.get(chain[k][side.lower() + '_key'])
            if qq and qq.get('ltp') is not None:
                vw = qq.get('vwap') or None
                cum[f'{k}{side}'] = [qq['ltp'], vw, qq.get('volume')]

    prev = todays[-1] if todays else None
    dlo, dhi = nifty_q.get('low'), nifty_q.get('high')
    plo = prev['nifty'].get('day_low') if prev else None
    phi = prev['nifty'].get('day_high') if prev else None
    new_low = prev is not None and dlo is not None and plo is not None and dlo < plo
    new_high = prev is not None and dhi is not None and phi is not None and dhi > phi
    if prev is None or new_low or new_high:
        anchor = {'dir': 1 if new_low else (-1 if new_high else 0),
                  'time': hhmm,
                  'ref': {k: v for k, v in cum.items()}}
    else:
        anchor = prev['anchor']

    # per-5-min volume of a key from consecutive snapshots
    def vol_hist(key):
        seq = [s.get('cum', {}).get(key) for s in todays] + [cum.get(key)]
        out = []
        for a, b in zip(seq[:-1], seq[1:]):
            if a and b and a[2] is not None and b[2] is not None and b[2] >= a[2]:
                out.append(b[2] - a[2])
        return out

    rows = []
    ce_day = pe_day = ce_anc = pe_anc = 0
    use_strikes = [atm + i * step for i in range(-use, use + 1)]
    for i, k in enumerate(use_strikes):
        off = i - use                                  # -2..+2 (strike below/above ATM)
        ce_role = 'ATM' if off == 0 else (f'ITM{-off}' if off < 0 else f'OTM{off}')
        pe_role = 'ATM' if off == 0 else (f'OTM{-off}' if off < 0 else f'ITM{off}')
        row = {'strike': k}
        for side, role in (('CE', ce_role), ('PE', pe_role)):
            key = f'{k}{side}'
            cur = cum.get(key)
            if not cur:
                row[side] = {'role': role, 'ltp': None}
                continue
            ltp, vw, _ = cur
            av = anchored_vwap(cur, anchor['ref'].get(key))
            above = vw is not None and ltp > vw
            aabove = av is not None and ltp > av
            vh = vol_hist(key)
            row[side] = {'role': role, 'ltp': ltp, 'vwap': vw, 'above_vwap': above,
                         'anc_vwap': av, 'above_anc': aabove,
                         'vol5': vh[-1] if vh else None,
                         'vol5_avg': round(sum(vh[-vavg - 1:-1]) / len(vh[-vavg - 1:-1])) if len(vh) > 1 else None}
            if side == 'CE':
                ce_day += above
                ce_anc += aabove
            else:
                pe_day += above
                pe_anc += aabove
        rows.append(row)

    day_score = ce_day - pe_day
    anc_score = ce_anc - pe_anc
    hist = [s['scores']['anc_score'] for s in todays[-(hold - 1):]
            if s.get('anchor', {}).get('time') == anchor['time']] if hold > 1 else []
    hist = hist + [anc_score]
    held_up = len(hist) == hold and all(x >= minsc for x in hist)
    held_dn = len(hist) == hold and all(x <= -minsc for x in hist)

    atm_row = rows[use]
    def vol_ok(side):
        d = atm_row.get(side, {})
        return d.get('vol5') is not None and d.get('vol5_avg') is not None and d['vol5'] > d['vol5_avg']

    tot = ce_day + pe_day
    if day_score < 3 and anchor['dir'] == 1 and held_up and vol_ok('CE'):
        verdict = 'REVERSAL UP - confirmed'
    elif day_score > -3 and anchor['dir'] == -1 and held_dn and vol_ok('PE'):
        verdict = 'REVERSAL DOWN - confirmed'
    elif day_score <= -3 and anchor['dir'] == 1 and anc_score > 0:
        verdict = 'Bounce - NOT confirmed'
    elif day_score >= 3 and anchor['dir'] == -1 and anc_score < 0:
        verdict = 'Pullback - NOT confirmed'
    elif day_score <= -3:
        verdict = 'Downtrend continues'
    elif day_score >= 3:
        verdict = 'Uptrend continues'
    elif tot <= 2:
        verdict = 'Both sides below VWAP - premium decay (seller zone)'
    elif tot >= 2 * nuse - 2:
        verdict = 'Both sides above VWAP - premium expansion'
    else:
        verdict = 'Mixed / sideways'

    return {
        'timestamp': ts,
        'nifty': {'ltp': nifty_q.get('ltp'), 'spot_chain': spot, 'fwd': fwd, 'atm': atm,
                  'day_high': dhi, 'day_low': dlo},
        'anchor': anchor,
        'scores': {'ce_day': ce_day, 'pe_day': pe_day, 'day_score': day_score,
                   'ce_anc': ce_anc, 'pe_anc': pe_anc, 'anc_score': anc_score,
                   'anc_hold': len(hist), 'held_up': held_up, 'held_down': held_dn},
        'signal': {'call_ok': ce_day == nuse, 'put_ok': pe_day == nuse, 'verdict': verdict},
        'strikes': rows,
        'cum': cum,
    }
