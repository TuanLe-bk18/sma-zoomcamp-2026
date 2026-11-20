# Vietnam Stock Market Trading System — SMA Project

Stock Market Analytics Zoomcamp project: a complete, empirically tested
trading system for the Vietnamese stock market (HOSE/HNX), plus an honest
machine-learning study of whether price features can forecast returns.

## What this project contains

1. **A rule-based trading strategy (v1.2)** — full spec in `STRATEGY.md`
   (Vietnamese; English summary: a regime switch — equal-weight index vs
   its 40-week SMA — selects between a trend-following leg, RRG two-level
   momentum picking Leading stocks in the top-3 Leading sectors, and a
   mean-reversion leg, Wyckoff spring entries allowed only shortly after a
   confirmed breadth washout; a breadth circuit breaker, B200 < 30, blocks
   bull-style entries; risk is managed with Friday-close stop-losses).
2. **A 10-year backtest with the actual engine code** (`strategy/`) —
   weekly Friday-close decisions, point-in-time liquidity universe,
   deep-audited. Latest verified run (2026-11-20, data through
   2026-11-13): **+984.2% total (CAGR +29.0%/yr), max drawdown −40.1%,
   657 trades**; train expectancy +8.18%/trade (≤2021), test +1.63%/trade
   (≥2022); VNINDEX buy-and-hold over the same span: +123.4%. Details in
   `results/backtest_summary.md`.
3. **An ML study with a negative result** — Decision Tree, Logistic
   Regression and Random Forest on 9 price-only features to predict the
   8-week direction across 254 tickers (158,925 ticker-weeks, 2002–2026):
   best model reaches only **AUC 0.516** out of sample; tuning on a
   2020–2021 validation split does not help (tuned RF: AUC 0.507), and
   adding market-regime features makes it worse (AUC 0.482). Price
   features do not forecast direction here, so the live system does not
   use ML signals. Full reports in `results/`, end-to-end notebook in
   `notebook.ipynb`.
4. **Vector trading simulations on the ML probabilities**
   (`trading_simulation.py`) — top-10-by-probability portfolios vs an
   equal-weight benchmark over 31 non-overlapping 8-week periods
   (≥2022): +156.5% / +149.7% vs −2.2% for the benchmark. Read with care:
   the ML panel's universe is an end-of-sample liquidity filter, so
   absolute levels are optimistic; with AUC ≈ 0.52 this is not evidence
   of a tradeable ML edge. See `results/trading_simulation.md`.
5. **A live data pipeline + paper trading** — daily incremental OHLCV
   fetch (Simplize), indicator computation (breadth, RSI, RRG), and a
   paper-trading loop (`strategy/paper_trade.py`: plan Saturday, execute
   Monday) that has been running on this strategy since October 2026.

## Data

Source: Simplize OHLCV. Volume is **matched orders only** — negotiated
(block) deals are excluded from every volume-based signal because they are
arranged trades, not real supply/demand.

Per course rules, **data files are not committed** to this repository. See
`data/README.md` for the expected store layout; set `SMA_DATA_DIR` to run
the ML scripts against a local store, and `SMA_MARKET_DIR` for the
strategy engine.

## Repository layout & how to run the workflow

The end-to-end workflow is: **download → transform → predict → simulate →
latest trades**, and every step is in this repo:

```bash
pip install -r requirements.txt
export SMA_DATA_DIR=/path/to/store/bars        # for the ML study
export SMA_MARKET_DIR=/path/to/store           # for the strategy engine

python ml_model.py            # transform + train -> results/sma-ml-prototype.md
python ml_model_regime.py     # + regime features -> results/sma-ml-prototype-regime.md
python trading_simulation.py  # simulate on ML probabilities -> results/trading_simulation.md
python strategy/strategy_v12.py stop   # audited v1.2 backtest (event-driven)
python strategy/paper_trade.py --plan  # weekly automation: plan Sat / --execute Mon
```

Or open `notebook.ipynb`: it runs the ML study end to end (EDA → models →
feature importance) and finishes with the simulation + the latest
top-10 signals and regime state.

## Project structure

- `STRATEGY.md` — the v1.2 strategy specification (Vietnamese).
- `strategy/` — the production engine: `bt_common.py` (data/universe
  helpers), `backtest_rrg.py` (matrices + RRG), `signals.py` (weekly
  signals), `sectors.py` (sector map loader), `strategy_v12.py`
  (backtest), `paper_trade.py` (live paper-trading automation).
- `results/backtest_summary.md` — audited backtest results + benchmark.
- `results/sma-ml-prototype.md`, `results/sma-ml-prototype-regime.md`,
  `results/trading_simulation.md` — ML study + simulation reports
  (negative results, reported as-is).
- `ml_model.py`, `ml_model_regime.py`, `trading_simulation.py` —
  reproducible scripts (fixed seeds).
- `notebook.ipynb` — end-to-end notebook with executed outputs.
- `data/` — data layout documentation only (no data files).
