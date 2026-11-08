-- =====================================================================
-- BazaarLink capstone | 03_analysis.sql
-- 22 queries answering business questions Q1-Q7, Q8-Q9 (SQL view of the
-- statistics), Q11-Q13, plus profiling and KPI reconciliation.
--
-- KPI rules (BRD section 7) used in every query:
--   * Revenue      = SUM(order_items.price), delivered orders only (no freight)
--   * Delivery KPIs = order_status = 'delivered' AND delivered date NOT NULL
--   * On time      = DATEDIFF(delivered date, estimated date) <= 0
--   * Delay days   = DATEDIFF(delivered date, estimated date), + = late
--   * Customers    = customer_unique_id (never customer_id)
--   * order_items is aggregated to order level BEFORE joining to other tables
--   * Trend window = Jan 2017 - Aug 2018 (complete months only)
--
-- Each query starts with a line "-- @query <ID> | <question> | <title>".
-- run_sql.py uses these lines to save every result to 04_sql/results/<ID>.csv
-- =====================================================================
USE bazaarlink;

-- @query SQL-00 | Profiling | Order status values and counts (DISTINCT)
SELECT DISTINCT order_status,
       COUNT(*) OVER (PARTITION BY order_status) AS orders
FROM orders
ORDER BY orders DESC;

-- @query SQL-01 | Q1 | Monthly orders, revenue, AOV and 3-month rolling revenue
SELECT purchase_month,
       orders,
       delivered_orders,
       revenue,
       ROUND(revenue / NULLIF(delivered_orders, 0), 2)                                  AS aov,
       ROUND(AVG(revenue) OVER (ORDER BY purchase_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2)
                                                                                        AS revenue_3m_rolling_avg
FROM (
    SELECT DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m')                              AS purchase_month,
           COUNT(*)                                                                      AS orders,
           SUM(CASE WHEN o.order_status = 'delivered' THEN 1 ELSE 0 END)                 AS delivered_orders,
           ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN COALESCE(oi.revenue, 0) ELSE 0 END), 2) AS revenue
    FROM orders o
    LEFT JOIN (SELECT order_id, SUM(price) AS revenue
               FROM order_items GROUP BY order_id) oi ON oi.order_id = o.order_id
    WHERE o.order_purchase_timestamp >= '2017-01-01'
      AND o.order_purchase_timestamp <  '2018-09-01'
    GROUP BY DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m')
) m
ORDER BY purchase_month;

-- @query SQL-01b | Q1 | Top 5 days by orders (peak event check)
SELECT DATE(order_purchase_timestamp) AS purchase_day,
       DAYNAME(order_purchase_timestamp) AS weekday,
       COUNT(*)                         AS orders
FROM orders
GROUP BY DATE(order_purchase_timestamp), DAYNAME(order_purchase_timestamp)
ORDER BY orders DESC
LIMIT 5;

-- @query SQL-02 | Q2 | Top 15 product categories by revenue (3-table INNER JOIN)
SELECT p.product_category_english       AS category,
       COUNT(DISTINCT oi.order_id)      AS orders,
       ROUND(SUM(oi.price), 2)          AS revenue,
       ROUND(SUM(oi.freight_value), 2)  AS freight
FROM order_items oi
INNER JOIN orders   o ON o.order_id   = oi.order_id
INNER JOIN products p ON p.product_id = oi.product_id
WHERE o.order_status = 'delivered'
GROUP BY p.product_category_english
ORDER BY revenue DESC
LIMIT 15;

-- @query SQL-03 | Q2 | Revenue by customer state with share of total (scalar subquery)
SELECT c.customer_state,
       COUNT(*)                                   AS delivered_orders,
       ROUND(SUM(oi.revenue), 2)                  AS revenue,
       ROUND(SUM(oi.revenue) / COUNT(*), 2)       AS aov,
       ROUND(100 * SUM(oi.revenue) /
             (SELECT SUM(i.price)
              FROM order_items i
              INNER JOIN orders o2 ON o2.order_id = i.order_id
              WHERE o2.order_status = 'delivered'), 2) AS pct_of_revenue
FROM orders o
INNER JOIN customers c ON c.customer_id = o.customer_id
INNER JOIN (SELECT order_id, SUM(price) AS revenue
            FROM order_items GROUP BY order_id) oi ON oi.order_id = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY revenue DESC;

