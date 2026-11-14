{{ config(materialized='table') }}

WITH a AS (
    SELECT 
        order_id, 
        sum(n_items) AS n_items, 
        count(*) FILTER (WHERE seller_id IS NOT NULL) AS n_sellers,
        sum(order_value) AS items_price_total, 
        sum(freight_total) AS freight_total, 
        bool_or(seller_late) AS any_seller_late
    FROM {{ ref('fact_order_seller') }} 
    GROUP BY order_id
),
p AS (
    SELECT 
        order_id, 
        sum(payment_value) AS payment_total, 
        count(*) AS payment_count 
    FROM {{ ref('stg_payments') }}
    GROUP BY order_id
)
SELECT 
    o.order_id, 
    coalesce(dc.customer_key, -1) AS customer_key, 
    coalesce(lc.location_key, -1) AS customer_location_key, 
    st.status_key,
    {{ date_key('o.purchase_ts') }} AS purchase_date_key, 
    {{ date_key('o.approved_ts') }} AS approved_date_key, 
    {{ date_key('o.carrier_ts') }} AS carrier_date_key,
    {{ date_key('o.delivered_ts') }} AS delivered_date_key, 
    {{ date_key('o.estimated_ts') }} AS estimated_date_key,
    o.purchase_ts, 
    o.approved_ts, 
    o.carrier_ts, 
    o.delivered_ts, 
    o.estimated_ts,
    date_sub('second', o.purchase_ts, o.approved_ts) / 86400.0 AS days_to_approve,
    date_sub('second', o.purchase_ts, o.carrier_ts) / 86400.0 AS days_to_carrier,
    date_sub('second', o.carrier_ts, o.delivered_ts) / 86400.0 AS days_in_transit,
    date_diff('day', CAST(o.estimated_ts AS DATE), CAST(o.delivered_ts AS DATE)) AS delay_days,
    CAST(o.delivered_ts AS DATE) > CAST(o.estimated_ts AS DATE) AS customer_late,
    a.any_seller_late,
    coalesce(a.n_items, 0) AS n_items, 
    coalesce(a.n_sellers, 0) AS n_sellers, 
    coalesce(a.items_price_total, 0) AS items_price_total, 
    coalesce(a.freight_total, 0) AS freight_total, 
    coalesce(a.items_price_total + a.freight_total, 0) AS order_total,
    coalesce(p.payment_total, 0) AS payment_total, 
    coalesce(p.payment_count, 0) AS payment_count,
    rv.review_score, 
    rv.first_review_ts,
    st.is_canceled,
    (o.order_status = 'delivered' AND o.delivered_ts IS NULL) OR (o.order_status <> 'delivered' AND o.delivered_ts IS NOT NULL) AS has_status_date_mismatch,
    coalesce(o.carrier_ts < o.purchase_ts, FALSE) OR coalesce(o.delivered_ts < o.carrier_ts, FALSE) OR coalesce(o.approved_ts < o.purchase_ts, FALSE) AS has_chronology_issue,
    o.first_batch AS dwh_first_batch, 
    o.last_batch AS dwh_last_batch, 
    o.n_versions
FROM {{ ref('stg_orders') }} o
LEFT JOIN a USING (order_id)
LEFT JOIN p USING (order_id)
LEFT JOIN {{ ref('int_reviews_by_order') }} rv USING (order_id)
LEFT JOIN {{ ref('dim_order_status') }} st ON st.status = o.order_status
LEFT JOIN {{ ref('stg_customers') }} c ON c.customer_id = o.customer_id
LEFT JOIN {{ ref('dim_customer') }} dc ON dc.customer_unique_id = c.customer_unique_id
LEFT JOIN {{ ref('dim_location') }} lc ON lc.zip_prefix = c.zip_prefix
