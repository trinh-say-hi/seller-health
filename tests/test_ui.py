"""Test giao dien bang trinh duyet that. Can app dang chay o cong 8599 va da cai playwright.

Chay: python -m tests.test_ui <thu_muc_anh>
"""
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd
from playwright.sync_api import sync_playwright

from src.config import DB_PATH, EVIDENCE_DIR

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else EVIDENCE_DIR / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)
URL = "http://localhost:8599"
SCREENS = ["Tổng quan", "Lỗi giao trễ", "Chi tiết seller", "Bảng kế hoạch", "What-if tuyến", "Kiểm chứng", "Đa chiều"]
ASCII = dict(zip(SCREENS, ["tong_quan", "loi_giao_tre", "chi_tiet_seller", "bang_ke_hoach", "whatif_tuyen", "kiem_chung", "da_chieu"]))
results = []


def check(name, ok, detail=""):
    results.append({"test": name, "ok": bool(ok), "detail": str(detail)})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" ({detail})" if detail != "" else ""), flush=True)


def settle(page):
    page.wait_for_timeout(1000)
    page.wait_for_function("""() => !document.querySelector('[data-testid="stStatusWidget"]')
        && !document.querySelector('[data-stale="true"]')
        && !document.querySelector('[data-testid="stSkeleton"]')""", timeout=90000)
    page.wait_for_timeout(2500)


def errors(page):
    return [e.inner_text()[:300] for e in page.locator('[data-testid="stException"]').all()]


def goto(page, name):
    """Chon man hinh trong sidebar: mo sidebar, bam ten man hinh, roi thu sidebar lai de do khung hinh nhu nguoi dung thay."""
    opener = page.locator('[data-testid="stExpandSidebarButton"]')
    if opener.count() and opener.first.is_visible():
        opener.first.click()
        page.wait_for_timeout(500)
    page.locator('[data-testid="stSidebar"] div[data-testid="stRadio"] label').filter(has_text=name).first.click()
    settle(page)
    closer = page.locator('[data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebarCollapseButton"]')
    if closer.count():
        closer.first.click()
        page.wait_for_timeout(800)
    settle(page)


def metric(page, label):
    box = page.locator('[data-testid="stMetric"]').filter(has_text=label).first
    return box.locator('[data-testid="stMetricValue"]').inner_text()


