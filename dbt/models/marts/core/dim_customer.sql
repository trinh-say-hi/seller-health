{{ config(materialized='table') }}

SELECT -1 AS customer_key, 'UNKNOWN' AS customer_unique_id, NULL AS city, NULL AS state
UNION ALL
SELECT 
    row_number() OVER (ORDER BY customer_unique_id) AS customer_key, 
    customer_unique_id, 
    mode(city) AS city, 
    mode(state) AS state
FROM {{ ref('stg_customers') }} 
GROUP BY customer_unique_id
