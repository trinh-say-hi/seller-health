-- Dimension va bang fact rong. Chay mot lan sau khi nap master data.

CREATE TABLE core.dim_date AS
WITH d AS (SELECT CAST(x AS DATE) AS full_date FROM generate_series(DATE '2016-01-01', DATE '2020-12-31', INTERVAL 1 DAY) t(x)),
holiday AS (
    SELECT * FROM (VALUES
        (DATE '2016-02-09'),(DATE '2016-03-25'),(DATE '2017-02-28'),(DATE '2017-04-14'),
        (DATE '2018-02-13'),(DATE '2018-03-30'),(DATE '2019-03-05'),(DATE '2019-04-19'),
        (DATE '2020-02-25'),(DATE '2020-04-10')) v(h))
SELECT core.date_key(full_date) AS date_key, full_date,
       year(full_date) AS year, quarter(full_date) AS quarter, month(full_date) AS month,
       strftime(full_date, '%Y-%m') AS year_month, weekofyear(full_date) AS week,
       isodow(full_date) AS day_of_week, isodow(full_date) >= 6 AS is_weekend,
       strftime(full_date, '%m-%d') IN ('01-01','04-21','05-01','09-07','10-12','11-02','11-15','12-25')
           OR full_date IN (SELECT h FROM holiday) AS is_holiday_br,
       full_date IN (DATE '2016-11-25', DATE '2017-11-24', DATE '2018-11-23', DATE '2019-11-29', DATE '2020-11-27') AS is_black_friday
FROM d;

-- Moi ZIP xuat hien o bat ky nguon nao la mot dong. ZIP khong co trong geolocation van co dong, toa do NULL.
CREATE TABLE core.dim_location AS
WITH z AS (
    SELECT zip_prefix FROM stg.geography
    UNION SELECT zip_prefix FROM stg.customers
    UNION SELECT zip_prefix FROM stg.sellers),
c AS (SELECT zip_prefix, mode(city ORDER BY city) AS city, mode(state ORDER BY state) AS state FROM stg.customers GROUP BY 1),
s AS (SELECT zip_prefix, mode(city ORDER BY city) AS city, mode(state ORDER BY state) AS state FROM stg.sellers GROUP BY 1)
SELECT -1 AS location_key, 'UNKNOWN' AS zip_prefix, 'khong ro' AS city, NULL AS state, 'Khong ro' AS region,
       NULL::DOUBLE AS lat, NULL::DOUBLE AS lng, FALSE AS has_coordinates
UNION ALL
SELECT row_number() OVER (ORDER BY z.zip_prefix), z.zip_prefix,
       coalesce(g.city, c.city, s.city, 'khong ro'), coalesce(g.state, c.state, s.state),
       core.region_of(coalesce(g.state, c.state, s.state)), g.lat, g.lng, g.lat IS NOT NULL
FROM z LEFT JOIN stg.geography g USING (zip_prefix) LEFT JOIN c USING (zip_prefix) LEFT JOIN s USING (zip_prefix);

CREATE TABLE core.dim_customer AS
SELECT -1 AS customer_key, 'UNKNOWN' AS customer_unique_id, NULL AS city, NULL AS state
UNION ALL
SELECT row_number() OVER (ORDER BY customer_unique_id), customer_unique_id, mode(city ORDER BY city), mode(state ORDER BY state)
FROM stg.customers GROUP BY customer_unique_id;

CREATE TABLE core.dim_product AS
SELECT -1 AS product_key, 'UNKNOWN' AS product_id, 'Unknown' AS category_en, NULL::DOUBLE AS weight_g,
       NULL::DOUBLE AS volume_cm3, 'Khong ro' AS size_group, NULL::INTEGER AS photos_qty
UNION ALL
SELECT row_number() OVER (ORDER BY product_id), product_id, category_en, weight_g, volume_cm3,
       CASE WHEN volume_cm3 IS NULL THEN 'Khong ro' WHEN volume_cm3 < 2000 THEN 'Nho'
            WHEN volume_cm3 < 15000 THEN 'Vua' ELSE 'Lon' END,
       photos_qty
FROM stg.products;

-- Khoang cach tinh giua tam cac bang: chi la xap xi, khong phai quang duong that.
CREATE TABLE core.dim_route AS
WITH c AS (SELECT state, avg(lat) AS lat, avg(lng) AS lng FROM core.dim_location WHERE has_coordinates GROUP BY state),
ss AS (SELECT DISTINCT state FROM stg.sellers WHERE state IS NOT NULL),
cs AS (SELECT DISTINCT state FROM stg.customers WHERE state IS NOT NULL)
SELECT -1 AS route_key, NULL AS seller_state, NULL AS customer_state, NULL AS route_name, NULL::BOOLEAN AS same_state, NULL::DOUBLE AS distance_km
UNION ALL
SELECT row_number() OVER (ORDER BY ss.state, cs.state), ss.state, cs.state, ss.state || '->' || cs.state, ss.state = cs.state,
       2 * 6371 * asin(sqrt(pow(sin(radians(c2.lat - c1.lat) / 2), 2)
           + cos(radians(c1.lat)) * cos(radians(c2.lat)) * pow(sin(radians(c2.lng - c1.lng) / 2), 2)))
