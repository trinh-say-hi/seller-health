"""Xuat cac bang Gold (star schema) ra Parquet cho mo hinh Power BI trong powerbi/.

Chay: python -m src.pipeline.powerbi_export   (hoac asset xuat_parquet trong Dagster, sau kho_phat_hanh)

Power BI doc Parquet bang Parquet.Document, nap vao VertiPaq (che do Import). Kho DuckDB van la nguon su that:
o day chi chon cot, them vai co tinh san (don x seller co hop le, da toi han, tre) va khoa thang cho bang KPI,
khong tinh lai so lieu nao. File duoc ghi vao thu muc tam roi doi ten, nen Power BI khong doc phai file viet do.
"""
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb

from src.config import HOME, LAST_BATCH, ROOT, current_db

OUT_DIR = HOME / "powerbi"
# Moc as-of cua kho day du: ngay chot dot cuoi. Don toi han truoc moc nay moi tinh tre.
AS_OF = (dt.date.fromisoformat(LAST_BATCH + "-01") + dt.timedelta(days=32)).replace(day=1).isoformat()

OS_KEY = "SELECT order_id, seller_id, CAST(row_number() OVER (ORDER BY order_id, seller_id) AS INTEGER) AS os_key FROM core.fact_order_seller"

TABLES = {
    "dim_date": "SELECT * FROM core.dim_date",
    "dim_region": """SELECT region FROM core.dim_location UNION SELECT region FROM core.dim_seller ORDER BY 1""",
    "dim_seller": "SELECT * FROM core.dim_seller",
    "dim_product": "SELECT * FROM core.dim_product",
    "dim_location": "SELECT * FROM core.dim_location",
    "dim_route": "SELECT * FROM core.dim_route",
    "dim_seller_health": "SELECT * FROM core.dim_seller_health",
    # os_key: khoa so cua cap don x seller, de DAX loc fact_order_seller theo san pham (TREATAS tren mot cot so, nhanh hon cap chuoi).
    "fact_sales_item": f"""SELECT i.* EXCLUDE (dwh_batch), k.os_key FROM core.fact_sales_item i JOIN ({OS_KEY}) k USING (order_id, seller_id)""",
    # Grain don x seller cho tre hen va review, giong man OLAP: chi cap co it nhat mot dong hang hop le.
    "fact_order_seller": f"""
        SELECT o.* EXCLUDE (dwh_first_batch, dwh_last_batch, n_versions),
               v.order_id IS NOT NULL AS is_valid_sale,
               o.estimated_ts < DATE '{AS_OF}' AS is_due,
               o.delivered_ts IS NULL OR CAST(o.delivered_ts AS DATE) > CAST(o.estimated_ts AS DATE) AS is_late,
               o.first_review_ts < DATE '{AS_OF}' AS is_review_known, k.os_key
        FROM core.fact_order_seller o
        LEFT JOIN ({OS_KEY}) k USING (order_id, seller_id)
        LEFT JOIN (SELECT DISTINCT order_id, seller_id FROM core.fact_sales_item WHERE is_valid_sale) v USING (order_id, seller_id)""",
    "fact_seller_monthly": "SELECT * FROM core.fact_seller_monthly",
    # KPI chot theo thang (CUBE). gmv la tong gia 2 chu so thap phan nen ep ve DECIMAL de cong khong sai so.
    "kpi_monthly": """
        SELECT CAST(strftime(month, '%Y%m%d') AS INTEGER) AS month_key, month, region, category_en, is_all_region, is_all_category,
               CAST(gmv AS DECIMAL(18, 2)) AS gmv, n_orders, n_sellers, n_due_orders, n_late_orders, avg_review
        FROM mart.kpi_monthly""",
    # De xuat DSS moi moc as-of, gan seller_key cua dong dim_seller hien hanh de loc theo seller va RLS theo vung.
    "dss_recommendation": """
        SELECT CAST(strftime(r.as_of, '%Y%m%d') AS INTEGER) AS as_of_key, r.*, s.seller_key
        FROM dss.recommendation r JOIN core.dim_seller s ON s.seller_id = r.seller_id AND s.is_current""",
}


def export(db: Path | None = None, out_dir: Path = OUT_DIR) -> dict:
    db = Path(db or current_db())
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = out_dir / f".tmp_{os.getpid()}"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir()
    con = duckdb.connect(str(db), read_only=True)
    rows = {}
    try:
        for name, sql in TABLES.items():
            path = (tmp / f"{name}.parquet").as_posix()
            con.execute(f"COPY ({sql}) TO '{path}' (FORMAT parquet, COMPRESSION snappy)")
            rows[name] = con.execute(f"SELECT count(*) FROM read_parquet('{path}')").fetchone()[0]
    finally:
        con.close()
    try:
        for f in tmp.iterdir():
            os.replace(f, out_dir / f.name)
    except PermissionError as e:
        raise RuntimeError(f"Khong ghi de duoc {e.filename}: Power BI dang lam moi? Thu lai sau khi refresh xong.") from e
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # Ke hoach da chot do app ghi rieng (src/app/decisions.py); chua ai chot thi tao file rong de Power BI refresh khong loi
    from src.app import decisions
    decisions.ensure(out_dir / decisions.FILE.name)
    manifest = {"release": db.name, "as_of": AS_OF, "exported_at": dt.datetime.now().isoformat(timespec="seconds"),
                "out_dir": str(out_dir), "rows": rows}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False), encoding="utf-8")
    if out_dir == OUT_DIR:
        sync_pbip_path(out_dir)
    return manifest


PBIP_EXPR = ROOT / "powerbi" / "OlistSellerHealth.SemanticModel" / "definition" / "expressions.tmdl"


def sync_pbip_path(out_dir: Path = OUT_DIR) -> bool:
    """Power BI chi nhan duong dan tuyet doi, nen tro tham so ThuMucParquet vao thu muc xuat cua may dang chay.
    Khong doi thi khong ghi file. Mo lai .pbip sau khi doi."""
    with open(PBIP_EXPR, encoding="utf-8", newline="") as f:  # giu CRLF/LF cua file goc
        text = f.read()
    new = re.sub(r'(expression ThuMucParquet = )"[^"]*"', lambda m: f'{m.group(1)}"{out_dir.resolve()}{os.sep}"', text, count=1)
    if new == text:
        return False
    PBIP_EXPR.write_text(new, encoding="utf-8", newline="")
    _hide_local_path()
    return True


def _hide_local_path():
    """Duong dan tuyet doi la cua rieng tung may: bao git bo qua thay doi o expressions.tmdl de khong commit nham.
    Muon sua that file nay thi chay: git update-index --no-skip-worktree <file>."""
    try:
        subprocess.run(["git", "-C", str(ROOT), "update-index", "--skip-worktree", str(PBIP_EXPR.relative_to(ROOT))],
                       check=False, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        pass  # khong co git (vd trong Docker): bo qua


if __name__ == "__main__":
    info = export(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    print(f"Da xuat {len(info['rows'])} bang tu {info['release']} vao {info['out_dir']}")
    for k, v in info["rows"].items():
        print(f"  {k:22s} {v:>8,}")
