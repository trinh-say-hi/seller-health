{{ config(materialized='table') }}

WITH _w AS (
    SELECT 
        i.seller_id, 
        i.seller_key, 
        i.order_id, 
        i.purchase_ts AS ts, 
        CAST(i.price AS DOUBLE) AS price, 
        i.shipping_limit_ts AS lim,
        p.category_en, 
        ds.region, 
        f.carrier_ts, 
        f.delivered_ts, 
        f.estimated_ts, 
        f.review_score, 
        f.first_review_ts,
        f.days_in_transit, 
        i.is_valid_sale
    FROM {{ ref('fact_sales_item') }} i
    JOIN {{ ref('dim_product') }} p USING (product_key)
    JOIN {{ ref('dim_seller') }} ds ON ds.seller_key = i.seller_key
    JOIN {{ ref('fact_order_seller') }} f ON f.order_id = i.order_id AND f.seller_id = i.seller_id
),
monthly AS (
    SELECT 
        date_trunc('month', ts)::DATE AS month,
        seller_id,
        count(DISTINCT order_id) AS n_orders,
        count(*) AS n_items,
        coalesce(sum(price), 0) AS gmv,
        avg(CASE WHEN carrier_ts IS NULL OR carrier_ts > lim THEN 1.0 ELSE 0.0 END) AS seller_late_rate,
        avg(CASE WHEN delivered_ts IS NULL OR CAST(delivered_ts AS DATE) > CAST(estimated_ts AS DATE) THEN 1.0 ELSE 0.0 END) AS customer_late_rate,
        avg(review_score) AS avg_review,
        avg(date_sub('second', ts, carrier_ts) / 86400.0) AS avg_days_to_carrier,
        avg(days_in_transit) AS avg_days_in_transit,
        -- So ngay tu lan ban cuoi toi moc chot dot (dau thang sau), nhu recency o src/sql/12_batch_close.sql.
        date_sub('second', max(ts), date_trunc('month', min(ts)) + INTERVAL 1 MONTH) / 86400.0 AS days_since_last_sale,
        count(DISTINCT category_en) AS n_categories
    FROM _w
    WHERE is_valid_sale
    GROUP BY date_trunc('month', ts)::DATE, seller_id
),
with_prev AS (
    SELECT 
        m.*,
        avg(m.gmv) OVER (
            PARTITION BY m.seller_id 
            ORDER BY m.month 
            ROWS BETWEEN 3 PRECEDING AND 1 PRECEDING
        ) AS gmv_prev_3m_avg,
        cur.seller_key
    FROM monthly m
    JOIN {{ ref('dim_seller') }} cur ON cur.seller_id = m.seller_id AND cur.is_current
)
SELECT 
    p.month,
    {{ date_key('p.month') }} AS month_key,
    p.seller_key,
    coalesce(h.health_key, -1) AS health_key,
    p.seller_id,
    p.n_orders,
    p.n_items,
    p.gmv,
    coalesce(p.gmv_prev_3m_avg, 0) AS gmv_prev_3m_avg,
    p.seller_late_rate,
    p.customer_late_rate,
    p.avg_review,
    p.avg_days_to_carrier,
    p.avg_days_in_transit,
    p.days_since_last_sale,
    p.n_categories
FROM with_prev p
LEFT JOIN {{ ref('mart_seller_features') }} sf ON sf.seller_id = p.seller_id
LEFT JOIN {{ ref('dim_seller_health') }} h ON h.health_tier = coalesce(sf.health_tier, 'Ổn định')
    AND h.size_band = CASE WHEN p.n_orders < 6 THEN 'Dưới 6 đơn' WHEN p.n_orders <= 30 THEN '6-30 đơn' ELSE 'Trên 30 đơn' END
    AND h.late_band = CASE WHEN p.seller_late_rate IS NULL THEN 'Chưa rõ' WHEN p.seller_late_rate <= 0.05 THEN 'Đến 5%' WHEN p.seller_late_rate <= 0.15 THEN '5-15%' WHEN p.seller_late_rate <= 0.30 THEN '15-30%' ELSE 'Trên 30%' END
    AND h.review_band = CASE WHEN p.avg_review IS NULL THEN 'Chưa rõ' WHEN p.avg_review < 3.5 THEN 'Dưới 3,5' WHEN p.avg_review <= 4.2 THEN '3,5-4,2' ELSE 'Trên 4,2' END