FROM ss CROSS JOIN cs
LEFT JOIN c c1 ON c1.state = ss.state
LEFT JOIN c c2 ON c2.state = cs.state;

CREATE TABLE core.dim_order_status AS
SELECT row_number() OVER (ORDER BY stage, status) AS status_key, status, stage, is_delivered, is_canceled
FROM (VALUES ('created', 1, FALSE, FALSE), ('approved', 2, FALSE, FALSE), ('invoiced', 3, FALSE, FALSE), ('processing', 4, FALSE, FALSE),
             ('shipped', 5, FALSE, FALSE), ('delivered', 6, TRUE, FALSE), ('canceled', 7, FALSE, TRUE), ('unavailable', 8, FALSE, TRUE)) v(status, stage, is_delivered, is_canceled);

-- Mini-dimension: ho so suc khoe thay doi nhanh tach khoi dim_seller. Moi to hop la mot dong, fact_seller_monthly tro toi.
CREATE TABLE core.dim_seller_health AS
SELECT -1 AS health_key, 'Khong ro' AS health_tier, 'Khong ro' AS size_band, 'Khong ro' AS late_band, 'Khong ro' AS review_band
UNION ALL
SELECT row_number() OVER (ORDER BY t, s, l, r), t, s, l, r
FROM (VALUES ('Vàng'), ('Ổn định'), ('Ít đơn'), ('Theo dõi'), ('Nguy cơ'), ('Tạm ngừng')) a(t)
CROSS JOIN (VALUES ('Dưới 6 đơn'), ('6-30 đơn'), ('Trên 30 đơn')) b(s)
CROSS JOIN (VALUES ('Chưa rõ'), ('Đến 5%'), ('5-15%'), ('15-30%'), ('Trên 30%')) c(l)
CROSS JOIN (VALUES ('Chưa rõ'), ('Dưới 3,5'), ('3,5-4,2'), ('Trên 4,2')) d(r);

-- SCD Type 2. Hang on dinh: chi doi khi hang thang giu nguyen 2 ky lien tiep.
CREATE TABLE core.dim_seller AS
SELECT -1 AS seller_key, 'UNKNOWN' AS seller_id, NULL AS zip_prefix, 'khong ro' AS city, NULL AS state, 'Khong ro' AS region,
       'Khong ro' AS health_tier, TIMESTAMP '2016-01-01' AS valid_from, TIMESTAMP '9999-12-31' AS valid_to, TRUE AS is_current
UNION ALL
SELECT row_number() OVER (ORDER BY seller_id), seller_id, zip_prefix, city, state, core.region_of(state),
       'Chưa hoạt động', TIMESTAMP '2016-01-01', TIMESTAMP '9999-12-31', TRUE
FROM stg.sellers;

CREATE TABLE core.fact_sales_item (
    order_id VARCHAR, order_item_id INTEGER, product_key BIGINT, seller_key BIGINT, seller_id VARCHAR,
    customer_key BIGINT, route_key BIGINT, customer_location_key BIGINT, seller_location_key BIGINT,
    purchase_date_key INTEGER, shipping_limit_date_key INTEGER, purchase_ts TIMESTAMP,
    shipping_limit_ts TIMESTAMP, price DECIMAL(12,2), freight_value DECIMAL(12,2), qty INTEGER,
    is_valid_sale BOOLEAN, dwh_batch VARCHAR);

-- Accumulating snapshot, grain 1 don. Moc giao hang thuoc ve don, nen dem don va tinh tre tai day.
CREATE TABLE core.fact_order (
    order_id VARCHAR, customer_key BIGINT, customer_location_key BIGINT, status_key BIGINT,
    purchase_date_key INTEGER, approved_date_key INTEGER, carrier_date_key INTEGER,
    delivered_date_key INTEGER, estimated_date_key INTEGER,
    purchase_ts TIMESTAMP, approved_ts TIMESTAMP, carrier_ts TIMESTAMP, delivered_ts TIMESTAMP, estimated_ts TIMESTAMP,
    days_to_approve DOUBLE, days_to_carrier DOUBLE, days_in_transit DOUBLE, delay_days INTEGER,
    customer_late BOOLEAN, any_seller_late BOOLEAN,
    n_items INTEGER, n_sellers INTEGER, items_price_total DECIMAL(14,2), freight_total DECIMAL(14,2), order_total DECIMAL(14,2),
    payment_total DECIMAL(14,2), payment_count INTEGER,
    review_score DOUBLE, first_review_ts TIMESTAMP,
    is_canceled BOOLEAN, has_status_date_mismatch BOOLEAN, has_chronology_issue BOOLEAN,
    dwh_first_batch VARCHAR, dwh_last_batch VARCHAR, n_versions INTEGER);

