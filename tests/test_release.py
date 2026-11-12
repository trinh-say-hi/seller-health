"""Kiem tra co che ban phat hanh kho tren mot thu muc tam, khong dong vao kho that.

Chay: python -m tests.test_release
Tinh huong chinh: app dang mo kho cu (Windows khoa file) ma pipeline van phat hanh duoc ban moi, va quay lui duoc.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from src.config import EVIDENCE_DIR, ROOT

# Chay phan kiem tra trong tien trinh con voi OLIST_HOME tam, vi src.config doc bien moi truong luc import.
CHILD = r'''
import json, os, sys
import duckdb
from src.config import POINTER, RELEASES_DIR, current_db
from src.pipeline import release
results = []
def check(name, ok, detail=""):
    results.append({"test": name, "ok": bool(ok), "detail": str(detail)})

def make(tag, value):
    p = release.new_release_path(tag)
    con = duckdb.connect(str(p)); con.execute(f"CREATE TABLE t AS SELECT {value} AS v"); con.execute("CHECKPOINT"); con.close()
    return p

check("Chua co con tro thi dung file cu olist.duckdb", current_db().name == "olist.duckdb", current_db())
a = make("a", 1)
check("Ban moi nam trong releases/", a.parent == RELEASES_DIR, a)
release.publish(a)
check("Phat hanh: current_db tro sang ban moi", current_db() == a, current_db())

# App dang mo ban a o che do chi doc, giong Streamlit
app = duckdb.connect(str(a), read_only=True)
import time; time.sleep(1.1)
b = make("b", 2)
info = release.publish(b)
check("Phat hanh duoc khi app dang mo ban cu", current_db() == b and info["previous"] == a.name, info)
check("App van doc duoc ban cu trong luc chuyen", app.execute("SELECT v FROM t").fetchone()[0] == 1)
import subprocess
probe = subprocess.run([sys.executable, "-c", f"import duckdb; duckdb.connect(r'{a}').close()"], capture_output=True, text=True)
check("Khoa ghi: app dang doc thi tien trinh khac khong mo ghi duoc (ly do phai dung ban moi)",
      probe.returncode != 0, probe.stderr[-200:])
check("Ket noi moi doc ban moi", duckdb.connect(str(current_db()), read_only=True).execute("SELECT v FROM t").fetchone()[0] == 2)

time.sleep(1.1)
c = make("c", 3)
release.publish(c)
names = sorted(p.name for p in RELEASES_DIR.glob("olist_*.duckdb"))
check("Don dep: giu ban dang dung va ban truoc", c.name in names and b.name in names, names)
check("Don dep: chi con 2 ban", a.name not in names and len(names) == 2, names)
check("Don dep khi app con mo ban cu: app van doc duoc toi khi tai lai trang", app.execute("SELECT v FROM t").fetchone()[0] == 1)
app.close()

info = release.rollback()
check("Quay lui: tro ve ban truoc", current_db() == b and info["previous"] == c.name, info)
release.rollback()
check("Quay lui lan nua: tro lai ban moi", current_db() == c)

try:
    release.publish(RELEASES_DIR.parent / "ngoai.duckdb")
    check("Tu choi phat hanh file ngoai releases/", False)
except ValueError:
    check("Tu choi phat hanh file ngoai releases/", True)

d = release.new_release_path("d")
con = duckdb.connect(str(d)); con.execute("CREATE TABLE t AS SELECT 4 AS v")
try:
    release.publish(d)
    ok = not d.with_name(d.name + ".wal").exists()
    check("Tu choi phat hanh ban con file .wal (dang ghi do)", ok, "khong co .wal de thu")
except ValueError:
    check("Tu choi phat hanh ban con file .wal (dang ghi do)", current_db() == c)
con.close()

POINTER.write_text("{hong", encoding="utf-8")
check("Con tro hong thi quay ve file mac dinh, khong vo app", current_db().name == "olist.duckdb", current_db())
print(json.dumps(results, ensure_ascii=False))
'''

with tempfile.TemporaryDirectory() as td:
    env = {k: v for k, v in os.environ.items() if k != "OLIST_DB"}
    env.update({"OLIST_HOME": td, "PYTHONUTF8": "1"})
    out = subprocess.run([sys.executable, "-c", CHILD], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
if out.returncode:
    print(out.stdout, out.stderr)
    sys.exit(1)
results = json.loads(out.stdout.strip().splitlines()[-1])
EVIDENCE_DIR.mkdir(exist_ok=True)
(EVIDENCE_DIR / "release_test_results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
bad = [r for r in results if not r["ok"]]
for r in results:
    print("OK  " if r["ok"] else "HONG", r["test"], "" if r["ok"] else r["detail"])
print(f"\n{len(results) - len(bad)}/{len(results)} test dat")
sys.exit(1 if bad else 0)
