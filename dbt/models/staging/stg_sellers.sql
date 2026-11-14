{{ config(materialized='view') }}

WITH a AS (
    SELECT
        seller_id,
        seller_zip_code_prefix AS zip_prefix,
        seller_city AS city_raw,
        {{ clean_city('seller_city') }} AS cand,
        upper(trim(seller_state)) AS state
    FROM {{ source('raw', 'sellers') }}
)
SELECT
    a.seller_id,
    a.zip_prefix,
    a.city_raw,
    coalesce(g.city, a.cand, 'khong ro') AS city,
    CASE
        WHEN g.city IS NOT NULL THEN 'theo_zip'
        WHEN a.cand IS NOT NULL THEN 'chuan_hoa'
        ELSE 'khong_ro'
    END AS city_source,
    a.state
FROM a
LEFT JOIN {{ ref('stg_geography') }} g
    USING (zip_prefix)
