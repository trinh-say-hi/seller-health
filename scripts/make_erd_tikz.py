"""Sinh sơ đồ ERD (nền sáng để in, ký hiệu crow's foot) dạng TikZ từ cấu trúc thật của lớp core.

    python scripts/make_erd_tikz.py <duong_dan_kho.duckdb> [thu_muc_ra]

Ghi ra report/figures/erd_sales.tex và report/figures/erd_order.tex.
"""
import sys
from pathlib import Path

import duckdb

DB = sys.argv[1]
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "report/figures")

ROW = 0.46      # chiều cao một dòng (cm)
W = 5.6         # bề rộng bảng (cm)
MAX_FACT_ROWS = 18

PK = {"dim_date": "date_key", "dim_customer": "customer_key", "dim_location": "location_key",
      "dim_product": "product_key", "dim_route": "route_key", "dim_order_status": "status_key",
      "dim_seller": "seller_key", "dim_seller_health": "health_key"}
# khóa ngoại -> chiều đích
FK_TARGET = {"customer_key": "dim_customer", "customer_location_key": "dim_location",
             "seller_location_key": "dim_location", "product_key": "dim_product", "route_key": "dim_route",
             "status_key": "dim_order_status", "seller_key": "dim_seller", "health_key": "dim_seller_health",
             "month_key": "dim_date"}
NATURAL = {"order_id", "seller_id", "review_id", "customer_unique_id", "product_id", "zip_prefix"}
SKIP = {"dwh_batch", "dwh_first_batch", "dwh_last_batch", "n_versions"}


def short_type(t):
    t = t.lower()
    return {"bigint": "bigint", "integer": "integer", "varchar": "text", "double": "double",
            "boolean": "boolean", "timestamp": "timestamp", "date": "date"}.get(t, t)


def fk_target(col):
    if col.endswith("_date_key"):
        return "dim_date"
    return FK_TARGET.get(col)


def esc(s):
    return s.replace("_", r"\_")


def columns(con, table):
    return con.sql(f"select column_name, data_type from information_schema.columns "
                   f"where table_schema='core' and table_name='{table}' order by ordinal_position").fetchall()


def table_rows(con, table):
    cols = [(c, t) for c, t in columns(con, table) if c not in SKIP]
    is_fact = table.startswith("fact_")
    if is_fact and len(cols) > MAX_FACT_ROWS:
        keep = [c for c in cols if fk_target(c[0]) or c[0] in NATURAL]
        rest = [c for c in cols if c not in keep]
        room = MAX_FACT_ROWS - len(keep) - 1
        hidden = len(rest) - room
        cols = keep + rest[:room] + [(f"+ {hidden} cột khác", None)]
    rows = []
    for c, t in cols:
        if t is None:
            kind = "more"
        elif PK.get(table) == c:
            kind = "pk"
        elif is_fact and fk_target(c):
            kind = "fk"
        elif c in NATURAL:
            kind = "nk"
        else:
            kind = "col"
        rows.append((c, short_type(t) if t else "", kind))
    return rows


ICON = {
    "pk": r"\fill[erdkey] ({x},{y}) circle (0.075); \fill[erdkey] ({x}+0.06,{y}-0.02) rectangle ({x}+0.2,{y}+0.02);",
    "fk": r"\draw[erdfk, line width=0.7pt] ({x},{y}) circle (0.07); \draw[erdfk, line width=0.7pt] ({x}+0.07,{y}) -- ({x}+0.2,{y});",
    "nk": r"\fill[erdnk] ({x}+0.07,{y}) circle (0.09); \node[text=white, font=\erdfont\fontsize{{4}}{{4}}\selectfont] at ({x}+0.07,{y}) {{1}};",
    "col": r"\fill[erdcol, rounded corners=0.5pt] ({x}+0.03,{y}-0.1) rectangle ({x}+0.12,{y}+0.1);",
    "more": "",
}