-- @query SQL-04 | Q3 | AOV by main payment type (largest payment line per order)
WITH main_pay AS (
    SELECT order_id, payment_type,
           ROW_NUMBER() OVER (PARTITION BY order_id
                              ORDER BY payment_value DESC, payment_sequential) AS rn
    FROM payments
),
rev AS (
    SELECT order_id, SUM(price) AS revenue FROM order_items GROUP BY order_id
)
SELECT mp.payment_type,
       COUNT(*)                            AS delivered_orders,
       ROUND(SUM(r.revenue), 2)            AS revenue,
       ROUND(SUM(r.revenue) / COUNT(*), 2) AS aov
FROM orders o
INNER JOIN main_pay mp ON mp.order_id = o.order_id AND mp.rn = 1
INNER JOIN rev r       ON r.order_id  = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY mp.payment_type
ORDER BY revenue DESC;

-- @query SQL-04b | Q3 | AOV and cancellation rate by number of instalments (CASE bands)
WITH inst AS (
    SELECT order_id, MAX(payment_installments) AS max_installments
    FROM payments GROUP BY order_id
),
rev AS (
    SELECT order_id, SUM(price) AS revenue FROM order_items GROUP BY order_id
)
SELECT CASE WHEN i.max_installments <= 1 THEN '1 (single)'
            WHEN i.max_installments <= 3 THEN '2-3'
            WHEN i.max_installments <= 6 THEN '4-6'
            ELSE '7+' END                                                       AS instalment_band,
       COUNT(*)                                                                 AS orders,
       SUM(CASE WHEN o.order_status = 'delivered' THEN 1 ELSE 0 END)            AS delivered_orders,
       ROUND(SUM(CASE WHEN o.order_status = 'delivered' THEN r.revenue ELSE 0 END)
             / NULLIF(SUM(CASE WHEN o.order_status = 'delivered' THEN 1 ELSE 0 END), 0), 2) AS aov,
       ROUND(100 * AVG(CASE WHEN o.order_status IN ('canceled', 'unavailable') THEN 1 ELSE 0 END), 2)
                                                                                AS cancellation_pct
FROM orders o
INNER JOIN inst i ON i.order_id = o.order_id
LEFT JOIN  rev r  ON r.order_id = o.order_id
GROUP BY instalment_band
ORDER BY instalment_band;

-- @query SQL-05 | Q4 | On-time delivery rate by month (CASE late / on time)
SELECT DATE_FORMAT(order_purchase_timestamp, '%Y-%m')                               AS purchase_month,
       COUNT(*)                                                                      AS delivered_orders,
       SUM(CASE WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) <= 0
                THEN 1 ELSE 0 END)                                                   AS on_time_orders,
       SUM(CASE WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) > 0
                THEN 1 ELSE 0 END)                                                   AS late_orders,
       ROUND(100 * AVG(CASE WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) <= 0
                            THEN 1 ELSE 0 END), 2)                                   AS on_time_pct
FROM orders
WHERE order_status = 'delivered'
  AND order_delivered_customer_date IS NOT NULL
  AND order_purchase_timestamp >= '2017-01-01'
  AND order_purchase_timestamp <  '2018-09-01'
GROUP BY DATE_FORMAT(order_purchase_timestamp, '%Y-%m')
ORDER BY purchase_month;

-- @query SQL-06 | Q5 | Delivery time and late rate by customer state (GROUP BY ... HAVING)
SELECT c.customer_state,
       COUNT(*)                                                                         AS delivered_orders,
       ROUND(AVG(TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date)) / 86400, 2)
                                                                                        AS avg_delivery_days,
       ROUND(AVG(DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date)), 2) AS avg_delay_days,
       ROUND(100 * AVG(CASE WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) > 0
                            THEN 1 ELSE 0 END), 2)                                      AS late_pct
FROM orders o
INNER JOIN customers c ON c.customer_id = o.customer_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY c.customer_state
HAVING COUNT(*) >= 30
ORDER BY late_pct DESC;

-- @query SQL-07 | Q5 | Delivery time, handover and late rate by seller state
WITH order_seller_state AS (
    SELECT DISTINCT oi.order_id, s.seller_state
    FROM order_items oi
    INNER JOIN sellers s ON s.seller_id = oi.seller_id
)
SELECT oss.seller_state,
       COUNT(*)                                                                         AS delivered_orders,
       ROUND(AVG(TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date)) / 86400, 2)
                                                                                        AS avg_delivery_days,
       ROUND(AVG(CASE WHEN o.order_delivered_carrier_date >= o.order_approved_at
                      THEN TIMESTAMPDIFF(SECOND, o.order_approved_at, o.order_delivered_carrier_date) END) / 86400, 2)
                                                                                        AS avg_seller_handover_days,
       ROUND(100 * AVG(CASE WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) > 0
                            THEN 1 ELSE 0 END), 2)                                      AS late_pct
