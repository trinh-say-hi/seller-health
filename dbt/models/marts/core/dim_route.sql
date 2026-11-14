{{ config(materialized='table') }}

WITH c AS (
    SELECT state, avg(lat) AS lat, avg(lng) AS lng 
    FROM {{ ref('dim_location') }} 
    WHERE has_coordinates 
    GROUP BY state
),
ss AS (SELECT DISTINCT state FROM {{ ref('stg_sellers') }} WHERE state IS NOT NULL),
cs AS (SELECT DISTINCT state FROM {{ ref('stg_customers') }} WHERE state IS NOT NULL)
SELECT -1 AS route_key, NULL AS seller_state, NULL AS customer_state, NULL AS route_name, NULL::BOOLEAN AS same_state, NULL::DOUBLE AS distance_km
UNION ALL
SELECT 
    row_number() OVER (ORDER BY ss.state, cs.state) AS route_key, 
    ss.state, 
    cs.state, 
    ss.state || '->' || cs.state AS route_name, 
    ss.state = cs.state AS same_state,
    2 * 6371 * asin(sqrt(pow(sin(radians(c2.lat - c1.lat) / 2), 2)
        + cos(radians(c1.lat)) * cos(radians(c2.lat)) * pow(sin(radians(c2.lng - c1.lng) / 2), 2))) AS distance_km
FROM ss 
CROSS JOIN cs
LEFT JOIN c c1 ON c1.state = ss.state
LEFT JOIN c c2 ON c2.state = cs.state
