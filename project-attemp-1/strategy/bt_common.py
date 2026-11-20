#!/usr/bin/env python3
"""Shared helpers for VN-market empirical work: universe, liquidity,
weekly resampling, benchmarks, RRG formulas (z-score + JdK)."""
import json
import os
import numpy as np
from pathlib import Path
from datetime import datetime, timezone

import os
# Store layout (no data committed to this repo): SMA_MARKET_DIR points at a
# directory with bars/*.json, vnindex.json, sector_map.json, exchange_map.json
# (Simplize OHLCV store). Defaults to ./data.
MARKET_DIR = Path(os.environ.get("SMA_MARKET_DIR", "data"))
BASE = MARKET_DIR
STORE = BASE / 'bars'
VNX_FP = BASE / 'vnindex.json'


def load_bars(t):
    fp = STORE / f'{t}.json'
    if not fp.exists():
        return None
    return json.loads(fp.read_text())


def load_all():
    data = {}
    for fp in STORE.glob('*.json'):
        bars = json.loads(fp.read_text())
        if bars:
            data[fp.stem] = bars
    return data


def closes_of(bars):
    return np.array([b['c'] for b in bars], dtype=float)


def opens_of(bars):
    return np.array([b['o'] for b in bars], dtype=float)


def values_of(bars):
    return np.array([b['v'] * b['c'] for b in bars], dtype=float)


def weekly(closes):
    """Sample every 5th session from the end (Friday-ish close)."""
    c = list(closes)
    w = [c[i] for i in range(len(c) - 1, -1, -5)]
    return np.array(w[::-1], dtype=float)


def ema(x, n):
    x = np.asarray(x, dtype=float)
    a = 2.0 / (n + 1)
    e = np.empty_like(x)
    e[0] = x[0]
    for i in range(1, len(x)):
        e[i] = a * x[i] + (1 - a) * e[i - 1]
    return e


def rrg_zscore(sec, bench, w):
    """Current pipeline formula. Returns (ratio, momentum, quadrant)."""
    c = np.asarray(sec[-w:], dtype=float)
    b = np.asarray(bench[-w:], dtype=float)
    n = min(len(c), len(b))
    if n < w:
        return None
    c, b = c[-n:], b[-n:]
    rs = 100 * (c / c[0]) / (b / b[0])
    rs_roc = rs[1:] / rs[:-1]

    def zs(x):
        s = x.std()
        return (x - x.mean()) / (s or 1)
    rr = float(100 + zs(rs)[-1])
    mm = float(100 + zs(rs_roc)[-1])
    quad = ('Leading' if rr >= 100 and mm >= 100 else
            'Weakening' if rr >= 100 else
            'Lagging' if mm < 100 else 'Improving')
    return rr, mm, quad


def rrg_jdk(sec, bench, n):
    """Canonical JdK two-stage EMA percentage-deviation."""
    c = np.asarray(sec[-n:], dtype=float)
    b = np.asarray(bench[-n:], dtype=float)
    m = min(len(c), len(b))
    if m < n:
        return None
    c, b = c[-m:], b[-m:]
    rs = 100 * c / b
    ratio = 100 * rs / ema(rs, n)
    mom = 100 * ratio / ema(ratio, n)
    rr, mm = float(ratio[-1]), float(mom[-1])
    quad = ('Leading' if rr >= 100 and mm >= 100 else
            'Weakening' if rr >= 100 else
            'Lagging' if mm < 100 else 'Improving')
    return rr, mm, quad


def avg_value_20d(bars):
    """Trailing 20-session average trading value series (VND)."""
    v = values_of(bars)
    out = np.full_like(v, np.nan)
    for i in range(19, len(v)):
        out[i] = v[i - 19:i + 1].mean()
    return out


def liquid_at(data, idx, min_value=1e9):
    """Tickers liquid enough at session index idx (trailing 20d avg value)."""
    out = []
    for t, bars in data.items():
        if idx < len(bars):
            v = values_of(bars)
            if idx >= 19 and v[idx - 19:idx + 1].mean() >= min_value:
                out.append(t)
    return out


def build_indices(data, tickers, idx0=0, idx1=None):
    """Equal-weight index (mean of daily returns) + median-ticker index,
    over tickers with data. Returns dict of rebased (100) arrays aligned
    to the longest common session range."""
    rets = []
    for t in tickers:
        c = closes_of(data[t])
        r = c[1:] / c[:-1] - 1
        rets.append(r)
    rets = np.array(rets)  # (n_tickers, n_sessions-1)
    mean_r = np.nanmean(rets, axis=0)
    med_r = np.nanmedian(rets, axis=0)
    eqw = 100 * np.cumprod(1 + np.nan_to_num(mean_r))
    med = 100 * np.cumprod(1 + np.nan_to_num(med_r))
    return {'eqw': eqw, 'median': med}
