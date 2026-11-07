"""Tao du lieu mau de nop bai: moi file nguon lay 200 dong dau vao data/sample.

Chay: python -m scripts.make_sample
Du lieu day du tai bang Kaggle, xem data/README.md.
"""
import pandas as pd

from src.config import RAW_DIR, ROOT

out = ROOT / "data" / "sample"
out.mkdir(parents=True, exist_ok=True)
for path in sorted(RAW_DIR.glob("*.csv")):
    pd.read_csv(path, nrows=200, dtype=str).to_csv(out / path.name, index=False)
    print(path.name)
