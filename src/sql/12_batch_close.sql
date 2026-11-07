-- Chot thang: tinh snapshot tu trang thai kho TAI moc c, roi dong bang.
-- Vi kho chua co du lieu sau c, feature tu nhien khong nhin duoc tuong lai.
-- Bien: c (moc chot, TIMESTAMP), m0 (dau thang dang chot).

DELETE FROM mart.seller_features WHERE as_of = CAST(getvariable('c') AS DATE);
DELETE FROM core.fact_seller_monthly WHERE month = CAST(getvariable('m0') AS DATE);
DELETE FROM mart.kpi_monthly WHERE month = CAST(getvariable('m0') AS DATE);
DELETE FROM mart.route_delivery WHERE as_of = CAST(getvariable('c') AS DATE);
DELETE FROM mart.seller_tier_monthly WHERE as_of = CAST(getvariable('c') AS DATE);

CREATE OR REPLACE TEMP TABLE _w AS
SELECT i.seller_id, i.seller_key, i.order_id, i.purchase_ts AS ts, CAST(i.price AS DOUBLE) AS price, i.shipping_limit_ts AS lim,
       p.category_en, ds.region, f.carrier_ts, f.delivered_ts, f.estimated_ts, f.review_score, f.first_review_ts,
       f.days_in_transit, i.is_valid_sale
FROM core.fact_sales_item i
JOIN core.dim_product p USING (product_key)
JOIN core.dim_seller ds ON ds.seller_key = i.seller_key
JOIN core.fact_order_seller f ON f.order_id = i.order_id AND f.seller_id = i.seller_id;

-- Bang feature cho DSS: seller co ban trong 90 ngay truoc c.
INSERT INTO mart.seller_features
WITH h AS (
    SELECT seller_id, max(ts) AS last_ts, min(ts) AS first_ts FROM _w WHERE is_valid_sale GROUP BY seller_id),
w AS (SELECT * FROM _w WHERE is_valid_sale AND ts >= getvariable('c') - INTERVAL 90 DAY),
late_orders AS (
    SELECT seller_id, order_id, bool_or(carrier_ts IS NOT NULL AND carrier_ts <= lim) AS seller_ok
    FROM w WHERE estimated_ts < getvariable('c')
      AND (delivered_ts IS NULL OR CAST(delivered_ts AS DATE) > CAST(estimated_ts AS DATE))
    GROUP BY seller_id, order_id),
lo AS (SELECT seller_id, count(*) AS n_late, count(*) FILTER (WHERE seller_ok) AS n_ok FROM late_orders GROUP BY seller_id),
a AS (
    SELECT seller_id,
           sum(price) AS gmv_90, count(DISTINCT order_id) AS orders_90,
           coalesce(sum(price) FILTER (WHERE ts >= getvariable('c') - INTERVAL 30 DAY), 0) AS gmv_30,
           count(DISTINCT order_id) FILTER (WHERE ts >= getvariable('c') - INTERVAL 30 DAY) AS orders_30,
           count(DISTINCT category_en) AS n_cat,
           avg(CASE WHEN carrier_ts IS NULL OR carrier_ts > lim THEN 1.0 ELSE 0.0 END) FILTER (WHERE lim < getvariable('c')) AS seller_late_rate,
           count(*) FILTER (WHERE lim < getvariable('c')) AS n_limit_known,
           avg(CASE WHEN delivered_ts IS NULL OR CAST(delivered_ts AS DATE) > CAST(estimated_ts AS DATE) THEN 1.0 ELSE 0.0 END)
               FILTER (WHERE estimated_ts < getvariable('c')) AS cust_late_rate,
           avg(review_score) FILTER (WHERE first_review_ts < getvariable('c')) AS avg_review,
           avg(date_sub('second', ts, carrier_ts) / 86400.0) FILTER (WHERE carrier_ts < getvariable('c')) AS days_to_carrier
    FROM w GROUP BY seller_id)
SELECT CAST(getvariable('c') AS DATE), a.seller_id, a.gmv_90, a.orders_90, a.gmv_30, a.orders_30,
       a.gmv_30 / nullif(a.gmv_90 / 3, 0) - 1,
       date_sub('second', h.last_ts, getvariable('c')) / 86400.0,
       date_sub('second', h.first_ts, getvariable('c')) / 86400.0,
       a.n_cat, a.seller_late_rate, a.cust_late_rate, a.avg_review, a.days_to_carrier, a.n_limit_known,
       coalesce(lo.n_late, 0), coalesce(lo.n_ok, 0), NULL
FROM a JOIN h USING (seller_id) LEFT JOIN lo USING (seller_id);

