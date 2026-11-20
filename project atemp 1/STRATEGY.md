# CHIẾN LƯỢC CHỐT v1.2 — 03/10/2026

Mọi tham số đều từ backtest 10 năm dữ liệu VN (2016–2026), train ≤2021 / test ≥2022.
File kiểm chứng: `workspace/research_notes/rrg-vietnam-empirical-backtest-20260929/report.md`.

## 1. Universe (đổi 01/10/2026 theo điều kiện lọc của anh)
Mã đạt cả hai tại thời điểm vào lệnh (point-in-time):
- Giá đóng cửa 2.000–500.000đ
- VOL trung bình 20 phiên 50.000–200 triệu cổ phiếu
(trước đây: giá trị giao dịch TB 20 phiên > 1 tỷ đồng)

### Quy ước khối lượng (chốt 01/10/2026)
- Dữ liệu volume của Simplize chỉ là **khớp lệnh**, chưa gồm **thỏa thuận**.
- Mọi tín hiệu liên quan khối lượng (vol_ratio, unusual volume, breakout kèm
  volume, GTGD, điều kiện VOL trong universe) đều dùng khớp lệnh và **không
  được cộng thỏa thuận vào** — thỏa thuận là giao dịch dàn xếp, không phản ánh
  cung-cầu thật trên sổ lệnh.
- Báo cáo ngày ghi rõ "GTGD khớp lệnh (chưa gồm thỏa thuận)".

## 2. Lịch chạy
Sáng thứ 7 hàng tuần, sau khi tuần giao dịch đã chốt.

## 3. Công tắc thị trường (regime)
- Giá trung bình toàn thị trường (EQW) > trung bình 40 tuần → **UPTREND**
- Ngược lại → **DOWNTREND**

## 4. Cầu chì breadth
- % mã nằm trên SMA200 (B200) < 30% → **cấm mở lệnh mới kiểu UPTREND**,
  đóng các vị thế UPTREND đang giữ. (B200<30 → forward -2.37%/8w;
  two-level +2.86% → -3.40%.)
- Lệnh bắt đáy kiểu DOWNTREND vẫn được mở (RSI<30 khi B200<30 vẫn +1.46%).

## 5. UPTREND → RRG two-level
- RRG tuần (JdK, w14, benchmark EQW) xếp hạng 13 ngành → lấy **3 ngành mạnh nhất**.
- Mua các mã đang ở góc **Leading** trong 3 ngành đó.
- Tối đa 10 mã, chia đều tiền, không quá 3 mã một ngành.
- Giữ tối đa **12 tuần**.
- Cắt lỗ theo §7.

## 6. DOWNTREND → bắt đáy Wyckoff (CÓ CỬA WASHOUT)
- Chỉ mở lệnh mới khi **vừa có washout**: B50 cắt xuống dưới B200 và giữ
  nguyên phía mới ít nhất 10 phiên (đã xác nhận), trong vòng 4 tuần gần nhất.
- Điểm cắt chỉ được tính là "đã xác nhận" SAU 10 phiên persist — tức tín
  hiệu live thấy được muộn hơn điểm cắt 10 phiên (fix lookahead 05/10/2026:
  backtest cũ dùng tín hiệu chưa xác nhận, live không bao giờ thấy).
- Mã có **spring** (thủng đáy 26 tuần rồi lấy lại trên +3%) hoặc **RSI tuần < 30**.
- Tối đa 10 mã, chia đều tiền, không quá 3 mã một ngành.
- Giữ tối đa **8 tuần** (mean-reversion phai sau T+40).
- Cắt lỗ theo §7.
- Không có washout → ngồi cash, không bắt đáy (bear mài mòn thua -7.9%/năm).

## 7. Stop-loss (mới từ v1.2 — 03/10/2026)
Lý do: entry bất định cao chỉ có kỳ vọng dương khi điểm sai rõ ràng và
stop ngắn. Kiểm chứng 10 năm: thêm stop-loss → total +268.9%→+302.1%,
DD -44.5%→-41.5%, 2026 -4.5%→-3.1% (xem §14).
- Quyết định mỗi sáng thứ 7 trên **giá đóng cửa tuần (T6)**; khớp lệnh bán
  phiên thứ 2 kế tiếp (gặp sàn dời tối đa 2 phiên như §9).