FROM order_seller_state oss
INNER JOIN orders o ON o.order_id = oss.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY oss.seller_state
HAVING COUNT(*) >= 30
ORDER BY late_pct DESC;

-- @query SQL-07b | Q5 | Top 15 categories by late rate (3-table join, categories with 300+ orders)
WITH order_category AS (
    SELECT DISTINCT oi.order_id, p.product_category_english AS category
    FROM order_items oi
    INNER JOIN products p ON p.product_id = oi.product_id
)
SELECT oc.category,
       COUNT(*)                                                                         AS delivered_orders,
       ROUND(AVG(TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date)) / 86400, 2)
                                                                                        AS avg_delivery_days,
       ROUND(100 * AVG(CASE WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) > 0
                            THEN 1 ELSE 0 END), 2)                                      AS late_pct
FROM order_category oc
INNER JOIN orders o ON o.order_id = oc.order_id
WHERE o.order_status = 'delivered'
  AND o.order_delivered_customer_date IS NOT NULL
GROUP BY oc.category
HAVING COUNT(*) >= 300
ORDER BY late_pct DESC
LIMIT 15;

-- @query SQL-08 | Q6 | Where time is lost: average days per journey stage, overall and by customer state
-- Stage days are blank when timestamps are in an impossible order (data quality log DQ-17, DQ-18).
SELECT customer_state,
       delivered_orders,
       approval_days,
       seller_handover_days,
       carrier_days,
       total_delivery_days
FROM (
    SELECT 'ALL STATES' AS customer_state, 0 AS sort_key, COUNT(*) AS delivered_orders,
           ROUND(AVG(TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_approved_at)) / 86400, 2) AS approval_days,
           ROUND(AVG(CASE WHEN o.order_delivered_carrier_date >= o.order_approved_at
                          THEN TIMESTAMPDIFF(SECOND, o.order_approved_at, o.order_delivered_carrier_date) END) / 86400, 2)
                                                                                         AS seller_handover_days,
           ROUND(AVG(CASE WHEN o.order_delivered_customer_date >= o.order_delivered_carrier_date
                          THEN TIMESTAMPDIFF(SECOND, o.order_delivered_carrier_date, o.order_delivered_customer_date) END) / 86400, 2)
                                                                                         AS carrier_days,
           ROUND(AVG(TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date)) / 86400, 2)
                                                                                         AS total_delivery_days
    FROM orders o
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
    UNION ALL
    SELECT c.customer_state, 1, COUNT(*),
           ROUND(AVG(TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_approved_at)) / 86400, 2),
           ROUND(AVG(CASE WHEN o.order_delivered_carrier_date >= o.order_approved_at
                          THEN TIMESTAMPDIFF(SECOND, o.order_approved_at, o.order_delivered_carrier_date) END) / 86400, 2),
           ROUND(AVG(CASE WHEN o.order_delivered_customer_date >= o.order_delivered_carrier_date
                          THEN TIMESTAMPDIFF(SECOND, o.order_delivered_carrier_date, o.order_delivered_customer_date) END) / 86400, 2),
           ROUND(AVG(TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date)) / 86400, 2)
    FROM orders o
    INNER JOIN customers c ON c.customer_id = o.customer_id
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
    GROUP BY c.customer_state
) stages
ORDER BY sort_key, total_delivery_days DESC;

-- @query SQL-09 | Q7 | Distribution of days early / late versus the estimated date
SELECT CASE WHEN delay_days <= -15 THEN '1. 15+ days early'
            WHEN delay_days <= -8  THEN '2. 8-14 days early'
            WHEN delay_days <= -1  THEN '3. 1-7 days early'
            WHEN delay_days =  0   THEN '4. On the estimated day'
            WHEN delay_days <= 3   THEN '5. 1-3 days late'
            WHEN delay_days <= 7   THEN '6. 4-7 days late'
            ELSE                        '7. 8+ days late' END                          AS arrival_bucket,
       COUNT(*)                                                                        AS delivered_orders,
       ROUND(100 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)                                AS pct_of_orders
