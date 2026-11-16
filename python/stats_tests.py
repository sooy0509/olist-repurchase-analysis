# =====================================================================
# p값 계산   → docs/04_repurchase.md
#   입력: outputs/first_orders_for_test.csv (13_repurchase.sql ⑩ 결과, 첫 구매 고객 55,227명)
# =====================================================================
import warnings
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

warnings.filterwarnings('ignore')
d = pd.read_csv('outputs/first_orders_for_test.csv')
k = d[d.in_cohort180 == 1].copy()          # cohort180 (55,209명)


def chi2_p(a, b, data):
    """교차표 카이제곱 검정 p값 (연속성 보정 없음)"""
    return stats.chi2_contingency(pd.crosstab(data[a], data[b]), correction=False).pvalue


# ---- 배송 경험·리뷰와 재구매 ----------------------------------------------------
# 예상일 지연 여부 × 재구매: 제때 2.02% vs 늦게 1.61%
print('지연 여부 × 재구매        p =', round(chi2_p('is_late', 'rep180', d), 3))            # 0.083

# 출고→배송 기간 5구간 × 재구매: 구간 순서를 숫자(0~4)로 놓고 추세 검정(로지스틱 회귀)
k['transit_band'] = pd.cut(k.transit_days, [-1, 3, 7, 14, 21, 9999], labels=False)
m = smf.logit('rep180 ~ transit_band', k).fit(disp=0)
print('배송 기간 추세            p =', round(m.pvalues['transit_band'], 4))                 # 0.0002

# 권역 × 재구매
print('권역 × 재구매             p =', round(chi2_p('region', 'rep180', k), 4))             # 0.0007 (유의)

# 첫 주문 리뷰 1~2점 vs 4~5점
r = d[d.first_review.notna()].copy()
r['review_grp'] = np.where(r.first_review <= 2, '1~2점', np.where(r.first_review < 4, '3점', '4~5점'))
r2 = r[r.review_grp != '3점']
print('리뷰 1~2점 vs 4~5점       p =', round(chi2_p('review_grp', 'rep180', r2), 3))        # 0.031

# 지연 고객 vs 제때 고객 재구매 (쿠폰 전략 3 근거)는 위 '지연 여부 × 재구매'와 같은 검정

# ---- 재구매 시점·금액·배송비 ----------------------------------------------------
# 재구매 시점(경과일)이 권역마다 다른가: 재구매 고객 1,102명, 크루스칼-월리스 검정
rep = k[k.rep180 == 1]
print('재구매 시점 권역 차이     p =',
      round(stats.kruskal(*[g.gap_days for _, g in rep.groupby('region')]).pvalue, 2))   # 0.70

# 첫 구매 금액 5구간 × 재구매
k['value_band'] = pd.cut(k.first_gmv, [0, 50, 100, 200, 500, 1e9], right=False)
print('첫 구매 금액 × 재구매     p =', round(chi2_p('value_band', 'rep180', k), 2))         # 0.24

# 배송비·상품 금액·권역·배송 기간을 함께 넣은 로지스틱 회귀 → 배송 기간의 p값
#   (배송비, 상품 금액은 치우친 분포라 로그를 씌움)
m = smf.logit('rep180 ~ np.log1p(first_freight) + np.log(first_gmv) + C(region) + transit_days', k).fit(disp=0)
print('배송 기간 (다른 요인 통제) p =', round(m.pvalues['transit_days'], 4))               # 0.0006
print(pd.DataFrame({'coef': m.params, 'p': m.pvalues}).round(4))
#   배송 기간 계수는 음수(길수록 재구매↓), 배송비 계수는 양수(배송비가 높아도 재구매가 낮아지지 않음)
#   → "재구매율을 낮추는 요인은 배송비가 아니라 배송 기간"
#   ※ 변수 형태(로그 여부 등)를 바꾸면 배송비의 p값은 0.002~0.07로 달라지지만, 배송 기간은 계속 유의

# ---- 쿠폰 전략 3 근거 ----------------------------------------------
# 예상일 안에 온 고객: 배송 기간이 길어도 재구매가 낮은가 (배송비 비중·권역 통제)
on = k[k.is_late == 0].copy()
on['freight_share'] = on.first_freight / (on.first_gmv + on.first_freight)
m = smf.logit('rep180 ~ freight_share + C(region) + transit_days', on).fit(disp=0)
print('제때 도착 고객의 배송 기간 p =', round(m.pvalues['transit_days'], 2))               # 0.15
#   → 유의하지 않음: 제때 온 고객은 배송이 오래 걸려도 재구매가 크게 낮지 않음
