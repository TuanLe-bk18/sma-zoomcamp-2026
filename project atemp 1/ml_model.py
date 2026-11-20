#!/usr/bin/env python3
"""SMA Project — prototype ML (muc 4 rubric): DecisionTree / RandomForest
tren du lieu VN de du bao loi nhuan tuong lai.

Quy uoc theo 'bai toan nguoc' cua anh (giong sweep_conditions.py):
- Du lieu: Simplize OHLCV khoi luong khop lenh, store/bars/*.json
- Chu ky tuan (lay gia dong cuoi moi 5 phien, nhu bt_common.weekly)
- Target: tang/giam sau 8 tuan (close[t+8] > close[t])
- Chia theo thoi gian: train <= 2021, test >= 2022 (khong lookahead)
- Baseline: doan mu (majority class)
- Features chi dung thong tin den tuan t (point-in-time)

Chay: python ml_model.py  (can SMA_DATA_DIR tro toi store bars)
Ket qua in ra stdout + ghi files/sma-ml-prototype.md
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import os
# Data store: one JSON file per ticker with daily bars [{date(epoch s), o, h, l, c, v}].
# Course rules: data files are NOT committed to this repo. Point SMA_DATA_DIR at a
# local store built from Simplize OHLCV (see README, "Data"), or place files in data/bars/.
STORE = Path(os.environ.get("SMA_DATA_DIR", Path(__file__).resolve().parent / "data" / "bars"))

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.tree import DecisionTreeClassifier

OUT_DIR = Path(__file__).resolve().parent / "results"
OUT_DIR.mkdir(exist_ok=True)
TRAIN_END = "2021-12-31"


def weekly_bars(bars):
    """Lay gia dong + tong khoi luong moi 5 phien, tu cuoi ve dau."""
    n = len(bars)
    idx = list(range(n - 1, -1, -5))[::-1]
    dates, closes, vols = [], [], []
    for i in idx:
        lo = max(0, i - 4)
        dates.append(pd.to_datetime(bars[i]["date"], unit="s", utc=True).tz_convert("Asia/Ho_Chi_Minh"))
        closes.append(float(bars[i]["c"]))
        vols.append(sum(float(b["v"]) for b in bars[lo:i + 1]))
    return pd.DataFrame({"date": dates, "close": closes, "vol": vols})


def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0)
    dn = (-d).clip(lower=0)
    ru = up.ewm(alpha=1 / n, adjust=False).mean()
    rd = dn.ewm(alpha=1 / n, adjust=False).mean()
    rs = ru / rd.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def build_panel():
    rows = []
    kept, skipped = 0, 0
    for fp in sorted(STORE.glob("*.json")):
        bars = json.loads(fp.read_text())
        if len(bars) < 260 * 5:  # can it nhat ~5 nam du lieu ngay
            skipped += 1
            continue
        w = weekly_bars(bars)
        if len(w) < 260:
            skipped += 1
            continue
        # Loc thanh khoan kieu LIQ: gia cuoi 2k-500k, VOL TB ngay >= 50k cp
        med_vol_day = float(np.median([b["v"] for b in bars]))
        last_close = w["close"].iloc[-1]
        if not (2000 <= last_close <= 500000 and med_vol_day >= 50_000):
            skipped += 1
            continue
        c = w["close"]
        f = pd.DataFrame({"date": w["date"]})
        f["ret4"] = c.pct_change(4)
        f["ret12"] = c.pct_change(12)
        f["ret26"] = c.pct_change(26)
        f["ret52"] = c.pct_change(52)
        f["rsi14"] = rsi(c, 14)
        f["dist_sma20"] = c / c.rolling(20).mean() - 1
        f["dist_sma50"] = c / c.rolling(50).mean() - 1
        f["dist_52w_high"] = c / c.rolling(52).max() - 1
        f["vol_ratio"] = w["vol"] / w["vol"].rolling(20).mean()
        f["fwd8"] = c.shift(-8) / c - 1
        f["ticker"] = fp.stem
        f = f.dropna()
        rows.append(f)
        kept += 1
    print(f"Universe: {kept} ma giu lai, {skipped} ma loai (thieu du lieu / ngoai LIQ)")
    panel = pd.concat(rows, ignore_index=True)
    panel["y"] = (panel["fwd8"] > 0).astype(int)
    return panel


FEATS = ["ret4", "ret12", "ret26", "ret52", "rsi14",
         "dist_sma20", "dist_sma50", "dist_52w_high", "vol_ratio"]


def evaluate(name, model, Xtr, ytr, Xte, yte):
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    proba = model.predict_proba(Xte)[:, 1] if hasattr(model, "predict_proba") else pred
    acc = accuracy_score(yte, pred)
    auc = roc_auc_score(yte, proba)
    f1 = f1_score(yte, pred, zero_division=0)
    print(f"{name:28s} acc={acc:.3f}  AUC={auc:.3f}  F1={f1:.3f}")
    return {"model": name, "acc": round(float(acc), 4),
            "auc": round(float(auc), 4), "f1": round(float(f1), 4)}


def main():
    panel = build_panel()
    print(f"Panel: {len(panel):,} dong (ma-tuan), {panel['date'].min().date()} -> "
          f"{panel['date'].max().date()}")
    tr = panel[panel["date"] <= TRAIN_END]
    te = panel[panel["date"] > TRAIN_END]
    print(f"Train (<=2021): {len(tr):,} dong | Test (>=2022): {len(te):,} dong")
    print(f"Ti le tang 8 tuan — train: {tr['y'].mean():.3f} | test: {te['y'].mean():.3f}")
    Xtr, ytr = tr[FEATS], tr["y"]
    Xte, yte = te[FEATS], te["y"]

    results = []
    # Baseline: doan mu (luon doan tang — class da so)
    maj = int(ytr.mean() >= 0.5)
    base_pred = np.full(len(yte), maj)
    results.append({"model": "Majority (doan mu)", "acc": round(float((base_pred == yte).mean()), 4),
                    "auc": 0.5, "f1": round(float(f1_score(yte, base_pred, zero_division=0)), 4)})
    print(f"{'Majority (doan mu)':28s} acc={results[0]['acc']:.3f}  AUC=0.500  "
          f"F1={results[0]['f1']:.3f}")

    for depth in [3, 5, 10, None]:
        results.append(evaluate(f"DecisionTree depth={depth}",
                                DecisionTreeClassifier(max_depth=depth, random_state=0),
                                Xtr, ytr, Xte, yte))
    rf = RandomForestClassifier(n_estimators=200, min_samples_leaf=5,
                                n_jobs=-1, random_state=0)
    results.append(evaluate("RandomForest n=200", rf, Xtr, ytr, Xte, yte))
    imp = pd.Series(rf.feature_importances_, index=FEATS).sort_values(ascending=False)
    print("\nFeature importance (RandomForest):")
    for k, v in imp.items():
        print(f"  {k:14s} {v:.3f}")

    # Ghi bao cao
    lines = [
        "# SMA Project — prototype ML (muc 4 rubric)",
        "",
        "Chay thu ngay 2026-11-14 (venv Midterm, sklearn 1.9.1). "
        "Muc dich: lap khoang trong duy nhat cua SMA Project theo rubric — "
        "train model ML kieu bai giang tren du lieu VN de du bao loi nhuan tuong lai.",
        "",
        "## Thiet lap (khop quy uoc 'bai toan nguoc')",
        "- Du lieu: Simplize OHLCV khop lenh, kho `store/bars/`; chu ky tuan "
        "(gia dong cuoi moi 5 phien).",
        f"- Universe: {panel['ticker'].nunique()} ma (du lieu >= 5 nam, gia cuoi 2k-500k, "
        "VOL TB ngay >= 50k cp — gan rule LIQ screener).",
        f"- Panel: {len(panel):,} dong ma-tuan, {panel['date'].min().date()} -> "
        f"{panel['date'].max().date()}.",
        "- Features (chi dung thong tin den tuan t): ret4/12/26/52, RSI14 tuan, "
        "khoang cach den SMA20/SMA50, khoang cach den dinh 52 tuan, vol ratio vs TB20w.",
        "- Target: tang/giam sau 8 tuan (close[t+8] > close[t]).",
        "- Chia theo thoi gian: train <= 2021, test >= 2022. "
        f"Ti le tang 8 tuan: train {tr['y'].mean():.1%}, test {te['y'].mean():.1%}.",
        "",
        "## Ket qua test (>= 2022)",
        "",
        "| Model | Accuracy | AUC | F1 |",
        "|---|---:|---:|---:|",
    ]
    for r in results:
        lines.append(f"| {r['model']} | {r['acc']:.3f} | {r['auc']:.3f} | {r['f1']:.3f} |")
    lines += [
        "",
        "## Feature importance (RandomForest)",
        "",
    ]
    for k, v in imp.items():
        lines.append(f"- {k}: {v:.3f}")
    lines += [
        "",
        "## Doc ket qua (noi thang)",
        "- Day la prototype chua tune ky: dung de lap muc 4 rubric, chua phai tin hieu giao dich.",
        "- Neu accuracy/AUC chi ngang doan mu thi ket luan thang nhu vay trong bao cao — "
        "giong cach Kronos da bi bac bang so lieu, khong to hong.",
        "- Buoc tiep theo neu anh giu de tai v1.2: tune nhe (validation 2020-2021), "
        "them regime EQW/SMA40w lam feature, roi ghep du bao vao backtest v1.2 "
        "de do xem model co cai thien gi so voi rule-based khong.",
        "",
        "Script: `ml_model.py` (chay lai duoc, seed co dinh).",
    ]
    (OUT_DIR / "sma-ml-prototype.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nDa ghi:", OUT_DIR / "sma-ml-prototype.md")


if __name__ == "__main__":
    main()
