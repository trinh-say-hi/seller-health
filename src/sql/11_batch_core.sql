-- Gold, phan core: cap nhat cho mot dot. Chay lai cung dot khong tao dong trung.

DELETE FROM core.fact_sales_item WHERE dwh_batch = getvariable('batch');
DELETE FROM core.fact_payment WHERE dwh_batch = getvariable('batch');

-- Transaction fact: seller_key la dong SCD2 co hieu luc luc mua.
INSERT INTO core.fact_sales_item
SELECT i.order_id, i.order_item_id, coalesce(p.product_key, -1), coalesce(s.seller_key, -1), i.seller_id,
       coalesce(dc.customer_key, -1), coalesce(r.route_key, -1), coalesce(lc.location_key, -1), coalesce(ls.location_key, -1),
       core.date_key(o.purchase_ts), core.date_key(i.shipping_limit_ts), o.purchase_ts, i.shipping_limit_ts, i.price, i.freight_value, 1,
       o.order_status NOT IN ('canceled','unavailable'), i.dwh_batch
FROM stg.items i
JOIN stg.orders o USING (order_id)
LEFT JOIN stg.customers c ON c.customer_id = o.customer_id
LEFT JOIN core.dim_customer dc ON dc.customer_unique_id = c.customer_unique_id
LEFT JOIN core.dim_product p ON p.product_id = i.product_id
LEFT JOIN core.dim_seller s ON s.seller_id = i.seller_id AND o.purchase_ts >= s.valid_from AND o.purchase_ts < s.valid_to
LEFT JOIN core.dim_route r ON r.seller_state = s.state AND r.customer_state = c.state
LEFT JOIN core.dim_location lc ON lc.zip_prefix = c.zip_prefix
LEFT JOIN core.dim_location ls ON ls.zip_prefix = s.zip_prefix
WHERE i.dwh_batch = getvariable('batch');

INSERT INTO core.fact_payment
SELECT pm.order_id, pm.payment_sequential, pm.payment_type, pm.payment_installments, pm.payment_value,
       coalesce(dc.customer_key, -1), core.date_key(o.purchase_ts), pm.dwh_batch
FROM stg.payments pm
JOIN stg.orders o USING (order_id)
LEFT JOIN stg.customers c ON c.customer_id = o.customer_id
LEFT JOIN core.dim_customer dc ON dc.customer_unique_id = c.customer_unique_id
WHERE pm.dwh_batch = getvariable('batch');

-- Accumulating snapshot: tinh lai cac don co ban moi hoac review moi trong dot.
CREATE OR REPLACE TEMP TABLE _aff AS
SELECT order_id FROM raw.orders WHERE dwh_batch = getvariable('batch')
UNION SELECT order_id FROM raw.order_reviews WHERE dwh_batch = getvariable('batch');

DELETE FROM core.fact_order_seller WHERE order_id IN (SELECT order_id FROM _aff);
DELETE FROM core.fact_order WHERE order_id IN (SELECT order_id FROM _aff);
DELETE FROM core.fact_review WHERE order_id IN (SELECT order_id FROM _aff);

INSERT INTO core.fact_order_seller
WITH a AS (
    SELECT order_id, seller_id, sum(price) AS order_value, sum(freight_value) AS freight_total,
           count(*) AS n_items, max(shipping_limit_ts) AS shipping_limit_ts
    FROM stg.items WHERE order_id IN (SELECT order_id FROM _aff) GROUP BY order_id, seller_id)
SELECT o.order_id, a.seller_id, coalesce(s.seller_key, -1), coalesce(dc.customer_key, -1), coalesce(r.route_key, -1),
       coalesce(lc.location_key, -1), coalesce(ls.location_key, -1),
       core.date_key(o.purchase_ts), core.date_key(o.approved_ts), core.date_key(o.carrier_ts),
       core.date_key(o.delivered_ts), core.date_key(o.estimated_ts),
       o.purchase_ts, o.approved_ts, o.carrier_ts, o.delivered_ts, o.estimated_ts,
       a.shipping_limit_ts, o.order_status,
       date_sub('second', o.purchase_ts, o.approved_ts) / 86400.0,
       date_sub('second', o.purchase_ts, o.carrier_ts) / 86400.0,
       date_sub('second', o.carrier_ts, o.delivered_ts) / 86400.0,
       date_diff('day', CAST(o.estimated_ts AS DATE), CAST(o.delivered_ts AS DATE)),
       o.carrier_ts > a.shipping_limit_ts,
       CAST(o.delivered_ts AS DATE) > CAST(o.estimated_ts AS DATE),
       rv.review_score, rv.has_comment, rv.first_review_ts,
       coalesce(a.order_value, 0), coalesce(a.freight_total, 0), coalesce(a.n_items, 0),
       o.first_batch, o.last_batch, o.n_versions
