{{ config(materialized='view') }}

WITH a AS (
    SELECT
        customer_id,
        customer_unique_id,
        customer_zip_code_prefix AS zip_prefix,
        customer_city AS city_raw,
        {{ clean_city('customer_city') }} AS cand,
        upper(trim(customer_state)) AS state
    FROM {{ source('raw', 'customers') }}
)
SELECT
    a.customer_id,
    a.customer_unique_id,
    a.zip_prefix,
    a.city_raw,
    coalesce(g.city, a.cand, 'khong ro') AS city,
    a.state
FROM a
LEFT JOIN {{ ref('stg_geography') }} g
    USING (zip_prefix)
