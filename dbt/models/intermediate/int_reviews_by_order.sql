{{ config(materialized='view') }}

SELECT
    order_id,
    avg(review_score) AS review_score,
    count(*) AS n_reviews,
    bool_or(has_comment) AS has_comment,
    min(review_ts) AS first_review_ts
FROM {{ ref('stg_reviews') }}
GROUP BY order_id
