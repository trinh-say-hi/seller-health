{{ config(materialized='table', alias='route_delivery') }}

WITH latest_cutoff AS (
    SELECT coalesce(max(delivered_ts), TIMESTAMP '2018-10-17') AS c
    FROM {{ ref('fact_order_seller') }}
)
SELECT 
    CAST(lc.c AS DATE) AS as_of, 
    r.route_key, 
    r.route_name, 
    r.seller_state, 
    r.customer_state,
    count(*) AS n_orders, 
    median(date_sub('second', f.purchase_ts, f.delivered_ts) / 86400.0) AS median_days,
    quantile_cont(date_sub('second', f.purchase_ts, f.delivered_ts) / 86400.0, 0.9) AS p90_days,
    avg(date_diff('day', CAST(f.purchase_ts AS DATE), CAST(f.estimated_ts AS DATE))) AS avg_promise_days,
    avg(CASE WHEN f.customer_late THEN 1.0 ELSE 0.0 END) AS late_rate,
    avg(CASE WHEN NOT coalesce(f.seller_late, FALSE) THEN 1.0 ELSE 0.0 END) FILTER (WHERE f.customer_late) AS late_seller_ok_share
FROM {{ ref('fact_order_seller') }} f
CROSS JOIN latest_cutoff lc
JOIN {{ ref('dim_route') }} r USING (route_key)
WHERE f.delivered_ts IS NOT NULL 
  AND f.route_key <> -1
GROUP BY ALL
