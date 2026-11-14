{{ config(materialized='view') }}

SELECT
    order_id,
    CAST(payment_sequential AS INTEGER) AS payment_sequential,
    payment_type,
    CAST(payment_installments AS INTEGER) AS payment_installments,
    CAST(payment_value AS DECIMAL(12,2)) AS payment_value,
    dwh_batch
FROM {{ source('raw', 'order_payments') }}
WHERE TRY_CAST(payment_value AS DECIMAL(12,2)) >= 0
