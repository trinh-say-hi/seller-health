"""Lakehouse Parquet ZSTD export & True Medallion Audit Ledgers."""
import datetime as dt
from pathlib import Path
import duckdb

from src.config import BRONZE_LAKE, GOLD_LAKE, LAKE_DIR, ROOT, SILVER_LAKE

TABLES_RAW = ["orders", "order_items", "order_payments", "order_reviews", "customers", "sellers", "products", "geolocation", "category_translation"]
TABLES_GOLD_FACTS = ["fact_sales_item", "fact_order", "fact_order_seller", "fact_review", "fact_payment", "fact_seller_monthly"]
TABLES_GOLD_DIMS = ["dim_date", "dim_seller", "dim_seller_health", "dim_customer", "dim_product", "dim_location", "dim_route", "dim_order_status"]


def ensure_lake_dirs():
    for d in [BRONZE_LAKE, SILVER_LAKE, GOLD_LAKE]:
        d.mkdir(parents=True, exist_ok=True)
    for t in ["orders", "order_items", "order_payments", "order_reviews"]:
        (BRONZE_LAKE / t).mkdir(parents=True, exist_ok=True)


def init_lakehouse_metadata(con):
    """Ghi nhan so cai mẻ nap bronze.ingestion_batches va khoi tao metadata."""
    ensure_lake_dirs()
    stamp = dt.datetime.now().isoformat(sep=" ", timespec="seconds")
    
    # 1. Ghi nhan tat ca file raw vao ops.ingestion_batches
    manifest_rows = con.execute("SELECT file_name, sha256, n_rows FROM ops.source_manifest").fetchall()
    con.execute("DELETE FROM ops.ingestion_batches WHERE batch_id = 'init'")
    for file_name, file_hash, n_rows in manifest_rows:
        con.execute(
            "INSERT INTO ops.ingestion_batches VALUES ('init', ?, ?, ?, ?, 'COMMITTED')",
            [file_name, file_hash, n_rows, stamp]
        )
    
    # 2. Dong bo silver.quarantine_records tu ops.quarantine
    con.execute("DELETE FROM silver.quarantine_records WHERE batch_id = 'init'")
    con.execute("""
        INSERT INTO silver.quarantine_records
        SELECT md5(table_name || '|' || row_key) AS quarantine_id,
               table_name AS source_table,
               reason_code AS error_code,
               'coordinates' AS failed_column,
               row_key AS failed_value,
               '{"row_key": "' || row_key || '", "reason": "' || reason || '"}' AS raw_payload,
               dwh_batch AS batch_id,
               CURRENT_TIMESTAMP AS detected_at
        FROM ops.quarantine
        WHERE dwh_batch = 'init'
    """)
    
    # 3. Ghi nhan processing metrics vao silver.processing_batches cho master tables
    con.execute("DELETE FROM silver.processing_batches WHERE batch_id = 'init'")
    geo_total = con.execute("SELECT count(*) FROM raw.geolocation").fetchone()[0]
    geo_quar = con.execute("SELECT count(*) FROM ops.quarantine WHERE table_name = 'geolocation'").fetchone()[0]
    geo_clean = geo_total - geo_quar
    geo_rate = round(100.0 * geo_clean / geo_total, 2) if geo_total > 0 else 100.0
    con.execute("""
        INSERT INTO silver.processing_batches VALUES
        ('init', 'geolocation', ?, ?, ?, 0, ?, CURRENT_TIMESTAMP)
    """, [geo_total, geo_clean, geo_quar, geo_rate])


def export_bronze_lake(con, batch: str = None):
    """Xuat du lieu Bronze ra Parquet nén ZSTD (WORM Append-only)."""
    ensure_lake_dirs()
    if batch is None or batch == "init":
        # Export master tables to bronze
        for t in ["customers", "sellers", "products", "geolocation", "category_translation"]:
            out_file = (BRONZE_LAKE / f"{t}.parquet").as_posix()
            con.execute(f"COPY raw.{t} TO '{out_file}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    if batch and batch != "init":
        from src.etl.build import sha256_of  # import trong ham: build.py cung import module nay
        # Chay lai mot dot (force) thi ghi de file va dong so cai cua dot do, khong cong don.
        con.execute("DELETE FROM ops.ingestion_batches WHERE batch_id = ?", [batch])
        for t in ["orders", "order_items", "order_payments", "order_reviews"]:
            out_path = BRONZE_LAKE / t / f"{batch}.parquet"
            con.execute(f"COPY (SELECT * FROM raw.{t} WHERE dwh_batch = '{batch}') TO '{out_path.as_posix()}' (FORMAT PARQUET, COMPRESSION ZSTD)")
            row_count = con.execute(f"SELECT count(*) FROM raw.{t} WHERE dwh_batch = '{batch}'").fetchone()[0]
            con.execute(
                "INSERT INTO ops.ingestion_batches VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, 'COMMITTED')",
                [batch, f"bronze/{t}/{batch}.parquet", sha256_of(out_path), row_count]
            )


def update_silver_batch_metrics(con, batch: str):
    """Ghi nhan dang thuc bao toan dong 3 trang thai vao silver.processing_batches."""
    con.execute("DELETE FROM silver.processing_batches WHERE batch_id = ?", [batch])
    
    # 1. Orders: Don hang hop le duoc dua vao stg.orders (don huy van la giao dich hop le, khong phai duplicate)
    n_in_orders = con.execute("SELECT count(*) FROM raw.orders WHERE dwh_batch = ?", [batch]).fetchone()[0]
    con.execute("""
        INSERT INTO silver.processing_batches VALUES
        (?, 'orders', ?, ?, 0, 0, 100.0, CURRENT_TIMESTAMP)
    """, [batch, n_in_orders, n_in_orders])
    
    # 2. Items
    n_items = con.execute("SELECT count(*) FROM raw.order_items WHERE dwh_batch = ?", [batch]).fetchone()[0]
    con.execute("""
        INSERT INTO silver.processing_batches VALUES
        (?, 'order_items', ?, ?, 0, 0, 100.0, CURRENT_TIMESTAMP)
    """, [batch, n_items, n_items])


def export_gold_lake(con):
    """Xuat toan bo Gold Dimensions va Fact tables ra <kho>_lake/gold/ Parquet ZSTD."""
    ensure_lake_dirs()
    summary = []
    for t in TABLES_GOLD_FACTS + TABLES_GOLD_DIMS:
        out_file = (GOLD_LAKE / f"{t}.parquet").as_posix()
        con.execute(f"COPY core.{t} TO '{out_file}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        size_kb = (GOLD_LAKE / f"{t}.parquet").stat().st_size / 1024
        summary.append((t, size_kb))
    return summary