- Chân bull: cắt khi đóng cửa T6 **dưới SMA50 ngày** HOẶC **lỗ -8%** từ giá
  vào — điều kiện nào tới trước.
- Chân bear: cắt khi đóng cửa T6 **thủng đáy spring** = đáy 26 tuần (MN26)
  tại tuần vào lệnh.
- Thứ tự ưu tiên khi thoát: stop-loss → đổi chiều regime → cầu chì → hết hạn.

Đã test và loại (03/10/2026, cùng dữ liệu/universe):
- Nới washout 10→3 phiên: cải thiện nhẹ, không decisive → **giữ nguyên 10 phiên**.
- Bỏ persist washout / combo stop+wash3: tệ hơn baseline → loại.
- Stop chỉ chân bull: total cao hơn (+322.1%) nhưng DD sâu hơn (-46.4%)
  và 2026 tệ hơn (-9.0%) → giữ stop cả hai chân.

## 8. Thoát sớm
Thị trường đổi chiều (UPTREND ↔ DOWNTREND) → đóng hết vị thế, chọn lại từ đầu.

## 9. Khớp lệnh (mô phỏng thực tế)
- Vào lệnh phiên thứ 2 sau tín hiệu, giá đóng cửa.
- Mã tăng trần (>+6.9% so với phiên trước) → bỏ qua, không mua đuổi.
- Bán gặp sàn (<-6.9%) → chờ tuần sau (tối đa 2 tuần rồi bán bằng được).

## 10. Phí
0.25% mỗi chiều + 0.1% thuế khi bán.

## 11. Sổ sách & đánh giá — PAPER TRADE ĐANG CHẠY (từ 30/09/2026)
- Engine: `market/paper_trade.py` — `--plan` / `--execute`. Vốn ảo 100tr VND,
  lô 100cp, phí/thuế như backtest. Sổ lệnh: `market/paper_ledger.json`.
  Từ v1.2 (03/10/2026): `--plan` kiểm tra stop-loss (§7) trên giá đóng cửa T6,
  lệnh cắt lỗ khớp thứ 2 như lệnh bán thường.
- Cron `paper-trade-plan`: thứ 7 ~08:20 giờ VN — báo cáo tuần (regime,
  B20/B50/B200, vị thế, lệnh chờ thứ 2).
- Cron `paper-trade-execute`: thứ 2 ~18:20 giờ VN — khớp giá đóng cửa thứ 2
  (trần bỏ qua mua, sàn dời bán tối đa 2 tuần), báo kết quả.
- Tuần lịch thực (Friday close) thay cách chia 5-phiên; backtest chuẩn
  `market/strategy_v12.py` dùng chung `signals.py` (calendar weeks) với
  paper-trade engine. Validate baseline v1.1 (universe screener 01/10):
  **+268.9%, DD -44.5%, 2026 -4.5%, 380 lệnh** (xem §14).
  (Số cũ +149.7% trong bản trước dùng universe LIQ cũ, đã thay.)
- Chấm điểm sau 6 tháng hoặc 50 lệnh đóng: đạt khi lãi ròng hơn mặt bằng chung
  và tỷ lệ thắng ≥ 45%.

## Những thứ đã loại (có bằng chứng)
Rotation quadrant RRG, sector rotation RRG, breakout Wyckoff, upthrust,
RRG daily, khung dưới 1 tuần, điểm giao cắt (RRG fresh cross, breadth cross,
B50/B200 cross làm tín hiệu mua/bán), B50>B200 làm công tắc.

## 12. Kết quả backtest v1.0 (ghi nhận 30/09/2026, chưa phải sửa đổi)
File: `market/strategy_backtest.py`, 12/2017–09/2026, 498 lệnh, đã trừ phí.
- Tổng +48.9% vs EQW buy&hold +0.9%; win rate 47%.
- Chân bull: +5.00%/lệnh (tốt). Chân bear: -1.13%/lệnh (KHÔNG đạt) —
  chỉ thắng ở năm crash-nảy (2020: +5.3%), thua nặng ở bear mài mòn
  (2022: -7.9%, 2026: -8.1%).
