# SMA Project — vector trading simulation on ML probabilities

RandomForest (n=200, trained <= 2021) 8-week up-probabilities,
turned into portfolios on the test period (>= 2022). Rebalance
every 8 weeks (non-overlapping windows), equal weight, period
return = mean realised fwd8 of the selected tickers. Returns
are approximate returns on capital (no costs / no limit-fill
simulation — see strategy/strategy_v12.py for the audited
event-driven backtest of the rule-based strategy). Note: the
ML panel's universe is the prototype's end-of-sample liquidity
filter (ml_model.py), NOT the point-in-time universe of the
strategy backtest, so absolute levels are optimistic.

Test span: 2021-12-31 -> 2026-09-25 | 31 rebalance periods

| Portfolio | Total return | Avg / period | Win rate (periods) |
|---|---:|---:|---:|
| Sim 1: top-10 by proba | +156.5% | +3.83% | 74% |
| Sim 2: top-10 with proba > 0.55 | +149.7% | +3.74% | 74% (invested 31/31) |
| Benchmark: equal-weight universe | -2.2% | +0.38% | 52% |

Reading: Sim 1 total +156.5% and Sim 2 total +149.7% vs benchmark -2.2% over 31 non-overlapping 8-week periods. With out-of-sample AUC ~0.52 the probability ranking is weak evidence at best; this vector sim also ignores transaction costs and limit-up/down fills, so it is NOT evidence of a tradeable ML edge — the live system remains the rule-based, audited strategy v1.2 (strategy/).

Latest panel week 2026-09-25 — top-10 signals by proba:

- PVC: proba 0.839
- APH: proba 0.729
- MSB: proba 0.720
- DDV: proba 0.713
- PVP: proba 0.702
- HHP: proba 0.698
- PET: proba 0.695
- MSR: proba 0.685
- QTP: proba 0.668
- DPG: proba 0.645

Regime that week (2026-09-25): BEAR (EQW < SMA40w), EQW vs SMA40w -13.08%.

Script: `trading_simulation.py` (run() is importable; the notebook's final section calls it).
