{{ config(materialized='table') }}

SELECT -1 AS product_key, 'UNKNOWN' AS product_id, 'Unknown' AS category_en, NULL::DOUBLE AS weight_g,
       NULL::DOUBLE AS volume_cm3, 'Khong ro' AS size_group, NULL::INTEGER AS photos_qty
UNION ALL
SELECT 
    row_number() OVER (ORDER BY product_id) AS product_key, 
    product_id, 
    category_en, 
    weight_g, 
    volume_cm3,
    CASE 
        WHEN volume_cm3 IS NULL THEN 'Khong ro' 
        WHEN volume_cm3 < 2000 THEN 'Nho'
        WHEN volume_cm3 < 15000 THEN 'Vua' 
        ELSE 'Lon' 
    END AS size_group,
    photos_qty
FROM {{ ref('stg_products') }}
