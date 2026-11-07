"""Ghi hash va so dong cua file nguon vao data/manifest.json. Chi chay lai khi co y doi bo du lieu.

Chay: python -m scripts.make_manifest
"""
import json

import duckdb

from src.config import RAW_DIR, ROOT
from src.etl.build import SOURCES, sha256_of

files = {}
con = duckdb.connect()
for file in SOURCES.values():
    path = RAW_DIR / file
    rows = con.execute(f"""SELECT count(*) FROM read_csv('{path.as_posix().replace("'", "''")}', header=true, all_varchar=true, quote='"', escape='"')""").fetchone()[0]
    files[file] = {"sha256": sha256_of(path), "rows": rows}
out = ROOT / "data" / "manifest.json"
out.write_text(json.dumps({"dataset": "olistbr/brazilian-ecommerce", "files": files}, indent=1), encoding="utf-8")
print(out, len(files))
