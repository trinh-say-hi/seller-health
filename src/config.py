"""Duong dan va tham so chung cua he thong."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "olist" / "raw"
SQL_DIR = ROOT / "src" / "sql"
EVIDENCE_DIR = ROOT / "evidence"

# Database dat ngoai OneDrive de tranh khoa file khi dong bo. Dat OLIST_DB de doi cho khac.
_LOCAL = Path(os.environ.get("LOCALAPPDATA", str(ROOT))) / "seller_health"
DB_PATH = Path(os.environ.get("OLIST_DB", str(_LOCAL / "olist.duckdb")))

FIRST_BATCH = "2016-09"
LAST_BATCH = "2018-10"
# Sau moc nay chi con vai don huy, khong dung de tinh nhan.
RELIABLE_END = "2018-09-01"
FIRST_SCORED_ASOF = "2017-09-01"
LAST_ASOF = "2018-09-01"
LAST_LABELED_ASOF = "2018-07-01"
HORIZON_DAYS = 45