FROM stg.orders o
JOIN _aff USING (order_id)
LEFT JOIN a USING (order_id)
LEFT JOIN stg.reviews_by_order rv USING (order_id)
LEFT JOIN stg.customers c ON c.customer_id = o.customer_id
LEFT JOIN core.dim_customer dc ON dc.customer_unique_id = c.customer_unique_id
LEFT JOIN core.dim_seller s ON s.seller_id = a.seller_id AND o.purchase_ts >= s.valid_from AND o.purchase_ts < s.valid_to
LEFT JOIN core.dim_route r ON r.seller_state = s.state AND r.customer_state = c.state
LEFT JOIN core.dim_location lc ON lc.zip_prefix = c.zip_prefix
LEFT JOIN core.dim_location ls ON ls.zip_prefix = s.zip_prefix;

INSERT INTO core.fact_order
WITH a AS (
    SELECT order_id, sum(n_items) AS n_items, count(*) FILTER (WHERE seller_id IS NOT NULL) AS n_sellers,
           sum(order_value) AS items_price_total, sum(freight_total) AS freight_total, bool_or(seller_late) AS any_seller_late
    FROM core.fact_order_seller WHERE order_id IN (SELECT order_id FROM _aff) GROUP BY order_id),
p AS (SELECT order_id, sum(payment_value) AS payment_total, count(*) AS payment_count FROM stg.payments
      WHERE order_id IN (SELECT order_id FROM _aff) GROUP BY order_id)
SELECT o.order_id, coalesce(dc.customer_key, -1), coalesce(lc.location_key, -1), st.status_key,
       core.date_key(o.purchase_ts), core.date_key(o.approved_ts), core.date_key(o.carrier_ts),
       core.date_key(o.delivered_ts), core.date_key(o.estimated_ts),
       o.purchase_ts, o.approved_ts, o.carrier_ts, o.delivered_ts, o.estimated_ts,
       date_sub('second', o.purchase_ts, o.approved_ts) / 86400.0,
       date_sub('second', o.purchase_ts, o.carrier_ts) / 86400.0,
       date_sub('second', o.carrier_ts, o.delivered_ts) / 86400.0,
       date_diff('day', CAST(o.estimated_ts AS DATE), CAST(o.delivered_ts AS DATE)),
       CAST(o.delivered_ts AS DATE) > CAST(o.estimated_ts AS DATE),
       a.any_seller_late,
       a.n_items, a.n_sellers, a.items_price_total, a.freight_total, a.items_price_total + a.freight_total,
       coalesce(p.payment_total, 0), coalesce(p.payment_count, 0),
       rv.review_score, rv.first_review_ts,
       st.is_canceled,
       (o.order_status = 'delivered' AND o.delivered_ts IS NULL) OR (o.order_status <> 'delivered' AND o.delivered_ts IS NOT NULL),
       coalesce(o.carrier_ts < o.purchase_ts, FALSE) OR coalesce(o.delivered_ts < o.carrier_ts, FALSE) OR coalesce(o.approved_ts < o.purchase_ts, FALSE),
       o.first_batch, o.last_batch, o.n_versions
FROM stg.orders o
JOIN _aff USING (order_id)
LEFT JOIN a USING (order_id)
LEFT JOIN p USING (order_id)
LEFT JOIN stg.reviews_by_order rv USING (order_id)
LEFT JOIN core.dim_order_status st ON st.status = o.order_status
LEFT JOIN stg.customers c ON c.customer_id = o.customer_id
LEFT JOIN core.dim_customer dc ON dc.customer_unique_id = c.customer_unique_id
LEFT JOIN core.dim_location lc ON lc.zip_prefix = c.zip_prefix;

-- Co truoc/sau khi nhan duoc tinh lai moi khi don co ngay giao moi.
INSERT INTO core.fact_review
SELECT r.review_id, r.order_id, coalesce(dc.customer_key, -1),
       core.date_key(r.created_ts), core.date_key(r.review_ts), r.created_ts, r.review_ts,
       r.review_score, r.has_title, r.has_comment,
       date_sub('second', r.created_ts, r.review_ts) / 3600.0,
       CAST(o.delivered_ts AS DATE) > CAST(o.estimated_ts AS DATE),
       o.delivered_ts IS NULL OR r.review_ts < o.delivered_ts,
       r.dwh_batch
FROM stg.reviews r
JOIN _aff USING (order_id)
JOIN stg.orders o USING (order_id)
LEFT JOIN stg.customers c ON c.customer_id = o.customer_id
LEFT JOIN core.dim_customer dc ON dc.customer_unique_id = c.customer_unique_id;
