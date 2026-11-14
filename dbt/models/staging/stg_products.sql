{{ config(materialized='view') }}

SELECT
    p.product_id,
    coalesce(t.product_category_name_english, 'Unknown') AS category_en,
    TRY_CAST(p.product_weight_g AS DOUBLE) AS weight_g,
    TRY_CAST(p.product_length_cm AS DOUBLE) * TRY_CAST(p.product_height_cm AS DOUBLE)
        * TRY_CAST(p.product_width_cm AS DOUBLE) AS volume_cm3,
    TRY_CAST(p.product_photos_qty AS INTEGER) AS photos_qty
FROM {{ source('raw', 'products') }} p
LEFT JOIN {{ ref('stg_category_translation') }} t
    ON p.product_category_name = t.product_category_name