def overflow(page):
    """Chieu cao noi dung vuot khung hinh bao nhieu pixel. 0 la khong phai cuon."""
    return page.evaluate("""() => { const m = document.querySelector('[data-testid="stMain"]');
        return [m.scrollHeight - m.clientHeight, m.scrollWidth - m.clientWidth]; }""")


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1440, "height": 800})
    console = []
    page.on("pageerror", lambda e: console.append(str(e)[:200]))
    page.goto(URL)
    page.wait_for_selector('input[type="range"][aria-label*="as-of"]', timeout=90000, state="attached")
    settle(page)

    for i, name in enumerate(SCREENS, 1):
        goto(page, name)
        err = errors(page)
        check(f"Man hinh '{name}' khong loi", not err, err[:1] or "")
        check(f"Man hinh '{name}' co KPI", page.locator('[data-testid="stMetric"]').count() >= 4, page.locator('[data-testid="stMetric"]').count())
        v, h = overflow(page)
        check(f"Man hinh '{name}' vua 1440x800, khong cuon", v <= 0 and h <= 0, f"doc {v}px, ngang {h}px")
        page.screenshot(path=str(OUT / f"{i}_{ASCII[name]}.png"))

    goto(page, "Tổng quan")
    check("Co chu thich KPI tu metrics.yml", page.locator('[data-testid="stMetric"] [data-testid="stTooltipIcon"], [data-testid="stMetric"] [data-testid="stTooltipHoverTarget"]').count() >= 4)
    v1 = metric(page, "GMV")
    db = duckdb.connect(str(DB_PATH), read_only=True)
    gmv, orders = db.execute("""SELECT sum(price), count(DISTINCT order_id) FROM core.fact_sales_item
                                WHERE is_valid_sale AND purchase_ts >= DATE '2018-06-01' AND purchase_ts < DATE '2018-07-01'""").fetchone()
    late, due = db.execute("""SELECT count(DISTINCT i.order_id) FILTER (WHERE o.d IS NULL OR CAST(o.d AS DATE) > CAST(o.est AS DATE)), count(DISTINCT i.order_id)
                              FROM core.fact_sales_item i JOIN (SELECT order_id, try_cast(order_estimated_delivery_date AS TIMESTAMP) est, try_cast(order_delivered_customer_date AS TIMESTAMP) d
                                  FROM raw.orders WHERE dwh_batch <= '2018-06' QUALIFY row_number() OVER (PARTITION BY order_id ORDER BY dwh_batch DESC) = 1) o USING (order_id)
                              WHERE i.is_valid_sale AND o.est >= DATE '2018-06-01' AND o.est < DATE '2018-07-01'""").fetchone()
    db.close()
    fmt = lambda x, d=0: f"{x:,.{d}f}".replace(",", "§").replace(".", ",").replace("§", ".")
    check("GMV tren giao dien khop SQL", v1 == f"{fmt(float(gmv) / 1000)}k", f"{v1} / {float(gmv):,.2f}")
    check("So don tren giao dien khop SQL", metric(page, "Số đơn") == fmt(orders), metric(page, "Số đơn"))
    check("Ty le tre tren giao dien khop SQL", metric(page, "Tỷ lệ đơn trễ hẹn") == fmt(100 * late / due, 1) + "%", f"{metric(page, 'Tỷ lệ đơn trễ hẹn')} / {late}/{due}")

    slider = page.locator('input[type="range"][aria-label*="as-of"]').first
    slider.focus()
    for _ in range(4):
        page.keyboard.press("ArrowLeft")
    settle(page)
    v2 = metric(page, "GMV")
    check("Doi as-of lam so GMV doi", v1 != v2, f"{v1} -> {v2}")
    check("Sau khi doi as-of khong loi", not errors(page))

    # Keo tha that tren bang kanban
    goto(page, "Bảng kế hoạch")
    frame = page.frame_locator("[data-testid=\"stMain\"] iframe").first
    columns = frame.locator(".sortable-container")
    check("Bang co 4 cot", columns.count() == 4, columns.count())
    headers = [columns.nth(i).locator(".column-title").inner_text() for i in range(columns.count())]
    check("Dung ten cac cot", headers == ["Gọi ngay", "Hỗ trợ vận hành", "Email tự động", "Chưa xử lý"], headers)
    boxes = [columns.nth(i).bounding_box() for i in range(4)]
    check("Cac cot nam ngang hang nhau", len({round(b["y"]) for b in boxes}) == 1 and boxes[0]["x"] < boxes[3]["x"], [round(b["x"]) for b in boxes])
    counts = [columns.nth(i).locator(".sortable-item").count() for i in range(4)]
    check("Co the tren bang", sum(counts) > 10, counts)
    saved0, cost0 = metric(page, "Giữ được"), metric(page, "Tiền đã dùng")
    check("Cac so nam tren bang keo", page.locator('[data-testid="stMetric"]').first.bounding_box()["y"] < boxes[0]["y"])
    page.screenshot(path=str(OUT / "7_bang_truoc_khi_keo.png"))

    def drag(src, dst):
        a, b = src.bounding_box(), dst.bounding_box()
        page.mouse.move(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2)
        page.mouse.down()
        page.mouse.move(a["x"] + a["width"] / 2 + 8, a["y"] + a["height"] / 2 + 8, steps=4)
        page.mouse.move(b["x"] + b["width"] / 2, b["y"] + min(b["height"], 300) - 12, steps=25)
        page.wait_for_timeout(300)
        page.mouse.up()

    # Bam the: khung chi tiet ben phai doi theo
    target = columns.nth(1).locator(".sortable-item").first
    target_id = target.locator(".id").inner_text()
    target.click()
    settle(page)
    check("Bam the hien chi tiet seller do", target_id in page.locator("#seller-detail").inner_text(), target_id)
    frame = page.frame_locator("[data-testid=\"stMain\"] iframe").first
    columns = frame.locator(".sortable-container")
    check("Bam the khong lam mat the", [columns.nth(i).locator(".sortable-item").count() for i in range(4)] == counts)

    moved_text = columns.nth(0).locator(".sortable-item .id").first.inner_text()
    drag(columns.nth(0).locator(".sortable-item").first, columns.nth(3).locator(".sortable-container-body"))
    settle(page)
    page.wait_for_timeout(1500)
    columns = page.frame_locator("[data-testid=\"stMain\"] iframe").first.locator(".sortable-container")
    counts2 = [columns.nth(i).locator(".sortable-item").count() for i in range(4)]
    cost1, saved1 = metric(page, "Tiền đã dùng"), metric(page, "Giữ được")
    check("Keo tha chuyen the giua cot", counts2[0] == counts[0] - 1 and counts2[3] == counts[3] + 1, f"{counts} -> {counts2}")
    check("Keo tha lam tien da dung doi", cost0 != cost1, f"{cost0} -> {cost1}")
    check("Keo tha lam GMV ky vong doi", saved0 != saved1, f"{saved0} -> {saved1}")
    check("Sau keo tha khong loi", not errors(page))
    v, h = overflow(page)
    check("Sau keo tha van khong phai cuon", v <= 0, f"doc {v}px")
    page.screenshot(path=str(OUT / "8_bang_sau_khi_keo.png"))

    moved_label = moved_text.strip()
    header_counts = [columns.nth(i).locator(".count").inner_text() for i in range(4)]
    check("So the tren tieu de cot cap nhat", header_counts == [str(c) for c in counts2], header_counts)
    with page.expect_download() as dl:
        page.get_by_role("button", name="Xuất kế hoạch ra CSV").click()
    csv_path = OUT.parent / "_export_test.csv"
    dl.value.save_as(csv_path)
    exported = pd.read_csv(csv_path, encoding="utf-8-sig")
    row = exported[exported.seller_id.str.startswith(moved_label)]
    check("CSV phan anh thao tac keo tay", len(row) == 1 and row["Hành động"].iloc[0] == "Chưa xử lý", row["Hành động"].tolist())
    check("CSV co ly do cho moi dong", exported.reason.notna().all() and len(exported) == sum(counts), len(exported))
    csv_path.unlink()

    moves = 0
    for _ in range(14):
        columns = page.frame_locator("[data-testid=\"stMain\"] iframe").first.locator(".sortable-container")
        src = columns.nth(3).locator(".sortable-item").first
        if src.count() == 0:
            break
        drag(src, columns.nth(1).locator(".sortable-container-body"))
        settle(page)
        moves += 1
        if page.get_by_text("Vượt").count():
            break
    check("Vuot rang buoc thi co canh bao", page.get_by_text("Vượt").count() > 0, f"sau {moves} lan keo tiep")
    page.screenshot(path=str(OUT / "9_bang_vuot_rang_buoc.png"))

    page.get_by_role("button", name="Đặt lại").click()
    settle(page)
    page.wait_for_timeout(1500)
    check("Dat lai tra ve de xuat", metric(page, "Tiền đã dùng") == cost0, metric(page, "Tiền đã dùng"))

    # Tra as-of ve mac dinh roi thu what-if
    goto(page, "What-if tuyến")
    r1 = metric(page, "Tỷ lệ trễ")
    s = page.locator('input[type="range"][aria-label*="Hứa thêm"]').first
    s.focus()
    for _ in range(3):
        page.keyboard.press("ArrowRight")
    settle(page)
    r2 = metric(page, "Tỷ lệ trễ")
    check("What-if hua them ngay lam ty le tre doi", r1 != r2, f"{r1} -> {r2}")
    page.screenshot(path=str(OUT / "10_whatif_sau_khi_doi.png"))

    # Cac moc as-of khac cung phai vua khung hinh
    slider = page.locator('input[type="range"][aria-label*="as-of"]').first
    slider.focus()
    page.keyboard.press("Home")
    settle(page)
    for name in SCREENS:
        goto(page, name)
        v, h = overflow(page)
        check(f"Moc som nhat: '{name}' khong cuon", v <= 0 and h <= 0, f"doc {v}px, ngang {h}px")
    check("Khong co loi JavaScript", not console, console[:2] or "")
    browser.close()

EVIDENCE_DIR.mkdir(exist_ok=True)
(EVIDENCE_DIR / "ui_test_results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
bad = [r for r in results if not r["ok"]]
if bad:
    print("\nHONG:")
    for r in bad:
        print(" -", r["test"], r["detail"])
print(f"\n{len(results) - len(bad)}/{len(results)} test UI dat")
sys.exit(1 if bad else 0)
