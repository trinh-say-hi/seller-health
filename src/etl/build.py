"""Dung kho du lieu: kiem tra nguon, nap master data, roi chay tung dot theo thang.

Chay: python -m src.etl.build
Mot dot da co trong etl_log (watermark) se duoc bo qua, tru khi force=True.
Loi hoac lech doi soat thi dung ngay, ghi status = failed va watermark khong tien; lan chay sau se chay lai dot do.
Khong dung giao dich vi DuckDB 2.0 bi crash khi COMMIT mot giao dich lon nhu vay. Dot da nap do co the chay lai an toan.
"""
import datetime as dt
import hashlib
import json
import shutil
import time

import duckdb
import pandas as pd

from src.config import DB_PATH, FIRST_BATCH, LAST_BATCH, RAW_DIR, ROOT, SQL_DIR, LAKE_DIR
from src.etl.lakehouse import (
    ensure_lake_dirs,
    init_lakehouse_metadata,
    export_bronze_lake,
    update_silver_batch_metrics,
    export_gold_lake
)

SOURCES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
}
MASTER = ["customers", "sellers", "products", "geolocation", "category_translation"]
TRANSACTIONAL = ["orders", "order_items", "order_payments", "order_reviews"]
MANIFEST = ROOT / "data" / "manifest.json"


class ReconciliationError(RuntimeError):
    """Doi soat giua cac lop khong khop."""


def run_sql(con, name):
    con.execute((SQL_DIR / name).read_text(encoding="utf-8"))


