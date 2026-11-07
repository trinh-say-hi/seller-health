"""Nap mo ta tu catalog.yml vao kho bang COMMENT ON, roi sinh docs/data_catalog.md tu chinh kho.

Chay: python -m src.etl.catalog
Bang hoac cot thieu mo ta o Gold, DSS, van hanh se lam lenh nay bao loi, de catalog khong bi lech.
"""
import sys

import duckdb
import yaml

from src.config import DB_PATH, ROOT

STRICT_SCHEMAS = ("core", "mart", "dss", "ops")
SCHEMA_ORDER = ["raw", "stg", "core", "mart", "dss", "ops"]


def sql_str(text):
    return "'" + str(text).replace("'", "''") + "'"


def apply(con, catalog):
    missing = []
    common = catalog["common"]
    existing = {f"{s}.{t}" for s, t in con.execute("SELECT schema_name, table_name FROM duckdb_tables()").fetchall()}
    for name, meta in catalog["tables"].items():
        if name not in existing:
            missing.append(f"catalog có {name} nhưng kho không có")
            continue
        con.execute(f"COMMENT ON TABLE {name} IS {sql_str(meta['description'])}")
        for col, in con.execute(f"SELECT column_name FROM information_schema.columns WHERE table_schema || '.' || table_name = '{name}'").fetchall():
            text = meta.get("columns", {}).get(col) or common.get(col)
            if text:
                con.execute(f'COMMENT ON COLUMN {name}."{col}" IS {sql_str(text)}')
            elif name.split(".")[0] in STRICT_SCHEMAS:
                missing.append(f"{name}.{col} chưa có mô tả")
    for name in existing:
        if name.split(".")[0] in STRICT_SCHEMAS + ("raw",) and name not in catalog["tables"]:
            missing.append(f"{name} chưa có trong catalog")
    return missing


def render(con, catalog):
    lines = ["# Data catalog", "",
             "Tự sinh từ kho bằng `python -m src.etl.catalog`, không sửa tay. Mô tả lấy từ `catalog.yml`.", "",
             "| Lớp | Schema | Vai trò |", "|---|---|---|",
             "| Bronze | `raw` | Dữ liệu gốc dạng chữ, thêm cột `dwh_` |",
             "| Silver | `stg` | Đã làm sạch: giao dịch là view, master là bảng |",
             "| Gold | `core` | Galaxy schema: dimension và fact |",
             "| Gold | `mart` | Tổng hợp, đóng băng lúc chốt đợt |",
             "| DSS | `dss` | Nhãn, điểm rủi ro, kế hoạch, đánh giá |",
             "| Vận hành | `ops` | Nhật ký, cách ly, đối soát, nguồn gốc |", ""]
    rows = {}
    for s, t in con.execute("SELECT schema_name, table_name FROM duckdb_tables()").fetchall():
        rows[f"{s}.{t}"] = con.execute(f"SELECT count(*) FROM {s}.{t}").fetchone()[0]
    lines += ["## Tổng quan", "", "| Bảng | Lớp | Loại | Grain | Số dòng |", "|---|---|---|---|---:|"]
    ordered = sorted(catalog["tables"], key=lambda n: (SCHEMA_ORDER.index(n.split(".")[0]), n))
    for name in ordered:
        m = catalog["tables"][name]
        lines.append(f"| `{name}` | {m['layer']} | {m['kind']} | {m['grain']} | {rows.get(name, 0):,} |".replace(",", "."))
    for schema in SCHEMA_ORDER:
        if schema in ("raw", "stg"):
            continue
        lines += ["", f"## Schema `{schema}`"]
        for name in [n for n in ordered if n.startswith(schema + ".")]:
            m = catalog["tables"][name]
            lines += ["", f"### `{name}`", "", f"{m['description']}", "", f"**Loại:** {m['kind']}. **Grain:** {m['grain']}.", "", "| Cột | Kiểu | Mô tả |", "|---|---|---|"]
            for col, typ, com in con.execute(f"SELECT column_name, data_type, comment FROM duckdb_columns() WHERE schema_name || '.' || table_name = '{name}' ORDER BY column_index").fetchall():
                lines.append(f"| `{col}` | {typ} | {com or ''} |")
    lines.append("")
    return "\n".join(lines)


def main():
    catalog = yaml.safe_load((ROOT / "catalog.yml").read_text(encoding="utf-8"))
    con = duckdb.connect(str(DB_PATH))
    missing = apply(con, catalog)
    if missing:
        print("Catalog chưa đủ:\n- " + "\n- ".join(missing))
        con.close()
        sys.exit(1)
    (ROOT / "docs" / "data_catalog.md").write_text(render(con, catalog), encoding="utf-8")
    con.execute("CHECKPOINT")
    n = con.execute("SELECT count(*), count(comment) FROM duckdb_columns() WHERE schema_name IN ('core','mart','dss','ops')").fetchone()
    con.close()
    print(f"Catalog xong: {n[1]}/{n[0]} cột có mô tả")


if __name__ == "__main__":
    main()
