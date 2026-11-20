#!/usr/bin/env python3
"""Empirical RRG validation on VN data (no theory worship).

Grid: formula {zscore, jdk} x window {10, 14} x benchmark {vnindex, eqw}
      x strategy {pure_rrg, rrg+wyckoff-proxy}
Point-in-time throughout. Weekly rebalance, next-session-open execution,
0.25% one-way cost, liquidity filter >=1 ty/day (trailing, point-in-time).
"""
import json
import numpy as np
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bt_common import load_all, rrg_zscore, rrg_jdk, VNX_FP, BASE

COST = 0.0025
MAX_POS = 10
MAX_HOLD_W = 8
WARM_SESSIONS = 110  # ~22 weeks: covers w14 + SMA50 + momentum delta

# ---------------- data matrices ----------------
data = load_all()
vnx_bars = json.loads(VNX_FP.read_text())
dates = [b['date'] for b in vnx_bars]
n_s = len(dates)
d2i = {d: i for i, d in enumerate(dates)}
tickers = sorted(data.keys())
n_t = len(tickers)
t2i = {t: i for i, t in enumerate(tickers)}

C = np.full((n_t, n_s), np.nan)
O = np.full((n_t, n_s), np.nan)
VAL = np.full((n_t, n_s), np.nan)
# QUY ƯỚC KHỐI LƯỢNG (chốt 01/10/2026): b['v'] của Simplize chỉ là KHỚP LỆNH,
# chưa gồm THỎA THUẬN. Mọi tín hiệu liên quan khối lượng (vol_ratio, unusual,
# breakout, GTGD, LIQ) đều dùng nguồn này và PHẢI giữ nguyên như vậy —
# không cộng thỏa thuận vào vì nó là giao dịch dàn xếp, không phản ánh
# cung-cầu thật trên sổ lệnh (VD: phiên 01/10/2026 MSR thỏa thuận ~3.240 tỷ
# của khối ngoại làm tổng GTGD báo chí ~19,6 nghìn tỷ trong khi khớp lệnh
# chỉ ~12,3 nghìn tỷ).
for ti, t in enumerate(tickers):
    for b in data[t]:
        i = d2i.get(b['date'])
        if i is not None:
            C[ti, i] = b['c']
            O[ti, i] = b['o']
            VAL[ti, i] = b['v'] * b['c']
vnx_c = np.array([b['c'] for b in vnx_bars], dtype=float)

# LIQ rule (point-in-time). 'value1e9': trailing-20d avg value >= 1e9 VND (legacy).
# 'screener': price 2k-500k VND and MA20 volume 50k-200M shares (user 2026-10-01).
LIQ_RULE = os.environ.get('LIQ_RULE', 'screener')
LIQ = np.zeros((n_t, n_s), dtype=bool)
if LIQ_RULE == 'screener':
    with np.errstate(all='ignore'):
        VOL = VAL / C  # shares per session
    for s in range(19, n_s):
        volma20 = np.nanmean(VOL[:, s - 19:s + 1], axis=1)
        px = C[:, s]
        LIQ[:, s] = (px >= 2000) & (px <= 500000) \
            & (volma20 >= 50000) & (volma20 <= 200000000)
else:
    for s in range(19, n_s):
        w = VAL[:, s - 19:s + 1]
        LIQ[:, s] = np.nanmean(w, axis=1) >= 1e9

# point-in-time equal-weight benchmark: daily mean return of liquid tickers
RET = np.full((n_t, n_s), np.nan)
RET[:, 1:] = C[:, 1:] / C[:, :-1] - 1
eqw_r = np.zeros(n_s)
for s in range(1, n_s):
    m = LIQ[:, s]
    if m.sum() > 0:
        eqw_r[s] = np.nanmean(RET[m, s])
eqw_c = 100 * np.cumprod(1 + np.nan_to_num(eqw_r))

