{{ config(materialized='table') }}

WITH latest_cutoff AS (
    SELECT coalesce(max(purchase_ts), TIMESTAMP '2018-09-03') AS c
    FROM {{ ref('fact_sales_item') }}
),
_w AS (
    SELECT 
        i.seller_id, 
        i.order_id, 
        i.purchase_ts AS ts, 
        CAST(i.price AS DOUBLE) AS price, 
        i.shipping_limit_ts AS lim,
        p.category_en, 
        ds.region, 
        f.carrier_ts, 
        f.delivered_ts, 
        f.estimated_ts, 
        f.review_score, 
        f.first_review_ts,
        f.days_in_transit, 
        i.is_valid_sale
    FROM {{ ref('fact_sales_item') }} i
    JOIN {{ ref('dim_product') }} p USING (product_key)
    JOIN {{ ref('dim_seller') }} ds ON ds.seller_key = i.seller_key
    JOIN {{ ref('fact_order_seller') }} f ON f.order_id = i.order_id AND f.seller_id = i.seller_id
),
h AS (
    SELECT 
        seller_id, 
        max(ts) AS last_ts, 
        min(ts) AS first_ts 
    FROM _w 
    WHERE is_valid_sale 
    GROUP BY seller_id
),
w AS (
    SELECT w0.* 
    FROM _w w0
    CROSS JOIN latest_cutoff lc
    WHERE w0.is_valid_sale AND w0.ts >= lc.c - INTERVAL 90 DAY
),
late_orders AS (
    SELECT 
        seller_id, 
        order_id, 
        bool_or(carrier_ts IS NOT NULL AND carrier_ts <= lim) AS seller_ok
    FROM w
    CROSS JOIN latest_cutoff lc
    WHERE estimated_ts < lc.c
      AND (delivered_ts IS NULL OR CAST(delivered_ts AS DATE) > CAST(estimated_ts AS DATE))
    GROUP BY seller_id, order_id
),
lo AS (
    SELECT 
        seller_id, 
        count(*) AS n_late, 
        count(*) FILTER (WHERE seller_ok) AS n_ok 
    FROM late_orders 
    GROUP BY seller_id
),
a AS (
    SELECT 
        w.seller_id,
        sum(w.price) AS gmv_90, 
        count(DISTINCT w.order_id) AS orders_90,
        coalesce(sum(w.price) FILTER (WHERE w.ts >= lc.c - INTERVAL 30 DAY), 0) AS gmv_30,
        count(DISTINCT w.order_id) FILTER (WHERE w.ts >= lc.c - INTERVAL 30 DAY) AS orders_30,
        count(DISTINCT w.category_en) AS n_cat,
        avg(CASE WHEN w.carrier_ts IS NULL OR w.carrier_ts > w.lim THEN 1.0 ELSE 0.0 END) FILTER (WHERE w.lim < lc.c) AS seller_late_rate,
        count(*) FILTER (WHERE w.lim < lc.c) AS n_limit_known,
        avg(CASE WHEN w.delivered_ts IS NULL OR CAST(w.delivered_ts AS DATE) > CAST(w.estimated_ts AS DATE) THEN 1.0 ELSE 0.0 END)
            FILTER (WHERE w.estimated_ts < lc.c) AS cust_late_rate,
        avg(w.review_score) FILTER (WHERE w.first_review_ts < lc.c) AS avg_review,
        avg(date_sub('second', w.ts, w.carrier_ts) / 86400.0) FILTER (WHERE w.carrier_ts < lc.c) AS days_to_carrier
    FROM w
    CROSS JOIN latest_cutoff lc
    GROUP BY w.seller_id
),
scored AS (
    SELECT 
        CAST(lc.c AS DATE) AS as_of, 
        a.seller_id, 
        a.gmv_90, 
        a.orders_90, 
        a.gmv_30, 
        a.orders_30,
        a.gmv_30 / nullif(a.gmv_90 / 3, 0) - 1 AS trend,
        date_sub('second', h.last_ts, lc.c) / 86400.0 AS recency,
        date_sub('second', h.first_ts, lc.c) / 86400.0 AS tenure,
        a.n_cat, 
        a.seller_late_rate, 
        a.cust_late_rate, 
        a.avg_review, 
        a.days_to_carrier, 
        a.n_limit_known,
        coalesce(lo.n_late, 0) AS n_cust_late_orders, 
        coalesce(lo.n_ok, 0) AS n_cust_late_seller_ok
    FROM a 
    CROSS JOIN latest_cutoff lc
    JOIN h USING (seller_id) 
    LEFT JOIN lo USING (seller_id)
)
SELECT 
    s.*,
    CASE 
        WHEN s.recency > 45 THEN 'Tạm ngừng'
        WHEN s.orders_90 < 6 THEN 'Ít đơn'
        WHEN (s.trend < -0.5 AND s.recency > 21) OR (s.seller_late_rate >= 0.30 AND s.n_limit_known >= 5) THEN 'Nguy cơ'
        WHEN s.trend < -0.40 OR (s.seller_late_rate >= 0.15 AND s.n_limit_known >= 5) OR s.avg_review < 3.5 THEN 'Theo dõi'
        WHEN s.gmv_90 >= quantile_cont(s.gmv_90, 0.8) OVER () THEN 'Vàng'
        ELSE 'Ổn định' 
    END AS health_tier
FROM scored s
