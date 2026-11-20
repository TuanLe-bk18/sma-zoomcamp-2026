# Backtest summary — Strategy v1.2 (weekly, Friday-close)

Rule-based strategy (full spec in `STRATEGY.md`): regime switch on the
equal-weight index vs its 40-week SMA — uptrend leg trades RRG two-level
momentum (Leading stocks in top-3 Leading sectors), downtrend leg trades
Wyckoff-spring mean reversion (only in the 4 weeks after a confirmed
B50-crosses-below-B200 breadth signal, persisted 10 sessions). Circuit
breaker: no bull-style entries while breadth B200 < 30. Stop-loss on Friday
closes (bull: below daily SMA50 or −8% from entry; bear: below the 26-week
spring low).

Backtest: weekly bars, decisions on Friday closes, point-in-time liquidity
universe (price 2,000–500,000 VND, matched-order volume MA20 50k–200M
shares; volume = matched orders only, negotiated deals excluded), deep
audit 05/10/2026. Engine code: `strategy/strategy_v12.py` (+ `signals.py`,
`backtest_rrg.py`, `bt_common.py`).

**Latest verified run: 2026-11-20** (repo code, store data through
2026-11-13; span 2017-06-30 → 2026-11-13, 9.4 years). An earlier audited
run (2026-10-05, data through Sep 2026) gave +937.9% / −40.1% / 661
trades — same drawdown, same train expectancy; the difference is the
extra ~6 weeks of data.

| Metric | Strategy v1.2 (run 2026-11-20) | v1.1 (previous) |
|---|---:|---:|
| Total return | **+984.2%** | +111.4% |
| CAGR | **+29.0% / year** | — |
| Max drawdown | **−40.1%** | −54.1% |
| Number of trades | 657 | 434 |
| Train (≤2021) expectancy | +8.18% / trade (n=331) | — |
| Test (≥2022) expectancy | +1.63% / trade (n=326) | — |
| Test, bear leg only | +0.37% / trade (n=87) | — |
| 2026 YTD (to 13 Nov) | +6.0% | — |

Benchmark, same span (2017-06-30 → 2026-11-13): **VNINDEX buy-and-hold
+123.4% (CAGR +9.0% / year)** — the strategy's excess return comes with a
−40.1% max drawdown, i.e. it is not a free lunch, just a better
risk/return trade than the index over this span.

Notes:
- Train and test expectancy have the same sign; the edge is concentrated in
  the bull (trend-following) leg, the bear leg is near flat out of sample —
  reported as-is, not cherry-picked.
- The live paper-trading system (`strategy/paper_trade.py`) runs this
  exact engine weekly: plan Saturday, execute Monday.
