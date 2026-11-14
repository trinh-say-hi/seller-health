{{ config(materialized='table') }}

SELECT 
    r.review_id, 
    r.order_id, 
    coalesce(dc.customer_key, -1) AS customer_key,
    {{ date_key('r.created_ts') }} AS created_date_key, 
    {{ date_key('r.review_ts') }} AS answered_date_key, 
    r.created_ts, 
    r.review_ts AS answered_ts,
    r.review_score, 
    r.has_title, 
    r.has_comment,
    date_sub('second', r.created_ts, r.review_ts) / 3600.0 AS answer_hours,
    CAST(o.delivered_ts AS DATE) > CAST(o.estimated_ts AS DATE) AS customer_late,
    o.delivered_ts IS NULL OR r.review_ts < o.delivered_ts AS is_before_delivery,
    r.dwh_batch
FROM {{ ref('stg_reviews') }} r
JOIN {{ ref('stg_orders') }} o USING (order_id)
LEFT JOIN {{ ref('stg_customers') }} c ON c.customer_id = o.customer_id
LEFT JOIN {{ ref('dim_customer') }} dc ON dc.customer_unique_id = c.customer_unique_id
