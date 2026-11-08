{{ config(materialized='view') }}

WITH ranked AS (
    SELECT
        order_id,
        customer_id,
        order_status,
        CAST(order_purchase_timestamp AS TIMESTAMP) AS purchase_ts,
        TRY_CAST(order_approved_at AS TIMESTAMP) AS approved_ts,
        TRY_CAST(order_delivered_carrier_date AS TIMESTAMP) AS carrier_ts,
        TRY_CAST(order_delivered_customer_date AS TIMESTAMP) AS delivered_ts,
        TRY_CAST(order_estimated_delivery_date AS TIMESTAMP) AS estimated_ts,
        min(dwh_batch) OVER (PARTITION BY order_id) AS first_batch,
        max(dwh_batch) OVER (PARTITION BY order_id) AS last_batch,
        count(*) OVER (PARTITION BY order_id) AS n_versions,
        ROW_NUMBER() OVER (PARTITION BY order_id ORDER BY dwh_batch DESC) AS rn
    FROM {{ source('raw', 'orders') }}
)
SELECT
    order_id,
    customer_id,
    order_status,
    purchase_ts,
    approved_ts,
    carrier_ts,
    delivered_ts,
    estimated_ts,
    first_batch,
    last_batch,
    n_versions
FROM ranked
WHERE rn = 1
