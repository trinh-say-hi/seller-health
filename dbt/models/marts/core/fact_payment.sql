{{ config(materialized='table') }}

SELECT 
    pm.order_id, 
    pm.payment_sequential, 
    pm.payment_type, 
    pm.payment_installments, 
    pm.payment_value,
    coalesce(dc.customer_key, -1) AS customer_key, 
    {{ date_key('o.purchase_ts') }} AS purchase_date_key, 
    pm.dwh_batch
FROM {{ ref('stg_payments') }} pm
JOIN {{ ref('stg_orders') }} o USING (order_id)
LEFT JOIN {{ ref('stg_customers') }} c ON c.customer_id = o.customer_id
LEFT JOIN {{ ref('dim_customer') }} dc ON dc.customer_unique_id = c.customer_unique_id
