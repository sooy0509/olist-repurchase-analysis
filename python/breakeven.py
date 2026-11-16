# =====================================================================
# 쿠폰 손익분기 (추가 재구매 1건 기준)   → docs/06_business_case.md
#   입력: outputs/repurchase_30d.csv (40_repurchase_30d_amount.sql ①, 30일 재구매 344건)
#
# 손익분기 효과 = s × 할인액 ÷ (V × 수수료율 − 할인액)
#   s: 30일 재구매 중 100헤알 이상 주문 비중 (원래 재구매할 고객 중 쿠폰을 쓸 수 있는 비중)
#   V: 100헤알 이상 재구매 주문 금액 중앙값 (추가 재구매 1건의 주문 금액으로 가정)
#   비용 = 원래 재구매할 고객의 할인 + 추가 재구매 고객의 할인
#   수익 = 추가 재구매 주문의 수수료
# =====================================================================
import numpy as np
import pandas as pd

MIN_ORDER = 100     # 쿠폰 최소 주문 금액 (헤알)
EFFECT = 0.33       # 설계한 최소 효과

r = pd.read_csv('outputs/repurchase_30d.csv')
s = (r.amount >= MIN_ORDER).mean()
V = r.amount[r.amount >= MIN_ORDER].median()
print(f'30일 재구매 {len(r)}건, 50헤알 이상 {100*(r.amount >= 50).mean():.1f}% / '
      f'100헤알 이상 {100*s:.1f}% / 200헤알 이상 {100*(r.amount >= 200).mean():.1f}%')
print(f'100헤알 이상 주문 금액 중앙값 {V:.1f}헤알 ({(r.amount >= MIN_ORDER).sum()}건)')


def breakeven(discount, fee):
    """할인액(헤알)과 수수료율에서 손해가 없는 최소 쿠폰 효과 (fee=1이면 거래액 기준)"""
    return s * discount / (V * fee - discount)


def max_discount(effect, fee):
    """쿠폰 효과가 effect일 때 손해가 없는 최대 할인액"""
    return effect * V * fee / (s + effect)


# ---- 수수료율별 최대 할인액 (효과 33%) ----
for fee in (0.10, 0.15, 0.20):
    print(f'수수료 {fee:.0%}: 최대 할인액 {max_discount(EFFECT, fee):.1f}헤알')

# ---- 확대 판단 기준표 (수수료 15%) ----
table = pd.DataFrame({'discount': [4, 6, 8, 10]})
table['breakeven_fee15'] = (100 * breakeven(table.discount, 0.15)).round(1)
table['breakeven_gmv'] = (100 * breakeven(table.discount, 1.0)).round(2)
table['ratio'] = (table.breakeven_fee15 / table.breakeven_gmv).round(1)
print(table.to_string(index=False))

# ---- 그래프 데이터 (g14) ----
d = np.round(np.arange(0.5, 25.01, 0.5), 1)
curve = pd.DataFrame({'discount': d,
                      'fee10': 100 * breakeven(d, 0.10),
                      'fee15': 100 * breakeven(d, 0.15),
                      'fee20': 100 * breakeven(d, 0.20),
                      'gmv': 100 * breakeven(d, 1.0)})
val = curve.columns[1:]
curve[val] = curve[val].where((curve[val] > 0) & (curve[val] <= 100)).round(2)   # 100% 초과·분모 음수 구간 제외
curve.to_csv('chart_data/11_breakeven.csv', index=False)