FROM (
    SELECT DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) AS delay_days
    FROM orders
    WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL
) d
GROUP BY arrival_bucket
ORDER BY arrival_bucket;

-- @query SQL-09b | Q7 | Promised vs actual delivery days (descriptive statistics)
SELECT COUNT(*)                                                                                     AS delivered_orders,
       ROUND(AVG(TIMESTAMPDIFF(SECOND, order_purchase_timestamp, order_estimated_delivery_date)) / 86400, 2) AS avg_promised_days,
       ROUND(AVG(TIMESTAMPDIFF(SECOND, order_purchase_timestamp, order_delivered_customer_date)) / 86400, 2) AS avg_actual_days,
       ROUND(AVG(DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date)), 2)       AS avg_delay_days,
       MIN(DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date))                 AS min_delay_days,
       MAX(DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date))                 AS max_delay_days,
       ROUND(STDDEV_SAMP(DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date)), 2) AS std_delay_days
FROM orders
WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL;

-- @query SQL-10 | Q8 | Review score for late vs on-time orders (LEFT JOIN keeps unreviewed orders)
SELECT CASE WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) > 0
            THEN 'Late' ELSE 'On time' END                                  AS delivery_status,
       COUNT(*)                                                             AS delivered_orders,
       COUNT(r.order_id)                                                    AS reviewed_orders,
       ROUND(AVG(r.review_score), 3)                                        AS avg_review_score,
       ROUND(100 * AVG(CASE WHEN r.review_score <= 2 THEN 1
                            WHEN r.review_score IS NOT NULL THEN 0 END), 2) AS negative_review_pct
FROM orders o
LEFT JOIN reviews r ON r.order_id = o.order_id
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY delivery_status
ORDER BY delivery_status;

-- @query SQL-11 | Q9 | Negative review rate by delay bucket = P(negative given bucket)
SELECT CASE WHEN d.delay_days <= 0 THEN '1. On time'
            WHEN d.delay_days <= 3 THEN '2. 1-3 days late'
            WHEN d.delay_days <= 7 THEN '3. 4-7 days late'
            ELSE                        '4. 8+ days late' END                AS delay_bucket,
       COUNT(*)                                                              AS reviewed_orders,
       ROUND(AVG(r.review_score), 3)                                         AS avg_review_score,
       SUM(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END)                  AS negative_reviews,
       ROUND(AVG(CASE WHEN r.review_score <= 2 THEN 1 ELSE 0 END), 4)        AS p_negative
FROM (
    SELECT order_id,
           DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) AS delay_days
    FROM orders
    WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL
) d
INNER JOIN reviews r ON r.order_id = d.order_id
GROUP BY delay_bucket
ORDER BY delay_bucket;

-- @query SQL-12 | Q10 | Same-state vs inter-state shipping (primary seller = first item)
SELECT CASE WHEN s.seller_state = c.customer_state THEN 'Same state' ELSE 'Inter-state' END AS route,
       COUNT(*)                                                                         AS delivered_orders,
       ROUND(AVG(TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date)) / 86400, 2)
                                                                                        AS avg_delivery_days,
       ROUND(100 * AVG(CASE WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) > 0
                            THEN 1 ELSE 0 END), 2)                                      AS late_pct,
       ROUND(AVG(oi.freight_value), 2)                                                  AS avg_first_item_freight
FROM orders o
INNER JOIN customers   c  ON c.customer_id = o.customer_id
INNER JOIN order_items oi ON oi.order_id   = o.order_id AND oi.order_item_id = 1
INNER JOIN sellers     s  ON s.seller_id   = oi.seller_id
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY route
ORDER BY avg_delivery_days;

-- @query SQL-13 | Q11 | Repeat customer rate by customer_unique_id (derived-table subquery)
SELECT COUNT(*)                                              AS customers,
       SUM(CASE WHEN n_orders >= 2 THEN 1 ELSE 0 END)        AS repeat_customers,
       ROUND(100 * AVG(CASE WHEN n_orders >= 2 THEN 1 ELSE 0 END), 2) AS repeat_customer_pct,
       (SELECT COUNT(DISTINCT customer_id) FROM customers)   AS customer_ids_for_comparison
