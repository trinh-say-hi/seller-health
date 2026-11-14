{{ config(materialized='table') }}

WITH z AS (
    SELECT zip_prefix FROM {{ ref('stg_geography') }}
    UNION SELECT zip_prefix FROM {{ ref('stg_customers') }}
    UNION SELECT zip_prefix FROM {{ ref('stg_sellers') }}
),
c AS (SELECT zip_prefix, mode(city ORDER BY city) AS city, mode(state ORDER BY state) AS state FROM {{ ref('stg_customers') }} GROUP BY 1),
s AS (SELECT zip_prefix, mode(city ORDER BY city) AS city, mode(state ORDER BY state) AS state FROM {{ ref('stg_sellers') }} GROUP BY 1)
SELECT -1 AS location_key, 'UNKNOWN' AS zip_prefix, 'khong ro' AS city, NULL AS state, 'Khong ro' AS region,
       NULL::DOUBLE AS lat, NULL::DOUBLE AS lng, FALSE AS has_coordinates
UNION ALL
SELECT 
    row_number() OVER (ORDER BY z.zip_prefix) AS location_key, 
    z.zip_prefix,
    coalesce(g.city, c.city, s.city, 'khong ro') AS city, 
    coalesce(g.state, c.state, s.state) AS state,
    {{ region_of('coalesce(g.state, c.state, s.state)') }} AS region, 
    g.lat, 
    g.lng, 
    g.lat IS NOT NULL AS has_coordinates
FROM z 
LEFT JOIN {{ ref('stg_geography') }} g USING (zip_prefix) 
LEFT JOIN c USING (zip_prefix) 
LEFT JOIN s USING (zip_prefix)
