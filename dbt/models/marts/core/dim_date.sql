{{ config(materialized='table') }}

WITH d AS (
    SELECT CAST(x AS DATE) AS full_date 
    FROM generate_series(DATE '2016-01-01', DATE '2020-12-31', INTERVAL 1 DAY) t(x)
),
holiday AS (
    SELECT * FROM (
        VALUES
            (DATE '2016-02-09'),(DATE '2016-03-25'),(DATE '2017-02-28'),(DATE '2017-04-14'),
            (DATE '2018-02-13'),(DATE '2018-03-30'),(DATE '2019-03-05'),(DATE '2019-04-19'),
            (DATE '2020-02-25'),(DATE '2020-04-10')
    ) v(h)
)
SELECT 
    {{ date_key('full_date') }} AS date_key, 
    full_date,
    year(full_date) AS year, 
    quarter(full_date) AS quarter, 
    month(full_date) AS month,
    strftime(full_date, '%Y-%m') AS year_month, 
    weekofyear(full_date) AS week,
    isodow(full_date) AS day_of_week, 
    isodow(full_date) >= 6 AS is_weekend,
    strftime(full_date, '%m-%d') IN ('01-01','04-21','05-01','09-07','10-12','11-02','11-15','12-25')
        OR full_date IN (SELECT h FROM holiday) AS is_holiday_br,
    full_date IN (DATE '2016-11-25', DATE '2017-11-24', DATE '2018-11-23', DATE '2019-11-29', DATE '2020-11-27') AS is_black_friday
FROM d
