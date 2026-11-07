-- Cac lop cua kho: raw (Bronze) -> stg (Silver) -> core, mart (Gold), cong voi dss (ket qua) va ops (van hanh)
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS stg;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS mart;
CREATE SCHEMA IF NOT EXISTS dss;
CREATE SCHEMA IF NOT EXISTS ops;

CREATE TABLE ops.etl_log (
    batch VARCHAR, watermark TIMESTAMP,
    orders_versions BIGINT, items BIGINT, payments BIGINT, reviews BIGINT,
    rows_loaded BIGINT, rows_rejected BIGINT,
    sellers_tier_changed BIGINT, run_at TIMESTAMP, duration_s DOUBLE, status VARCHAR, error_message VARCHAR
);
CREATE TABLE ops.quarantine (dwh_batch VARCHAR, table_name VARCHAR, row_key VARCHAR, reason_code VARCHAR, reason VARCHAR);
CREATE TABLE ops.dq_issue (rule_name VARCHAR, table_name VARCHAR, n_rows BIGINT, handling VARCHAR);
CREATE TABLE ops.layer_reconciliation (
    batch VARCHAR, check_name VARCHAR, layer_from VARCHAR, layer_to VARCHAR,
    value_from DOUBLE, value_to DOUBLE, difference DOUBLE, is_ok BOOLEAN
);
CREATE TABLE ops.source_manifest (file_name VARCHAR, table_name VARCHAR, sha256 VARCHAR, n_rows BIGINT, verified_at TIMESTAMP);

CREATE MACRO core.region_of(s) AS CASE
    WHEN s IN ('AC','AM','AP','PA','RO','RR','TO') THEN 'Norte'
    WHEN s IN ('AL','BA','CE','MA','PB','PE','PI','RN','SE') THEN 'Nordeste'
    WHEN s IN ('DF','GO','MS','MT') THEN 'Centro-Oeste'
    WHEN s IN ('ES','MG','RJ','SP') THEN 'Sudeste'
    WHEN s IN ('PR','RS','SC') THEN 'Sul'
    ELSE 'Khong ro' END;
CREATE MACRO core.date_key(ts) AS CAST(strftime(ts, '%Y%m%d') AS INTEGER);

-- Chuan hoa ten thanh pho: bo dau, bo phan sau dau phan cach, bo ma bang o cuoi. Ten chua so hoac @ la khong dung duoc.
CREATE MACRO stg.clean_city_step1(s) AS trim(regexp_split_to_array(lower(strip_accents(regexp_replace(trim(replace(s, '´', '''')), '\s+', ' ', 'g'))), '\s*[/\\,]\s*|\s+-\s+')[1]);
CREATE MACRO stg.clean_city_step2(s) AS trim(regexp_replace(stg.clean_city_step1(s), '[\s-](ac|al|am|ap|ba|ce|df|es|go|ma|mg|ms|mt|pa|pb|pe|pi|pr|rj|rn|ro|rr|rs|sc|se|sp|to)$', ''));
CREATE MACRO stg.clean_city(s) AS CASE WHEN stg.clean_city_step2(s) IS NULL OR stg.clean_city_step2(s) = '' OR regexp_matches(stg.clean_city_step2(s), '[0-9@]') THEN NULL ELSE stg.clean_city_step2(s) END;
