{{ config(materialized='table') }}

/*
  In production DW_DSS, core.dim_seller is an SCD Type-2 dimension populated and updated
  across 26 monthly batches by src/sql/12_batch_close.sql.
  If the populated SCD-2 table already exists in DuckDB (with historical revisions), preserve it;
  otherwise initialize the baseline seed from stg_sellers.
*/

{% set check_scd2 = adapter.get_relation(database=target.database, schema='core', identifier='dim_seller') %}

{% if check_scd2 is not none and execute %}
SELECT 
    seller_key,
    seller_id,
    zip_prefix,
    city,
    state,
    region,
    health_tier,
    valid_from,
    valid_to,
    is_current
FROM {{ check_scd2 }}
{% else %}
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
{% endif %}