def batches():
    return [str(p) for p in pd.period_range(FIRST_BATCH, LAST_BATCH, freq="M")]


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_sources(manifest_path=MANIFEST):
    """So file nguon voi manifest. File bi doi, thieu hoac sai cot thi dung ngay, chua dong vao kho."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems, verified = [], []
    for table, file in SOURCES.items():
        path, expected = RAW_DIR / file, manifest["files"].get(file)
        if expected is None:
            problems.append(f"{file}: khong co trong manifest")
            continue
        if not path.exists():
            problems.append(f"{file}: thieu file, xem data/README.md")
            continue
        actual = sha256_of(path)
        if actual != expected["sha256"]:
            problems.append(f"{file}: hash khac manifest ({actual[:12]} thay vi {expected['sha256'][:12]})")
            continue
        verified.append((file, table, actual, expected["rows"]))
    if problems:
        raise ValueError("Nguon du lieu khong khop manifest:\n- " + "\n- ".join(problems))
    return verified


def attach_sources(con):
    con.execute("CREATE SCHEMA IF NOT EXISTS src")
    for table, file in SOURCES.items():
        path = (RAW_DIR / file).as_posix().replace("'", "''")
        con.execute(f"""CREATE OR REPLACE VIEW src.{table} AS
            SELECT * FROM read_csv('{path}', header=true, all_varchar=true, quote='"', escape='"')""")


def init(con):
    verified = verify_sources()
    run_sql(con, "00_schema.sql")
    attach_sources(con)
    stamp = dt.datetime.now().isoformat(sep=" ", timespec="seconds")
    for row in verified:
        con.execute("INSERT INTO ops.source_manifest VALUES (?,?,?,?,?)", [*row, stamp])
    for table in TRANSACTIONAL:
        con.execute(f"""CREATE TABLE raw.{table} AS SELECT *, ''::VARCHAR AS dwh_batch, ''::VARCHAR AS dwh_loaded_at,
                        ''::VARCHAR AS dwh_source_file, ''::VARCHAR AS dwh_row_hash FROM src.{table} LIMIT 0""")
    for table in MASTER:
        con.execute(f"""CREATE TABLE raw.{table} AS SELECT t.*, 'init' AS dwh_batch, '{stamp}' AS dwh_loaded_at,
                        '{SOURCES[table]}' AS dwh_source_file, md5(CAST(t AS VARCHAR)) AS dwh_row_hash FROM src.{table} t""")
    run_sql(con, "01_staging.sql")
    run_sql(con, "02_dimensions.sql")
    # Dimension tinh khong bi xoa ghi lai theo dot, nen khai bao duoc khoa chinh. Fact va dim_seller duoc test thay the.
    for table, key in [("dim_date", "date_key"), ("dim_location", "location_key"), ("dim_customer", "customer_key"), ("dim_product", "product_key"),
                       ("dim_route", "route_key"), ("dim_order_status", "status_key"), ("dim_seller_health", "health_key")]:
        con.execute(f"ALTER TABLE core.{table} ADD PRIMARY KEY ({key})")
    n_rejected = con.execute("SELECT count(*) FROM ops.quarantine WHERE dwh_batch = 'init'").fetchone()[0]
    n_loaded = sum(con.execute(f"SELECT count(*) FROM raw.{t}").fetchone()[0] for t in MASTER)
    con.execute("INSERT INTO ops.etl_log VALUES ('init', NULL, 0, 0, 0, 0, ?, ?, 0, ?, 0, 'ok', NULL)", [n_loaded, n_rejected, stamp])
    
    # Khoi tao True Medallion Ledgers & Bronze Lakehouse
    init_lakehouse_metadata(con)
    export_bronze_lake(con, "init")


def run_batch(con, batch, force=False):
    done = con.execute("SELECT count(*) FROM ops.etl_log WHERE batch = ? AND status = 'ok'", [batch]).fetchone()[0]
    if done and not force:
        return False
    start = time.time()
    period = pd.Period(batch, freq="M")
    cutoff = (period + 1).start_time.strftime("%Y-%m-%d")
    m0 = period.start_time.strftime("%Y-%m-%d")
    stamp = dt.datetime.now().isoformat(sep=" ", timespec="seconds")
    con.execute(f"SET VARIABLE batch = '{batch}'")
    con.execute(f"SET VARIABLE c = TIMESTAMP '{cutoff}'")
    con.execute(f"SET VARIABLE m0 = TIMESTAMP '{m0}'")
    con.execute(f"SET VARIABLE is_final = {'TRUE' if batch == LAST_BATCH else 'FALSE'}")
    con.execute(f"SET VARIABLE loaded_at = '{stamp}'")
    try:
        run_sql(con, "10_batch_raw.sql")
        run_sql(con, "11_batch_core.sql")
        run_sql(con, "12_batch_close.sql")
        run_sql(con, "13_batch_checks.sql")
        bad = con.execute("SELECT check_name, layer_from, layer_to, value_from, value_to FROM ops.layer_reconciliation WHERE batch = ? AND NOT is_ok", [batch]).fetchall()
        if bad:
            detail = "; ".join(f"{b[0]} {b[1]}->{b[2]}: {b[3]:,.2f} khac {b[4]:,.2f}" for b in bad)
            raise ReconciliationError(f"Doi soat dot {batch} khong khop: {detail}")
        counts = {t: con.execute(f"SELECT count(*) FROM raw.{t} WHERE dwh_batch = ?", [batch]).fetchone()[0] for t in TRANSACTIONAL}
        rejected = con.execute("SELECT count(*) FROM ops.quarantine WHERE dwh_batch = ?", [batch]).fetchone()[0]
        changed = con.execute("SELECT count(*) FROM _chg").fetchone()[0]
        con.execute("DELETE FROM ops.etl_log WHERE batch = ?", [batch])
        con.execute("INSERT INTO ops.etl_log VALUES (?,?,?,?,?,?,?,?,?,?,?,?,NULL)", [
            batch, cutoff, counts["orders"], counts["order_items"], counts["order_payments"], counts["order_reviews"],
            sum(counts.values()), rejected, changed, stamp, round(time.time() - start, 2), "ok"])
        
        # True Medallion: Export batch Parquet ZSTD va cap nhat ledger
        export_bronze_lake(con, batch)
        update_silver_batch_metrics(con, batch)
    except Exception as exc:
        con.execute("DELETE FROM ops.etl_log WHERE batch = ?", [batch])
        con.execute("INSERT INTO ops.etl_log VALUES (?,?,0,0,0,0,0,0,0,?,?,'failed',?)",
                    [batch, cutoff, stamp, round(time.time() - start, 2), str(exc)[:1000]])
        raise
    return True


def record_dq(con):
    """Ghi lai cac bat thuong da thay trong du lieu va cach xu ly."""
    rules = [
        ("Giao vận chuyển trước khi mua", "fact_order", "SELECT count(*) FROM core.fact_order WHERE carrier_ts < purchase_ts", "Giữ dòng, đánh cờ has_chronology_issue"),
        ("Khách nhận trước khi giao vận chuyển", "fact_order", "SELECT count(*) FROM core.fact_order WHERE delivered_ts < carrier_ts", "Giữ dòng, đánh cờ has_chronology_issue"),
        ("Duyệt trước khi mua", "fact_order", "SELECT count(*) FROM core.fact_order WHERE approved_ts < purchase_ts", "Giữ dòng, đánh cờ has_chronology_issue"),
        ("Đơn không có dòng hàng", "fact_order", "SELECT count(*) FROM core.fact_order WHERE coalesce(n_items, 0) = 0", "Giữ, seller_key = -1 ở fact_order_seller"),
        ("Đơn có nhiều seller", "fact_order", "SELECT count(*) FROM core.fact_order WHERE n_sellers > 1", "Tách fact_order và fact_order_seller"),
        ("Đơn có nhiều review", "order_reviews", "SELECT count(*) FROM (SELECT order_id FROM stg.reviews GROUP BY 1 HAVING count(*) > 1)", "Gộp về đơn trước khi nối; fact_review giữ từng review"),
        ("review_id dùng cho nhiều đơn", "order_reviews", "SELECT count(*) FROM (SELECT review_id FROM stg.reviews GROUP BY 1 HAVING count(DISTINCT order_id) > 1)", "Khóa fact_review là (review_id, order_id)"),
        ("Trạng thái và ngày giao mâu thuẫn", "fact_order", "SELECT count(*) FROM core.fact_order WHERE has_status_date_mismatch", "Giữ dòng, đánh cờ has_status_date_mismatch"),
        ("Đơn trả khác tiền hàng + phí", "fact_order", "SELECT count(*) FROM core.fact_order WHERE payment_count > 0 AND n_items > 0 AND abs(payment_total - order_total) > 0.01", "Giữ nguyên, phần lớn do lãi trả góp"),
        ("Sản phẩm không có danh mục", "dim_product", "SELECT count(*) FROM core.dim_product WHERE category_en = 'Unknown' AND product_key <> -1", "Ghi Unknown"),
        ("Sản phẩm nhờ bản dịch bổ sung", "stg.category_translation", "SELECT count(*) FROM raw.products p JOIN stg.category_translation t USING (product_category_name) LEFT JOIN raw.category_translation r USING (product_category_name) WHERE r.product_category_name IS NULL", "Thêm 2 bản dịch thiếu"),
        ("Tọa độ ngoài lãnh thổ Brazil", "geolocation", "SELECT count(*) FROM ops.quarantine WHERE reason_code = 'GEO_OUTSIDE_BRAZIL'", "Cách ly, không tính vào trung vị"),
        ("Tọa độ trùng theo ZIP", "geolocation", "SELECT (SELECT count(*) FROM raw.geolocation) - (SELECT count(*) FROM stg.geography)", "Lấy trung vị theo ZIP"),
        ("ZIP của khách không có tọa độ", "dim_location", "SELECT count(*) FROM stg.customers c JOIN core.dim_location l USING (zip_prefix) WHERE NOT l.has_coordinates", "Giữ dòng trong dim_location, tọa độ NULL"),
        ("ZIP của seller không có tọa độ", "dim_location", "SELECT count(*) FROM stg.sellers s JOIN core.dim_location l USING (zip_prefix) WHERE NOT l.has_coordinates", "Giữ dòng trong dim_location, tọa độ NULL"),
        ("Tên thành phố seller phải sửa theo ZIP", "stg.sellers", "SELECT count(*) FROM stg.sellers WHERE city_source = 'theo_zip'", "Giữ tên gốc ở city_raw"),
        ("Bang của seller khác bang theo ZIP", "stg.sellers", "SELECT count(*) FROM stg.sellers s JOIN stg.geography g USING (zip_prefix) WHERE s.state <> g.state", "Giữ bang của seller, không sửa"),
        ("Sản phẩm có cân nặng 0 g", "dim_product", "SELECT count(*) FROM core.dim_product WHERE weight_g = 0", "Giữ nguyên, chỉ ghi nhận"),
        ("Đơn đã giao nhưng thiếu ngày giao", "fact_order", "SELECT count(*) FROM core.fact_order o JOIN core.dim_order_status s USING (status_key) WHERE s.is_delivered AND o.delivered_ts IS NULL", "Không điền giả"),
    ]
    con.execute("DELETE FROM ops.dq_issue")
    for name, table, sql, handling in rules:
        con.execute("INSERT INTO ops.dq_issue VALUES (?,?,?,?)", [name, table, con.execute(sql).fetchone()[0], handling])


def build():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", ".wal"):
        path = DB_PATH.with_name(DB_PATH.name + suffix)
        if path.exists():
            path.unlink()
    shutil.rmtree(LAKE_DIR, ignore_errors=True)
    con = duckdb.connect(str(DB_PATH))
    start = time.time()
    init(con)
    print(f"init xong {time.time() - start:.1f}s")
    for batch in batches():
        run_batch(con, batch)
        row = con.execute("SELECT rows_loaded, sellers_tier_changed, duration_s FROM ops.etl_log WHERE batch = ?", [batch]).fetchone()
        print(f"  dot {batch}: {row[0]:>7} dong, {row[1]:>5} seller doi hang, {row[2]:.1f}s", flush=True)
    record_dq(con)
    
    # Export Gold layer ra Parquet ZSTD
    gold_summary = export_gold_lake(con)
    print(f"Lakehouse Gold Parquet xong: {len(gold_summary)} tables exported.")
    
    con.execute("CHECKPOINT")
    con.close()
    print(f"Kho xong sau {time.time() - start:.1f}s: {DB_PATH}")


if __name__ == "__main__":
    build()
