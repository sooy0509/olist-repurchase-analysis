-- =====================================================================
-- 40. 쿠폰 사업성: 30일 재구매 주문 금액   → docs/06_business_case.md
--   대상: 32_ab_simulation_58071.sql 과 같은 남동부 첫 구매 고객 58,071명
--   재구매 주문: 첫 주문 배송 완료 후 30일 안의 첫 재구매 (첫 주문과 같은 날 주문 제외)
--   주문 금액 = 상품 가격 합계 (배송비 제외)
-- =====================================================================
USE olist;

-- ---------------------------------------------------------------------
-- ① 30일 재구매 주문과 금액
--   저장: outputs/repurchase_30d.csv → python/breakeven.py 입력
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS repurchase_30d;
CREATE TABLE repurchase_30d AS
WITH v AS (
  SELECT c.customer_unique_id,
         c.customer_state,
         o.order_id,
         o.order_status,
         o.order_purchase_timestamp       AS t,
         o.order_delivered_carrier_date   AS carrier,
         o.order_delivered_customer_date  AS delivered,
         ROW_NUMBER() OVER (PARTITION BY c.customer_unique_id
                            ORDER BY o.order_purchase_timestamp, o.order_id) AS rn
  FROM orders o
  JOIN customers c ON c.customer_id = o.customer_id
  WHERE o.order_status NOT IN ('canceled', 'unavailable')
),
first_order AS (
  SELECT *
  FROM v
  WHERE rn = 1
    AND t >= '2017-01-01'
    AND delivered + INTERVAL 30 DAY <= '2018-08-31'
    AND order_status = 'delivered'
    AND carrier IS NOT NULL
    AND delivered IS NOT NULL
    AND delivered >= carrier
    AND customer_state IN ('SP', 'RJ', 'MG', 'ES')
),
rep AS (                                      -- 첫 주문과 다른 날 주문 중 가장 이른 주문
  SELECT f.customer_unique_id,
         f.delivered,
         w.order_id,
         w.t,
         ROW_NUMBER() OVER (PARTITION BY f.customer_unique_id ORDER BY w.t, w.order_id) AS k
  FROM first_order f
  JOIN v w
    ON w.customer_unique_id = f.customer_unique_id
   AND w.rn > 1
   AND DATE(w.t) > DATE(f.t)
)
SELECT r.customer_unique_id,
       r.order_id,
       SUM(i.price) AS amount
FROM rep r
JOIN order_items i ON i.order_id = r.order_id
WHERE r.k = 1
  AND r.t >= r.delivered
  AND r.t <  r.delivered + INTERVAL 30 DAY
GROUP BY r.customer_unique_id, r.order_id;

SELECT * FROM repurchase_30d;
-- [결과] 344건 (32_ab_simulation_58071.sql 의 30일 재구매 344명과 같음)


-- ---------------------------------------------------------------------
-- ② 쿠폰 최소 주문 금액별 사용 가능 비중
--   원래 재구매할 고객 중 쿠폰을 쓸 수 있는 비중 = 할인 비용이 생기는 비중
-- ---------------------------------------------------------------------
SELECT COUNT(*)                          AS n_rep30,
       ROUND(100 * AVG(amount >= 50), 1)  AS over50_pct,
       ROUND(100 * AVG(amount >= 100), 1) AS over100_pct,
       ROUND(100 * AVG(amount >= 200), 1) AS over200_pct
FROM repurchase_30d;
-- [결과] 344 / 67.2% / 40.1% / 13.1%
-- [결정] 쿠폰 조건 100헤알 이상


-- ---------------------------------------------------------------------
-- ③ 100헤알 이상 재구매 주문 금액 중앙값 (138건, 짝수 → 가운데 두 값의 평균)
-- ---------------------------------------------------------------------
WITH r AS (
  SELECT amount,
         ROW_NUMBER() OVER (ORDER BY amount) AS rn,
         COUNT(*)     OVER ()                AS n
  FROM repurchase_30d
  WHERE amount >= 100
)
SELECT MAX(n) AS n_over100,
       ROUND(AVG(CASE WHEN rn IN (FLOOR((n + 1) / 2), CEIL((n + 1) / 2)) THEN amount END), 1) AS median_amount
FROM r;
-- [결과] 138건 / 159.9헤알
