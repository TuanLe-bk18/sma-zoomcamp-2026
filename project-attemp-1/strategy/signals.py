#!/usr/bin/env python3
"""Weekly signals on CALENDAR weeks (Friday close), shared by backtests and
the paper-trade engine. Overrides backtest_rrg's 5-session week sampling."""
import numpy as np
import os
import sys
import json
from pathlib import Path
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest_rrg as B
from backtest_rrg import C, LIQ, n_t, n_s, tickers, t2i, precompute_signals, RRG
from sectors import SECTORS

_t0 = datetime.now()


def load_band(tickers):
    """Ngưỡng trần/sàn theo sàn niêm yết (fix audit M2 05/10/2026).
    HOSE ±7% → 0.069, HNX ±10% → 0.099, UPCoM ±15% → 0.149.
    Mã chưa rõ sàn → 0.069 (hành vi cũ, conservative)."""
    try:
        ex = json.load(open(Path(os.environ.get('SMA_MARKET_DIR', 'data')) / 'exchange_map.json'))
    except Exception:
        ex = {}
    b = {'HOSE': 0.069, 'HNX': 0.099, 'UPCoM': 0.149}
    return np.array([b.get(ex.get(t), 0.069) for t in tickers])


def calendar_weeks():
    """Group sessions by ISO calendar week; week_end = last session of week."""
    keys, order = {}, []
    for s in range(n_s):
        dt = datetime.fromtimestamp(B.dates[s], timezone.utc)
        k = (dt.isocalendar()[0], dt.isocalendar()[1])
        if k not in keys:
            keys[k] = []
            order.append(k)
        keys[k].append(s)
    we = [v[-1] for k, v in ((k, keys[k]) for k in order)]
    return we


def use_calendar_weeks():
    we = calendar_weeks()
    B.week_ends = we
    B.n_w = len(we)
    B.WC = C[:, we]
    B.WO = B.O[:, we]
    B.WV = B.VAL[:, we]
    B.WB_vnx = B.vnx_c[we]
    B.WB_eqw = B.eqw_c[we]
    return we


def sma_mat(X, n, min_frac=0.8):
    # FIX 05/10/2026 (audit M3): chịu được dữ liệu thiếu — chỉ cần >=80%
    # phiên finite trong window (trước đây đòi đủ 100%: 1 phiên gap/suspension
    # làm NaN cả chuỗi → âm thầm tắt stop-loss chân bull và loại mã khỏi breadth).
    f = np.isfinite(X).astype(float)
    Xf = np.where(np.isfinite(X), X, 0.0)
    cs = np.cumsum(Xf, axis=1)
    cc = np.cumsum(f, axis=1)
    cs0 = np.concatenate([np.zeros((n_t, n)), cs[:, :-n]], axis=1)
    cc0 = np.concatenate([np.zeros((n_t, n)), cc[:, :-n]], axis=1)
    cnt = cc - cc0
    need = max(1, int(np.ceil(n * min_frac)))
    return np.where(cnt >= need, (cs - cs0) / np.maximum(cnt, 1), np.nan)


def roll(X, n, fn):
    out = np.full_like(X, np.nan)
    for j in range(n - 1, X.shape[1]):
        out[:, j] = fn(X[:, j - n + 1:j + 1], axis=1)
    return out