-- Hang suc khoe: luat minh bach, ap dung tai moc c.
UPDATE mart.seller_features f SET health_tier = t.tier
FROM (
    SELECT seller_id,
           CASE WHEN recency > 45 THEN 'Tạm ngừng'
                WHEN orders_90 < 6 THEN 'Ít đơn'
                WHEN (trend < -0.5 AND recency > 21) OR (seller_late_rate >= 0.30 AND n_limit_known >= 5) THEN 'Nguy cơ'
                WHEN trend < -0.40 OR (seller_late_rate >= 0.15 AND n_limit_known >= 5) OR avg_review < 3.5 THEN 'Theo dõi'
                WHEN gmv_90 >= quantile_cont(gmv_90, 0.8) OVER () THEN 'Vàng'
                ELSE 'Ổn định' END AS tier
    FROM mart.seller_features WHERE as_of = CAST(getvariable('c') AS DATE)) t
WHERE f.seller_id = t.seller_id AND f.as_of = CAST(getvariable('c') AS DATE);

-- Periodic snapshot theo seller x thang. Moi chi so theo thang xay ra su kien, nen da chin luc chot.
INSERT INTO core.fact_seller_monthly
WITH cur AS (SELECT seller_id, seller_key FROM core.dim_seller WHERE is_current),
base AS (
    SELECT seller_id FROM mart.seller_features WHERE as_of = CAST(getvariable('c') AS DATE)
    UNION SELECT seller_id FROM _w WHERE is_valid_sale AND ts >= getvariable('m0')),
m AS (
    SELECT seller_id,
           count(DISTINCT order_id) FILTER (WHERE ts >= getvariable('m0')) AS n_orders,
           count(*) FILTER (WHERE ts >= getvariable('m0')) AS n_items,
           coalesce(sum(price) FILTER (WHERE ts >= getvariable('m0')), 0) AS gmv,
           coalesce(sum(price) FILTER (WHERE ts >= getvariable('m0') - INTERVAL 3 MONTH AND ts < getvariable('m0')), 0) / 3 AS gmv_prev,
           avg(CASE WHEN carrier_ts IS NULL OR carrier_ts > lim THEN 1.0 ELSE 0.0 END)
               FILTER (WHERE lim >= getvariable('m0') AND lim < getvariable('c')) AS seller_late_rate,
           avg(CASE WHEN delivered_ts IS NULL OR CAST(delivered_ts AS DATE) > CAST(estimated_ts AS DATE) THEN 1.0 ELSE 0.0 END)
               FILTER (WHERE estimated_ts >= getvariable('m0') AND estimated_ts < getvariable('c')) AS customer_late_rate,
           avg(review_score) FILTER (WHERE first_review_ts >= getvariable('m0') AND first_review_ts < getvariable('c')) AS avg_review,
           avg(date_sub('second', ts, carrier_ts) / 86400.0) FILTER (WHERE carrier_ts >= getvariable('m0') AND carrier_ts < getvariable('c')) AS d_carrier,
           avg(days_in_transit) FILTER (WHERE delivered_ts >= getvariable('m0') AND delivered_ts < getvariable('c')) AS d_transit,
           date_sub('second', max(ts), getvariable('c')) / 86400.0 AS recency,
           count(DISTINCT category_en) FILTER (WHERE ts >= getvariable('m0')) AS n_cat
    FROM _w WHERE is_valid_sale GROUP BY seller_id)
SELECT CAST(getvariable('m0') AS DATE), core.date_key(getvariable('m0')), cur.seller_key, coalesce(h.health_key, -1), b.seller_id,
       m.n_orders, m.n_items, m.gmv, m.gmv_prev, m.seller_late_rate, m.customer_late_rate, m.avg_review,
       m.d_carrier, m.d_transit, m.recency, m.n_cat
FROM base b JOIN m USING (seller_id) JOIN cur USING (seller_id)
LEFT JOIN mart.seller_features sf ON sf.seller_id = b.seller_id AND sf.as_of = CAST(getvariable('c') AS DATE)
LEFT JOIN core.dim_seller_health h ON h.health_tier = sf.health_tier
    AND h.size_band = CASE WHEN sf.orders_90 < 6 THEN 'Dưới 6 đơn' WHEN sf.orders_90 <= 30 THEN '6-30 đơn' ELSE 'Trên 30 đơn' END
    AND h.late_band = CASE WHEN sf.seller_late_rate IS NULL THEN 'Chưa rõ' WHEN sf.seller_late_rate <= 0.05 THEN 'Đến 5%' WHEN sf.seller_late_rate <= 0.15 THEN '5-15%' WHEN sf.seller_late_rate <= 0.30 THEN '15-30%' ELSE 'Trên 30%' END
    AND h.review_band = CASE WHEN sf.avg_review IS NULL THEN 'Chưa rõ' WHEN sf.avg_review < 3.5 THEN 'Dưới 3,5' WHEN sf.avg_review <= 4.2 THEN '3,5-4,2' ELSE 'Trên 4,2' END;

