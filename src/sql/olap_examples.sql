-- Truy van OLAP mau tren kho. Moi cau tra loi mot cau hoi nghiep vu.
-- Chay thu: tests/test_system.py chay tung cau va kiem tra co ket qua.

-- ROLL-UP: GMV tu thang len quy, len nam, kem dong tong.
SELECT d.year, d.quarter, d.month, sum(f.price) AS gmv, count(DISTINCT f.order_id) AS n_orders
FROM core.fact_sales_item f JOIN core.dim_date d ON f.purchase_date_key = d.date_key
WHERE f.is_valid_sale
GROUP BY ROLLUP (d.year, d.quarter, d.month)
ORDER BY d.year NULLS LAST, d.quarter NULLS LAST, d.month NULLS LAST;

-- DRILL-DOWN: tu vung xuong bang, xuong seller. Dung dong SCD2 co hieu luc luc mua.
SELECT s.region, s.state, s.seller_id, sum(f.price) AS gmv
FROM core.fact_sales_item f JOIN core.dim_seller s USING (seller_key)
WHERE f.is_valid_sale AND s.region = 'Sudeste' AND s.state = 'SP'
GROUP BY s.region, s.state, s.seller_id
ORDER BY gmv DESC LIMIT 20;

-- SLICE: chi danh muc housewares, GMV va review theo thang.
SELECT d.year_month, sum(f.price) AS gmv, avg(o.review_score) AS avg_review
FROM core.fact_sales_item f
JOIN core.dim_product p USING (product_key)
JOIN core.dim_date d ON f.purchase_date_key = d.date_key
JOIN core.fact_order_seller o ON o.order_id = f.order_id AND o.seller_id = f.seller_id
WHERE p.category_en = 'housewares' AND f.is_valid_sale
GROUP BY d.year_month ORDER BY d.year_month;

-- DICE: khach o bang SP, quy 4/2017, don giao tre.
SELECT d.year_month, r.route_name, count(*) AS n_late, avg(o.delay_days) AS avg_delay
FROM core.fact_order_seller o
JOIN core.dim_route r USING (route_key)
JOIN core.dim_date d ON o.purchase_date_key = d.date_key
WHERE r.customer_state = 'SP' AND d.year = 2017 AND d.quarter = 4 AND o.customer_late
GROUP BY d.year_month, r.route_name ORDER BY n_late DESC LIMIT 20;

-- PIVOT: GMV theo thang x hang suc khoe tai luc ban.
PIVOT (
    SELECT d.year_month, s.health_tier, f.price
    FROM core.fact_sales_item f
    JOIN core.dim_seller s USING (seller_key)
    JOIN core.dim_date d ON f.purchase_date_key = d.date_key
    WHERE f.is_valid_sale AND d.year = 2018
) ON health_tier USING sum(price) GROUP BY year_month ORDER BY year_month;

-- CUBE: mart KPI tinh san, lay tong theo vung cua mot thang.
SELECT region, gmv, n_orders, n_late_orders * 1.0 / nullif(n_due_orders, 0) AS late_rate, avg_review
FROM mart.kpi_monthly
WHERE month = DATE '2018-06-01' AND is_all_category AND NOT is_all_region
ORDER BY gmv DESC;

-- SCD2: phan bo hang tai mot thoi diem bat ky trong qua khu.
SELECT health_tier, count(*) AS n_sellers
FROM core.dim_seller
WHERE valid_from <= TIMESTAMP '2018-01-15' AND valid_to > TIMESTAMP '2018-01-15' AND seller_key <> -1
GROUP BY health_tier ORDER BY n_sellers DESC;

-- ROLE-PLAYING: mot dim_date dung cho ngay mua va ngay giao, so don Black Friday 2017.
SELECT dp.full_date AS ngay_mua, count(*) AS n_orders, avg(CASE WHEN o.customer_late THEN 1.0 ELSE 0.0 END) AS late_rate,
       median(dd.full_date - dp.full_date) AS ngay_giao_trung_vi
FROM core.fact_order_seller o
JOIN core.dim_date dp ON o.purchase_date_key = dp.date_key
JOIN core.dim_date dd ON o.delivered_date_key = dd.date_key
WHERE dp.is_black_friday
GROUP BY dp.full_date;
