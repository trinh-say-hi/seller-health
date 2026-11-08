"""Dung lai toan bo he thong tu CSV: kho -> DSS -> catalog -> test.

Chay: python run_all.py
Hay tat app truoc khi chay, vi app dang giu file database.
"""
import subprocess
import sys

MODULES = [
    "src.etl.build",
    "src.dss.run",
    "src.etl.catalog",
    "tests.test_system",
    "tests.test_lakehouse_medallion",
]

for module in MODULES:
    print(f"\n=== {module} ===", flush=True)
    code = subprocess.call([sys.executable, "-m", module])
    if code:
        sys.exit(code)
print("\nXong. Mo app: python -m streamlit run src/app/app.py")