-- KPI toan san: moi thuoc do theo thang xay ra su kien, tinh san bang CUBE.
INSERT INTO mart.kpi_monthly
WITH e AS (
    SELECT *,
           is_valid_sale AND ts >= getvariable('m0') AS in_sale,
           is_valid_sale AND estimated_ts >= getvariable('m0') AND estimated_ts < getvariable('c') AS in_due,
           is_valid_sale AND first_review_ts >= getvariable('m0') AND first_review_ts < getvariable('c') AS in_rev,
           delivered_ts IS NULL OR CAST(delivered_ts AS DATE) > CAST(estimated_ts AS DATE) AS is_late
    FROM _w)
SELECT CAST(getvariable('m0') AS DATE), region, category_en, GROUPING(region) = 1, GROUPING(category_en) = 1,
       coalesce(sum(price) FILTER (WHERE in_sale), 0),
       count(DISTINCT order_id) FILTER (WHERE in_sale),
       count(DISTINCT seller_id) FILTER (WHERE in_sale),
       count(DISTINCT order_id) FILTER (WHERE in_due),
       count(DISTINCT order_id) FILTER (WHERE in_due AND is_late),
       avg(review_score) FILTER (WHERE in_rev)
FROM e WHERE in_sale OR in_due OR in_rev
GROUP BY CUBE (region, category_en);

-- Tuyen: don da giao trong 180 ngay truoc c.
INSERT INTO mart.route_delivery
SELECT CAST(getvariable('c') AS DATE), r.route_key, r.route_name, r.seller_state, r.customer_state,
       count(*), median(date_sub('second', f.purchase_ts, f.delivered_ts) / 86400.0),
       quantile_cont(date_sub('second', f.purchase_ts, f.delivered_ts) / 86400.0, 0.9),
       avg(date_diff('day', CAST(f.purchase_ts AS DATE), CAST(f.estimated_ts AS DATE))),
       avg(CASE WHEN f.customer_late THEN 1.0 ELSE 0.0 END),
       avg(CASE WHEN NOT coalesce(f.seller_late, FALSE) THEN 1.0 ELSE 0.0 END) FILTER (WHERE f.customer_late)
FROM core.fact_order_seller f JOIN core.dim_route r USING (route_key)
WHERE f.delivered_ts < getvariable('c') AND f.purchase_ts >= getvariable('c') - INTERVAL 180 DAY AND f.route_key <> -1
GROUP BY ALL;

-- Hang tho cua moi seller tai moc c.
INSERT INTO mart.seller_tier_monthly
SELECT CAST(getvariable('c') AS DATE), s.seller_id,
       coalesce(f.health_tier,
                CASE WHEN s.seller_id IN (SELECT seller_id FROM _w WHERE is_valid_sale) THEN 'Tạm ngừng' ELSE 'Chưa hoạt động' END)
FROM core.dim_seller s
LEFT JOIN mart.seller_features f ON f.seller_id = s.seller_id AND f.as_of = CAST(getvariable('c') AS DATE)
WHERE s.is_current AND s.seller_key <> -1;

-- SCD2: hang on dinh chi doi khi hang tho giu nguyen 2 ky lien tiep, tru lan dau seller bat dau ban.
-- Dao dong ngan han nam o mini-dimension dim_seller_health va mart.seller_tier_monthly.
CREATE OR REPLACE TEMP TABLE _chg AS
SELECT s.seller_key, s.seller_id, s.zip_prefix, s.city, s.state, s.region, t.health_tier AS tier
FROM core.dim_seller s
JOIN mart.seller_tier_monthly t ON t.seller_id = s.seller_id AND t.as_of = CAST(getvariable('c') AS DATE)
LEFT JOIN mart.seller_tier_monthly p ON p.seller_id = s.seller_id AND p.as_of = CAST(getvariable('c') - INTERVAL 1 MONTH AS DATE)
WHERE s.is_current AND s.health_tier <> t.health_tier
  AND (s.health_tier = 'Chưa hoạt động' OR p.health_tier = t.health_tier);

UPDATE core.dim_seller SET valid_to = getvariable('c'), is_current = FALSE
WHERE seller_key IN (SELECT seller_key FROM _chg);

INSERT INTO core.dim_seller
SELECT (SELECT max(seller_key) FROM core.dim_seller) + row_number() OVER (ORDER BY seller_id),
       seller_id, zip_prefix, city, state, region, tier, getvariable('c'), TIMESTAMP '9999-12-31', TRUE
FROM _chg;