FROM (
    SELECT c.customer_unique_id, COUNT(DISTINCT o.order_id) AS n_orders
    FROM orders o
    INNER JOIN customers c ON c.customer_id = o.customer_id
    GROUP BY c.customer_unique_id
) per_customer;

-- @query SQL-14 | Q11 | Do customers whose FIRST order was late come back less often?
WITH ranked AS (
    SELECT c.customer_unique_id,
           o.order_status,
           o.order_delivered_customer_date,
           o.order_estimated_delivery_date,
           ROW_NUMBER() OVER (PARTITION BY c.customer_unique_id ORDER BY o.order_purchase_timestamp) AS order_number,
           COUNT(*)     OVER (PARTITION BY c.customer_unique_id)                                      AS total_orders
    FROM orders o
    INNER JOIN customers c ON c.customer_id = o.customer_id
)
SELECT CASE WHEN order_status <> 'delivered' OR order_delivered_customer_date IS NULL THEN 'Not delivered'
            WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) > 0 THEN 'Late'
            ELSE 'On time' END                                              AS first_order_delivery,
       COUNT(*)                                                             AS customers,
       SUM(CASE WHEN total_orders >= 2 THEN 1 ELSE 0 END)                   AS returned_customers,
       ROUND(100 * AVG(CASE WHEN total_orders >= 2 THEN 1 ELSE 0 END), 2)   AS repeat_pct
FROM ranked
WHERE order_number = 1
GROUP BY first_order_delivery
ORDER BY first_order_delivery;

-- @query SQL-15 | Q12 | Seller watch list: 30+ delivered orders AND (late rate >= 12% OR avg review < 3.8)
-- Items are first aggregated per seller-order so reviews are counted once per order, not per item.
WITH seller_orders AS (
    SELECT seller_id, order_id, SUM(price) AS revenue
    FROM order_items
    GROUP BY seller_id, order_id
)
SELECT so.seller_id,
       s.seller_state,
       COUNT(*)                                                                    AS delivered_orders,
       ROUND(SUM(so.revenue), 2)                                                   AS revenue,
       ROUND(100 * AVG(CASE WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) > 0
                            THEN 1 ELSE 0 END), 2)                                 AS late_pct,
       ROUND(AVG(CASE WHEN o.order_delivered_carrier_date >= o.order_approved_at
                      THEN TIMESTAMPDIFF(SECOND, o.order_approved_at, o.order_delivered_carrier_date) END) / 86400, 2)
                                                                                   AS avg_handover_days,
       ROUND(AVG(r.review_score), 2)                                               AS avg_review_score
FROM seller_orders so
INNER JOIN orders  o ON o.order_id  = so.order_id
LEFT JOIN  sellers s ON s.seller_id = so.seller_id
LEFT JOIN  reviews r ON r.order_id  = so.order_id
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY so.seller_id, s.seller_state
HAVING COUNT(*) >= 30
   AND (late_pct >= 12 OR avg_review_score < 3.8)
ORDER BY late_pct DESC
LIMIT 25;

-- @query SQL-15b | Q12 | Sellers with 30+ orders: how many are on the watch list? (IN subquery)
SELECT COUNT(DISTINCT seller_id)                                          AS sellers_with_30_plus_orders,
       SUM(CASE WHEN seller_id IN (
               SELECT so.seller_id
               FROM (SELECT seller_id, order_id FROM order_items GROUP BY seller_id, order_id) so
               INNER JOIN orders o ON o.order_id = so.order_id
               WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
               GROUP BY so.seller_id
               HAVING COUNT(*) >= 30
                  AND AVG(CASE WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) > 0
                               THEN 1 ELSE 0 END) >= 0.12)
           THEN 1 ELSE 0 END)                                             AS sellers_with_late_rate_12_plus
FROM (
    SELECT oi.seller_id
    FROM order_items oi
    INNER JOIN orders o ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
    GROUP BY oi.seller_id
    HAVING COUNT(DISTINCT oi.order_id) >= 30
) big_sellers;

-- @query SQL-16 | Q13 | Freight ratio by customer state (freight / revenue, delivered orders)
SELECT c.customer_state,
       COUNT(DISTINCT o.order_id)                          AS delivered_orders,
       ROUND(SUM(oi.price), 2)                             AS revenue,
       ROUND(SUM(oi.freight_value), 2)                     AS freight,
       ROUND(100 * SUM(oi.freight_value) / SUM(oi.price), 2) AS freight_ratio_pct
