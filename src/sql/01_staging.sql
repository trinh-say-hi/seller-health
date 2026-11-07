-- Silver. Giao dich la view tren raw, vi thay doi moi dot. Master data duoc lam sach va luu thanh bang mot lan.

CREATE VIEW stg.orders AS
SELECT order_id, customer_id, order_status,
       CAST(order_purchase_timestamp AS TIMESTAMP) AS purchase_ts,
       TRY_CAST(order_approved_at AS TIMESTAMP) AS approved_ts,
       TRY_CAST(order_delivered_carrier_date AS TIMESTAMP) AS carrier_ts,
       TRY_CAST(order_delivered_customer_date AS TIMESTAMP) AS delivered_ts,
       TRY_CAST(order_estimated_delivery_date AS TIMESTAMP) AS estimated_ts,
       min(dwh_batch) OVER w AS first_batch,
       max(dwh_batch) OVER w AS last_batch,
       count(*) OVER w AS n_versions
FROM raw.orders
WINDOW w AS (PARTITION BY order_id)
QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY dwh_batch DESC) = 1;

CREATE VIEW stg.items AS
SELECT order_id, CAST(order_item_id AS INTEGER) AS order_item_id, product_id, seller_id,
       CAST(shipping_limit_date AS TIMESTAMP) AS shipping_limit_ts,
       CAST(price AS DECIMAL(12,2)) AS price,
       CAST(freight_value AS DECIMAL(12,2)) AS freight_value,
       dwh_batch
FROM raw.order_items
WHERE TRY_CAST(price AS DECIMAL(12,2)) > 0;

CREATE VIEW stg.payments AS
SELECT order_id, CAST(payment_sequential AS INTEGER) AS payment_sequential, payment_type,
       CAST(payment_installments AS INTEGER) AS payment_installments,
       CAST(payment_value AS DECIMAL(12,2)) AS payment_value, dwh_batch
FROM raw.order_payments
WHERE TRY_CAST(payment_value AS DECIMAL(12,2)) >= 0;

-- review_ts la luc khach tra loi: chi tu luc nay kho moi biet diem.
CREATE VIEW stg.reviews AS
SELECT review_id, order_id, CAST(review_score AS INTEGER) AS review_score,
       review_comment_title IS NOT NULL AND trim(review_comment_title) <> '' AS has_title,
       review_comment_message IS NOT NULL AND trim(review_comment_message) <> '' AS has_comment,
       TRY_CAST(review_creation_date AS TIMESTAMP) AS created_ts,
       CAST(review_answer_timestamp AS TIMESTAMP) AS review_ts, dwh_batch
FROM raw.order_reviews
WHERE TRY_CAST(review_score AS INTEGER) BETWEEN 1 AND 5
  AND TRY_CAST(review_answer_timestamp AS TIMESTAMP) IS NOT NULL;

-- Mot don co the co nhieu review: gop truoc khi noi de khong nhan dong.
CREATE VIEW stg.reviews_by_order AS
SELECT order_id, avg(review_score) AS review_score, count(*) AS n_reviews,
       bool_or(has_comment) AS has_comment, min(review_ts) AS first_review_ts
FROM stg.reviews GROUP BY order_id;

-- ===== Master data =====

-- Toa do ngoai lanh tho Brazil la loi, dua vao cach ly va khong tinh vao trung vi.
CREATE TEMP TABLE _geo AS
SELECT geolocation_zip_code_prefix AS zip_prefix, TRY_CAST(geolocation_lat AS DOUBLE) AS lat, TRY_CAST(geolocation_lng AS DOUBLE) AS lng,
       stg.clean_city(geolocation_city) AS city, upper(trim(geolocation_state)) AS state
FROM raw.geolocation;

INSERT INTO ops.quarantine
SELECT 'init', 'geolocation', zip_prefix || '|' || lat || '|' || lng, 'GEO_OUTSIDE_BRAZIL', 'Toa do nam ngoai khung lanh tho Brazil'
FROM _geo WHERE lat NOT BETWEEN -34 AND 6 OR lng NOT BETWEEN -74 AND -34;

CREATE TABLE stg.geography AS
SELECT zip_prefix,
       median(lat) FILTER (WHERE lat BETWEEN -34 AND 6 AND lng BETWEEN -74 AND -34) AS lat,
       median(lng) FILTER (WHERE lat BETWEEN -34 AND 6 AND lng BETWEEN -74 AND -34) AS lng,
       mode(city) AS city, mode(state) AS state
FROM _geo GROUP BY zip_prefix;

-- Tap ten thanh pho hop le lay tu geolocation, dung de nhan ra ten sai.
-- Ten 2 ky tu la ma bang, khong phai ten thanh pho (geolocation cung co dong ghi 'sp').
CREATE TEMP TABLE _known_city AS SELECT DISTINCT city FROM _geo WHERE city IS NOT NULL AND length(city) > 2;

-- Giu ten da chuan hoa neu co that; neu khong thi lay theo ZIP; khong co ZIP thi giu ban chuan hoa.
CREATE TABLE stg.sellers AS
WITH a AS (SELECT seller_id, seller_zip_code_prefix AS zip_prefix, seller_city AS city_raw, stg.clean_city(seller_city) AS cand, upper(trim(seller_state)) AS state FROM raw.sellers)
SELECT a.seller_id, a.zip_prefix, a.city_raw,
       CASE WHEN a.cand IN (SELECT city FROM _known_city) THEN a.cand ELSE coalesce(g.city, a.cand, 'khong ro') END AS city,
       CASE WHEN a.cand IN (SELECT city FROM _known_city) THEN 'chuan_hoa' WHEN g.city IS NOT NULL THEN 'theo_zip' WHEN a.cand IS NOT NULL THEN 'chuan_hoa_chua_doi_chieu' ELSE 'khong_ro' END AS city_source,
       a.state
FROM a LEFT JOIN stg.geography g USING (zip_prefix);

CREATE TABLE stg.customers AS
WITH a AS (SELECT customer_id, customer_unique_id, customer_zip_code_prefix AS zip_prefix, customer_city AS city_raw, stg.clean_city(customer_city) AS cand, upper(trim(customer_state)) AS state FROM raw.customers)
SELECT a.customer_id, a.customer_unique_id, a.zip_prefix, a.city_raw,
       CASE WHEN a.cand IN (SELECT city FROM _known_city) THEN a.cand ELSE coalesce(g.city, a.cand, 'khong ro') END AS city,
       a.state
FROM a LEFT JOIN stg.geography g USING (zip_prefix);

-- Hai danh muc co trong products nhung thieu trong bang dich cua nguon.
CREATE TABLE stg.category_translation AS
SELECT product_category_name, product_category_name_english FROM raw.category_translation
UNION ALL SELECT * FROM (VALUES ('pc_gamer', 'pc_gamer'),
                                ('portateis_cozinha_e_preparadores_de_alimentos', 'portable_kitchen_and_food_preparators')) v(a, b);

CREATE TABLE stg.products AS
SELECT p.product_id,
       coalesce(t.product_category_name_english, 'Unknown') AS category_en,
       TRY_CAST(p.product_weight_g AS DOUBLE) AS weight_g,
       TRY_CAST(p.product_length_cm AS DOUBLE) * TRY_CAST(p.product_height_cm AS DOUBLE)
           * TRY_CAST(p.product_width_cm AS DOUBLE) AS volume_cm3,
       TRY_CAST(p.product_photos_qty AS INTEGER) AS photos_qty
FROM raw.products p
LEFT JOIN stg.category_translation t ON p.product_category_name = t.product_category_name;