def build():
    """Compute every weekly signal. Returns dict S."""
    we = use_calendar_weeks()
    n_w = B.n_w
    WC = B.WC
    S = {'week_ends': np.array(we), 'n_w': n_w}
    S['dates_w'] = [datetime.fromtimestamp(B.dates[s], timezone.utc)
                    .strftime('%Y-%m-%d') for s in we]

    # regime: EQW vs SMA40w
    eqw_w = B.eqw_c[we]
    bullw = np.zeros(n_w, dtype=bool)
    for j in range(39, n_w):
        bullw[j] = eqw_w[j] > np.mean(eqw_w[j - 39:j + 1])
    S['bullw'] = bullw

    # breadth
    S200 = sma_mat(C, 200)
    S50 = sma_mat(C, 50)
    S20 = sma_mat(C, 20)
    nliq = LIQ.sum(axis=0)
    with np.errstate(all='ignore'):
        a = (np.isfinite(S200) & (C > S200)).astype(float)
        a[~LIQ] = np.nan
        B200d = np.where(nliq >= 30, np.nanmean(a, axis=0) * 100, np.nan)
        a = (np.isfinite(S50) & (C > S50)).astype(float)
        a[~LIQ] = np.nan
        B50d = np.where(nliq >= 30, np.nanmean(a, axis=0) * 100, np.nan)
        a = (np.isfinite(S20) & (C > S20)).astype(float)
        a[~LIQ] = np.nan
        B20d = np.where(nliq >= 30, np.nanmean(a, axis=0) * 100, np.nan)
    try:
        np.save(os.path.join(os.environ.get('SMA_MARKET_DIR', 'data'),
                             'breadth.npy'),
                np.array([B50d, B200d]))
    except Exception as e:
        print('could not save breadth.npy:', e)
    S['B200w'] = B200d[we]
    S['B50w'] = B50d[we]
    S['B20w'] = B20d[we]

    # W2 PIT-đúng (fix lookahead 05/10/2026): điểm cắt tại s chỉ được
    # "xác nhận" tại s+10 (persist 10 phiên); cửa bear mở 20 phiên SAU
    # thời điểm xác nhận. Tại tuần j chỉ thấy các điểm cắt đã xác nhận
    # (s+10 <= we[j]) — khớp với những gì live thấy sáng thứ 7.
    dd = B50d - B200d
    dn_cross = np.zeros(n_s, dtype=bool)
    s = 11
    while s < n_s - 10:
        if np.isfinite(dd[s - 1]) and np.isfinite(dd[s]) \
                and dd[s - 1] >= 0 > dd[s]:
            if np.isfinite(dd[s + 1:s + 11]).all() \
                    and (dd[s + 1:s + 11] < 0).all():
                dn_cross[s] = True
                s += 10
                continue
        s += 1
    W2d = np.zeros(n_s, dtype=bool)
    for s in np.where(dn_cross)[0]:
        a, b = s + 10, min(s + 30, n_s)
        W2d[a:b] = True
    S['W2w'] = W2d[we]

    # RSI weekly (Wilder 14)
    d = np.diff(WC, axis=1)
    g = np.where(d > 0, d, 0.)
    l = np.where(d < 0, -d, 0.)
    ag = np.full((n_t, n_w), np.nan)
    al = np.full((n_t, n_w), np.nan)
    ag[:, 14] = np.nanmean(g[:, :14], axis=1)
    al[:, 14] = np.nanmean(l[:, :14], axis=1)
    for j in range(15, n_w):
        ag[:, j] = (ag[:, j - 1] * 13 + g[:, j - 1]) / 14
        al[:, j] = (al[:, j - 1] * 13 + l[:, j - 1]) / 14
    S['RSIw'] = 100 - 100 / (1 + ag / np.where(al == 0, np.nan, al))

    # spring: 26w low in last 3 weeks, reclaimed +3%
    MN26 = roll(WC, 26, np.nanmin)
    SPRING = np.zeros((n_t, n_w), dtype=bool)
    for j in range(26, n_w):
        seg = np.where(np.isfinite(WC[:, j - 25:j + 1]),
                       WC[:, j - 25:j + 1], np.inf)
        amin = np.argmin(seg, axis=1)
        SPRING[:, j] = (amin >= 23) & (WC[:, j] > MN26[:, j] * 1.03) \
            & np.isfinite(MN26[:, j])
    S['SPRING'] = SPRING

    # RRG stock-level (JdK w14 vs EQW)
    sig = precompute_signals('jdk', 14, 'eqw')
    S['LEAD'] = (sig['Q'] == 'Leading') & np.isfinite(sig['R'])
    S['Rw'] = sig['R']
    S['LIQw'] = LIQ[:, we]

    # sector RRG top-3
    # Aggregate ngành: trung bình lợi suất tuần của các mã THANH KHOẢN
    # tại ĐÚNG tuần đó (không peek tương lai — chốt 05/10/2026, vụ DRI).
    # Mã kém thanh khoản gây nhiễu cho đo momentum ngành nên loại khỏi
    # aggregate, nhưng vẫn được map ngành để đủ điều kiện chọn mã.
    WRET = WC[:, 1:] / WC[:, :-1] - 1  # n_t x (n_w-1)
    LIQw = S['LIQw']
    sec_rets, sec_names = [], []
    for sname, members in SECTORS.items():
        ms_all = list(dict.fromkeys(m.strip() for m in members
                                    if m.strip() in t2i))
        if len(ms_all) < 3:
            continue
        wret = np.full(n_w, np.nan)
        for j in range(1, n_w):
            ms = [m for m in ms_all if LIQw[t2i[m], j]]
            if len(ms) < 3:
                ms = ms_all  # fallback: tuần quá ít mã thanh khoản
            wret[j] = np.nanmean(WRET[[t2i[m] for m in ms], j - 1])
        sec_names.append(sname)
        sec_rets.append(wret)
    n_sec = len(sec_names)
    SEC_W = np.cumprod(1 + np.nan_to_num(np.array(sec_rets), nan=0.0),
                       axis=1)
    jdk = RRG['jdk']
    SR = np.full((n_sec, n_w), np.nan)
    SM = np.full((n_sec, n_w), np.nan)
    SQ = np.full((n_sec, n_w), '', dtype=object)
    for si in range(n_sec):
        sec = SEC_W[si]
        if np.isfinite(sec).sum() < 16:
            continue
        for j in range(13, n_w):
            r = jdk(sec[j - 13:j + 1], eqw_w[j - 13:j + 1], 14)
            if r:
                SR[si, j], SM[si, j], SQ[si, j] = r
    sec_of = {}
    for sname, members in SECTORS.items():
        for m in members:
            m = m.strip()
            if m in t2i and m not in sec_of:
                sec_of[m] = sname
    sidx = {s: i for i, s in enumerate(sec_names)}
    stk_sec = np.array([sidx.get(sec_of.get(t, ''), -1) for t in tickers])
    S['stk_sec'] = stk_sec
    S['sec_names'] = sec_names
    # CHỐT CHẶN 05/10/2026 (vụ DRI), cứng hoá sau audit cùng ngày:
    # mọi ticker phải thuộc đúng 1 ngành — unmapped là LỖI CHẾT, raise ngay.
    _unmapped = [t for t in tickers if t not in sec_of]
    if _unmapped:
        raise RuntimeError(
            f'{len(_unmapped)} tickers KHÔNG có ngành '
            f'(VD: {_unmapped[:10]}). Chạy build_sector_map.py để vá!')
    print(f'sector coverage: {len(sec_of)}/{len(tickers)} (100%)',
          flush=True)
    qp = {'Leading': 3, 'Improving': 2, 'Weakening': 1, 'Lagging': 0}
    topsec = np.zeros((n_t, n_w), dtype=bool)
    top3_sec = []  # ordered top-3 sector names per week (RRG rank)
    for j in range(n_w):
        out = []
        for si in range(n_sec):
            q = SQ[si, j]
            if q == '' or not np.isfinite(SR[si, j]):
                continue
            out.append((qp[q] * 1000 + np.hypot(SR[si, j] - 100,
                                               SM[si, j] - 100), si))
        rk = sorted(out, reverse=True)[:3]
        top3_sec.append([sec_names[si] for _, si in rk])
        rkset = set(si for _, si in rk)
        topsec[:, j] = np.array([s in rkset for s in stk_sec])
    S['topsec'] = topsec
    S['top3_sec'] = top3_sec
    # Mirror cho v1.2-INV (backtest falsification): mã Lagging + 3 ngành
    # RRG yếu nhất. Chỉ thêm key mới, không đổi logic hiện có.
    S['LAG'] = (sig['Q'] == 'Lagging') & np.isfinite(sig['R'])
    botsec = np.zeros((n_t, n_w), dtype=bool)
    for j in range(n_w):
        out = []
        for si in range(n_sec):
            q = SQ[si, j]
            if q == '' or not np.isfinite(SR[si, j]):
                continue
            out.append((qp[q] * 1000 + np.hypot(SR[si, j] - 100,
                                               SM[si, j] - 100), si))
        rk = sorted(out)[:3]  # ascending = 3 ngành yếu nhất
        rkset = set(si for _, si in rk)
        botsec[:, j] = np.array([s in rkset for s in stk_sec])
    S['botsec'] = botsec
    S['band'] = load_band(tickers)
    print(f'signals built: {n_w} cal weeks, '
          f'{datetime.now() - _t0}', flush=True)
    return S


if __name__ == '__main__':
    S = build()
    print('last weeks:', S['dates_w'][-3:])
    print('bull now:', bool(S['bullw'][-1]),
          'B200:', round(float(S['B200w'][-1]), 1),
          'W2:', bool(S['W2w'][-1]))
