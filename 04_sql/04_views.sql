-- =====================================================================
-- BazaarLink capstone | 04_views.sql
-- =====================================================================
USE bazaarlink;

CREATE OR REPLACE VIEW vw_order_delivery AS
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    o.order_status,
    o.order_purchase_timestamp,
    DATE(o.order_purchase_timestamp)  AS purchase_date,
    DATE_FORMAT(o.order_purchase_timestamp, '%Y-%m')  AS purchase_month,
    o.order_approved_at,
    o.order_delivered_carrier_date,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    CASE WHEN o.order_status = 'delivered' THEN 1 ELSE 0 END  AS is_delivered,
    CASE WHEN o.order_status = 'delivered'
          AND o.order_delivered_customer_date IS NOT NULL THEN 1 ELSE 0 END  AS is_delivery_measurable,
    CASE WHEN o.order_status IN ('canceled', 'unavailable') THEN 1 ELSE 0 END AS is_cancelled,
    CASE WHEN o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
         THEN ROUND(TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date) / 86400, 2) END
                                                                             AS delivery_days,
    CASE WHEN o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
         THEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) END
                                                                             AS delay_days,
    CASE WHEN o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
          AND o.order_delivered_carrier_date >= o.order_approved_at
         THEN ROUND(TIMESTAMPDIFF(SECOND, o.order_approved_at, o.order_delivered_carrier_date) / 86400, 2) END
                                                                             AS seller_handover_days,
    CASE WHEN o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
          AND o.order_delivered_customer_date >= o.order_delivered_carrier_date
         THEN ROUND(TIMESTAMPDIFF(SECOND, o.order_delivered_carrier_date, o.order_delivered_customer_date) / 86400, 2) END
                                                                             AS carrier_days,
    CASE WHEN o.order_status <> 'delivered' OR o.order_delivered_customer_date IS NULL THEN 'Not delivered'
         WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) <= 0 THEN 'On time'
         ELSE 'Late' END    AS delivery_status,
    CASE WHEN o.order_status <> 'delivered' OR o.order_delivered_customer_date IS NULL THEN 'Not delivered'
         WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) <= 0 THEN 'On time'
         WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) <= 3 THEN '1-3 days late'
         WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) <= 7 THEN '4-7 days late'
         ELSE '8+ days late' END    AS delay_bucket,
    -- money 
    COALESCE(oi.n_items, 0)   AS n_items,
    COALESCE(oi.item_revenue, 0)   AS item_revenue,
    COALESCE(oi.freight_value, 0)  AS freight_value,
    oi.primary_seller_id,
    s.seller_state  AS primary_seller_state,
    oi.primary_category,
    CASE WHEN s.seller_state IS NULL THEN NULL
         WHEN s.seller_state = c.customer_state THEN 'Same state'
         ELSE 'Inter-state' END   AS route,
    mp.main_payment_type,
    pay.max_installments,
    pay.payment_total,
    r.review_score,
    CASE WHEN r.review_score IS NULL THEN NULL
         WHEN r.review_score <= 2 THEN 1 ELSE 0 END    AS is_negative_review
FROM orders o
INNER JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN (
    SELECT i.order_id,
           COUNT(*)   AS n_items,
           SUM(i.price)   AS item_revenue,
           SUM(i.freight_value)   AS freight_value,
           MAX(CASE WHEN i.order_item_id = 1 THEN i.seller_id END)  AS primary_seller_id,
           MAX(CASE WHEN i.order_item_id = 1 THEN p.product_category_english END) AS primary_category
    FROM order_items i
    INNER JOIN products p ON p.product_id = i.product_id
    GROUP BY i.order_id
) oi ON oi.order_id = o.order_id
LEFT JOIN sellers s ON s.seller_id = oi.primary_seller_id
LEFT JOIN (
    SELECT order_id,
           SUM(payment_value) AS payment_total,
           MAX(payment_installments)   AS max_installments
    FROM payments
    GROUP BY order_id
) pay ON pay.order_id = o.order_id
LEFT JOIN (
    -- main payment type = the payment line with the largest value (same rule as SQL-04)
    SELECT order_id, payment_type AS main_payment_type
    FROM (SELECT order_id, payment_type,
                 ROW_NUMBER() OVER (PARTITION BY order_id
                                    ORDER BY payment_value DESC, payment_sequential) AS rn
          FROM payments) ranked
    WHERE rn = 1
) mp ON mp.order_id = o.order_id
LEFT JOIN reviews r ON r.order_id = o.order_id;

