"""Sinh 4 so do cho bao cao vao docs/diagrams, dang SVG va PNG.

Chay: python -m scripts.make_diagrams
Star schema lay quan he tu cot khoa ngoai that trong kho. Lineage bao loi neu nhac toi bang khong con ton tai.
PNG can playwright (requirements-dev.txt) va Edge; khong co thi chi sinh SVG.
"""
from html import escape

import duckdb

from src.config import DB_PATH, ROOT

OUT = ROOT / "docs" / "diagrams"
INK, MUTED, LINE = "#0b0b0b", "#52514e", "#8a8983"
FILL = {"src": "#f4f4f1", "raw": "#f6e3d2", "stg": "#e8e7e3", "core": "#fbeec4", "mart": "#f7e2a0", "dss": "#cde2fb", "ops": "#e8e7e3", "app": "#d5efe3",
        "dim": "#cde2fb", "fact": "#fbeec4", "mini": "#d5efe3"}


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.body = w, h, []

    def box(self, x, y, w, h, title, lines=(), fill="#fff", size=13, bold=True, stroke=LINE):
        self.body.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="7" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
        ty = y + 18 if lines else y + h / 2 + size * .36
        anchor = 'x="%s" text-anchor="middle"' % (x + w / 2) if not lines else f'x="{x + 9}"'
        self.body.append(f'<text {anchor} y="{ty}" font-size="{size}" font-weight="{600 if bold else 400}" fill="{INK}">{escape(title)}</text>')
        for i, ln in enumerate(lines):
            self.body.append(f'<text x="{x + 9}" y="{ty + 16 + i * 15}" font-size="11.5" fill="{MUTED}">{escape(ln)}</text>')

    def text(self, x, y, s, size=13, bold=False, color=INK, anchor="start"):
        self.body.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{600 if bold else 400}" fill="{color}" text-anchor="{anchor}">{escape(s)}</text>')

    def line(self, x1, y1, x2, y2, arrow=True, color=LINE, width=1.2, dash=None):
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        marker = ' marker-end="url(#a)"' if arrow else ""
        self.body.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"{extra}{marker}/>')

    def render(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" font-family="Segoe UI, system-ui, sans-serif">'
                f'<defs><marker id="a" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 0 L8 4 L0 8 z" fill="{LINE}"/></marker></defs>'
                f'<rect width="{self.w}" height="{self.h}" fill="#ffffff"/>' + "".join(self.body) + "</svg>")


def architecture():
    s = Svg(1400, 560)
    s.text(20, 30, "Kiến trúc Seller Health: Medallion cho các lớp, Kimball cho mô hình trong Gold", 18, True)
    cards = [("Nguồn", "src", ["9 file CSV Olist", "manifest kiểm tra hash", "Giả lập 26 đợt tháng"], 150),
             ("Bronze: raw", "raw", ["Loại: bảng", "Nạp: theo đợt, nối thêm", "Biến đổi: không", "Thêm cột dwh_", "Đơn có nhiều phiên bản", "Mô hình: như nguồn"], 195),
             ("Silver: stg", "stg", ["Loại: view + bảng master", "Nạp: giao dịch là view", "Biến đổi: ép kiểu, làm sạch", "thành phố, tọa độ, gộp review", "Lỗi: vào ops.quarantine", "Mô hình: như nguồn, đã sạch"], 215),
             ("Gold: core", "core", ["Loại: bảng", "Nạp: thêm, cập nhật, SCD2", "Biến đổi: khóa thay thế, số đo", "Mô hình: galaxy schema", "8 dimension, 6 fact", "Đủ 3 kiểu fact"], 215),
             ("Gold: mart", "mart", ["Loại: bảng", "Nạp: đóng băng lúc chốt đợt", "Biến đổi: tổng hợp, CUBE", "feature seller, KPI, tuyến", "Mô hình: bảng phẳng"], 205),
             ("DSS: dss", "dss", ["Nhãn, Logistic Regression", "Bảng luật, MILP", "Kế hoạch, đánh giá"], 170)]
    x = 20
    pos = {}
    for title, key, lines, w in cards:
        s.box(x, 60, w, 165, title, lines, FILL[key])
        pos[key] = (x, w)
        x += w + 26
    for a, b in zip(["src", "raw", "stg", "core", "mart"], ["raw", "stg", "core", "mart", "dss"]):
        s.line(pos[a][0] + pos[a][1], 142, pos[b][0], 142)
    # Cong chat luong ben duoi
    s.box(pos["raw"][0], 290, pos["mart"][0] + pos["mart"][1] - pos["raw"][0], 74, "Vận hành: ops", ["Cổng chất lượng: mỗi đợt 11 phép đối soát số dòng và số tiền giữa các lớp. Lệch thì dừng đợt, ghi failed, watermark không tiến.",
                                                                                                         "etl_log: nhật ký đợt · quarantine: dòng lỗi có mã · dq_issue: bất thường và cách xử lý · source_manifest: nguồn gốc file"], FILL["ops"])
    for k in ["raw", "stg", "core", "mart"]:
        s.line(pos[k][0] + pos[k][1] / 2, 225, pos[k][0] + pos[k][1] / 2, 290, dash="4 3")
    s.box(pos["raw"][0], 420, 1160, 110, "Ứng dụng Streamlit: chỉ đọc Gold, DSS, ops", ["Tổng quan · Lỗi giao trễ · Chi tiết seller: phân tích, drill-down theo as-of",
                                                                                         "Bảng kế hoạch: kéo thả, tối ưu lại theo ngân sách và số suất · What-if tuyến: hứa thêm N ngày · Kiểm chứng: so với các cách chọn đơn giản",
                                                                                         "Chú thích từng chỉ số lấy từ metrics.yml"], FILL["app"])
    s.line(pos["mart"][0] + 100, 225, pos["mart"][0] + 100, 420, dash="4 3")
    s.line(pos["dss"][0] + 85, 225, pos["dss"][0] + 85, 420 if pos["dss"][0] + 85 < 1400 else 420)
    return s


