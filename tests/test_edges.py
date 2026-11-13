"""Chay moi man hinh tren moi moc as-of va mot so bo loc hiem, khong can trinh duyet.

Chay: python -m tests.test_edges
"""
import json
import sys
import time

from streamlit.testing.v1 import AppTest

from src.config import EVIDENCE_DIR, ROOT

SCREENS = ["Cần chú ý", "Chi tiết seller", "Bảng kế hoạch", "What-if tuyến", "Kiểm chứng"]
results, failed = [], 0
at = AppTest.from_file(str(ROOT / "src" / "app" / "app.py"), default_timeout=120).run()
asofs = list(at.select_slider[0].options)
for label in asofs:
    for screen in SCREENS:
        at.select_slider[0].set_value(label)
        at.radio[0].set_value(screen)
        t0 = time.time()
        at.run()
        ok = not at.exception
        failed += not ok
        results.append({"as_of": label, "screen": screen, "ok": ok, "seconds": round(time.time() - t0, 2), "error": [e.message[:200] for e in at.exception]})
        if not ok:
            print("FAIL", label, screen, at.exception[0].message[:400], flush=True)
    print("xong", label, flush=True)

EVIDENCE_DIR.mkdir(exist_ok=True)
(EVIDENCE_DIR / "edge_test_results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
times = sorted(r["seconds"] for r in results if "seconds" in r)
print(f"Thoi gian xu ly phia server moi man hinh: trung vi {times[len(times) // 2]}s, lau nhat {times[-1]}s")
print(f"{len(results) - failed}/{len(results)} truong hop khong loi")
sys.exit(1 if failed else 0)
