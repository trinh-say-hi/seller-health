"""Chay dbt (dbt/) tren mot ban kho: dung lai cac model vao schema dbt_* roi chay test, gom ca doi chieu voi kho chinh.

Chay tay tren kho dang dung: python -m src.pipeline.dbt_runner          (mac dinh: build)
                              python -m src.pipeline.dbt_runner test     (hoac docs generate, ...)
run_all.py va Dagster goi build() voi OLIST_DB tro vao ban dang dung, truoc khi phat hanh.
dbt ghi vao dbt_stg, dbt_core, dbt_mart nen khong bao gio ghi de bang core/mart ma app va Power BI dang doc.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from src.config import ROOT, current_db

DBT_DIR = ROOT / "dbt"


def available() -> bool:
    return importlib.util.find_spec("dbt.adapters.duckdb") is not None


def run(db: Path, args: list[str]) -> int:
    """Goi dbt bang chinh Python dang chay (khong can dbt.exe tren PATH), voi duong dan tuong doi theo repo."""
    # resolve(): dbt chay trong thu muc dbt/, nen duong dan tuong doi phai doi ve tuyet doi truoc.
    env = {**os.environ, "OLIST_DB": str(Path(db).resolve()), "PYTHONUTF8": "1"}
    cmd = [sys.executable, "-W", "ignore::RuntimeWarning", "-m", "dbt.cli.main", *args,
           "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]
    return subprocess.call(cmd, cwd=DBT_DIR, env=env)


def build(db: Path) -> int:
    return run(db, ["build"])


if __name__ == "__main__":
    if not available():
        sys.exit("Chua cai dbt-duckdb: pip install -r requirements-dev.txt")
    sys.exit(run(current_db(), sys.argv[1:] or ["build"]))
