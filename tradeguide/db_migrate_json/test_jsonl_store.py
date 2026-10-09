"""Offline test of jsonl_store v2 with fake Upstox-like rows. Uses a temp folder and a temp log only.
Run: python db_migrate_json/test_jsonl_store.py"""
import os, sys, tempfile, datetime, logging, time
from types import SimpleNamespace as N
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jsonl_store as S

tmp = tempfile.mkdtemp()
S.ROOT = tmp
for h in list(S.log.handlers):
    S.log.removeHandler(h)
tlog = os.path.join(tmp, 'opt_fut_entry_logger.log')
h = logging.FileHandler(tlog); h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s')); S.log.addHandler(h)
EXP = {'v': '2026-10-13'}
S.current_expiry = lambda ul='NIFTY': EXP['v']


def row(exp, k, c_oi, p_oi):
    md = lambda oi, ltp: N(oi=oi, prev_oi=oi - 1000, volume=5000, ltp=ltp)
    return N(expiry=exp, strike_price=float(k), underlying_spot_price=22514.3, pcr=1.11,
             call_options=N(market_data=md(c_oi, 120.5), option_greeks=N(iv=13.2)),
             put_options=N(market_data=md(p_oi, 98.25), option_greeks=N(iv=14.1)))


d1 = datetime.datetime(2026, 10, 9, 13, 46, 5)
near = [row('2026-10-13', k, 100000 + k, 200000 + k) for k in (22500, 22400, 22600)]
near.append(N(expiry='2026-10-13', strike_price=22700.0, underlying_spot_price=22514.3, pcr=1.11, call_options=None, put_options=None))
nxt = [row('2026-10-19', 22500, 1, 2)]
assert S.write_optionchain(near, now=d1) == 4            # app calls once per expiry
assert S.write_optionchain(nxt, now=d1) == 1
assert S.write_optionchain(near, now=d1 + datetime.timedelta(minutes=5)) == 4
p_cur = os.path.join(tmp, 'Current_Expiry', 'NIFTY', 'options_2026-10-13', '2026-10-09.jsonl')
p_nxt = os.path.join(tmp, 'Next_Expiry', 'NIFTY', 'options_2026-10-19', '2026-10-09.jsonl')
assert os.path.exists(p_cur) and os.path.exists(p_nxt)
with open(p_cur, 'a') as f:
    f.write('{"ts": "half-written')                     # crash mid-line
lines = S.read_optionchain('2026-10-13', '2026-10-09')
assert len(lines) == 2 and [r[0] for r in lines[0]['rows']] == [22400, 22500, 22600, 22700] and lines[0]['rows'][3][1] == 0

# roll: data.json moves to the next expiry after 13 Oct
EXP['v'] = '2026-10-19'
d2 = datetime.datetime(2026, 10, 14, 9, 21, 0)
S.write_optionchain([row('2026-10-19', 22500, 5, 6)], now=d2)
assert os.path.isdir(os.path.join(tmp, 'Archived_All', 'NIFTY', 'options_2026-10-13'))
assert os.path.exists(os.path.join(tmp, 'Current_Expiry', 'NIFTY', 'options_2026-10-19', '2026-10-09.jsonl'))   # moved up from Next
assert os.path.exists(os.path.join(tmp, 'Current_Expiry', 'NIFTY', 'options_2026-10-19', '2026-10-14.jsonl'))
g = S.getopt('2026-10-19')
assert len(g) == 2 and g[-1]['call_writer_oi'] == 5 and g[0]['expiry_date'] == datetime.date(2026, 10, 19)
g13 = S.getopt(datetime.date(2026, 10, 13))             # archived expiry still readable
assert len(g13) == 8 and g13[0]['strike_price'] == 22400 and g13[0]['call_iv'] == 13.2

# futures: one file per contract, appended; old contract moves to Archived_All
q = lambda sym, ltp: {'NSE_FO|NIFTY': N(symbol=sym, timestamp='2026-10-09T13:46:04+05:30', average_price=22560, last_price=ltp,
                                        oi=12345600, total_buy_quantity=150000, total_sell_quantity=90000, volume=800000)}
S.write_futures(q('NIFTY26OCTFUT', 22571.5), now=d1)
S.write_futures(q('NIFTY26OCTFUT', 22575.0), now=d1 + datetime.timedelta(minutes=5))
fo = os.path.join(tmp, 'Current_Expiry', 'NIFTY', 'futures', 'NIFTY26OCTFUT.jsonl')
assert sum(1 for _ in S.iter_lines(fo)) == 2
os.utime(fo, (time.time() - 40 * 86400,) * 2)          # pretend October contract last written long ago
S.write_futures(q('NIFTY26NOVFUT', 22650.0), now=datetime.datetime.now())
assert os.path.exists(os.path.join(tmp, 'Archived_All', 'NIFTY', 'futures', 'NIFTY26OCTFUT.jsonl'))
f = S.getfut()
assert len(f) == 1 and f[0].symbol == 'NIFTY26NOVFUT' and f[0].last_price == 22650.0

# retention
dry = S.retention(dry_run=True, today='2026-11-10')    # 13 Oct expiry is 28 days old (> 21)
assert any('options_2026-10-13' in p for p in dry) and os.path.isdir(os.path.join(tmp, 'Archived_All', 'NIFTY', 'options_2026-10-13'))
S.retention(today='2026-11-10')
assert not os.path.isdir(os.path.join(tmp, 'Archived_All', 'NIFTY', 'options_2026-10-13'))
assert os.path.exists(os.path.join(tmp, 'Archived_All', 'NIFTY', 'futures', 'NIFTY26OCTFUT.jsonl'))   # 40 days < 92: kept

logtxt = open(tlog).read()
assert 'OPT NIFTY 2026-10-13 strikes=4' in logtxt and 'ROLL NIFTY options_2026-10-13: Current_Expiry -> Archived_All' in logtxt
assert 'FUT NIFTY NIFTY26OCTFUT' in logtxt and 'RETENTION deleted' in logtxt
print('jsonl_store v2 tests: ALL PASS')
print('--- sample log lines ---'); print('\n'.join(logtxt.splitlines()[:4]))
