#!/usr/bin/env python3
"""SMA Project — vector trading simulation on the ML probabilities.

Bridges the ML study (ml_model.py) and the trading rubric item: the
RandomForest 8-week up-probabilities are turned into two simple,
fully vectorised portfolio simulations on the out-of-sample test period
(>= 2022), plus an equal-weight buy-and-hold benchmark of the universe.

Method (deliberately simple and overlap-free):
- Panel: same point-in-time weekly panel as ml_model.py (9 price features,
  target = sign of the 8-week forward return, train <= 2021 / test >= 2022).
- Rebalance every 8 panel weeks (step 8) so holding windows never overlap;
  each period's portfolio return is the equal-weight mean of the selected
  tickers' realised 8-week forward returns (fwd8).
- Sim 1 "top-10": hold the 10 tickers with the highest predicted up-proba.
- Sim 2 "top-10 & proba>0.55": same, but only tickers with proba > 0.55
  qualify; if none qualify the portfolio stays in cash (0% that period).
- Benchmark: equal-weight all universe tickers at the same rebalance dates.

Returns are approximate returns on capital (no transaction costs, no
limit-up/down fill simulation — the audited event-driven backtest of the
rule-based strategy v1.2 lives in strategy/strategy_v12.py).

Run:  python trading_simulation.py   (needs SMA_DATA_DIR, see ml_model.py)
Writes results/trading_simulation.md and prints a summary.
"""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from ml_model import FEATS, TRAIN_END, build_panel

OUT = Path(__file__).resolve().parent / "results" / "trading_simulation.md"
STEP = 8        # rebalance every 8 weeks -> non-overlapping fwd8 windows
TOPN = 10
THRESH = 0.55


def _compound(period_rets):
    r = np.asarray(period_rets, dtype=float)
    return float(np.prod(1 + r) - 1) if len(r) else 0.0


def simulate(test, step=STEP):
    """Run both sims + benchmark on the test panel (needs cols
    date/ticker/fwd8/proba). Returns (summary dict, trades DataFrame).

    Rows are grouped by ISO calendar week (per-ticker weekly bars are
    sampled from each ticker's own series end, so raw dates do NOT align
    across tickers); rebalancing every `step` calendar weeks makes the
    8-week holding windows non-overlapping."""
    t = test.copy()
    t["week"] = t["date"].dt.to_period("W")
    weeks = sorted(t["week"].unique())[::step]
    rows, trades = [], []
    for d in weeks:
        g = t[t["week"] == d]
        top = g.nlargest(TOPN, "proba")
        r_top = float(top["fwd8"].mean())
        qual = g[g["proba"] > THRESH].nlargest(TOPN, "proba")
        r_thr = float(qual["fwd8"].mean()) if len(qual) else 0.0
        r_bench = float(g["fwd8"].mean())
        rows.append({"date": d, "sim1_top10": r_top,
                     "sim2_thr": r_thr, "bench_eqw": r_bench,
                     "n_thr": len(qual)})
        for _, r in top.iterrows():
            trades.append({"date": d, "sim": "sim1_top10",
                           "ticker": r["ticker"], "proba": r["proba"],
                           "fwd8": r["fwd8"]})
        for _, r in qual.iterrows():
            trades.append({"date": d, "sim": "sim2_thr",
                           "ticker": r["ticker"], "proba": r["proba"],
                           "fwd8": r["fwd8"]})
    per = pd.DataFrame(rows)
    invested = per[per["n_thr"] > 0]
    summary = {
        "n_periods": len(per),
        "sim1_total": _compound(per["sim1_top10"]),
        "sim1_win": float((per["sim1_top10"] > 0).mean()),
        "sim1_avg": float(per["sim1_top10"].mean()),
        "sim2_total": _compound(per["sim2_thr"]),
        "sim2_win": float((invested["sim2_thr"] > 0).mean())
        if len(invested) else float("nan"),
        "sim2_avg": float(invested["sim2_thr"].mean())
        if len(invested) else float("nan"),
        "sim2_invested_periods": len(invested),
        "bench_total": _compound(per["bench_eqw"]),
        "bench_win": float((per["bench_eqw"] > 0).mean()),
        "bench_avg": float(per["bench_eqw"].mean()),
    }
    return summary, pd.DataFrame(trades), per


def latest_signals(panel, model):
    """Top-10 tickers by predicted up-proba at the panel's last week,
    plus the regime state (EQW vs SMA40w) of that week — the 'latest new
    trades' view of the end-to-end workflow."""
    pp = panel.copy()
    pp["week"] = pp["date"].dt.to_period("W")
    last_week = pp["week"].max()
    g = pp[pp["week"] == last_week].copy()
    last_date = g["date"].max()
    g["proba"] = model.predict_proba(g[FEATS])[:, 1]
    top = g.nlargest(TOPN, "proba")[["ticker", "proba"]]
    # regime: EQW from the panel's own weekly closes (same definition as
    # ml_model_regime.add_regime: ISO-week mean return, cumprod from 100)
    from ml_model_regime import build_panel_with_close, add_regime
    p = build_panel_with_close()
    p = add_regime(p)
    row = p[p["week"] == p["week"].max()].iloc[0]
    regime = {"week": str(row["date"].date()),
              "bull": bool(row["regime_bull"]),
              "dist_eqw_sma40": float(row["dist_eqw_sma40"])}
    return last_date, top, regime