- Max drawdown -68.4% (11/2021 → 03/2024).
- 2026 YTD -21.0%.
Điểm yếu đã xác định: bắt đáy RSI<30/spring thua trong bear mài mòn.
Hướng sửa đang cân nhắc: chân bear chỉ mở khi có washout thật
(DN cross đã xác nhận hoặc B200<30 kèm spring), chưa backtest.

## 13. Backtest v1.1 (30/09/2026) — so sánh cửa cho chân bear
File: `market/strategy_v11.py` (khối 5 phiên — đã nghỉ hưu, thay bằng
`strategy_v12.py`). Bull leg giữ nguyên mọi bản.

| Cửa chân bear | Tổng | 2026 | MaxDD | Bear test |
|---|---|---|---|---|
| none (v1.0) | +48.9% | -21.0% | -68.4% | -3.11% (n=144) |
| w1: chỉ khi B200<30 | +50.7% | -10.2% | -73.2% | -4.70% (n=94) |
| **w2: chỉ trong 4w sau cắt xuống XN** | **+131.5%** | **-2.3%** | **-55.3%** | **+0.28% (n=66)** |
| w3: w1 hoặc w2 | +72.6% | -10.2% | -67.8% | -3.01% (n=112) |
| tắt hẳn chân bear | +119.2% | — | -58.0% | — |

Chốt w2. Lưu ý trung thực: bear test chỉ +0.28%/lệnh (nhỏ nhưng cùng dấu
train +1.08%); phần lớn +131.5% đến từ chân bull và việc ngồi cash qua bear
mài mòn. DD vẫn sâu (-55%). 2026: w2 chỉ đánh 10 lệnh (03/2026, sau cắt xuống
06/03), còn lại ngồi ngoài → -2.3% thay vì -21%.
> Ghi chú 05/10/2026 (chiều): bản so sánh này dùng W2 cũ có **lookahead**
> (xác nhận bằng 10 phiên tương lai) — xem §17. Kết luận w2 > các cửa khác
> vẫn đứng sau khi fix, nhưng con số chân bear đã đổi.

## 14. Backtest v1.2 (03/10/2026) — thêm stop-loss
File: `market/strategy_v12.py` (mode `baseline` | `stop` | `stopbull`),
12/2017–09/2026, tuần lịch Friday-close, universe screener 01/10, phí/thuế
như §10. Baseline tái lập đúng số validate (khớp `validate_cal.py` w2 đến
0.1pp) — backtest đã chuẩn.

| Bản | Tổng | MaxDD | 2026 | n lệnh | Win | TB/lệnh | Chân bear TB/lệnh |
|---|---|---|---|---|---|---|---|
| v1.1 baseline (không stop) | +268.9% | -44.5% | -4.5% | 380 | 54% | +4.55% | +4.92% (n=85) |
| **v1.2 stop cả 2 chân** | **+302.1%** | **-41.5%** | **-3.1%** | 611 | 44% | +3.00% | +2.14% (n=138) |
| stop chỉ chân bull (đã loại) | +322.1% | -46.4% | -9.0% | 547 | 47% | +3.52% | +4.92% (n=85) |

Train/test không đảo dấu — v1.2: train +5.99%/lệnh (bear +1.99%, n=29),
test +0.62%/lệnh (bear +2.18%, n=109); baseline: train +9.27%, test +0.07%.
Cơ chế: stop thoát ~58% lệnh (bull 356/554, bear 31/107 — số sau audit
§17) — cắt đuôi trái để nhường slot cho lệnh mới, tổng số lệnh tăng
nhưng DD nông hơn.
Bản stop-chỉ-bull total cao hơn nhưng DD sâu hơn và 2026 tệ hơn hẳn
(-9.0%) → chốt stop cả hai chân.

### Cập nhật 05/10/2026 — chạy lại sau khi vá sector mapping (§16)
Cùng code/mode `stop`, chỉ thay sector map (đủ 1.520 mã + aggregate
ngành từ mã thanh khoản từng tuần):

| Bản | Tổng | MaxDD | 2026 | n lệnh | Win | TB/lệnh |
|---|---|---|---|---|---|---|
| **v1.2 stop 2 chân** | **+844.4%** | **-39.7%** | **+4.1%** | 628 | 43% | +4.68% |

