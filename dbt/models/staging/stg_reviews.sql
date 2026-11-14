{{ config(materialized='view') }}

SELECT
    review_id,
    order_id,
    CAST(review_score AS INTEGER) AS review_score,
    review_comment_title IS NOT NULL AND trim(review_comment_title) <> '' AS has_title,
    review_comment_message IS NOT NULL AND trim(review_comment_message) <> '' AS has_comment,
    TRY_CAST(review_creation_date AS TIMESTAMP) AS created_ts,
    CAST(review_answer_timestamp AS TIMESTAMP) AS review_ts,
    dwh_batch
FROM {{ source('raw', 'order_reviews') }}
WHERE TRY_CAST(review_score AS INTEGER) BETWEEN 1 AND 5
  AND TRY_CAST(review_answer_timestamp AS TIMESTAMP) IS NOT NULL