-- ---------------------------------------------------------------------
-- vw_seller_scorecard
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_seller_scorecard AS
SELECT
    so.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(*)     AS delivered_orders,
    ROUND(SUM(so.revenue), 2)   AS revenue,
    ROUND(SUM(so.freight), 2)   AS freight,
    SUM(CASE WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) > 0
             THEN 1 ELSE 0 END) AS late_orders,
    ROUND(AVG(CASE WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) > 0
                   THEN 1 ELSE 0 END), 4)    AS late_rate,
    ROUND(AVG(CASE WHEN o.order_delivered_carrier_date >= o.order_approved_at
                   THEN TIMESTAMPDIFF(SECOND, o.order_approved_at, o.order_delivered_carrier_date) END) / 86400, 2)
                                                                                 AS avg_handover_days,
    ROUND(AVG(TIMESTAMPDIFF(SECOND, o.order_purchase_timestamp, o.order_delivered_customer_date)) / 86400, 2)
                                                                                 AS avg_delivery_days,
    COUNT(r.order_id)  AS reviewed_orders,
    ROUND(AVG(r.review_score), 2)   AS avg_review_score,
    ROUND(AVG(CASE WHEN r.review_score <= 2 THEN 1
                   WHEN r.review_score IS NOT NULL THEN 0 END), 4) AS negative_review_rate,
    CASE WHEN COUNT(*) >= 30
          AND (AVG(CASE WHEN DATEDIFF(o.order_delivered_customer_date, o.order_estimated_delivery_date) > 0
                        THEN 1 ELSE 0 END) >= 0.12
               OR AVG(r.review_score) < 3.8)
         THEN 'Watch list' ELSE 'OK' END   AS watch_status
FROM (
    SELECT seller_id, order_id, SUM(price) AS revenue, SUM(freight_value) AS freight
    FROM order_items
    GROUP BY seller_id, order_id
) so
INNER JOIN orders  o ON o.order_id  = so.order_id
LEFT JOIN  sellers s ON s.seller_id = so.seller_id
LEFT JOIN  reviews r ON r.order_id  = so.order_id
WHERE o.order_status = 'delivered' AND o.order_delivered_customer_date IS NOT NULL
GROUP BY so.seller_id, s.seller_city, s.seller_state;

-- ---------------------------------------------------------------------
-- vw_monthly_kpis
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_monthly_kpis AS
SELECT
    purchase_month,
    COUNT(*) AS orders,
    SUM(is_delivered) AS delivered_orders,
    ROUND(SUM(CASE WHEN is_delivered = 1 THEN item_revenue ELSE 0 END), 2)  AS revenue,
    ROUND(SUM(CASE WHEN is_delivered = 1 THEN item_revenue ELSE 0 END) / NULLIF(SUM(is_delivered), 0), 2) AS aov,
    ROUND(SUM(CASE WHEN delivery_status = 'On time' THEN 1 ELSE 0 END)
          / NULLIF(SUM(is_delivery_measurable), 0), 4)  AS on_time_rate,
    ROUND(AVG(delivery_days), 2)   AS avg_delivery_days,
    ROUND(AVG(review_score), 3)  AS avg_review_score,
    ROUND(AVG(is_cancelled), 4)  AS cancellation_rate
FROM vw_order_delivery
WHERE purchase_month BETWEEN '2017-01' AND '2018-08'
GROUP BY purchase_month;
