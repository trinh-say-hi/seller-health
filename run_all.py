"""Dung lai toan bo he thong tu CSV: kho -> DSS -> catalog -> test (ca lakehouse va dbt neu co), roi phat hanh.

Chay: python run_all.py
Kho moi duoc dung thanh mot ban phat hanh rieng, qua test moi tro current.json sang, nen khong can tat app.
Neu dat OLIST_DB (vi du trong Docker) thi dung thang vao file do nhu truoc, khong qua buoc phat hanh.
Muon xem tung buoc, lich su chay va lineage thi dung Dagster: .\run_pipeline.ps1
"""
import os
import shutil
import subprocess
import sys

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

# dbt doc OLIST_DB trong profiles.yml nen chay tren chinh ban dang dung, truoc khi phat hanh.
if shutil.which("dbt"):
    print("\n=== dbt staging & test ===", flush=True)
    dbt_args = ["--project-dir", "dbt", "--profiles-dir", "dbt"]
    code = subprocess.call(["dbt", "run", "--select", "staging", *dbt_args], env=env)
    if code:
        stop("dbt run", code)
    code = subprocess.call(["dbt", "test", *dbt_args], env=env)
    if code:
        stop("dbt test", code)

if not fixed:
    info = publish(target, note="run_all.py")
    print(f"\nDa phat hanh {info['current']} (ban truoc: {info['previous']})")
print("\nXong. Mo app: python -m streamlit run src/app/app.py")
