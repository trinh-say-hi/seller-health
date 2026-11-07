-- Cong chat luong giua cac lop: tinh luy ke toi dot hien tai. Lech o bat ky dong nao thi ca dot bi huy.
-- Bien: batch, c, m0.

DELETE FROM ops.layer_reconciliation WHERE batch = getvariable('batch');

INSERT INTO ops.layer_reconciliation
WITH checks(check_name, layer_from, layer_to, value_from, value_to) AS (
    SELECT 'So don', 'raw.orders', 'core.fact_order',
           (SELECT count(DISTINCT order_id) FROM raw.orders),
           (SELECT count(*) FROM core.fact_order)
    UNION ALL
    SELECT 'So dong hang', 'raw.order_items', 'core.fact_sales_item',
           (SELECT count(*) FROM raw.order_items) - (SELECT count(*) FROM ops.quarantine WHERE table_name = 'order_items'),
           (SELECT count(*) FROM core.fact_sales_item)
    UNION ALL
    SELECT 'Tien hang', 'raw.order_items', 'core.fact_sales_item',
           (SELECT sum(TRY_CAST(price AS DECIMAL(14,2))) FROM raw.order_items WHERE TRY_CAST(price AS DECIMAL(14,2)) > 0),
           (SELECT sum(price) FROM core.fact_sales_item)
    UNION ALL
    SELECT 'Tien hang', 'core.fact_sales_item', 'core.fact_order_seller',
           (SELECT sum(price) FROM core.fact_sales_item),
           (SELECT sum(order_value) FROM core.fact_order_seller)
    UNION ALL
    SELECT 'Tien hang', 'core.fact_sales_item', 'core.fact_order',
           (SELECT sum(price) FROM core.fact_sales_item),
           (SELECT sum(items_price_total) FROM core.fact_order)
    UNION ALL
    SELECT 'So dong thanh toan', 'raw.order_payments', 'core.fact_payment',
           (SELECT count(*) FROM raw.order_payments) - (SELECT count(*) FROM ops.quarantine WHERE table_name = 'order_payments'),
           (SELECT count(*) FROM core.fact_payment)
    UNION ALL
    SELECT 'Tien thanh toan', 'raw.order_payments', 'core.fact_payment',
           (SELECT sum(TRY_CAST(payment_value AS DECIMAL(14,2))) FROM raw.order_payments WHERE TRY_CAST(payment_value AS DECIMAL(14,2)) >= 0),
           (SELECT sum(payment_value) FROM core.fact_payment)
    UNION ALL
    SELECT 'So review', 'raw.order_reviews', 'core.fact_review',
           (SELECT count(*) FROM raw.order_reviews) - (SELECT count(*) FROM ops.quarantine WHERE table_name = 'order_reviews'),
           (SELECT count(*) FROM core.fact_review)
    UNION ALL
    SELECT 'GMV thang', 'core.fact_sales_item', 'mart.kpi_monthly',
           (SELECT coalesce(sum(price), 0) FROM core.fact_sales_item WHERE is_valid_sale AND purchase_ts >= getvariable('m0') AND purchase_ts < getvariable('c')),
           (SELECT coalesce(sum(gmv), 0) FROM mart.kpi_monthly WHERE month = CAST(getvariable('m0') AS DATE) AND is_all_region AND is_all_category)
    UNION ALL
    SELECT 'GMV thang', 'core.fact_sales_item', 'core.fact_seller_monthly',
           (SELECT coalesce(sum(price), 0) FROM core.fact_sales_item WHERE is_valid_sale AND purchase_ts >= getvariable('m0') AND purchase_ts < getvariable('c')),
           (SELECT coalesce(sum(gmv), 0) FROM core.fact_seller_monthly WHERE month = CAST(getvariable('m0') AS DATE))
    UNION ALL
    SELECT 'GMV 90 ngay', 'core.fact_sales_item', 'mart.seller_features',
           (SELECT coalesce(sum(price), 0) FROM core.fact_sales_item WHERE is_valid_sale AND purchase_ts >= getvariable('c') - INTERVAL 90 DAY AND purchase_ts < getvariable('c')),
           (SELECT coalesce(sum(gmv_90), 0) FROM mart.seller_features WHERE as_of = CAST(getvariable('c') AS DATE))
)
SELECT getvariable('batch'), check_name, layer_from, layer_to, value_from, value_to,
       value_to - value_from, abs(value_to - value_from) < 0.01
FROM checks;