class Erd:
    def __init__(self, con):
        self.con = con
        self.out = []
        self.anchor = {}   # (table, col) -> (x0, x1, y)
        self.box = {}

    def table(self, name, x, ytop, width=W):
        rows = table_rows(self.con, name)
        h = (len(rows) + 2) * ROW
        o = self.out
        o.append(rf"\fill[erdbody, rounded corners=1.5pt] ({x},{ytop}) rectangle ({x+width},{ytop-h});")
        # dòng schema và dòng tên bảng
        y1 = ytop - ROW / 2
        o.append(rf"\fill[erdhead] ({x},{ytop}) rectangle ({x+width},{ytop-ROW});")
        o.append(rf"\draw[erdred, line width=0.8pt, fill=white] ({x+0.25},{y1}) ++(0,0.1) -- ++(0.1,-0.1) -- ++(-0.1,-0.1) -- ++(-0.1,0.1) -- cycle;")
        o.append(rf"\node[anchor=west, text=erdtext, font=\erdfont\scriptsize\bfseries] at ({x+0.45},{y1}) {{core}};")
        y2 = ytop - 1.5 * ROW
        o.append(rf"\draw[erdtbl, line width=0.6pt] ({x+0.17},{y2-0.09}) rectangle ({x+0.35},{y2+0.09}); \draw[erdtbl] ({x+0.17},{y2+0.03}) -- ({x+0.35},{y2+0.03});")
        o.append(rf"\node[anchor=west, text=erdtext, font=\erdfont\scriptsize\bfseries] at ({x+0.45},{y2}) {{{esc(name)}}};")
        for i, (c, t, kind) in enumerate(rows):
            ytop_r = ytop - (2 + i) * ROW
            y = ytop_r - ROW / 2
            o.append(rf"\draw[erdgrid, line width=0.4pt] ({x},{ytop_r}) -- ({x+width},{ytop_r});")
            if kind == "more":
                o.append(rf"\node[anchor=west, text=erdmuted, font=\erdfont\scriptsize\itshape] at ({x+0.45},{y}) {{{c}}};")
                continue
            o.append(ICON[kind].format(x=f"{x+0.15:.3f}", y=f"{y:.3f}"))
            o.append(rf"\node[anchor=west, text=erdtext, font=\erdfont\scriptsize] at ({x+0.45},{y}) {{{esc(c)} \textcolor{{erdmuted}}{{{t}}}}};")
            self.anchor[(name, c)] = (x, x + width, y)
        o.append(rf"\draw[erdborder, line width=0.6pt, rounded corners=1.5pt] ({x},{ytop}) rectangle ({x+width},{ytop-h});")
        self.box[name] = (x, x + width, ytop, ytop - h)

    def link(self, fact, col, lane, bottom=None, lane2=None):
        """Nối khóa ngoại fact.col tới khóa chính của chiều, đi vòng qua làn x = lane.
        Nếu có bottom/lane2: đi xuống y = bottom, sang làn lane2 rồi mới lên chiều đích."""
        dim = fk_target(col)
        fx0, fx1, fy = self.anchor[(fact, col)]
        dx0, dx1, dy = self.anchor[(dim, PK[dim])]
        sx, sdir = (fx0, -1) if lane < fx0 else (fx1, 1)
        last = lane2 if lane2 is not None else lane
        tx, tdir = (dx1, 1) if last > dx1 else (dx0, -1)
        o = self.out
        if bottom is None:
            o.append(rf"\draw[erdline] ({sx},{fy}) -- ({lane},{fy}) -- ({lane},{dy}) -- ({tx},{dy});")
        else:
            o.append(rf"\draw[erdline] ({sx},{fy}) -- ({lane},{fy}) -- ({lane},{bottom}) -- ({lane2},{bottom}) -- ({lane2},{dy}) -- ({tx},{dy});")
        # crow's foot ở phía nhiều (fact)
        b = sx + sdir * 0.32
        o.append(rf"\draw[erdline] ({b},{fy}) -- ({sx},{fy+0.13}) ({b},{fy}) -- ({sx},{fy-0.13});")
        o.append(rf"\fill[erdline] ({sx + sdir*0.42},{fy}) circle (0.045);")
        # hai vạch ở phía một (dimension)
        for d in (0.18, 0.28):
            xx = tx + tdir * d
            o.append(rf"\draw[erdline] ({xx},{dy-0.13}) -- ({xx},{dy+0.13});")

    def render(self, path, width, height):
        head = [r"\begin{tikzpicture}[x=1cm, y=1cm, erdline/.style={draw=erdwire, line width=0.55pt}]",
                rf"\fill[erdbg] (-0.4,0.4) rectangle ({width},{-height});"]
        Path(path).write_text("\n".join(head + self.out + [r"\end{tikzpicture}", ""]), encoding="utf-8")