LINEAGE = {
    "csv": ["orders.csv", "order_items.csv", "order_payments.csv", "order_reviews.csv", "customers.csv", "sellers.csv", "products.csv", "geolocation.csv", "category_translation.csv"],
    "raw": ["raw.orders", "raw.order_items", "raw.order_payments", "raw.order_reviews", "raw.customers", "raw.sellers", "raw.products", "raw.geolocation", "raw.category_translation"],
    "stg": ["stg.orders", "stg.items", "stg.payments", "stg.reviews", "stg.customers", "stg.sellers", "stg.products", "stg.geography", "stg.category_translation"],
    "core": ["core.fact_order", "core.fact_order_seller", "core.fact_sales_item", "core.fact_payment", "core.fact_review", "core.fact_seller_monthly", "core.dim_customer", "core.dim_seller", "core.dim_product", "core.dim_location", "core.dim_route", "core.dim_seller_health"],
    "mart": ["mart.seller_features", "mart.seller_tier_monthly", "mart.kpi_monthly", "mart.route_delivery"],
    "dss": ["dss.labels", "dss.scores", "dss.recommendation", "dss.eval_lists", "dss.eval_auc", "dss.sensitivity"],
}
EDGES = [("stg.orders", "core.fact_order"), ("stg.orders", "core.fact_order_seller"), ("stg.items", "core.fact_order_seller"), ("stg.items", "core.fact_sales_item"),
         ("stg.payments", "core.fact_payment"), ("stg.payments", "core.fact_order"), ("stg.reviews", "core.fact_review"), ("stg.reviews", "core.fact_order"),
         ("stg.customers", "core.dim_customer"), ("stg.sellers", "core.dim_seller"), ("stg.products", "core.dim_product"), ("stg.geography", "core.dim_location"), ("stg.category_translation", "stg.products"),
         ("stg.geography", "stg.sellers"), ("stg.geography", "stg.customers"), ("core.dim_location", "core.dim_route"),
         ("core.fact_sales_item", "mart.seller_features"), ("core.fact_order_seller", "mart.seller_features"), ("core.fact_order_seller", "mart.route_delivery"), ("core.fact_sales_item", "mart.kpi_monthly"),
         ("mart.seller_features", "core.fact_seller_monthly"), ("mart.seller_features", "mart.seller_tier_monthly"), ("mart.seller_tier_monthly", "core.dim_seller"), ("core.dim_seller_health", "core.fact_seller_monthly"),
         ("mart.seller_features", "dss.labels"), ("core.fact_sales_item", "dss.labels"), ("mart.seller_features", "dss.scores"), ("dss.labels", "dss.scores"), ("dss.scores", "dss.recommendation"),
         ("dss.recommendation", "dss.eval_lists"), ("dss.labels", "dss.eval_lists"), ("dss.labels", "dss.eval_auc"), ("dss.scores", "dss.eval_auc"), ("dss.scores", "dss.sensitivity")]


