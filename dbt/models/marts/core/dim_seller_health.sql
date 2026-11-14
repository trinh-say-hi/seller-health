{{ config(materialized='table') }}

SELECT -1 AS health_key, 'Khong ro' AS health_tier, 'Khong ro' AS size_band, 'Khong ro' AS late_band, 'Khong ro' AS review_band
UNION ALL
SELECT 
    row_number() OVER (ORDER BY t, s, l, r) AS health_key, 
    t, s, l, r
FROM (VALUES ('Vàng'), ('Ổn định'), ('Ít đơn'), ('Theo dõi'), ('Nguy cơ'), ('Tạm ngừng')) a(t)
CROSS JOIN (VALUES ('Dưới 6 đơn'), ('6-30 đơn'), ('Trên 30 đơn')) b(s)
CROSS JOIN (VALUES ('Chưa rõ'), ('Đến 5%'), ('5-15%'), ('15-30%'), ('Trên 30%')) c(l)
CROSS JOIN (VALUES ('Chưa rõ'), ('Dưới 3,5'), ('3,5-4,2'), ('Trên 4,2')) d(r)