-- Accumulating snapshot, grain 1 don x 1 seller. Trach nhiem ban giao thuoc ve seller nen nam o day.
-- Cot moc va review lap lai cho moi seller cua don: khong cong tu bang nay, dung fact_order.
CREATE TABLE core.fact_order_seller (
    order_id VARCHAR, seller_id VARCHAR, seller_key BIGINT, customer_key BIGINT, route_key BIGINT,
    customer_location_key BIGINT, seller_location_key BIGINT,
    purchase_date_key INTEGER, approved_date_key INTEGER, carrier_date_key INTEGER,
    delivered_date_key INTEGER, estimated_date_key INTEGER,
    purchase_ts TIMESTAMP, approved_ts TIMESTAMP, carrier_ts TIMESTAMP, delivered_ts TIMESTAMP, estimated_ts TIMESTAMP,
    shipping_limit_ts TIMESTAMP, order_status VARCHAR,
    days_to_approve DOUBLE, days_to_carrier DOUBLE, days_in_transit DOUBLE, delay_days INTEGER,
    seller_late BOOLEAN, customer_late BOOLEAN,
    review_score DOUBLE, has_comment BOOLEAN, first_review_ts TIMESTAMP,
    order_value DECIMAL(14,2), freight_total DECIMAL(14,2), n_items INTEGER,
    dwh_first_batch VARCHAR, dwh_last_batch VARCHAR, n_versions INTEGER);

-- Transaction, grain review x don. Mot review_id co the dung cho nhieu don.
CREATE TABLE core.fact_review (
    review_id VARCHAR, order_id VARCHAR, customer_key BIGINT,
    created_date_key INTEGER, answered_date_key INTEGER, created_ts TIMESTAMP, answered_ts TIMESTAMP,
    review_score INTEGER, has_title BOOLEAN, has_comment BOOLEAN, answer_hours DOUBLE,
    customer_late BOOLEAN, is_before_delivery BOOLEAN, dwh_batch VARCHAR);

CREATE TABLE core.fact_payment (
    order_id VARCHAR, payment_sequential INTEGER, payment_type VARCHAR, payment_installments INTEGER,
    payment_value DECIMAL(12,2), customer_key BIGINT, purchase_date_key INTEGER, dwh_batch VARCHAR);

-- Periodic snapshot: moi dong dong bang tai luc chot thang, moi chi so tinh theo thang xay ra su kien.
CREATE TABLE core.fact_seller_monthly (
    month DATE, month_key INTEGER, seller_key BIGINT, health_key BIGINT, seller_id VARCHAR,
    n_orders BIGINT, n_items BIGINT, gmv DOUBLE, gmv_prev_3m_avg DOUBLE,
    seller_late_rate DOUBLE, customer_late_rate DOUBLE, avg_review DOUBLE, avg_days_to_carrier DOUBLE,
    avg_days_in_transit DOUBLE, days_since_last_sale DOUBLE, n_categories BIGINT);

CREATE TABLE mart.seller_features (
    as_of DATE, seller_id VARCHAR, gmv_90 DOUBLE, orders_90 BIGINT, gmv_30 DOUBLE, orders_30 BIGINT,
    trend DOUBLE, recency DOUBLE, tenure DOUBLE, n_cat BIGINT,
    seller_late_rate DOUBLE, cust_late_rate DOUBLE, avg_review DOUBLE, days_to_carrier DOUBLE,
    n_limit_known BIGINT, n_cust_late_orders BIGINT, n_cust_late_seller_ok BIGINT, health_tier VARCHAR);

-- Hang tho theo thang cua moi seller, ke ca seller khong hoat dong. Dung de xet dieu kien giu hang 2 ky.
CREATE TABLE mart.seller_tier_monthly (as_of DATE, seller_id VARCHAR, health_tier VARCHAR);

CREATE TABLE mart.kpi_monthly (
    month DATE, region VARCHAR, category_en VARCHAR, is_all_region BOOLEAN, is_all_category BOOLEAN,
    gmv DOUBLE, n_orders BIGINT, n_sellers BIGINT, n_due_orders BIGINT, n_late_orders BIGINT, avg_review DOUBLE);

CREATE TABLE mart.route_delivery (
    as_of DATE, route_key BIGINT, route_name VARCHAR, seller_state VARCHAR, customer_state VARCHAR,
    n_orders BIGINT, median_days DOUBLE, p90_days DOUBLE, avg_promise_days DOUBLE,
    late_rate DOUBLE, late_seller_ok_share DOUBLE);