def lineage(con):
    known = {f"{a}.{b}" for a, b in con.execute("SELECT schema_name, table_name FROM duckdb_tables() UNION ALL SELECT schema_name, view_name FROM duckdb_views()").fetchall()}
    missing = [n for k, v in LINEAGE.items() if k != "csv" for n in v if n not in known]
    missing += [n for e in EDGES for n in e if n not in known]
    assert not missing, f"So do lineage nhac toi bang khong ton tai: {missing}"
    s = Svg(1400, 640)
    s.text(20, 30, "Lineage theo bảng: dữ liệu đi qua các lớp", 18, True)
    xs = {"csv": 20, "raw": 225, "stg": 450, "core": 690, "mart": 950, "dss": 1190}
    names = {"csv": "Nguồn CSV", "raw": "Bronze: raw", "stg": "Silver: stg", "core": "Gold: core", "mart": "Gold: mart", "dss": "DSS"}
    w = {"csv": 170, "raw": 190, "stg": 200, "core": 225, "mart": 200, "dss": 190}
    fill = {"csv": FILL["src"], "raw": FILL["raw"], "stg": FILL["stg"], "core": FILL["core"], "mart": FILL["mart"], "dss": FILL["dss"]}
    pos = {}
    for k, nodes in LINEAGE.items():
        s.text(xs[k] + w[k] / 2, 60, names[k], 13, True, anchor="middle")
        gap = 568 / len(nodes)
        for i, n in enumerate(nodes):
            y = 72 + i * gap
            pos[n] = (xs[k], y + 13, w[k])
            s.box(xs[k], y, w[k], 26, n, fill=fill[k], size=11.5, bold=False)
    for a, b in zip(LINEAGE["csv"], LINEAGE["raw"]):
        s.line(pos[a][0] + pos[a][2], pos[a][1], pos[b][0], pos[b][1], color="#c9c8c2")
    for a, b in zip(LINEAGE["raw"], LINEAGE["stg"]):
        s.line(pos[a][0] + pos[a][2], pos[a][1], pos[b][0], pos[b][1], color="#c9c8c2")
    for a, b in EDGES:
        xa, ya, wa = pos[a]
        xb, yb, wb = pos[b]
        if xa < xb:
            s.line(xa + wa, ya, xb, yb, width=1)
        elif xa > xb:
            s.line(xa, ya, xb + wb, yb, width=1, dash="4 3")
        else:
            s.line(xa + wa - 6, ya + 13 if yb > ya else ya - 13, xb + wb - 6, yb - 13 if yb > ya else yb + 13, width=1)
    return s


def star(con):
    target = {"product_key": "dim_product", "seller_key": "dim_seller", "customer_key": "dim_customer", "route_key": "dim_route", "customer_location_key": "dim_location",
              "seller_location_key": "dim_location", "status_key": "dim_order_status", "health_key": "dim_seller_health"}
    facts = ["fact_sales_item", "fact_order_seller", "fact_order", "fact_review", "fact_payment", "fact_seller_monthly"]
    edges = set()
    for f in facts:
        for col, in con.execute(f"SELECT column_name FROM information_schema.columns WHERE table_schema = 'core' AND table_name = '{f}'").fetchall():
            if col in target:
                edges.add((target[col], f))
            elif col.endswith("date_key") or col == "month_key":
                edges.add(("dim_date", f))
    kinds = {"fact_sales_item": ["Transaction", "1 sản phẩm trong 1 đơn"], "fact_order_seller": ["Accumulating snapshot", "1 đơn × 1 seller"], "fact_order": ["Accumulating snapshot", "1 đơn"],
             "fact_review": ["Transaction", "1 review × 1 đơn"], "fact_payment": ["Transaction", "1 phần thanh toán"], "fact_seller_monthly": ["Periodic snapshot", "1 seller × 1 tháng"]}
    top = {"dim_date": ["Nhiều vai trò", "ngày mua, nhận, hẹn..."], "dim_customer": ["Theo người mua"], "dim_location": ["1 ZIP, cho khách và seller"], "dim_order_status": ["Trạng thái đơn"]}
    bottom = {"dim_product": ["Danh mục, kích thước"], "dim_route": ["Bang seller → bang khách"], "dim_seller": ["SCD Type 2", "hạng ổn định"], "dim_seller_health": ["Mini-dimension", "hạng và nhóm theo tháng"]}
    s = Svg(1400, 620)
    s.text(20, 30, "Galaxy schema: 6 fact dùng chung 8 dimension", 18, True)
    pos = {}
    for i, (d, ln) in enumerate(top.items()):
        x = 90 + i * 310
        s.box(x, 55, 230, 66, d, ln, FILL["dim"])
        pos[d] = (x + 115, 121)
    for i, (d, ln) in enumerate(bottom.items()):
        x = 90 + i * 310
        s.box(x, 500, 230, 66, d, ln, FILL["mini"] if d == "dim_seller_health" else FILL["dim"])
        pos[d] = (x + 115, 500)
    fp = {}
    for i, f in enumerate(facts):
        x = 20 + i * 228
        fp[f] = (x + 106, 268, 346)
    for d, f in sorted(edges):
        s.line(pos[d][0], pos[d][1], fp[f][0], fp[f][1] if pos[d][1] < 300 else fp[f][2], arrow=False, color="#b7b6b0", width=1)
    for i, f in enumerate(facts):
        s.box(20 + i * 228, 268, 212, 78, f, kinds[f], FILL["fact"])
    s.text(20, 600, "Đường nối sinh tự động từ các cột khóa ngoại trong kho.", 11.5, color=MUTED)
    return s


