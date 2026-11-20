# Vietnam Stock Market Trading System — SMA Project

Stock Market Analytics Zoomcamp project: a complete, empirically tested
trading system for the Vietnamese stock market (HOSE/HNX), plus an honest
machine-learning study of whether price features can forecast returns.

## What this project contains

1. **A rule-based trading strategy (v1.2)** — full spec in `STRATEGY.md`.
   A regime switch (equal-weight index vs its 40-week SMA) selects between
   a trend-following leg (RRG two-level momentum: Leading stocks in top-3
   Leading sectors) and a mean-reversion leg (Wyckoff spring, only shortly
   after a confirmed breadth washout). A breadth circuit breaker (B200 < 30)
   blocks bull-style entries. Risk is managed with Friday-close stop-losses.
2. **A 10-year backtest** — weekly Friday-close decisions, point-in-time
   liquidity universe, deep-audited: **+937.9% total, max drawdown −40.1%,
   661 trades**; train expectancy +8.18%/trade (≤2021), test +1.30%/trade
   (≥2022). Details in `results/backtest_summary.md`.
3. **An ML study with a negative result** — Decision Tree / Random Forest
   on 9 price-only features to predict the 8-week direction across 254
   tickers (158,671 ticker-weeks, 2002–2026): best model reaches only
   **AUC 0.516** out of sample, and adding the market-regime features makes
   it worse (AUC 0.482). Price features do not forecast direction here, so
   the live system does not use ML signals. Full reports in `results/`,
   end-to-end notebook in `notebook.ipynb`.
4. **A live data pipeline + paper trading** — daily incremental OHLCV
   fetch (Simplize via a relay), indicator computation (breadth, RSI, RRG),
   and a paper-trading loop (plan Saturday, execute Monday) that has been
   running on this strategy since October 2026.

## Data

Source: Simplize OHLCV. Volume is **matched orders only** — negotiated
(block) deals are excluded from every volume-based signal because they are
arranged trades, not real supply/demand.

Per course rules, **data files are not committed** to this repository. See
`data/README.md` for the expected store layout; set `SMA_DATA_DIR` to run
the ML scripts against a local store.

## Run the ML study

```bash
pip install -r requirements.txt
export SMA_DATA_DIR=/path/to/store/bars
python ml_model.py          # base features -> results/sma-ml-prototype.md
python ml_model_regime.py   # + regime features -> results/sma-ml-prototype-regime.md
```

Or open `notebook.ipynb` for the same study end to end with outputs.

## Project structure

- `STRATEGY.md` — the v1.2 strategy specification (Vietnamese).
- `results/backtest_summary.md` — audited 10-year backtest results.
- `results/sma-ml-prototype.md`, `results/sma-ml-prototype-regime.md` —
  ML study reports (negative results, reported as-is).
- `ml_model.py`, `ml_model_regime.py` — reproducible ML scripts (fixed seeds).
- `notebook.ipynb` — end-to-end ML notebook with executed outputs.
- `data/` — data layout documentation only (no data files).
