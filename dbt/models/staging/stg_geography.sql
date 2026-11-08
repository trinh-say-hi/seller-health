{{ config(materialized='view') }}

WITH geo AS (
    SELECT
        geolocation_zip_code_prefix AS zip_prefix,
        TRY_CAST(geolocation_lat AS DOUBLE) AS lat,
        TRY_CAST(geolocation_lng AS DOUBLE) AS lng,
        {{ clean_city('geolocation_city') }} AS city,
        upper(trim(geolocation_state)) AS state
    FROM {{ source('raw', 'geolocation') }}
)
SELECT
    zip_prefix,
    median(lat) FILTER (WHERE lat BETWEEN -34 AND 6 AND lng BETWEEN -74 AND -34) AS lat,
    median(lng) FILTER (WHERE lat BETWEEN -34 AND 6 AND lng BETWEEN -74 AND -34) AS lng,
    mode(city) AS city,
    mode(state) AS state
FROM geo
GROUP BY zip_prefix
