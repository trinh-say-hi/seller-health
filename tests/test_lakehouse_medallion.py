"""Kiem tra cac co che Medallion thuc thu va Lakehouse Parquet storage.

Chay: python -m tests.test_lakehouse_medallion
"""
from decimal import Decimal
import duckdb
from src.config import BRONZE_LAKE, DB_PATH, GOLD_LAKE, LAKE_DIR, ROOT

con = duckdb.connect(str(DB_PATH), read_only=True)
results = []


def check(name, ok, detail=""):
    results.append({"test": name, "ok": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" ({detail})" if detail != "" else ""))


print("\n=== KIỂM ĐỊNH CƠ CHẾ MEDALLION THỰC THỤ & LAKEHOUSE PARQUET ===")

# 1. Kiem tra thu muc Lakehouse Bronze Parquet
master_parquets = ["customers", "sellers", "products", "geolocation", "category_translation"]
all_master_exist = all((BRONZE_LAKE / f"{t}.parquet").exists() for t in master_parquets)
check("Bronze Lake: Du 5 master parquet files", all_master_exist)

# 2. Kiem tra transaction partitioned batches
orders_parquet_count = len(list((BRONZE_LAKE / "orders").glob("*.parquet")))
check("Bronze Lake: Du 26 partitioned batch files cho orders", orders_parquet_count == 26, f"{orders_parquet_count}/26")

# 3. Kiem tra Gold Lakehouse Parquet
gold_tables = ["dim_customer", "dim_date", "dim_location", "dim_order_status", "dim_product",
               "dim_route", "dim_seller", "dim_seller_health", "fact_order", "fact_order_seller",
               "fact_payment", "fact_review", "fact_sales_item", "fact_seller_monthly"]
all_gold_exist = all((GOLD_LAKE / f"{t}.parquet").exists() for t in gold_tables)
check("Gold Lake: Du 14 dimensional parquet files", all_gold_exist)

# 4. Kiem tra dong bo du lieu tuyet doi giua DuckDB va Gold Parquet (Zero Data Loss)
fact_db_rows = con.execute("SELECT count(*) FROM core.fact_sales_item").fetchone()[0]
fact_pq_rows = con.execute(f"SELECT count(*) FROM read_parquet('{(GOLD_LAKE / 'fact_sales_item.parquet').as_posix()}')").fetchone()[0]
check("Gold Lake: fact_sales_item row count khop 100%", fact_db_rows == fact_pq_rows, f"{fact_db_rows} == {fact_pq_rows}")

fact_db_sum = con.execute("SELECT sum(price) FROM core.fact_sales_item").fetchone()[0]
fact_pq_sum = con.execute(f"SELECT sum(price) FROM read_parquet('{(GOLD_LAKE / 'fact_sales_item.parquet').as_posix()}')").fetchone()[0]
check("Gold Lake: fact_sales_item tong tien khop 13.591.643,70 BRL", round(float(fact_db_sum), 2) == round(float(fact_pq_sum), 2) == 13591643.70, float(fact_pq_sum))

# 5. Kiem tra ti le nen ZSTD: Gold layer phai nho hon 45 MB
gold_size_mb = sum(f.stat().st_size for f in GOLD_LAKE.glob("*.parquet")) / (1024 * 1024)
check("Gold Lake: Toan bo kho Gold Parquet nho hon 45 MB", gold_size_mb < 45.0, f"{gold_size_mb:.2f} MB")

# 6. Kiem tra So cai me nap Bronze Ingestion Ledger
n_ingest_batches = con.execute("SELECT count(*) FROM ops.ingestion_batches WHERE status = 'COMMITTED'").fetchone()[0]
check("Audit Ledger: bronze.ingestion_batches ghi nhan day du me nap", n_ingest_batches >= 113, f"{n_ingest_batches} batches")

# 7. Kiem tra Bang cach ly loi Dead-Letter Quarantine
n_quarantine = con.execute("SELECT count(*) FROM silver.quarantine_records").fetchone()[0]
check("Quarantine: silver.quarantine_records luu 42 ban ghi vi pham", n_quarantine == 42, f"{n_quarantine} records")

invalid_coords = con.execute("SELECT count(*) FROM silver.quarantine_records WHERE error_code = 'GEO_OUTSIDE_BRAZIL' AND raw_payload LIKE '%row_key%'").fetchone()[0]
check("Quarantine: Ban ghi cach ly co day du ma loi va raw JSON payload", invalid_coords == 42, invalid_coords)

# 8. Kiem tra So cai chat luong va Dang thuc bao toan dong 3 trang thai
n_proc_batches = con.execute("SELECT count(*) FROM silver.processing_batches").fetchone()[0]
check("Quality Ledger: silver.processing_batches do luong du 26 dot", n_proc_batches >= 53, f"{n_proc_batches} entries")

conservation_violations = con.execute("""
    SELECT count(*) FROM silver.processing_batches
    WHERE input_rows <> (accepted_rows + quarantined_rows + deduplicated_rows)
""").fetchone()[0]
check("Quality Ledger: Bao toan dang thuc dong 3 trang thai (0 vi pham)", conservation_violations == 0, conservation_violations)

# Tong ket
n_pass = sum(1 for r in results if r["ok"])
print(f"\n{n_pass}/{len(results)} test dat")
con.close()
if n_pass < len(results):
    import sys; sys.exit(1)