# ---------------- weekly sampling ----------------
week_ends = list(range(n_s - 1, WARM_SESSIONS - 1, -5))[::-1]
n_w = len(week_ends)
WC = C[:, week_ends]          # ticker weekly closes
WO = O[:, week_ends]
WV = VAL[:, week_ends]
WB_vnx = vnx_c[week_ends]
WB_eqw = eqw_c[week_ends]
print(f'sessions={n_s} weeks={n_w} tickers={n_t} '
      f'liquid_now={int(LIQ[:, -1].sum())}', flush=True)

RRG = {'zscore': rrg_zscore, 'jdk': rrg_jdk}


def sma(arr, n, end):
    w = arr[end - n + 1:end + 1]
    return np.nanmean(w) if np.isfinite(w).all() else np.nan


def wyckoff_proxy(ti, s):
    """Crude Phase-D/markup proxy at session s (point-in-time):
    close > SMA50 and (volume > 1.5x 20d avg or 20d closing high)."""
    c = C[ti, s]
    if not np.isfinite(c) or s < 50:
        return False
    s50 = sma(C[ti], 50, s)
    if not np.isfinite(s50) or c <= s50:
        return False
    v = VAL[ti, s] / (c or 1)
    v20 = np.nanmean(VAL[ti, s - 19:s + 1] / C[ti, s - 19:s + 1])
    vol_boom = np.isfinite(v) and np.isfinite(v20) and v > 1.5 * v20
    hi20 = np.isfinite(C[ti, s - 19:s + 1]).all() and \
        c >= np.nanmax(C[ti, s - 19:s + 1])
    return bool(vol_boom or hi20)


def precompute_signals(formula, w, bench_name):
    """RRG per ticker per week + entry/exit signal flags. Strategy-independent."""
    rrg = RRG[formula]
    WB = WB_vnx if bench_name == 'vnindex' else WB_eqw
    R = np.full((n_t, n_w), np.nan)
    Q = np.full((n_t, n_w), '', dtype=object)
    M = np.full((n_t, n_w), np.nan)
    for ti in range(n_t):
        sec = WC[ti]
        if np.isfinite(sec).sum() < w + 2:
            continue
        for j in range(w - 1, n_w):
            r = rrg(sec[j - w + 1:j + 1], WB[j - w + 1:j + 1], w)
            if r:
                R[ti, j], M[ti, j], Q[ti, j] = r
    # entry signal at week j; exit flag at week j
    ENTRY = np.zeros((n_t, n_w), dtype=bool)
    EXITQ = np.zeros((n_t, n_w), dtype=bool)
    for j in range(w, n_w):
        q, q0 = Q[:, j], Q[:, j - 1]
        mom_up = M[:, j] > M[:, j - 1]
        valid = (q != '') & (q0 != '')
        sig = ((q == 'Improving') & mom_up) | \
              (((q0 == 'Lagging') | (q0 == 'Improving')) & (q == 'Leading'))
        ENTRY[:, j] = valid & sig
        EXITQ[:, j] = (q == 'Weakening') | (q == 'Lagging')
    return {'R': R, 'M': M, 'Q': Q, 'ENTRY': ENTRY, 'EXITQ': EXITQ}


