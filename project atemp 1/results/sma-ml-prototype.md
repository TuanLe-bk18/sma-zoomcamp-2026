# SMA Project — prototype ML (muc 4 rubric)

Chay thu ngay 2026-11-14 (venv Midterm, sklearn 1.9.1). Muc dich: lap khoang trong duy nhat cua SMA Project theo rubric — train model ML kieu bai giang tren du lieu VN de du bao loi nhuan tuong lai.

## Thiet lap (khop quy uoc 'bai toan nguoc')
- Du lieu: Simplize OHLCV khop lenh, kho `store/bars/`; chu ky tuan (gia dong cuoi moi 5 phien).
- Universe: 254 ma (du lieu >= 5 nam, gia cuoi 2k-500k, VOL TB ngay >= 50k cp — gan rule LIQ screener).
- Panel: 158,671 dong ma-tuan, 2002-04-05 -> 2026-09-18.
- Features (chi dung thong tin den tuan t): ret4/12/26/52, RSI14 tuan, khoang cach den SMA20/SMA50, khoang cach den dinh 52 tuan, vol ratio vs TB20w.
- Target: tang/giam sau 8 tuan (close[t+8] > close[t]).
- Chia theo thoi gian: train <= 2021, test >= 2022. Ti le tang 8 tuan: train 51.3%, test 46.4%.

## Ket qua test (>= 2022)

| Model | Accuracy | AUC | F1 |
|---|---:|---:|---:|
| Majority (doan mu) | 0.464 | 0.500 | 0.633 |
| DecisionTree depth=3 | 0.486 | 0.496 | 0.502 |
| DecisionTree depth=5 | 0.482 | 0.492 | 0.506 |
| DecisionTree depth=10 | 0.501 | 0.503 | 0.466 |
| DecisionTree depth=None | 0.504 | 0.504 | 0.489 |
| RandomForest n=200 | 0.507 | 0.516 | 0.506 |

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
- **Model gia thuan gan nhu khong co edge.** RandomForest tot nhat cung chi AUC **0,516**
  (doan mu = 0,500), accuracy 0,507 — tham chi thap hon ca chien luoc "luon doan giam"
  (53,6%, vi test >= 2022 chi co 46,4% truong hop tang 8 tuan). DecisionTree moi depth
  deu AUC ~0,49-0,50, tuc la khong hon tung dong xu.
- Feature importance phang deu (~0,10-0,12 moi feature) — khong co feature gia nao
  noi troi, khop voi ket qua AUC: 9 feature gia thuan khong du bao duoc huong 8 tuan.
- **Day la ket qua am hop le cho muc 4 rubric, khong phai that bai can giau** — giong
  cach Kronos da bi bac bang so lieu: ghi thang vao bao cao la model khong du bao duoc,
  va chien luoc giao dich van dung rule v1.2 (rule-based), khong xay tren du bao cua model.
## Bien the regime — DA CHAY 2026-11-14, ket qua am (xem `sma-ml-prototype-regime.md`)
- Them `regime_bull` + `dist_eqw_sma40` (EQW/SMA40w, dung dinh nghia v1.2):
  RandomForest AUC **0,482** / acc 0,490 — TE HON ban goc (0,516 / 0,507),
  duoi ca doan mu. DecisionTree cung te di o moi depth.
- Tach test theo regime: tuan bull AUC 0,469, tuan bear AUC 0,497 — gia thuyet
  "test thien bear lam lech so" bi bac. Khong thu them bien the regime nao nua.
- Buoc tiep theo neu anh giu de tai v1.2: tune nhe
  tren validation 2020-2021 — nhung dung ky vong cao khi AUC goc moi 0,516.

Script: `hidden_files/sma_ml_prototype.py` (chay lai duoc, seed co dinh).