def dss_flow():
    s = Svg(1400, 470)
    s.text(20, 30, "Luồng DSS: từ mart đến quyết định, theo 4 pha của Simon", 18, True)
    phases = [("Intelligence", 20, 280), ("Design", 310, 480), ("Choice", 800, 340), ("Implementation", 1150, 230)]
    for name, x, w in phases:
        s.box(x, 50, w, 30, name, fill="#f4f4f1", size=13)
    s.box(20, 105, 280, 95, "Phát hiện", ["Tổng quan: KPI, hạng tháng", "Lỗi giao trễ: tách seller và vận chuyển", "Chi tiết seller: drill-down"], FILL["app"])
    s.box(310, 105, 150, 95, "Feature", ["mart.seller_features", "Đóng băng lúc chốt", "12 chỉ số"], FILL["mart"])
    s.box(475, 105, 150, 95, "Nhãn", ["dss.labels", "45 ngày sau as-of", "Train cuốn"], FILL["dss"])
    s.box(640, 105, 150, 95, "Mô hình", ["Logistic Regression", "p_decline", "p_dormant"], FILL["dss"])
    s.box(800, 105, 165, 95, "Bảng luật", ["Rủi ro × giá trị × vận hành", "Phân khúc", "Lý do bằng chữ"], FILL["dss"])
    s.box(975, 105, 165, 95, "Tối ưu MILP", ["Ngân sách, số suất", "Tối đa 1 hành động", "mỗi seller"], FILL["dss"])
    s.box(1150, 105, 230, 95, "Bảng kế hoạch", ["Người dùng kéo thả, sửa đề xuất", "Cảnh báo vượt ràng buộc", "Xuất CSV"], FILL["app"])
    for a, b in [(460, 475), (625, 640), (790, 800), (965, 975), (1140, 1150)]:
        s.line(a, 152, b, 152)
    s.box(800, 250, 340, 72, "Giả định (không có trong dữ liệu)", ["Chi phí và hiệu quả can thiệp", "Người dùng đổi được, có phân tích độ nhạy"], "#fdecec")
    s.line(970, 250, 1057, 200, dash="4 3")
    s.box(1150, 250, 230, 72, "What-if", ["Đổi ràng buộc: tính lại kế hoạch", "Tuyến: hứa thêm N ngày"], FILL["app"])
    s.line(1265, 250, 1265, 200, dash="4 3")
    s.box(310, 360, 830, 80, "Kiểm chứng trên các tháng đã biết", ["So với chọn theo GMV, số ngày không bán, luật đơn giản, ngẫu nhiên. Tham số chọn trên 09/2017–02/2018, báo cáo trên 03–07/2018.",
                                                                     "Chỉ đo được seller có sụt thật hay không, chưa đo được can thiệp có hiệu quả."], FILL["stg"])
    s.line(1057, 200, 1057, 250, arrow=False, color="#ffffff")
    s.line(715, 200, 715, 360, dash="4 3")
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH), read_only=True)
    charts = {"01_kien_truc": architecture(), "02_lineage": lineage(con), "03_galaxy_schema": star(con), "04_luong_dss": dss_flow()}
    con.close()
    for name, svg in charts.items():
        (OUT / f"{name}.svg").write_text(svg.render(), encoding="utf-8")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Khong co playwright, chi sinh SVG")
        return
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        for name, svg in charts.items():
            page = browser.new_page(viewport={"width": svg.w, "height": svg.h}, device_scale_factor=2)
            page.set_content(f"<!doctype html><meta charset='utf-8'><body style='margin:0'>{svg.render()}</body>")
            page.screenshot(path=str(OUT / f"{name}.png"))
            page.close()
        browser.close()
    print("Da sinh", list(charts))


if __name__ == "__main__":
    main()
