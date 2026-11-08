{{ config(materialized='table') }}

WITH a AS (
    SELECT 
        order_id, 
        seller_id, 
        sum(price) AS order_value, 
        sum(freight_value) AS freight_total,
        count(*) AS n_items, 
        max(shipping_limit_ts) AS shipping_limit_ts
    FROM {{ ref('stg_items') }}
    GROUP BY order_id, seller_id
)
SELECT 
    o.order_id, 
    a.seller_id, 
    coalesce(s.seller_key, -1) AS seller_key, 
    coalesce(dc.customer_key, -1) AS customer_key, 
    coalesce(r.route_key, -1) AS route_key,
    coalesce(lc.location_key, -1) AS customer_location_key, 
    coalesce(ls.location_key, -1) AS seller_location_key,
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
    a.shipping_limit_ts, 
    o.order_status,
    date_sub('second', o.purchase_ts, o.approved_ts) / 86400.0 AS days_to_approve,
    date_sub('second', o.purchase_ts, o.carrier_ts) / 86400.0 AS days_to_carrier,
    date_sub('second', o.carrier_ts, o.delivered_ts) / 86400.0 AS days_in_transit,
    date_diff('day', CAST(o.estimated_ts AS DATE), CAST(o.delivered_ts AS DATE)) AS delay_days,
    o.carrier_ts > a.shipping_limit_ts AS seller_late,
    CAST(o.delivered_ts AS DATE) > CAST(o.estimated_ts AS DATE) AS customer_late,
    rv.review_score, 
    rv.has_comment, 
    rv.first_review_ts,
    coalesce(a.order_value, 0) AS order_value, 
    coalesce(a.freight_total, 0) AS freight_total, 
    coalesce(a.n_items, 0) AS n_items,
    o.first_batch AS dwh_first_batch, 
    o.last_batch AS dwh_last_batch, 
    o.n_versions
FROM {{ ref('stg_orders') }} o
LEFT JOIN a USING (order_id)
LEFT JOIN {{ ref('int_reviews_by_order') }} rv USING (order_id)
LEFT JOIN {{ ref('stg_customers') }} c ON c.customer_id = o.customer_id
LEFT JOIN {{ ref('dim_customer') }} dc ON dc.customer_unique_id = c.customer_unique_id
LEFT JOIN {{ ref('dim_seller') }} s ON s.seller_id = a.seller_id AND o.purchase_ts >= s.valid_from AND o.purchase_ts < s.valid_to
LEFT JOIN {{ ref('dim_route') }} r ON r.seller_state = s.state AND r.customer_state = c.state
LEFT JOIN {{ ref('dim_location') }} lc ON lc.zip_prefix = c.zip_prefix
LEFT JOIN {{ ref('dim_location') }} ls ON ls.zip_prefix = s.zip_prefix