Chân bull: n=491, avg +5.94%/lệnh. Chân bear: n=137, avg +0.17%/lệnh
(train bear -2.47% n=31 — mẫu nhỏ; test bear +0.94% n=106). Train tổng
+9.34%/lệnh, test +0.81%/lệnh — cùng dấu, không đảo. DD nông hơn bản cũ
(-39.7% so với -41.5%) dù total cao gấp ~2.8 lần: đo momentum ngành trên
mã thanh khoản cho tín hiệu sạch hơn hẳn.

### Cập nhật 05/10/2026 (chiều) — chạy lại sau deep audit (§17)
Hai fix ảnh hưởng backtest: **W2 point-in-time** (bỏ lookahead: điểm cắt
chỉ "đã xác nhận" sau 10 phiên persist, cửa bear mở 20 phiên sau xác nhận)
và **trần/sàn theo sàn** (HOSE 6.9% / HNX 9.9% / UPCoM 14.9%, từ
`store/exchange_map.json` 1.515 mã — thay cho ±6.9% cào bằng):

| Bản | Tổng | MaxDD | 2026 | n lệnh | Win | TB/lệnh |
|---|---|---|---|---|---|---|
| **v1.2 stop 2 chân** | **+937.9%** | **-40.1%** | **-5.8%** | 661 | 41% | +4.75% |
| v1.1 baseline (không stop) | +111.4% | -54.1% | +2.5% | 434 | 47% | +3.06% |

v1.2: bull n=554 avg +5.36%; bear n=107 avg +1.59% (train bear +6.88%
n=20; test bear +0.37% n=87 — cùng dấu). Train tổng +8.18%/lệnh (n=331),
test +1.30%/lệnh (n=330). Band theo sàn gỡ 105 lần delay bán oan và hết
skip mua oan ở HNX/UPCoM → total tăng so với bản ±6.9% cào bằng (số cũ
conservative). Baseline không stop hưởng ít hơn từ fix này (+111.4%).

## 15. Backtest v1.2-INV (05/10/2026) — bản ngược: mua leaders khi v1.2 từ chối
File: `market/strategy_v12_inv.py`. Cùng tập candidates với chân bull
v1.2 (LEAD & topsec & LIQ, xếp theo Rw giảm dần — tức cùng những mã
"như DRI") nhưng vào lệnh khi **(regime BEAR) hoặc (cầu chì B200<30
bật)** — đúng lúc v1.2 đứng ngoài. Bỏ qua cầu chì cho chân này.
**KHÔNG dùng stop-loss** (quyết định 05/10/2026). Nắm tối đa 26 tuần,
không flip-exit (sweep 120 combo `market/sweep_inv_exits.py`: 107/120
lỗ; flip-exit bán đúng đáy chuyển giao là tệ nhất). Single-leg.

Số sau deep audit 05/10/2026 (chiều) — W2 point-in-time + trần/sàn theo sàn (§17):

| Bản | Tổng | MaxDD | 2026 | n lệnh | Win | TB/lệnh |
|---|---|---|---|---|---|---|
| **v1.2** | **+937.9%** | **-40.1%** | **-5.8%** | 661 | 41% | +4.75% |
| **v1.2-INV** | **+91.7%** | **-40.7%** | **-26.5%** | 115 | 48% | +8.35% |

INV: train +6.23%/lệnh (n=38), test +9.40%/lệnh (n=77) — cùng dấu nhưng
n nhỏ. Kết luận giữ nguyên qua mọi biến thể (cũ +302% vs +74%; map đủ
+844% vs +53%; sau audit +938% vs +92%): **v1.2 thắng INV áp đảo** —
bộ lọc regime + cầu chì có giá trị thật. Đu momentum khi thị trường yếu
chỉ lãi khiêm tốn và phải gồng 6 tháng xuyên nhịp hồi — R:R tệ.

## 16. Vá sector mapping 100% (05/10/2026) — vụ DRI
Phát hiện: từ điển ngành tay trong `compute_simplize.py` chỉ có ~278 mã;
**1.242/1.520 mã không thuộc ngành nào** → DRI (RS ratio 124.1, mạnh nhất
thị trường) rớt vòng lọc top-3 ngành dù đang Leading. Đã vá:
- Scrape `industryActivity` của 1.515/1.520 mã từ Simplize
  (`market/scrape_industry.sh` → `store/industry_raw.json`).
