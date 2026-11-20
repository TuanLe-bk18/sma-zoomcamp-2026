#!/usr/bin/env python3
"""Backtest STRATEGY v1.2 trên TUẦN LỊCH (Friday close).

Tín hiệu tuần lấy từ signals.build() — cùng nguồn duy nhất với paper-trade
engine (calendar weeks), thay cách chia khối 5 phiên của strategy_v11.py.

Modes:
  baseline : rule v1.1 nguyên vẹn (cửa bear w2, không stop) — phải tái lập
             số STRATEGY.md §10 (w2: +149.7%, DD -44.6%, 2026 -8.6%).
  stop     : v1.2 — thêm stop-loss tường minh:
             - chân bear: đóng cửa tuần (T6) thủng đáy spring
               (= đáy 26 tuần MN26 tại tuần vào lệnh)
             - chân bull: đóng cửa tuần (T6) dưới SMA50 ngày
               HOẶC lỗ -8% từ giá vào (điều kiện nào tới trước)
             Quyết định trên giá đóng cửa T6 (thứ 7), khớp lệnh phiên thứ 2
             kế tiếp (gặp sàn dời tối đa 2 phiên như các lệnh bán khác).
"""
import numpy as np
import os, sys, json
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import signals as SG
import backtest_rrg as B
from backtest_rrg import C, tickers, n_t, n_s

t0 = datetime.now()
MODE = sys.argv[1] if len(sys.argv) > 1 else 'stop'
assert MODE in ('baseline', 'stop', 'stopbull'), 'mode: baseline | stop | stopbull'
USE_STOP = (MODE in ('stop', 'stopbull'))
STOP_BULL_ONLY = (MODE == 'stopbull')

S = SG.build()
we = S['week_ends']
n_w = S['n_w']
dates_w = S['dates_w']
bullw, B200w, W2w = S['bullw'], S['B200w'], S['W2w']
LEAD, Rw, LIQw = S['LEAD'], S['Rw'], S['LIQw']
topsec, RSIw, SPRING = S['topsec'], S['RSIw'], S['SPRING']
stk_sec = S['stk_sec']
WC = B.WC  # calendar weekly closes (signals.build đã override)

# stop inputs
S50d = SG.sma_mat(C, 50)          # SMA50 ngày
MN26 = SG.roll(WC, 26, np.nanmin)  # đáy 26 tuần (weekly)

FEE, TAX = 0.0025, 0.001
J0 = 60
positions, cash, trades, eq_curve = [], 1.0, [], []


def pval(j):
    v = cash
    px = C[:, we[j]]
    for p in positions:
        if np.isfinite(px[p['ti']]):
            v += p['sh'] * px[p['ti']]
    return v


def exit_at(p, j, why):
    """Bán phiên thứ 2 sau quyết định; gặp sàn chờ tối đa 2 phiên."""
    global cash
    ti = p['ti']
    x = we[j] + 1
    delay = 0
    while delay < 2 and x + 1 < n_s and np.isfinite(C[ti, x]) \
            and np.isfinite(C[ti, x - 1]) \
            and C[ti, x] / C[ti, x - 1] - 1 < -S['band'][ti]:
        x += 1
        delay += 1
    px = C[ti, x]
    if not np.isfinite(px):
        return
    cash += p['sh'] * px * (1 - FEE - TAX)
    ret = px / p['px'] * (1 - FEE - TAX) / (1 + FEE) - 1
    trades.append({'t': tickers[ti], 'in': dates_w[p['ej']],
                   'out': datetime.fromtimestamp(
                       B.dates[x], timezone.utc).strftime('%Y-%m-%d'),
                   'ret': round(float(ret) * 100, 2),
                   'regime': p['regime'], 'why': why})
    positions.remove(p)


def stop_hit(p, j):
    """Trigger trên giá đóng cửa tuần (T6)."""
    ti = p['ti']
    if STOP_BULL_ONLY and p['regime'] == 'bear':
        return False
    f = we[j]  # phiên cuối tuần = thứ 6
    if p['regime'] == 'bull':
        c = C[ti, f]
        s50 = S50d[ti, f]
        if np.isfinite(c) and np.isfinite(s50) and c < s50:
            return True
        if np.isfinite(c) and c / p['px'] - 1 <= -0.08:
            return True
        return False
    sl = p.get('sl')
    if sl is None or not np.isfinite(sl):
        return False
    wc = WC[ti, j]
    return bool(np.isfinite(wc) and wc < sl)


