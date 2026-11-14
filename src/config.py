"""Duong dan va tham so chung cua he thong."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "olist" / "raw"
SQL_DIR = ROOT / "src" / "sql"
EVIDENCE_DIR = ROOT / "evidence"

# Kho, ban phat hanh, Parquet Power BI deu nam trong warehouse/ cua repo (da gitignore), nen doi may khong phai sua duong dan.
# Repo nam trong OneDrive thi dat OLIST_HOME ra ngoai (vd %LOCALAPPDATA%\seller_health) de dong bo khong khoa file.
HOME = Path(os.environ.get("OLIST_HOME", str(ROOT / "warehouse")))
# Moi lan dung lai, kho duoc dung thanh mot ban phat hanh moi trong releases/, kiem tra xong moi tro current.json sang.
# Khi app dang doc mot file DuckDB thi tien trinh khac khong mo file do de ghi duoc, nen khong dung de len kho app dang doc.
RELEASES_DIR = HOME / "releases"
POINTER = HOME / "current.json"


def current_db() -> Path:
    """Kho dang dung: OLIST_DB neu dat (Docker, test, buoc dung ban moi), roi con tro current.json, roi file cu olist.duckdb."""
    if os.environ.get("OLIST_DB"):
        return Path(os.environ["OLIST_DB"])
    try:
        return RELEASES_DIR / json.loads(POINTER.read_text(encoding="utf-8"))["current"]
    except (FileNotFoundError, KeyError, ValueError):
        return HOME / "olist.duckdb"


DB_PATH = current_db()


def lake_dir(db: Path) -> Path:
    """Lakehouse Parquet di kem tung ban kho (olist_x.duckdb -> olist_x_lake/), nen quay lui hay dung hong khong lam lech nhau."""
    return db.with_name(db.stem + "_lake")


LAKE_DIR = lake_dir(DB_PATH)
BRONZE_LAKE = LAKE_DIR / "bronze"
SILVER_LAKE = LAKE_DIR / "silver"
GOLD_LAKE = LAKE_DIR / "gold"

FIRST_BATCH = "2016-09"
LAST_BATCH = "2018-10"
# Sau moc nay chi con vai don huy, khong dung de tinh nhan.
RELIABLE_END = "2018-09-01"
FIRST_SCORED_ASOF = "2017-09-01"
LAST_ASOF = "2018-09-01"
LAST_LABELED_ASOF = "2018-07-01"
HORIZON_DAYS = 45
