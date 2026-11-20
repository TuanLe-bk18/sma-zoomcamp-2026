# SMA Project — prototype ML (muc 4 rubric)

Chay thu ngay 2026-11-14, cap nhat 2026-11-20 (them LogisticRegression, tuning RandomForest tren validation 2020-2021, rule nguong xac suat). Muc dich: lap khoang trong duy nhat cua SMA Project theo rubric — train model ML kieu bai giang tren du lieu VN de du bao loi nhuan tuong lai.

## Thiet lap (khop quy uoc 'bai toan nguoc')
- Du lieu: Simplize OHLCV khop lenh, kho `store/bars/`; chu ky tuan (gia dong cuoi moi 5 phien).
- Universe: 254 ma (du lieu >= 5 nam, gia cuoi 2k-500k, VOL TB ngay >= 50k cp — gan rule LIQ screener).
- Panel: 158,925 dong ma-tuan, 2002-04-05 -> 2026-09-25.
- Features (chi dung thong tin den tuan t): ret4/12/26/52, RSI14 tuan, khoang cach den SMA20/SMA50, khoang cach den dinh 52 tuan, vol ratio vs TB20w.
- Target: tang/giam sau 8 tuan (close[t+8] > close[t]).
- Chia theo thoi gian: train <= 2021, test >= 2022. Ti le tang 8 tuan: train 51.3%, test 46.3%.

## Ket qua test (>= 2022)

| Model | Accuracy | AUC | F1 |
|---|---:|---:|---:|
| Majority (doan mu) | 0.463 | 0.500 | 0.633 |
| DecisionTree depth=3 | 0.486 | 0.496 | 0.502 |
| DecisionTree depth=5 | 0.482 | 0.492 | 0.506 |
| DecisionTree depth=10 | 0.502 | 0.504 | 0.466 |
| DecisionTree depth=None | 0.504 | 0.504 | 0.488 |
| LogisticRegression | 0.473 | 0.470 | 0.487 |
| RandomForest n=200 | 0.507 | 0.516 | 0.505 |
| RandomForest tuned (n=100, depth=10) | 0.500 | 0.507 | 0.505 |

## Tuning RandomForest (validation 2020-2021, train <=2019)

| n_estimators | max_depth | Val AUC |
|---:|---:|---:|
| 100 | None | 0.513 |
| 100 | 10 | 0.519 |
| 100 | 20 | 0.512 |
| 200 | None | 0.514 |
| 200 | 10 | 0.519 |
| 200 | 20 | 0.514 |

Cau hinh duoc chon (val AUC cao nhat): n_estimators=100, max_depth=10 — refit tren toan bo train <=2021, ket qua test o bang tren.

## Rule nguong xac suat (RandomForest n=200, test >=2022)

| Nguong proba | So dong duoc chon | Precision (ti le tang that) | Ti le bat duoc lenh tang |
|---:|---:|---:|---:|
| > 0.55 | 20,841 | 0.482 | 36.3% |
| > 0.6 | 11,486 | 0.489 | 20.3% |

## Feature importance (RandomForest)

- dist_sma50: 0.119
- ret52: 0.117
- ret26: 0.116
- rsi14: 0.111
- dist_52w_high: 0.109
- dist_sma20: 0.109
- ret12: 0.108
- vol_ratio: 0.107
- ret4: 0.104

## Doc ket qua (noi thang)
- Da tune (validation 2020-2021) va da thu rule nguong xac suat: AUC test van quanh 0,5x — ket luan am dung vung, khong phai do chua tune.
- Neu accuracy/AUC chi ngang doan mu thi ket luan thang nhu vay trong bao cao — giong cach Kronos da bi bac bang so lieu, khong to hong.
- Bien the them regime EQW/SMA40w lam feature nam o `ml_model_regime.py` (ket qua con te hon). Mo phong giao dich tren xac suat cua model nay nam o `trading_simulation.py` — cung khong danh bai benchmark.

Script: `ml_model.py` (chay lai duoc, seed co dinh).
