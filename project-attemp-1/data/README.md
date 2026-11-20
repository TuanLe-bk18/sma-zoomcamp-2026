# Data (not committed)

Course rules prohibit uploading data files to GitHub, so the price store is
not part of this repository.

Expected layout: `data/bars/<TICKER>.json` — one JSON array per ticker with
daily bars `{"date": <epoch seconds>, "o": ..., "h": ..., "l": ..., "c": ...,
"v": ...}` (volume = matched orders only, negotiated deals excluded).

Source: Simplize OHLCV API for HOSE/HNX tickers, fetched into a local store
by a daily incremental pipeline (plus a weekly full reconcile). To run the
ML scripts against your own store, set:

```bash
export SMA_DATA_DIR=/path/to/store/bars
python ml_model.py
```

The strategy engine (`strategy/`) expects the store root instead —
`<dir>/bars/*.json` plus `<dir>/vnindex.json` (same bar format),
`<dir>/sector_map.json` ({ticker: sector}) and `<dir>/exchange_map.json`
({ticker: HOSE|HNX|UPCoM}):

```bash
export SMA_MARKET_DIR=/path/to/store
python strategy/strategy_v12.py stop
```