def run_variant(sig, w, strategy):
    ENTRY, EXITQ, R = sig['ENTRY'], sig['EXITQ'], sig['R']
    cash = 100.0
    pos = {}
    equity = []
    trades = []
    port_val = 100.0

    for j in range(w, n_w - 1):
        s = week_ends[j]
        exits = [ti for ti, p in pos.items()
                 if EXITQ[ti, j] or (j - p['entry_w']) >= MAX_HOLD_W]
        for ti in exits:
            px = O[ti, s + 1]
            if not np.isfinite(px):
                continue
            p = pos.pop(ti)
            cash += p['shares'] * px * (1 - COST)
            trades.append(px * (1 - COST) / (p['entry_px'] * (1 + COST)) - 1)

        liq_now = LIQ[:, s]
        cands = [(R[ti, j], ti) for ti in range(n_t)
                 if ti not in pos and liq_now[ti] and ENTRY[ti, j] and
                 (strategy == 'pure' or wyckoff_proxy(ti, s))]
        cands.sort(reverse=True)
        room = MAX_POS - len(pos)
        port_val = cash + sum(p['shares'] * C[ti, s] for ti, p in pos.items()
                              if np.isfinite(C[ti, s]))
        for _, ti in cands[:room]:
            px = O[ti, s + 1]
            if not np.isfinite(px) or px <= 0:
                continue
            size = min(cash, 0.10 * port_val) * (1 - COST)
            if size <= 0:
                break
            shares = size / px
            cash -= size
            pos[ti] = {'shares': shares, 'entry_w': j, 'entry_px': px}
        port_val = cash + sum(p['shares'] * C[ti, s] for ti, p in pos.items()
                              if np.isfinite(C[ti, s]))
        equity.append(port_val)

    s = week_ends[-1]
    for ti, p in pos.items():
        px = C[ti, s]
        if np.isfinite(px):
            cash += p['shares'] * px * (1 - COST)
    return {'equity': np.array(equity), 'trades': np.array(trades)}


def metrics(eq, trades):
    if len(eq) < 5:
        return None
    tot = eq[-1] / eq[0] - 1
    yrs = len(eq) / 50
    cagr = (1 + tot) ** (1 / yrs) - 1 if tot > -1 else -1
    wr = eq[1:] / eq[:-1] - 1
    sharpe = (wr.mean() / (wr.std() or 1)) * np.sqrt(50)
    dd = float(((eq / np.maximum.accumulate(eq)) - 1).min())
    wins = (trades > 0).mean() if len(trades) else np.nan
    return {'ret': tot, 'cagr': cagr, 'sharpe': sharpe, 'maxdd': dd,
            'win': wins, 'ntrades': len(trades),
            'avg_trade': float(trades.mean()) if len(trades) else np.nan}


# ---------------- run grid ----------------
if __name__ == '__main__':
    results = {}
    sig_cache = {}
    for formula in ('zscore', 'jdk'):
        for w in (10, 14):
            for bench in ('vnindex', 'eqw'):
                key = f'{formula}/w{w}/{bench}'
                sig_cache[key] = precompute_signals(formula, w, bench)
                print(f'signals done: {key}', flush=True)
    for formula in ('zscore', 'jdk'):
        for w in (10, 14):
            for bench in ('vnindex', 'eqw'):
                sig = sig_cache[f'{formula}/w{w}/{bench}']
                for strat in ('pure', 'wyckoff'):
                    key = f'{formula}/w{w}/{bench}/{strat}'
                    r = run_variant(sig, w, strat)
                    m = metrics(r['equity'], r['trades'])
                    results[key] = m
                    print(f'{key:28s} ret={m["ret"]:+.1%} cagr={m["cagr"]:+.1%} '
                          f'sharpe={m["sharpe"]:+.2f} dd={m["maxdd"]:.1%} '
                          f'win={m["win"]:.0%} n={m["ntrades"]}', flush=True)

    # benchmark: VNINDEX buy & hold over the same span
    s0, s1 = week_ends[14] + 1, n_s - 1
    bh = vnx_c[s1] / vnx_c[s0] * (1 - COST) / (1 + COST) - 1
    print(f'\nVNINDEX buy&hold (same span): {bh:+.1%}')

    import json as _j
    _out = {k: {kk: (round(float(v), 4) if isinstance(v, float) else int(v))
                for kk, v in m.items()} for k, m in results.items()}
    try:
        Path('backtest-rrg.json').write_text(_j.dumps(_out, indent=1))
        print('saved backtest-rrg.json')
    except Exception as e:
        print('could not save backtest-rrg.json:', e)
