{{ config(materialized='table') }}

SELECT 
    row_number() OVER (ORDER BY stage, status) AS status_key, 
    status, 
    stage, 
    is_delivered, 
    is_canceled
FROM (
    VALUES 
        ('created', 1, FALSE, FALSE), 
        ('approved', 2, FALSE, FALSE), 
        ('invoiced', 3, FALSE, FALSE), 
        ('processing', 4, FALSE, FALSE),
        ('shipped', 5, FALSE, FALSE), 
        ('delivered', 6, TRUE, FALSE), 
        ('canceled', 7, FALSE, TRUE), 
        ('unavailable', 8, FALSE, TRUE)
) v(status, stage, is_delivered, is_canceled)
