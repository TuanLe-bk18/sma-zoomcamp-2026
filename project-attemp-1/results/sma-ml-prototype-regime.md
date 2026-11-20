# SMA Project — prototype ML, bien the regime (EQW/SMA40w)

Chay thu ngay 2026-11-14 (venv Midterm, sklearn 1.9.1). Cung thiet lap voi ban goc (`sma-ml-prototype.md`: universe 254 ma, panel ma-tuan, 9 feature gia thuan, target tang/giam sau 8 tuan, train <=2021 / test >=2022), chi them 2 feature regime tinh point-in-time tu chinh universe: `regime_bull` (EQW tuan > SMA40w) va `dist_eqw_sma40` (EQW/SMA40w - 1), dung dinh nghia regime cua STRATEGY v1.2.

- Panel sau khi them regime: 158,671 dong, 2002-04-05 -> 2026-09-18.
- Bull share: train 73.1%, test 61.7%.
- Ti le tang 8 tuan: train 51.3%, test 46.4%.

## Ket qua test (>= 2022) — co regime

| Model | Accuracy | AUC | F1 |
|---|---:|---:|---:|
| Majority (doan mu) | 0.464 | 0.500 | 0.633 |
| DecisionTree depth=3 + regime | 0.515 | 0.498 | 0.420 |
| DecisionTree depth=5 + regime | 0.495 | 0.470 | 0.392 |
| DecisionTree depth=10 + regime | 0.479 | 0.469 | 0.356 |
| DecisionTree depth=None + regime | 0.487 | 0.486 | 0.456 |
| RandomForest n=200 + regime | 0.489 | 0.482 | 0.469 |

So voi ban goc khong regime: RandomForest AUC 0,516 / acc 0,507; DecisionTree AUC 0,492–0,504.

## Feature importance (RandomForest + regime)

- dist_eqw_sma40: 0.158
- ret52: 0.099
- ret26: 0.098
- dist_sma50: 0.097
- dist_sma20: 0.093
- dist_52w_high: 0.092
- rsi14: 0.092
- ret12: 0.089
- vol_ratio: 0.089
- ret4: 0.089
- regime_bull: 0.004

## Test tach theo regime (RandomForest + regime)

- Bull weeks: n=36,745 base_up=0.472 acc=0.481 AUC=0.469 F1=0.479
- Bear weeks: n=22,808 base_up=0.450 acc=0.504 AUC=0.497 F1=0.450

## Doc ket qua (noi thang)
- Them regime EQW/SMA40w khong cuu duoc model gia thuan — ma con te hon ban goc:
  RandomForest AUC **0,482** (duoi ca doan mu 0,500), acc 0,490, so voi ban goc
  khong regime AUC 0,516 / acc 0,507. DecisionTree cung te di o moi depth
  (AUC 0,469–0,498 so voi 0,492–0,504).
- Dac biet: `dist_eqw_sma40` co feature importance cao nhat (0,158) nhung lai lam
  model te hon tren test — quan he regime-hoc duoc o train khong giu duoc sang
  test, kieu overfit quen thuoc. `regime_bull` nhi phan gan nhu vo dung (0,004).
- Gia thuyet "test thien bear lam lech so" BI BAC: tach test theo regime,
  RF van duoi 0,5 o ca hai phia — tuan bull AUC 0,469 (n=36.745), tuan bear
  AUC 0,497 (n=22.808). Model hong ca khi bull lan bear.
- Ket luan am cua ban goc dung vung, khong phai do thieu regime. Ghi thang vao
  bao cao SMA nhu ket qua am hop le cho muc 4 rubric; chien luoc giao dich
  van dung rule v1.2, khong xay tren du bao cua model. Khong can thu them
  bien the regime nao nua cho muc nay.

Script: `ml_model_regime.py` (chay lai duoc, seed co dinh).
