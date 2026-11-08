-- Kiem tra bat bien bao toan doanh so: Doanh thu tu fact_sales_item phai khop tuyet doi voi raw order items
WITH raw_total AS (
    SELECT round(sum(price::DOUBLE), 2) AS raw_gmv
    FROM {{ source('raw', 'order_items') }}
),
fact_total AS (
    SELECT round(sum(price), 2) AS fact_gmv
    FROM {{ ref('fact_sales_item') }}
)
SELECT 
    raw_gmv, 
    fact_gmv, 
    abs(raw_gmv - fact_gmv) AS diff
FROM raw_total, fact_total
WHERE abs(raw_gmv - fact_gmv) > 0.01
