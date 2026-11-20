# Backtest summary — Strategy v1.2 (10 years, weekly, Friday-close)

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
audit 05/10/2026.

| Metric | Strategy v1.2 | v1.1 (previous) |
|---|---:|---:|
| Total return (10y) | **+937.9%** | +111.4% |
| Max drawdown | **−40.1%** | −54.1% |
| Number of trades | 661 | 434 |
| Train (≤2021) expectancy | +8.18% / trade (n=331) | — |
| Test (≥2022) expectancy | +1.30% / trade (n=330) | — |
| Test, bear leg only | +0.37% / trade (n=87) | — |
| 2026 YTD (to Oct) | −5.8% | — |

Notes:
- Train and test expectancy have the same sign; the edge is concentrated in
  the bull (trend-following) leg, the bear leg is near flat out of sample —
  reported as-is, not cherry-picked.
- Gross figures before ~0.5% round-trip fees in the earliest runs; the audit
  version above is the reference result used by the live paper-trading
  system (`paper_trade` runs weekly: plan Saturday, execute Monday).