def run(write_report=True):
    panel = build_panel()
    tr = panel[panel["date"] <= TRAIN_END]
    te = panel[panel["date"] > TRAIN_END].copy()
    print(f"Panel: {len(panel):,} rows | train {len(tr):,} | test {len(te):,}")
    rf = RandomForestClassifier(n_estimators=200, min_samples_leaf=5,
                                n_jobs=-1, random_state=0)
    rf.fit(tr[FEATS], tr["y"])
    te["proba"] = rf.predict_proba(te[FEATS])[:, 1]
    s, trades, per = simulate(te)
    print(f"Sim 1 top-10          : total {s['sim1_total']:+.1%} | "
          f"{s['n_periods']} periods | win {s['sim1_win']:.0%} | "
          f"avg {s['sim1_avg']:+.2%}/period")
    print(f"Sim 2 top-10 & p>0.55 : total {s['sim2_total']:+.1%} | "
          f"invested {s['sim2_invested_periods']}/{s['n_periods']} periods "
          f"| win {s['sim2_win']:.0%} | avg {s['sim2_avg']:+.2%}/period")
    print(f"Benchmark EQW B&H     : total {s['bench_total']:+.1%} | "
          f"win {s['bench_win']:.0%} | avg {s['bench_avg']:+.2%}/period")
    last_date, top, regime = latest_signals(panel, rf)
    print(f"\nLatest panel week {last_date.date()} — top-10 by proba:")
    for _, t in top.iterrows():
        print(f"  {t['ticker']:6s} proba={t['proba']:.3f}")
    print(f"Regime @ {regime['week']}: "
          f"{'BULL' if regime['bull'] else 'BEAR'} "
          f"(EQW vs SMA40w: {regime['dist_eqw_sma40']:+.2%})")
    if write_report:
        lines = [
            "# SMA Project — vector trading simulation on ML probabilities",
            "",
            "RandomForest (n=200, trained <= 2021) 8-week up-probabilities,",
            "turned into portfolios on the test period (>= 2022). Rebalance",
            "every 8 weeks (non-overlapping windows), equal weight, period",
            "return = mean realised fwd8 of the selected tickers. Returns",
            "are approximate returns on capital (no costs / no limit-fill",
            "simulation — see strategy/strategy_v12.py for the audited",
            "event-driven backtest of the rule-based strategy). Note: the",
            "ML panel's universe is the prototype's end-of-sample liquidity",
            "filter (ml_model.py), NOT the point-in-time universe of the",
            "strategy backtest, so absolute levels are optimistic.",
            "",
            f"Test span: {te['date'].min().date()} -> {te['date'].max().date()}"
            f" | {s['n_periods']} rebalance periods",
            "",
            "| Portfolio | Total return | Avg / period | Win rate (periods) |",
            "|---|---:|---:|---:|",
            f"| Sim 1: top-10 by proba | {s['sim1_total']:+.1%} | "
            f"{s['sim1_avg']:+.2%} | {s['sim1_win']:.0%} |",
            f"| Sim 2: top-10 with proba > 0.55 | {s['sim2_total']:+.1%} | "
            f"{s['sim2_avg']:+.2%} | {s['sim2_win']:.0%} "
            f"(invested {s['sim2_invested_periods']}/{s['n_periods']}) |",
            f"| Benchmark: equal-weight universe | {s['bench_total']:+.1%} | "
            f"{s['bench_avg']:+.2%} | {s['bench_win']:.0%} |",
            "",
            f"Reading: Sim 1 total {s['sim1_total']:+.1%} and Sim 2 total "
            f"{s['sim2_total']:+.1%} vs benchmark {s['bench_total']:+.1%} "
            f"over {s['n_periods']} non-overlapping 8-week periods. With "
            "out-of-sample AUC ~0.52 the probability ranking is weak "
            "evidence at best; this vector sim also ignores transaction "
            "costs and limit-up/down fills, so it is NOT evidence of a "
            "tradeable ML edge — the live system remains the rule-based, "
            "audited strategy v1.2 (strategy/).",
            "",
            f"Latest panel week {last_date.date()} — top-10 signals by proba:",
            "",
        ]
        for _, t in top.iterrows():
            lines.append(f"- {t['ticker']}: proba {t['proba']:.3f}")
        lines += [
            "",
            f"Regime that week ({regime['week']}): "
            f"{'BULL (EQW > SMA40w)' if regime['bull'] else 'BEAR (EQW < SMA40w)'}"
            f", EQW vs SMA40w {regime['dist_eqw_sma40']:+.2%}.",
            "",
            "Script: `trading_simulation.py` (run() is importable; the "
            "notebook's final section calls it).",
        ]
        OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\nWrote:", OUT)
    return {"summary": s, "trades": trades, "periods": per,
            "latest": (last_date, top, regime)}


if __name__ == "__main__":
    run()
