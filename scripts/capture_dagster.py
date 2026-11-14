"""Chụp giao diện Dagster (đồ thị asset, lần chạy, Gantt) để đưa vào báo cáo.

Chạy sau khi đã mở Dagster bằng .\\run_pipeline.ps1 (http://localhost:3000):
    python scripts/capture_dagster.py [thu_muc_ra] [run_id]
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
LOC = "src.pipeline.definitions"
OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "report/image")
RUN_ID = sys.argv[2] if len(sys.argv) > 2 else None


def prepare(page, url):
    page.goto(url)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(2500)
    skip = page.get_by_role("button", name="Skip")
    if skip.count():
        skip.first.click()
        page.wait_for_timeout(500)
    hide = page.get_by_role("button", name="Hide navigation")
    if hide.count():
        hide.first.click()
        page.wait_for_timeout(500)


def expand_groups(page):
    """Mở menu cài đặt của đồ thị và chọn 'Expand all groups'."""
    item = page.locator("text=Expand all groups >> visible=true")
    # nút bánh răng nằm trong cột nút ở góc phải dưới đồ thị
    w, h = page.viewport_size["width"], page.viewport_size["height"]
    for b in page.locator("button").all():
        box = b.bounding_box()
        if not (box and box["x"] > w - 80 and box["y"] > h - 160):
            continue
        b.click()
        page.wait_for_timeout(500)
        if item.count():
            item.first.click()
            page.wait_for_timeout(2500)
            return
        page.keyboard.press("Escape")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 900}, device_scale_factor=2)

        # 1) Đồ thị phụ thuộc toàn bộ asset (tương đương Graph View của Airflow)
        prepare(page, f"{BASE}/asset-groups")
        expand_groups(page)
        page.keyboard.press("Escape")
        page.mouse.click(1000, 300)          # đóng menu cài đặt
        page.mouse.click(340, 80)            # thu gọn cây nhóm bên trái
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "dagster_1_asset_lineage.png"),
                        clip={"x": 75, "y": 110, "width": 1525, "height": 520})
        print("Captured dagster_1_asset_lineage")

        # 2) Danh sách lần chạy
        prepare(page, f"{BASE}/runs")
        page.screenshot(path=str(OUT / "dagster_3_runs.png"))
        print("Captured dagster_3_runs")

        # 3) Chi tiết một lần chạy: biểu đồ Gantt các bước
        if RUN_ID:
            prepare(page, f"{BASE}/runs/{RUN_ID}")
            page.wait_for_timeout(2000)
            page.mouse.click(1378, 80)       # nút mở rộng vùng biểu đồ Gantt
            page.wait_for_timeout(2000)
            page.mouse.move(1590, 10)
            page.wait_for_timeout(800)
            page.screenshot(path=str(OUT / "dagster_4_run_gantt.png"))
            print("Captured dagster_4_run_gantt")
        browser.close()


if __name__ == "__main__":
    main()
