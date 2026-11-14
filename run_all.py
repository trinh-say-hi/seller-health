"""Dung lai toan bo he thong tu CSV: kho -> DSS -> catalog -> test (ca lakehouse va dbt neu co), roi phat hanh.

Chay: python run_all.py
Kho moi duoc dung thanh mot ban phat hanh rieng, qua test moi tro current.json sang, nen khong can tat app.
Neu dat OLIST_DB (vi du trong Docker) thi dung thang vao file do nhu truoc, khong qua buoc phat hanh.
Muon xem tung buoc, lich su chay va lineage thi dung Dagster: .\run_pipeline.ps1
"""
import os
import subprocess
import sys

from src.pipeline import dbt_runner
from src.pipeline.release import new_release_path, publish

MODULES = [
    "src.etl.build",
    "src.dss.run",
    "src.etl.catalog",
    "tests.test_system",
    "tests.test_lakehouse_medallion",
]

fixed = os.environ.get("OLIST_DB")
target = fixed or str(new_release_path("run_all"))
env = {**os.environ, "OLIST_DB": target, "PYTHONUTF8": "1"}


def stop(step: str, code: int) -> None:
    print(f"\nDung o {step}. Kho dang dung khong doi; ban dung do nam o {target}.")
    sys.exit(code)


for module in MODULES:
    print(f"\n=== {module} ===", flush=True)
    code = subprocess.call([sys.executable, "-m", module], env=env)
    if code:
        stop(module, code)

# dbt dung lai kho tu raw vao schema dbt_* va doi chieu voi kho chinh, tren chinh ban dang dung, truoc khi phat hanh.
if dbt_runner.available():
    print("\n=== dbt build ===", flush=True)
    code = dbt_runner.build(target)
    if code:
        stop("dbt build", code)
else:
    print("\n(Bo qua dbt: chua cai dbt-duckdb, xem requirements-dev.txt)")

if not fixed:
    info = publish(target, note="run_all.py")
    print(f"\nDa phat hanh {info['current']} (ban truoc: {info['previous']})")
print("\nXong. Mo app: python -m streamlit run src/app/app.py")