for j in range(J0, n_w):
    e = we[j] + 1
    if e >= n_s:
        break
    bull = bool(bullw[j])
    fuse = bool(np.isfinite(B200w[j]) and B200w[j] < 30)
    # ---- exits ----
    for p in positions[:]:
        ti = p['ti']
        held = j - p['ej']
        maxh = 12 if p['regime'] == 'bull' else 8
        flip = bull != (p['regime'] == 'bull')
        fuse_hit = p['regime'] == 'bull' and fuse
        if USE_STOP and stop_hit(p, j):
            exit_at(p, j, 'stop')
            continue
        if flip or fuse_hit or held >= maxh:
            exit_at(p, j, 'flip' if flip else
                    ('fuse' if fuse_hit else 'expiry'))
    # ---- entries ----
    held_ti = set(p['ti'] for p in positions)
    sec_cnt = {}
    for p in positions:
        sec_cnt[p['sec']] = sec_cnt.get(p['sec'], 0) + 1
    cands = []
    if bull and not fuse:
        idx = [i for i in np.where(LEAD[:, j] & topsec[:, j] & LIQw[:, j])[0]
               if i not in held_ti and np.isfinite(C[i, e])
               and np.isfinite(C[i, e - 1])]
        idx.sort(key=lambda i: -Rw[i, j])
        cands = [('bull', i) for i in idx]
    elif not bull and bool(W2w[j]):
        idx_s = [i for i in np.where(SPRING[:, j] & LIQw[:, j])[0]
                 if i not in held_ti]
        idx_r = [i for i in np.where((RSIw[:, j] < 30) & LIQw[:, j]
                                     & ~SPRING[:, j])[0] if i not in held_ti]
        idx_r.sort(key=lambda i: RSIw[i, j])
        cands = [('bear', i) for i in idx_s + idx_r]
    V = pval(j)
    for regime, ti in cands:
        if len(positions) >= 10:
            break
        sec = stk_sec[ti]
        if sec_cnt.get(sec, 0) >= 3:
            continue
        if not (np.isfinite(C[ti, e]) and np.isfinite(C[ti, e - 1])):
            continue
        if C[ti, e] / C[ti, e - 1] - 1 > S['band'][ti]:
            continue  # trần: bỏ qua
        alloc = min(V / 10, cash)
        if alloc <= 0:
            break
        px = C[ti, e]
        sh = alloc * (1 - FEE) / px
        cash -= alloc
        sl = float(MN26[ti, j]) if np.isfinite(MN26[ti, j]) else None
        positions.append({'ti': ti, 'ej': j, 'px': px, 'sh': sh,
                          'regime': regime, 'sec': sec, 'sl': sl})
        sec_cnt[sec] = sec_cnt.get(sec, 0) + 1
    eq_curve.append((dates_w[j], pval(j)))

# ---------- report ----------
eq = np.array([v for _, v in eq_curve])
ds = [d for d, _ in eq_curve]
tot = eq[-1] / eq[0] - 1
pk = np.maximum.accumulate(eq)
mdd = ((eq - pk) / pk).min()
i0 = next(k for k, d in enumerate(ds) if d >= '2026-01-01')
ytd = eq[-1] / eq[i0] - 1
rs = np.array([t['ret'] for t in trades])
win = (rs > 0).mean() if len(rs) else 0

print(f'\n=== STRATEGY v1.2 mode={MODE} '
      f'(weeks {dates_w[J0]}..{dates_w[-1]}) ===')
print(f'total {tot:+.1%} | maxDD {mdd:.1%} | YTD26 {ytd:+.1%} | '
      f'n={len(trades)} win={win:.0%} avg={rs.mean():+.2f}%/lệnh')
for nm in ('bull', 'bear'):
    tt = [t for t in trades if t['regime'] == nm]
    if tt:
        r2 = np.array([t['ret'] for t in tt])
        why = {}
        for t in tt:
            why[t['why']] = why.get(t['why'], 0) + 1
        print(f'  {nm}: n={len(tt)} win={(r2 > 0).mean():.0%} '
              f'avg={r2.mean():+.2f}% exits={why}')
for per, lo, hi in (('train<=2021', 0, 2021), ('test>=2022', 2022, 9999)):
    tt = [t for t in trades if lo <= int(t['in'][:4]) <= hi]
    if tt:
        r2 = np.array([t['ret'] for t in tt])
        bb = [t for t in tt if t['regime'] == 'bear']
        r3 = np.array([t['ret'] for t in bb])
        bs = f' bear_avg={r3.mean():+.2f}%(n={len(bb)})' if len(bb) else ''
        print(f'  {per}: n={len(tt)} win={(r2 > 0).mean():.0%} '
              f'avg={r2.mean():+.2f}%{bs}')
print(f'runtime: {datetime.now()-t0}')

json.dump({'mode': MODE, 'trades': trades,
           'equity': [[d, float(v)] for d, v in eq_curve],
           'summary': {'total': round(float(tot) * 100, 1),
                       'mdd': round(float(mdd) * 100, 1),
                       'ytd26': round(float(ytd) * 100, 1),
                       'n': len(trades), 'win': round(float(win) * 100, 1),
                       'avg': round(float(rs.mean()), 2) if len(rs) else 0}},
          open(f'strategy-v12-{MODE}.json', 'w'))
print(f'saved strategy-v12-{MODE}.json')
