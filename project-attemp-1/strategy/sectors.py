"""Sector membership for the VN universe, loaded from sector_map.json.

Replaces `from compute_simplize import SECTORS` in the original research
codebase: reads <SMA_MARKET_DIR>/sector_map.json ({ticker: sector}) and
exposes SECTORS as {sector_name: [tickers...]} over the fixed 13-sector
list used by the strategy (same format as the original loader).
"""
import json
import os
from pathlib import Path

_SECTOR_NAMES = ['Banking', 'Securities', 'RealEstate', 'Steel', 'OilGas',
                 'Retail', 'Technology', 'Industrial', 'Materials',
                 'Consumer', 'Pharma', 'Insurance', 'Construction']


def _load_sectors():
    fp = Path(os.environ.get('SMA_MARKET_DIR', 'data')) / 'sector_map.json'
    _map = json.loads(fp.read_text())
    _out = {s: [] for s in _SECTOR_NAMES}
    for _t, _s in sorted(_map.items()):
        if _s in _out:
            _out[_s].append(_t)
    return _out


SECTORS = _load_sectors()
