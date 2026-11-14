-- Doi chieu hai duong dung kho: dbt (dbt_core, dung lai tu raw) phai ra cung so dong va so tien voi kho chinh (core, do src/sql dung theo dot).
-- Lech la mot ben doi logic ma ben kia chua theo. Bang thang va mart khong so: dbt chi tinh moc cuoi, kho chinh giu anh chup tung dot.
WITH pairs AS (
    SELECT 'fact_sales_item' AS t, (SELECT count(*) FROM core.fact_sales_item) AS py, (SELECT count(*) FROM {{ ref('fact_sales_item') }}) AS dbt
    UNION ALL SELECT 'fact_sales_item.price', (SELECT sum(price) FROM core.fact_sales_item), (SELECT sum(price) FROM {{ ref('fact_sales_item') }})
    UNION ALL SELECT 'fact_order', (SELECT count(*) FROM core.fact_order), (SELECT count(*) FROM {{ ref('fact_order') }})
    UNION ALL SELECT 'fact_order_seller', (SELECT count(*) FROM core.fact_order_seller), (SELECT count(*) FROM {{ ref('fact_order_seller') }})
    UNION ALL SELECT 'fact_payment.value', (SELECT sum(payment_value) FROM core.fact_payment), (SELECT sum(payment_value) FROM {{ ref('fact_payment') }})
    UNION ALL SELECT 'fact_review', (SELECT count(*) FROM core.fact_review), (SELECT count(*) FROM {{ ref('fact_review') }})
    UNION ALL SELECT 'dim_customer', (SELECT count(*) FROM core.dim_customer), (SELECT count(*) FROM {{ ref('dim_customer') }})
    UNION ALL SELECT 'dim_product', (SELECT count(*) FROM core.dim_product), (SELECT count(*) FROM {{ ref('dim_product') }})
    UNION ALL SELECT 'dim_seller', (SELECT count(*) FROM core.dim_seller), (SELECT count(*) FROM {{ ref('dim_seller') }})
    UNION ALL SELECT 'dim_route', (SELECT count(*) FROM core.dim_route), (SELECT count(*) FROM {{ ref('dim_route') }})
    UNION ALL SELECT 'dim_location.city_state_khac',
        0, (SELECT count(*) FROM core.dim_location a JOIN {{ ref('dim_location') }} b USING (zip_prefix)
            WHERE a.city IS DISTINCT FROM b.city OR a.state IS DISTINCT FROM b.state)
)
SELECT * FROM pairs WHERE py IS DISTINCT FROM dbt
