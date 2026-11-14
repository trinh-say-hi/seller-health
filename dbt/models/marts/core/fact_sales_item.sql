{{ config(materialized='table') }}

SELECT 
    i.order_id, 
    i.order_item_id, 
    coalesce(p.product_key, -1) AS product_key, 
    coalesce(s.seller_key, -1) AS seller_key, 
    i.seller_id,
    coalesce(dc.customer_key, -1) AS customer_key, 
    coalesce(r.route_key, -1) AS route_key, 
    coalesce(lc.location_key, -1) AS customer_location_key, 
    coalesce(ls.location_key, -1) AS seller_location_key,
    {{ date_key('o.purchase_ts') }} AS purchase_date_key, 
    {{ date_key('i.shipping_limit_ts') }} AS shipping_limit_date_key, 
    o.purchase_ts, 
    i.shipping_limit_ts, 
    i.price, 
    i.freight_value, 
    1 AS qty,
    o.order_status NOT IN ('canceled','unavailable') AS is_valid_sale, 
    i.dwh_batch
FROM {{ ref('stg_items') }} i
JOIN {{ ref('stg_orders') }} o USING (order_id)
LEFT JOIN {{ ref('stg_customers') }} c ON c.customer_id = o.customer_id
LEFT JOIN {{ ref('dim_customer') }} dc ON dc.customer_unique_id = c.customer_unique_id
LEFT JOIN {{ ref('dim_product') }} p ON p.product_id = i.product_id
-- dim_seller la SCD2: lay dong co hieu luc luc mua (giong src/sql/11_batch_core.sql), khong thi moi dong hang nhan theo so phien ban seller.
LEFT JOIN {{ ref('dim_seller') }} s ON s.seller_id = i.seller_id AND o.purchase_ts >= s.valid_from AND o.purchase_ts < s.valid_to
LEFT JOIN {{ ref('dim_route') }} r ON r.seller_state = s.state AND r.customer_state = c.state
LEFT JOIN {{ ref('dim_location') }} lc ON lc.zip_prefix = c.zip_prefix
LEFT JOIN {{ ref('dim_location') }} ls ON ls.zip_prefix = s.zip_prefix
