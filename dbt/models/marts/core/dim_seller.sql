{{ config(materialized='table') }}

SELECT -1 AS seller_key, 'UNKNOWN' AS seller_id, NULL AS zip_prefix, 'khong ro' AS city, NULL AS state, 'Khong ro' AS region,
       'Khong ro' AS health_tier, TIMESTAMP '2016-01-01' AS valid_from, TIMESTAMP '9999-12-31' AS valid_to, TRUE AS is_current
UNION ALL
SELECT 
    row_number() OVER (ORDER BY seller_id) AS seller_key, 
    seller_id, 
    zip_prefix, 
    city, 
    state, 
    {{ region_of('state') }} AS region,
    'Chưa hoạt động' AS health_tier, 
    TIMESTAMP '2016-01-01' AS valid_from, 
    TIMESTAMP '9999-12-31' AS valid_to, 
    TRUE AS is_current
FROM {{ ref('stg_sellers') }}