def lanes(start, step, n):
    return [round(start + i * step, 3) for i in range(n)]


def build_sales(con):
    e = Erd(con)
    # chiều bên trái
    e.table("dim_date", 0, 0)
    e.table("dim_customer", 0, -7.2)
    e.table("dim_location", 0, -10.4)
    # fact ở giữa
    e.table("fact_sales_item", 10.4, 0)
    e.table("fact_order_seller", 10.4, -9.6)
    # chiều bên phải
    e.table("dim_product", 20.8, 0)
    e.table("dim_route", 20.8, -5.0)
    e.table("dim_seller", 20.8, -9.0)
    left = [("fact_sales_item", c) for c in ["purchase_date_key", "shipping_limit_date_key", "customer_key", "customer_location_key", "seller_location_key"]] + \
           [("fact_order_seller", c) for c in ["purchase_date_key", "approved_date_key", "carrier_date_key", "delivered_date_key", "estimated_date_key", "customer_key", "customer_location_key", "seller_location_key"]]
    for (f, c), x in zip(left, lanes(6.0, 0.32, len(left))):
        e.link(f, c, x)
    right = [("fact_sales_item", c) for c in ["product_key", "route_key", "seller_key"]] + \
            [("fact_order_seller", c) for c in ["route_key", "seller_key"]]
    for (f, c), x in zip(right, lanes(16.8, 0.6, len(right))):
        e.link(f, c, x)
    e.render(OUT / "erd_sales.tex", 26.8, 19.6)


def build_order(con):
    e = Erd(con)
    e.table("dim_date", 0, 0)
    e.table("dim_customer", 0, -7.2)
    e.table("dim_location", 0, -10.4)
    e.table("fact_order", 10.4, 0)
    e.table("fact_payment", 10.4, -9.8)
    e.table("fact_review", 10.4, -14.3)
    e.table("dim_order_status", 20.8, 0)
    e.table("dim_seller", 20.8, -4.0)
    e.table("dim_seller_health", 20.8, -10.4)
    e.table("fact_seller_monthly", 20.8, -14.3)
    left = [("fact_order", c) for c in ["purchase_date_key", "approved_date_key", "carrier_date_key", "delivered_date_key", "estimated_date_key", "customer_key", "customer_location_key"]] + \
           [("fact_payment", c) for c in ["purchase_date_key", "customer_key"]] + \
           [("fact_review", c) for c in ["created_date_key", "answered_date_key", "customer_key"]]
    for (f, c), x in zip(left, lanes(6.0, 0.33, len(left))):
        e.link(f, c, x)
    e.link("fact_order", "status_key", 17.4)
    # fact_seller_monthly nằm cột phải: nối lên seller, seller_health, và vòng sang trái tới dim_date
    e.link("fact_seller_monthly", "seller_key", 27.0)
    e.link("fact_seller_monthly", "health_key", 26.75)
    e.link("fact_seller_monthly", "month_key", 18.6, bottom=-22.85, lane2=5.85)
    e.render(OUT / "erd_order.tex", 27.6, 23.0)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(DB, read_only=True)
    build_sales(con)
    build_order(con)
    print("ok", OUT)


if __name__ == "__main__":
    main()