FROM orders o
INNER JOIN customers   c  ON c.customer_id = o.customer_id
INNER JOIN order_items oi ON oi.order_id   = o.order_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY freight_ratio_pct DESC;

-- @query SQL-16b | Q13 | Freight ratio by product category (categories with 300+ orders)
SELECT p.product_category_english                        AS category,
       COUNT(DISTINCT o.order_id)                          AS delivered_orders,
       ROUND(SUM(oi.price), 2)                             AS revenue,
       ROUND(SUM(oi.freight_value), 2)                     AS freight,
       ROUND(100 * SUM(oi.freight_value) / SUM(oi.price), 2) AS freight_ratio_pct
FROM order_items oi
INNER JOIN orders   o ON o.order_id   = oi.order_id
INNER JOIN products p ON p.product_id = oi.product_id
WHERE o.order_status = 'delivered'
GROUP BY p.product_category_english
HAVING COUNT(DISTINCT o.order_id) >= 300
ORDER BY freight_ratio_pct DESC
LIMIT 15;

-- @query SQL-17 | KPI | Cancellation rate by month
SELECT DATE_FORMAT(order_purchase_timestamp, '%Y-%m')                                      AS purchase_month,
       COUNT(*)                                                                             AS orders,
       SUM(CASE WHEN order_status IN ('canceled', 'unavailable') THEN 1 ELSE 0 END)         AS cancelled_orders,
       ROUND(100 * AVG(CASE WHEN order_status IN ('canceled', 'unavailable') THEN 1 ELSE 0 END), 2) AS cancellation_pct
FROM orders
WHERE order_purchase_timestamp >= '2017-01-01'
  AND order_purchase_timestamp <  '2018-09-01'
GROUP BY DATE_FORMAT(order_purchase_timestamp, '%Y-%m')
ORDER BY purchase_month;

-- @query SQL-18 | KPI | Headline KPIs for reconciliation with Python, Power BI and Tableau
SELECT
    (SELECT COUNT(DISTINCT order_id) FROM orders)                                        AS orders,
    (SELECT COUNT(*) FROM orders WHERE order_status = 'delivered')                       AS delivered_orders,
    (SELECT ROUND(SUM(i.price), 2) FROM order_items i
       INNER JOIN orders o ON o.order_id = i.order_id WHERE o.order_status = 'delivered') AS revenue,
    (SELECT ROUND(SUM(i.price) / COUNT(DISTINCT o.order_id), 2) FROM order_items i
       INNER JOIN orders o ON o.order_id = i.order_id WHERE o.order_status = 'delivered') AS aov,
    (SELECT ROUND(SUM(i.freight_value), 2) FROM order_items i
       INNER JOIN orders o ON o.order_id = i.order_id WHERE o.order_status = 'delivered') AS freight,
    (SELECT ROUND(100 * SUM(i.freight_value) / SUM(i.price), 2) FROM order_items i
       INNER JOIN orders o ON o.order_id = i.order_id WHERE o.order_status = 'delivered') AS freight_ratio_pct,
    (SELECT ROUND(100 * AVG(CASE WHEN DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date) <= 0
                                 THEN 1 ELSE 0 END), 2)
       FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL) AS on_time_pct,
    (SELECT ROUND(AVG(TIMESTAMPDIFF(SECOND, order_purchase_timestamp, order_delivered_customer_date)) / 86400, 2)
       FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL) AS avg_delivery_days,
    (SELECT ROUND(AVG(DATEDIFF(order_delivered_customer_date, order_estimated_delivery_date)), 2)
       FROM orders WHERE order_status = 'delivered' AND order_delivered_customer_date IS NOT NULL) AS avg_delay_days,
    (SELECT ROUND(AVG(review_score), 3) FROM reviews)                                     AS avg_review_score,
    (SELECT ROUND(100 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) FROM reviews) AS negative_review_pct,
    (SELECT ROUND(100 * AVG(CASE WHEN n >= 2 THEN 1 ELSE 0 END), 2)
       FROM (SELECT c.customer_unique_id, COUNT(*) AS n FROM orders o
             INNER JOIN customers c ON c.customer_id = o.customer_id
             GROUP BY c.customer_unique_id) t)                                            AS repeat_customer_pct,
    (SELECT ROUND(100 * AVG(CASE WHEN order_status IN ('canceled', 'unavailable') THEN 1 ELSE 0 END), 2)
       FROM orders)                                                                       AS cancellation_pct;
