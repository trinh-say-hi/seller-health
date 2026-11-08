{{ config(materialized='table') }}

WITH _w AS (
    SELECT 
        i.seller_id, 
        i.order_id, 
        i.purchase_ts AS ts, 
        CAST(i.price AS DOUBLE) AS price, 
        p.category_en, 
        ds.region, 
        f.delivered_ts, 
        f.estimated_ts, 
        f.review_score, 
        f.first_review_ts,
        i.is_valid_sale
    FROM {{ ref('fact_sales_item') }} i
    JOIN {{ ref('dim_product') }} p USING (product_key)
    JOIN {{ ref('dim_seller') }} ds ON ds.seller_key = i.seller_key
    JOIN {{ ref('fact_order_seller') }} f ON f.order_id = i.order_id AND f.seller_id = i.seller_id
)
SELECT 
    date_trunc('month', ts)::DATE AS month,
    region, 
    category_en, 
    GROUPING(region) = 1 AS is_all_region, 
    GROUPING(category_en) = 1 AS is_all_category,
    coalesce(sum(price), 0) AS gmv,
    count(DISTINCT order_id) AS n_orders,
    count(DISTINCT seller_id) AS n_sellers,
    count(DISTINCT order_id) FILTER (WHERE estimated_ts IS NOT NULL) AS n_due_orders,
    count(DISTINCT order_id) FILTER (WHERE delivered_ts IS NULL OR CAST(delivered_ts AS DATE) > CAST(estimated_ts AS DATE)) AS n_late_orders,
    avg(review_score) AS avg_review
FROM _w
WHERE is_valid_sale
GROUP BY date_trunc('month', ts)::DATE, CUBE (region, category_en)
