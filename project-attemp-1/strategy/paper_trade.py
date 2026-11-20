#!/usr/bin/env python3
"""Paper-trade engine for STRATEGY v1.2 (calendar weeks).

  --plan     Saturday: fetch data, signals on last COMPLETE week (Friday),
             stage exits/entries, print weekly report (Vietnamese).
             Exits include v1.2 stop-loss: trigger on Friday close,
             filled at Monday close like other exits.
  --execute  Monday ~18:30: fetch data, fill staged orders at Monday close
             (trần: skip entry; sàn: delay exit up to 2 weeks).

Ledger: paper_ledger.json (default). Paper cash start: 100,000,000 VND.
"""
import numpy as np
import sys, json, os, subprocess
from datetime import datetime, timezone, timedelta
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LEDGER = os.path.join(os.getcwd(), 'paper_ledger.json')
START_CASH = 100_000_000.0
FEE, TAX = 0.0025, 0.001
VN = timezone(timedelta(hours=7))


def vn_today():
    return datetime.now(VN).strftime('%Y-%m-%d')


def fetch():
    fp = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      'fetch_inc.py')
    if not os.path.exists(fp):
        print('fetch_inc.py not bundled in this repo — skipping data '
              'refresh, using the local store as-is.')
        return
    try:
        r = subprocess.run([sys.executable, fp],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            print('FETCH FAILED (continuing with local store):',
                  r.stderr[-500:])
    except Exception as e:
        print('fetch skipped:', e)


def load_ledger(path):
    if os.path.exists(path):
        return json.load(open(path))
    return {'cash': START_CASH, 'positions': [], 'staged_exits': [],
            'staged_entries': [], 'pending_exits': [], 'history': [],
            'meta': {'strategy': 'v1.1', 'started': vn_today(),
                     'start_cash': START_CASH}}


def save_ledger(path, L):
    tmp = path + '.tmp'
    json.dump(L, open(tmp, 'w'), ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def last_complete_week(S):
    """Latest week whose Friday has passed (drop trailing partial week)."""
    today = vn_today()
    j = S['n_w'] - 1
    while j > 0 and S['dates_w'][j] >= today:
        j -= 1
    # drop partial week (week_end not a Friday)
    while j > 0:
        dt = datetime.strptime(S['dates_w'][j], '%Y-%m-%d')
        if dt.weekday() == 4:  # Friday
            break
        j -= 1
    return j


def fmt_vnd(x):
    return f'{x/1e6:.1f}tr'


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--plan', action='store_true')
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--ledger', default=LEDGER)
    args = ap.parse_args()
    assert args.plan != args.execute, 'choose --plan or --execute'

    fetch()
    import signals as SG
    import backtest_rrg as B
    from backtest_rrg import C, tickers, t2i, n_s
    S = SG.build()
    we = S['week_ends']
    j = last_complete_week(S)
    wlabel = S['dates_w'][j]
    bull = bool(S['bullw'][j])
    b200 = float(S['B200w'][j]) if np.isfinite(S['B200w'][j]) else float('nan')
    fuse = b200 < 30
    w2 = bool(S['W2w'][j])
    L = load_ledger(args.ledger)
    L['meta']['strategy'] = 'v1.2'

    # ---- v1.2 stop-loss inputs (trigger trên giá đóng cửa T6) ----
    S50d = SG.sma_mat(C, 50)
    WC = B.WC                      # weekly closes (calendar weeks)
    MN26 = SG.roll(WC, 26, np.nanmin)  # đáy 26 tuần

    def stop_triggered(p, ti):
        f = we[j]  # phiên cuối tuần = thứ 6
        if p['regime'] == 'bull':
            c = C[ti, f]
            s50 = S50d[ti, f]
            if np.isfinite(c) and np.isfinite(s50) and c < s50:
                return True
            if np.isfinite(c) and c / p['px_in'] - 1 <= -0.08:
                return True
            return False
        wj = p.get('week_j')
        if wj is None or wj >= len(S['dates_w']):
            return False
        sl = MN26[ti, wj]
        wc = WC[ti, j]
        return bool(np.isfinite(sl) and np.isfinite(wc) and wc < sl)

    if args.plan:
        # ---- exits ----
        staged_ex, staged_en = [], []
        for p in L['positions']:
            ti = t2i[p['ticker']]
            held_w = j - p['week_j']
            maxh = 12 if p['regime'] == 'bull' else 8
            flip = bull != (p['regime'] == 'bull')
            fuse_hit = p['regime'] == 'bull' and fuse
            # thứ tự ưu tiên: stop-loss → đổi chiều → cầu chì → hết hạn
            if stop_triggered(p, ti):
                reason = 'cắt lỗ'
            elif flip:
                reason = 'đổi chiều'
            elif fuse_hit:
                reason = 'cầu chì'
            elif held_w >= maxh:
                reason = 'hết hạn'
            else:
                continue
            staged_ex.append({'ticker': p['ticker'], 'reason': reason})
        # ---- entries ----
        held = set(p['ticker'] for p in L['positions'])
        sec_cnt = {}
        for p in L['positions']:
            sec_cnt[p['sec']] = sec_cnt.get(p['sec'], 0) + 1
        cands = []
        if bull and not fuse:
            idx = [i for i in np.where(
                S['LEAD'][:, j] & S['topsec'][:, j] & S['LIQw'][:, j])[0]
                if tickers[i] not in held]
            idx.sort(key=lambda i: -S['Rw'][i, j])
            cands = [('bull', i) for i in idx]
        elif not bull and w2:
            idx_s = [i for i in np.where(
                S['SPRING'][:, j] & S['LIQw'][:, j])[0]
                if tickers[i] not in held]
            idx_r = [i for i in np.where(
                (S['RSIw'][:, j] < 30) & S['LIQw'][:, j]
                & ~S['SPRING'][:, j])[0] if tickers[i] not in held]
            idx_r.sort(key=lambda i: S['RSIw'][i, j])
            cands = [('bear', i) for i in idx_s + idx_r]
        # FIX 05/10/2026 (audit M1): mọi staged_ex đều từ positions, execute
        # bán trước mua sau → slot đúng = 10 - len(positions) + len(staged_ex)
        # (công thức cũ trừ 2 lần, bỏ lỡ lệnh mua). sec_cnt trừ vị thế sắp bán
        # vì slot ngành được giải phóng trong cùng phiên khớp.
        sell_set = set(e['ticker'] for e in staged_ex)
        slots = 10 - len(L['positions']) + len(staged_ex)
        sec_cnt = {}
        for p in L['positions']:
            if p['ticker'] not in sell_set:
                sec_cnt[p['sec']] = sec_cnt.get(p['sec'], 0) + 1
        for regime, ti in cands:
            if slots <= 0:
                break
            sec = int(S['stk_sec'][ti])
            if sec_cnt.get(sec, 0) >= 3:
                continue
            t = tickers[ti]
            if t in [e['ticker'] for e in staged_en]:
                continue
            staged_en.append({'ticker': t, 'regime': regime,
                              'sec': sec,
                              'sec_name': S['sec_names'][sec]
                              if sec >= 0 else ''})
            sec_cnt[sec] = sec_cnt.get(sec, 0) + 1
            slots -= 1
        L['staged_exits'] = staged_ex
        L['staged_entries'] = staged_en
        L['plan_week'] = wlabel
        L['plan_j'] = int(j)
        save_ledger(args.ledger, L)

        # ---- report ----
        px = C[:, we[j]]
        mkt = sum(p['qty'] * px[t2i[p['ticker']]]
                  for p in L['positions']
                  if np.isfinite(px[t2i[p['ticker']]]))
        equity = L['cash'] + mkt
        start = L['meta']['start_cash']
        print(f'📊 BÁO CÁO TUẦN — tuần kết thúc {wlabel}')
        print(f"Thị trường: {'UPTREND' if bull else 'DOWNTREND'} | "
              f"B200: {b200:.1f}%"
              f"{' ⛔ CẦU CHÌ BẬT' if fuse else ''} | "
              f"Washout gần: {'CÓ' if w2 else 'không'} | "
              f"B20/B50/B200: {S['B20w'][j]:.0f}/{S['B50w'][j]:.0f}/{b200:.0f}%")
        print(f'Tiền mặt: {fmt_vnd(L["cash"])} | Cổ phiếu: '
              f'{fmt_vnd(mkt)} | Tổng: {fmt_vnd(equity)} '
              f'({equity/start-1:+.1%} từ đầu)')
        if L['positions']:
            print('Vị thế đang giữ:')
            for p in L['positions']:
                ti = t2i[p['ticker']]
                last = px[ti]
                pnl = (last / p['px_in'] - 1) * 100 \
                    if np.isfinite(last) else float('nan')
                print(f"  {p['ticker']:6s} {p['qty']:5d}cp "
                      f"mua {p['px_in']:,.0f} ({p['date_in']}) "
                      f"→ {last:,.0f} {pnl:+.1f}% [{p['regime']}]")
        else:
            print('Vị thế đang giữ: (trống)')
        if staged_ex:
            print('Chờ bán thứ 2:',
                  ', '.join(f"{e['ticker']} ({e['reason']})"
                            for e in staged_ex))
        if staged_en:
            print('Chờ mua thứ 2:',
                  ', '.join(f"{e['ticker']} [{e['regime']}]"
                            for e in staged_en))
        if not staged_ex and not staged_en:
            print('Thứ 2 tới: không có lệnh mới.')
        h = L['history']
        if h:
            r = np.array([t['ret_pct'] for t in h])
            print(f'Thống kê: {len(h)} lệnh đóng, thắng '
                  f'{(r > 0).mean():.0%}, TB {r.mean():+.2f}%/lệnh')
        return

    # ---- execute ----
    if 'plan_j' not in L:
        print('Chưa có kế hoạch thứ 7 — bỏ qua.')
        return
    e = we[L['plan_j']] + 1
    if e >= n_s or not np.isfinite(B.dates[e]):
        print('⚠️ Chưa có dữ liệu phiên thứ 2 sau tuần '
              f"{L['plan_week']} — giữ nguyên kế hoạch, thử lại sau.")
        return
    exd = datetime.fromtimestamp(B.dates[e], timezone.utc).strftime('%Y-%m-%d')
    # exits: staged + pending (sàn-delay)
    exits = ([{'ticker': x['ticker'], 'deadline': 2}
             for x in L['staged_exits']]
             + L.get('pending_exits', []))
    L['staged_exits'] = []
    still_pending = []
    for x in exits:
        t = x['ticker']
        p = next((p for p in L['positions'] if p['ticker'] == t), None)
        if p is None:
            continue
        ti = t2i[t]
        if not (np.isfinite(C[ti, e]) and np.isfinite(C[ti, e - 1])):
            still_pending.append(x)
            continue
        # Ngưỡng sàn theo sàn niêm yết (fix audit M2 05/10/2026).
        if C[ti, e] / C[ti, e - 1] - 1 < -S['band'][ti] and x['deadline'] > 0:
            x['deadline'] -= 1
            still_pending.append(x)
            print(f'  {t}: sàn, dời bán sang tuần sau')
            continue
        px = C[ti, e]
        proceeds = p['qty'] * px * (1 - FEE - TAX)
        L['cash'] += proceeds
        ret = px / p['px_in'] * (1 - FEE - TAX) / (1 + FEE) - 1
        L['history'].append({'ticker': t, 'date_in': p['date_in'],
                             'date_out': exd, 'px_in': p['px_in'],
                             'px_out': round(float(px), 1),
                             'ret_pct': round(float(ret) * 100, 2),
                             'regime': p['regime']})
        L['positions'].remove(p)
        print(f'  BÁN {t} {p["qty"]}cp @ {px:,.0f} → '
              f'{ret*100:+.2f}%')
    L['pending_exits'] = still_pending
    # entries
    px_fri = C[:, we[L['plan_j']]]
    mkt = sum(p['qty'] * px_fri[t2i[p['ticker']]] for p in L['positions'])
    equity = L['cash'] + mkt
    for en in L['staged_entries']:
        if len(L['positions']) >= 10:
            break
        t = en['ticker']
        ti = t2i[t]
        if any(p['ticker'] == t for p in L['positions']):
            continue
        if not (np.isfinite(C[ti, e]) and np.isfinite(C[ti, e - 1])):
            print(f'  {t}: không có giá, bỏ qua')
            continue
        if C[ti, e] / C[ti, e - 1] - 1 > S['band'][ti]:
            print(f'  {t}: trần, không mua đuổi')
            continue
        alloc = min(equity / 10, L['cash'])
        # FIX 05/10/2026 (audit C3): trừ phí trước khi tính qty — nếu không
        # cost = qty*px*(1+FEE) có thể vượt cash một chút, phá invariant cash>=0.
        qty = int(alloc / (C[ti, e] * (1 + FEE)) // 100 * 100)
        if qty < 100:
            print(f'  {t}: không đủ tiền lẻ 100cp, bỏ qua')
            continue
        cost = qty * C[ti, e] * (1 + FEE)
        L['cash'] -= cost
        L['positions'].append({
            'ticker': t, 'qty': qty, 'px_in': round(float(C[ti, e]), 1),
            'date_in': exd, 'week_j': int(L['plan_j']),
            'regime': en['regime'], 'sec': en['sec']})
        print(f"  MUA {t} {qty}cp @ {C[ti, e]:,.0f} [{en['regime']}]")
    L['staged_entries'] = []
    save_ledger(args.ledger, L)
    mkt = sum(p['qty'] * C[t2i[p['ticker']], e] for p in L['positions'])
    print(f"Xong phiên {exd}. Tiền mặt {fmt_vnd(L['cash'])}, "
          f"tổng {fmt_vnd(L['cash']+mkt)}.")


if __name__ == '__main__':
    main()
