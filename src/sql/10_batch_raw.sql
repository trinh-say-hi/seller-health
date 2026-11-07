-- Bronze: nap mot dot. Bien: batch ('YYYY-MM'), c (moc chot), is_final.
-- CSV chi co trang thai cuoi cung, nen moi dot che di cac moc chua xay ra truoc c. Day la gia lap nguon, khong phai bien doi.

DELETE FROM raw.orders WHERE dwh_batch = getvariable('batch');
DELETE FROM raw.order_items WHERE dwh_batch = getvariable('batch');
DELETE FROM raw.order_payments WHERE dwh_batch = getvariable('batch');
DELETE FROM raw.order_reviews WHERE dwh_batch = getvariable('batch');
DELETE FROM ops.quarantine WHERE dwh_batch = getvariable('batch');

CREATE OR REPLACE TEMP TABLE _src_o AS
SELECT *, CAST(order_purchase_timestamp AS TIMESTAMP) AS p,
       TRY_CAST(order_approved_at AS TIMESTAMP) AS a,
       TRY_CAST(order_delivered_carrier_date AS TIMESTAMP) AS car,
       TRY_CAST(order_delivered_customer_date AS TIMESTAMP) AS d
FROM src.orders;

CREATE OR REPLACE TEMP TABLE _known AS
SELECT order_id, customer_id,
       CASE WHEN getvariable('is_final') THEN order_status
            WHEN order_status IN ('canceled','unavailable') THEN order_status
            WHEN d < getvariable('c') THEN 'delivered'
            WHEN car < getvariable('c') THEN 'shipped'
            WHEN a < getvariable('c') THEN 'approved'
            ELSE 'created' END AS order_status,
       order_purchase_timestamp,
       CASE WHEN getvariable('is_final') OR a < getvariable('c') THEN order_approved_at END AS order_approved_at,
       CASE WHEN getvariable('is_final') OR car < getvariable('c') THEN order_delivered_carrier_date END AS order_delivered_carrier_date,
       CASE WHEN getvariable('is_final') OR d < getvariable('c') THEN order_delivered_customer_date END AS order_delivered_customer_date,
       order_estimated_delivery_date
FROM _src_o WHERE p < getvariable('c');

-- Chi them ban moi khi trang thai doi (giong nguon gui thay doi).
INSERT INTO raw.orders
SELECT k.order_id, k.customer_id, k.order_status, k.order_purchase_timestamp, k.order_approved_at,
       k.order_delivered_carrier_date, k.order_delivered_customer_date, k.order_estimated_delivery_date,
       getvariable('batch'), getvariable('loaded_at'), 'olist_orders_dataset.csv', md5(CAST(k AS VARCHAR))
FROM _known k
LEFT JOIN (SELECT * FROM raw.orders QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY dwh_batch DESC) = 1) l USING (order_id)
WHERE l.order_id IS NULL
   OR k.order_status IS DISTINCT FROM l.order_status
   OR k.order_approved_at IS DISTINCT FROM l.order_approved_at
   OR k.order_delivered_carrier_date IS DISTINCT FROM l.order_delivered_carrier_date
   OR k.order_delivered_customer_date IS DISTINCT FROM l.order_delivered_customer_date;

INSERT INTO raw.order_items
SELECT i.*, getvariable('batch'), getvariable('loaded_at'), 'olist_order_items_dataset.csv', md5(CAST(i AS VARCHAR))
FROM src.order_items i JOIN _src_o o USING (order_id)
WHERE strftime(o.p, '%Y-%m') = getvariable('batch');

INSERT INTO raw.order_payments
SELECT i.*, getvariable('batch'), getvariable('loaded_at'), 'olist_order_payments_dataset.csv', md5(CAST(i AS VARCHAR))
FROM src.order_payments i JOIN _src_o o USING (order_id)
WHERE strftime(o.p, '%Y-%m') = getvariable('batch');

-- Review den vao thang khach tra loi, nhung khong truoc thang cua don.
INSERT INTO raw.order_reviews
SELECT r.*, getvariable('batch'), getvariable('loaded_at'), 'olist_order_reviews_dataset.csv', md5(CAST(r AS VARCHAR))
FROM src.order_reviews r JOIN _src_o o USING (order_id)
WHERE greatest(strftime(TRY_CAST(r.review_answer_timestamp AS TIMESTAMP), '%Y-%m'), strftime(o.p, '%Y-%m')) = getvariable('batch');

INSERT INTO ops.quarantine
SELECT dwh_batch, 'order_items', order_id || '#' || order_item_id, 'INVALID_PRICE', 'price khong hop le'
FROM raw.order_items WHERE dwh_batch = getvariable('batch') AND coalesce(TRY_CAST(price AS DECIMAL(12,2)), 0) <= 0;
INSERT INTO ops.quarantine
SELECT dwh_batch, 'order_payments', order_id || '#' || payment_sequential, 'INVALID_PAYMENT', 'payment_value khong hop le'
FROM raw.order_payments WHERE dwh_batch = getvariable('batch') AND coalesce(TRY_CAST(payment_value AS DECIMAL(12,2)), -1) < 0;
INSERT INTO ops.quarantine
SELECT dwh_batch, 'order_reviews', review_id, 'INVALID_REVIEW', 'review_score hoac thoi diem tra loi khong hop le'
FROM raw.order_reviews WHERE dwh_batch = getvariable('batch')
  AND (coalesce(TRY_CAST(review_score AS INTEGER), 0) NOT BETWEEN 1 AND 5 OR TRY_CAST(review_answer_timestamp AS TIMESTAMP) IS NULL);
