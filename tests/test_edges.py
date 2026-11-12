"""Chay moi man hinh tren moi moc as-of va mot so bo loc hiem, khong can trinh duyet.

Chay: python -m tests.test_edges
"""
import json
import sys
import time

from streamlit.testing.v1 import AppTest

from src.config import EVIDENCE_DIR, ROOT

SCREENS = ["Tổng quan", "Lỗi giao trễ", "Chi tiết seller", "Bảng kế hoạch", "What-if tuyến", "Kiểm chứng", "Đa chiều"]
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

# Bo loc hiem o moc som nhat: co the khong co du lieu
at.select_slider[0].set_value(asofs[0])
at.radio[0].set_value("Tổng quan")
at.run()
for region in at.selectbox[0].options:
    for cat in at.selectbox[1].options[-4:]:
        at.selectbox[0].set_value(region)
        at.selectbox[1].set_value(cat)
        at.run()
        ok = not at.exception
        failed += not ok
        results.append({"as_of": asofs[0], "screen": f"Tổng quan: {region}/{cat}", "ok": ok, "error": [e.message[:200] for e in at.exception]})
        if not ok:
            print("FAIL", region, cat, at.exception[0].message[:400], flush=True)

EVIDENCE_DIR.mkdir(exist_ok=True)
(EVIDENCE_DIR / "edge_test_results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
times = sorted(r["seconds"] for r in results if "seconds" in r)
print(f"Thoi gian xu ly phia server moi man hinh: trung vi {times[len(times) // 2]}s, lau nhat {times[-1]}s")
print(f"{len(results) - failed}/{len(results)} truong hop khong loi")
sys.exit(1 if failed else 0)
