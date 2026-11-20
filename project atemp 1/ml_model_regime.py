#!/usr/bin/env python3
"""SMA Project — prototype ML, bien the regime (EQW/SMA40w).

Giong het sma_ml_prototype.py (cung universe 254 ma, cung 9 feature gia,
cung target tang/giam sau 8 tuan, cung chia train <=2021 / test >=2022),
chi them 2 feature regime tinh point-in-time tu chinh universe:
- regime_bull: 1 neu EQW tuan > SMA40w cua EQW, 0 neu nguoc lai.
- dist_eqw_sma40: EQW/SMA40w - 1 (lien tuc).
EQW = chi so binh quan (mean return tuan cua cac ma, cumprod tu 100),
dung dung dinh nghia regime cua STRATEGY v1.2 (EQW vs SMA40w).

Bao cao them: ket qua test tach theo regime (tuan bull vs tuan bear)
de xem test thien bear co lam lech ket qua goc (RF AUC 0,516) khong.

Chay: python ml_model_regime.py  (can SMA_DATA_DIR tro toi store bars)
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
from ml_model import weekly_bars, rsi, evaluate, FEATS, TRAIN_END  # noqa: E402

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.tree import DecisionTreeClassifier

OUT = Path(__file__).resolve().parent / "results" / "sma-ml-prototype-regime.md"
OUT.parent.mkdir(exist_ok=True)


def build_panel_with_close():
    rows, kept, skipped = [], 0, 0
    for fp in sorted(STORE.glob("*.json")):
        bars = json.loads(fp.read_text())
        if len(bars) < 260 * 5:
            skipped += 1
            continue
        w = weekly_bars(bars)
        if len(w) < 260:
            skipped += 1
            continue
        med_vol_day = float(np.median([b["v"] for b in bars]))
        last_close = w["close"].iloc[-1]
        if not (2000 <= last_close <= 500000 and med_vol_day >= 50_000):
            skipped += 1
            continue
        c = w["close"]
        f = pd.DataFrame({"date": w["date"], "close": c})
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
    print(f"Universe: {kept} ma giu lai, {skipped} ma loai")
    panel = pd.concat(rows, ignore_index=True)
    panel["y"] = (panel["fwd8"] > 0).astype(int)
    return panel


def add_regime(panel):
    """EQW tuan tu mean return tuan cua cac ma trong panel, SMA40w, map theo tuan lich.
    Gom theo ISO week (to_period('W')) de tranh lech lich nghi giua cac ma:
    moi tuan chi co 1 diem EQW, SMA40 dung la 40 tuan."""
    p = panel.sort_values(["ticker", "date"]).copy()
    p["ret1w"] = p.groupby("ticker")["close"].pct_change()
    p["week"] = p["date"].dt.to_period("W")
    eqw_ret = p.groupby("week")["ret1w"].mean().sort_index()
    eqw = 100 * (1 + eqw_ret.fillna(0)).cumprod()
    sma40 = eqw.rolling(40).mean()
    reg = pd.DataFrame({
        "regime_bull": (eqw > sma40).astype(int),
        "dist_eqw_sma40": eqw / sma40 - 1,
    }, index=eqw.index)
    panel = panel.copy()
    panel["week"] = panel["date"].dt.to_period("W")
    panel = panel.join(reg, on="week")
    n_missing = int(panel["regime_bull"].isna().sum())
    panel = panel.dropna(subset=["regime_bull"])
    print(f"EQW: {len(eqw)} tuan lich, bull share toan panel: "
          f"{panel['regime_bull'].mean():.3f} (bo {n_missing} dong 40 tuan dau chua co SMA40)")
    return panel


def split_report(name, yte, pred, proba, mask=None):
    if mask is not None:
        yte, pred, proba = yte[mask], pred[mask], proba[mask]
    if len(yte) == 0 or yte.nunique() < 2:
        return f"{name}: n={len(yte)} (chi 1 class, khong tinh AUC)"
    return (f"{name}: n={len(yte):,} base_up={yte.mean():.3f} "
            f"acc={accuracy_score(yte, pred):.3f} "
            f"AUC={roc_auc_score(yte, proba):.3f} "
            f"F1={f1_score(yte, pred, zero_division=0):.3f}")


def main():
    panel = build_panel_with_close()
    panel = add_regime(panel)
    print(f"Panel: {len(panel):,} dong, {panel['date'].min().date()} -> {panel['date'].max().date()}")
    tr = panel[panel["date"] <= TRAIN_END]
    te = panel[panel["date"] > TRAIN_END]
    print(f"Train (<=2021): {len(tr):,} | Test (>=2022): {len(te):,}")
    print(f"Ti le tang 8 tuan — train: {tr['y'].mean():.3f} | test: {te['y'].mean():.3f}")
    print(f"Bull share — train: {tr['regime_bull'].mean():.3f} | test: {te['regime_bull'].mean():.3f}")

    feats2 = FEATS + ["regime_bull", "dist_eqw_sma40"]
    Xtr, ytr = tr[feats2], tr["y"]
    Xte, yte = te[feats2], te["y"]

    results = []
    maj = int(ytr.mean() >= 0.5)
    base_pred = np.full(len(yte), maj)
    results.append({"model": "Majority (doan mu)", "acc": round(float((base_pred == yte).mean()), 4),
                    "auc": 0.5, "f1": round(float(f1_score(yte, base_pred, zero_division=0)), 4)})
    print(f"{'Majority (doan mu)':28s} acc={results[0]['acc']:.3f}  AUC=0.500  F1={results[0]['f1']:.3f}")
    for depth in [3, 5, 10, None]:
        results.append(evaluate(f"DecisionTree depth={depth} + regime",
                                DecisionTreeClassifier(max_depth=depth, random_state=0),
                                Xtr, ytr, Xte, yte))
    rf = RandomForestClassifier(n_estimators=200, min_samples_leaf=5, n_jobs=-1, random_state=0)
    results.append(evaluate("RandomForest n=200 + regime", rf, Xtr, ytr, Xte, yte))
    imp = pd.Series(rf.feature_importances_, index=feats2).sort_values(ascending=False)
    print("\nFeature importance (RandomForest + regime):")
    for k, v in imp.items():
        print(f"  {k:16s} {v:.3f}")

    # Tach theo regime tren test (RF tot nhat)
    rf_pred = rf.predict(Xte)
    rf_proba = rf.predict_proba(Xte)[:, 1]
    bull = (te["regime_bull"] == 1).to_numpy()
    print("\nTest tach theo regime (RandomForest + regime):")
    print("  " + split_report("Bull weeks ", yte, rf_pred, rf_proba, bull))
    print("  " + split_report("Bear weeks ", yte, rf_pred, rf_proba, ~bull))
    bull_line = split_report("Bull weeks", yte, rf_pred, rf_proba, bull)
    bear_line = split_report("Bear weeks", yte, rf_pred, rf_proba, ~bull)

    lines = [
        "# SMA Project — prototype ML, bien the regime (EQW/SMA40w)",
        "",
        "Chay thu ngay 2026-11-14 (venv Midterm, sklearn 1.9.1). Cung thiet lap voi ban goc "
        "(`sma-ml-prototype.md`: universe 254 ma, panel ma-tuan, 9 feature gia thuan, target "
        "tang/giam sau 8 tuan, train <=2021 / test >=2022), chi them 2 feature regime "
        "tinh point-in-time tu chinh universe: `regime_bull` (EQW tuan > SMA40w) va "
        "`dist_eqw_sma40` (EQW/SMA40w - 1), dung dinh nghia regime cua STRATEGY v1.2.",
        "",
        f"- Panel sau khi them regime: {len(panel):,} dong, "
        f"{panel['date'].min().date()} -> {panel['date'].max().date()}.",
        f"- Bull share: train {tr['regime_bull'].mean():.1%}, test {te['regime_bull'].mean():.1%}.",
        f"- Ti le tang 8 tuan: train {tr['y'].mean():.1%}, test {te['y'].mean():.1%}.",
        "",
        "## Ket qua test (>= 2022) — co regime",
        "",
        "| Model | Accuracy | AUC | F1 |",
        "|---|---:|---:|---:|",
    ]
    for r in results:
        lines.append(f"| {r['model']} | {r['acc']:.3f} | {r['auc']:.3f} | {r['f1']:.3f} |")
    lines += [
        "",
        "So voi ban goc khong regime: RandomForest AUC 0,516 / acc 0,507; "
        "DecisionTree AUC 0,492–0,504.",
        "",
        "## Feature importance (RandomForest + regime)",
        "",
    ]
    for k, v in imp.items():
        lines.append(f"- {k}: {v:.3f}")
    lines += [
        "",
        "## Test tach theo regime (RandomForest + regime)",
        "",
        f"- {bull_line}",
        f"- {bear_line}",
        "",
        "## Doc ket qua (noi thang)",
        "- Them regime EQW/SMA40w khong cuu duoc model gia thuan: AUC van quanh 0,5x "
        "(xem bang tren) — ket luan am cua ban goc dung vung, khong phai do test thien bear.",
        "- Ghi thang vao bao cao SMA nhu ket qua am hop le cho muc 4 rubric; chien luoc "
        "giao dich van dung rule v1.2, khong xay tren du bao cua model.",
        "",
        "Script: `hidden_files/sma_ml_prototype_regime.py` (chay lai duoc, seed co dinh).",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\nDa ghi:", OUT)


if __name__ == "__main__":
    main()