- `market/build_sector_map.py`: map 51 nhóm ngành → 13 ngành hệ thống;
  ưu tiên override tay đã review (25 mã: các cty cao su Simplize phân
  loại sai vào "Ô tô", DPR/GVR/PHR về Materials, mã mới LPS/KAI/PCB/GTX/
  V68) > list tay cũ > industry. Kết quả: **1.520/1.520 (100%)**,
  mỗi mã đúng 1 ngành → `store/sector_map.json`.
- `compute_simplize.py`: SECTORS build từ sector_map.json (không sửa tay
  nữa). `signals.py`: aggregate ngành = trung bình lợi suất tuần của mã
  **thanh khoản tại đúng tuần đó** (không peek; mã illiquid gây nhiễu đo
  momentum ngành). In `sector coverage: X/Y` mỗi lần build; **raise**
  ngay nếu còn mã unmapped (§17 cứng hoá).
- `refresh_universe.py`: mã mới hàng tháng tự fetch industry + rebuild
  sector map; fail LOUDLY nếu thiếu → gán tay OVERRIDES.
- Kiểm chứng A/B: aggregate toàn bộ members +277%/-53.8% (nhiễu);
  aggregate mã thanh khoản +844%/-39.7% (sạch, chốt). Kết quả v1.2 cũ
  (+302%) dùng map tay thiếu — số mới thay thế.

## 17. Deep audit 05/10/2026 (chiều) — 2 CRITICAL, 5 MAJOR, 13 MINOR
Audit 3 mũi độc lập (data / signals / backtest-paper), chỉ đọc. Hai điểm
đã biết được xác nhận (một nặng hơn mô tả cũ). Đã fix toàn bộ critical +
major trong ngày:

**C1 — corporate action:** không cron `--full` → vách giá giả nếu CA rơi
ngoài window 30 phiên của fetch incremental. Đã xác minh 5 mã nghi ngờ
(TPB/VOS/DHC/DGW/NVL) đều đã tự lành qua fetch thứ Sáu. Fix: cron mới
`market-data-weekly-full` (thứ 7 ~07:20, trước paper-plan) + `fetch_inc.py`
fsync trước replace, lọc NaN (`not (c > 0)`).
**C2 — W2 lookahead:** điểm cắt "xác nhận" bằng 10 phiên tương lai nhưng
backtest dùng ngay → 74% lệnh bear sai thời điểm, live không bao giờ thấy
tín hiệu đó. Fix: `signals.py` — điểm cắt chỉ visible sau s+10, cửa bear
mở 20 phiên sau xác nhận. Mọi số chân bear cũ phải bỏ.
**M1 — paper slot trừ 2 lần:** `10 - len(pos) - len(staged_ex)` → đúng là
`+ len(staged_ex)` (bán trước mua sau); sec_cnt trừ vị thế sắp bán. Paper
cũ bỏ lỡ hàng chục lượt mua/năm.
**M2 — trần/sàn ±6.9% cào bằng:** scrape `stockExchange` 1.515/1.520 mã
(`market/scrape_exchange.sh` → `store/exchange_map.json`: HOSE 411, HNX
297, UPCoM 807) → band theo sàn 6.9%/9.9%/14.9% (`S['band']`) ở cả 4 file
vào/ra. Số cũ conservative (105 lần delay bán oan, -1.67%/lệnh).
**M3:** `sma_mat` chịu NaN (≥80% phiên) — trước đây 1 phiên gap tắt stop
bull. **M4:** backfill chỉ skip mã `status=='ok'`. **M5:** xem C1.
Minor: cash paper không âm (trừ phí trước khi tính qty), xóa hàm chết
`stop_hit` trong INV, `refresh_universe.py` exit(1) khi build fail,
`signals.py` raise (không chỉ WARNING) khi unmapped, buildId scrape lấy
tươi từ HTML. Số sau fix: v1.2 **+937.9%**/DD -40.1%/2026 -5.8% (n=661);
v1.1 +111.4% (n=434); INV +91.7% (n=115).
