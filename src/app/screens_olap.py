"""Man hinh phan tich da chieu (OLAP): drill-down, roll-up, slice, dice, pivot truc tiep tren core.

Moi thao tac sinh mot cau SQL tren lop core (ROLAP), cau SQL duoc hien cho nguoi dung xem.
Moi so deu tinh tai moc as-of: chi dung don mua truoc as-of, tre va review chi tinh phan da biet luc do.
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.app.common import BLUE, MUTED, SEQ, compact, kpi, note, num, pct, q, show, style, table, title

# Moi phan cap la danh sach cap: (nhan, bieu thuc SQL). Cap cuoi khong di sau duoc nua.
HIERARCHIES = {
    "Seller theo địa lý": [("Vùng seller", "s.region"), ("Bang seller", "s.state"), ("Thành phố seller", "s.city"), ("Seller", "i.seller_id")],
    "Danh mục sản phẩm": [("Danh mục", "coalesce(p.category_en, 'chưa rõ')"), ("Seller", "i.seller_id")],
    "Thời gian mua": [("Năm", "CAST(d.year AS VARCHAR)"), ("Quý", "CAST(d.year AS VARCHAR) || '-Q' || CAST(d.quarter AS VARCHAR)"), ("Tháng", "d.year_month")],
    "Khách hàng theo địa lý": [("Vùng khách", "core.region_of(c.state)"), ("Bang khách", "c.state")],
}

# Chieu thu hai de xoay (pivot). Khong trung voi chieu dang drill.
PIVOTS = {
    "Không chia": None,
    "Năm": "CAST(d.year AS VARCHAR)",
    "Hạng sức khỏe lúc bán": "s.health_tier",
    "Vùng seller": "s.region",
    "Vùng khách": "core.region_of(c.state)",
    "Cùng bang hay khác bang": "CASE WHEN s.state = c.state THEN 'Cùng bang' ELSE 'Khác bang' END",
}

MEASURES = {
    "GMV": ("gmv", "olap_gmv"),
    "Số đơn": ("n_orders", "olap_orders"),
    "Số seller": ("n_sellers", "olap_sellers"),
    "Tỷ lệ trễ hẹn": ("late_rate", "olap_late_rate"),
    "Review trung bình": ("avg_review", "olap_review"),
}
ADDITIVE = {"gmv", "n_orders"}
H = 250
MIN_N = 30

BASE = """
FROM core.fact_sales_item i
JOIN core.fact_order_seller o USING (order_id, seller_id)
JOIN core.dim_seller s ON s.seller_key = i.seller_key
JOIN core.dim_product p ON p.product_key = i.product_key
JOIN core.dim_date d ON d.date_key = i.purchase_date_key
JOIN core.dim_customer c ON c.customer_key = i.customer_key
WHERE i.is_valid_sale AND i.purchase_ts >= CAST(? AS DATE) AND i.purchase_ts < CAST(? AS DATE)"""


def cube_sql(groups: list[str], where: list[str], rollup: bool = False) -> str:
    """Hai buoc: gom ve grain don x seller de review va tre khong bi nhan theo so dong hang, roi gom theo cac chieu."""
    names = [f"g{k}" for k in range(len(groups))]
    sel = "".join(f"{expr} AS {n}, " for expr, n in zip(groups, names))
    cond = "".join(f"\n  AND {w}" for w in where)
    by = ", ".join(names + ["order_id", "seller_id"])
    outer = ", ".join(names)
    group = (f"GROUP BY ROLLUP ({outer})" if rollup else f"GROUP BY {outer}") if names else ""
    return f"""WITH os AS (
SELECT {sel}i.order_id, i.seller_id, sum(i.price) AS gmv,
       any_value(o.estimated_ts < CAST(? AS DATE)) AS is_due,
       any_value(o.delivered_ts IS NULL OR CAST(o.delivered_ts AS DATE) > CAST(o.estimated_ts AS DATE)) AS is_late,
       any_value(CASE WHEN o.first_review_ts < CAST(? AS DATE) THEN o.review_score END) AS review{BASE}{cond}
GROUP BY {by})
SELECT {outer + ', ' if names else ''}sum(gmv) AS gmv, count(DISTINCT order_id) AS n_orders, count(DISTINCT seller_id) AS n_sellers,
       count(DISTINCT order_id) FILTER (WHERE is_due) AS n_due,
       count(DISTINCT order_id) FILTER (WHERE is_due AND is_late) AS n_late,
       avg(review) AS avg_review
FROM os
{group}"""


def run(groups, where, params, frm, to, as_of, rollup=False):
    df = q(cube_sql(groups, where, rollup), (as_of, as_of, frm, to) + tuple(params))
    df["late_rate"] = df.n_late / df.n_due.where(df.n_due > 0)
    return df


def fmt(measure: str, x) -> str:
    if measure in ("late_rate",):
        return pct(x)
    if measure == "avg_review":
        return num(x, 2)
    return compact(x)


def _months(as_of):
    end = pd.Timestamp(as_of).to_period("M")
    return [str(p) for p in pd.period_range("2017-01", end - 1, freq="M")]


def olap(as_of):
    months = _months(as_of)
    c = st.columns([1.2, 1.0, 1.1, 2.1, 0.9], vertical_alignment="bottom")
    hier_name = c[0].selectbox("Phân cấp drill-down", list(HIERARCHIES))
    measure_label = c[1].selectbox("Độ đo", list(MEASURES))
    pivot_name = c[2].selectbox("Chia theo (pivot)", list(PIVOTS))
    frm_m, to_m = c[3].select_slider("Khoảng thời gian mua (slice theo thời gian)", months, value=(months[max(0, len(months) - 12)], months[-1]))
    frm, to = f"{frm_m}-01", str((pd.Period(to_m) + 1).start_time.date())

    cats = q("SELECT category_en FROM core.dim_product WHERE category_en IS NOT NULL GROUP BY 1 ORDER BY 1").category_en.tolist()
    regions = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]
    n_dice = sum(len(st.session_state.get(k, [])) > 0 for k in ("olap-cat", "olap-reg", "olap-cust"))
    with c[4].popover(f"Dice ({n_dice} lọc)" if n_dice else "Dice: lọc", width="stretch"):
        pick_cat = st.multiselect("Danh mục", cats, placeholder="Tất cả danh mục", key="olap-cat")
        pick_reg = st.multiselect("Vùng seller", regions, placeholder="Tất cả vùng", key="olap-reg")
        pick_cust = st.multiselect("Vùng khách", regions, placeholder="Tất cả vùng", key="olap-cust")

    where, params = [], []
    for values, expr in ((pick_cat, "p.category_en"), (pick_reg, "s.region"), (pick_cust, "core.region_of(c.state)")):
        if values:
            where.append(f"{expr} IN ({', '.join('?' for _ in values)})")
            params += values

    levels = HIERARCHIES[hier_name]
    key = f"olap_path::{hier_name}"
    path = st.session_state.setdefault(key, [])
    # Duong dan cu co the khong con hop le khi doi bo loc hoac as-of; cat bot cho an toan.
    path = path[:len(levels) - 1]
    m_col, m_id = MEASURES[measure_label]

    # Breadcrumb: tong cua tung cap tren duong dan, tu toan san xuong nut hien tai (roll-up).
    crumbs = [("Toàn sàn", run([], where, params, frm, to, as_of).iloc[0])]
    for depth in range(len(path)):
        w = where + [f"{levels[k][1]} = ?" for k in range(depth + 1)]
        crumbs.append((f"{levels[depth][0]}: {path[depth]}", run([], w, params + path[:depth + 1], frm, to, as_of).iloc[0]))

    depth = len(path)
    level_label, level_expr = levels[depth]
    can_drill = depth < len(levels) - 1
    nav = st.columns([1.1] * (len(crumbs) - 1) + [1.9, max(0.3, 4.4 - 1.1 * (len(crumbs) - 1)), 2.2, 1.1], vertical_alignment="bottom")
    for k, (label, row) in enumerate(crumbs):
        text = f"{label} · {fmt(m_col, row[m_col])}"
        if k < len(crumbs) - 1:
            if nav[k].button(f"↑ {text}", key=f"crumb-{hier_name}-{k}", help="Roll-up: quay về cấp này", width="stretch"):
                st.session_state[key] = path[:k]
                st.rerun()
        else:
            nav[k].markdown(f"**{text}**")

    node = crumbs[-1][1]
    parent = crumbs[-2][1] if len(crumbs) > 1 else None
    m = st.columns(5)
    share = lambda col: f"{pct(node[col] / parent[col], 0)} của cấp trên" if parent is not None and parent[col] else "toàn bộ lát đang lọc"
    kpi(m[0], "olap_gmv", compact(node.gmv), share("gmv"), tone="off")
    kpi(m[1], "olap_orders", num(node.n_orders), share("n_orders"), tone="off")
    kpi(m[2], "olap_sellers", num(node.n_sellers), None)
    late_delta = None if parent is None or pd.isna(node.late_rate) or pd.isna(parent.late_rate) else \
        f"{'+' if node.late_rate >= parent.late_rate else ''}{num(100 * (node.late_rate - parent.late_rate), 1)} điểm % so với cấp trên"
    kpi(m[3], "olap_late_rate", pct(node.late_rate), late_delta, tone="inverse")
    rev_delta = None if parent is None or pd.isna(node.avg_review) or pd.isna(parent.avg_review) else \
        f"{node.avg_review - parent.avg_review:+.2f} so với cấp trên".replace(".", ",")
    kpi(m[4], "olap_review", num(node.avg_review, 2), rev_delta)

    w_now = where + [f"{levels[k][1]} = ?" for k in range(depth)]
    p_now = params + path
    children = run([level_expr], w_now, p_now, frm, to, as_of, rollup=True)
    total_row = children[children.g0.isna()]
    children = children[children.g0.notna()].copy()
    if children.empty:
        st.warning("Không có dữ liệu cho lát cắt này. Hãy nới bộ lọc hoặc khoảng thời gian.")
        return
    time_level = hier_name == "Thời gian mua"
    children = children.sort_values("g0" if time_level else m_col, ascending=time_level, na_position="last")
    # Do do ti le: bo thanh vien qua it don de khong bi nhieu, giong quy uoc o man Loi giao tre.
    pool = children
    if not time_level and m_col == "late_rate":
        pool = children[children.n_due >= MIN_N]
    elif not time_level and m_col == "avg_review":
        pool = children[children.n_orders >= MIN_N]
    shown = pool if time_level else pool.head(25)
    if shown.empty:
        st.warning(f"Không thành viên nào đủ {MIN_N} đơn để tính tỷ lệ. Hãy nới bộ lọc hoặc khoảng thời gian.")
        return

    left, right = st.columns([1.25, 1])
    with left:
        nxt = f" Bấm một cột để xuống cấp {levels[depth + 1][0].lower()}." if can_drill else " Đây là cấp chi tiết nhất."
        title(f"{measure_label} theo {level_label.lower()}" + ("" if time_level else f", {len(shown)}/{len(children)} thành viên đầu bảng")
              + (f" (từ {MIN_N} đơn)" if pool is not children else ""),
              f"Mỗi cột là một {level_label.lower()}.{nxt}")
        labels = shown.g0.astype(str).tolist()
        vals = shown[m_col]
        if time_level:
            fig = go.Figure(go.Bar(x=labels, y=vals, marker_color=BLUE, customdata=labels,
                                   hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>"))
        else:
            disp = [lab[:8] if level_label == "Seller" else lab for lab in labels]
            fig = go.Figure(go.Bar(x=vals[::-1], y=disp[::-1], orientation="h", marker_color=BLUE, customdata=labels[::-1],
                                   hovertemplate="%{customdata}<br>%{x:,.2f}<extra></extra>"))
        style(fig, height=H)
        if m_col == "late_rate":
            fig.update_layout(xaxis_tickformat=".0%") if not time_level else fig.update_layout(yaxis_tickformat=".0%")
        event = st.plotly_chart(fig, width="stretch", config={"displayModeBar": False}, on_select="rerun",
                                selection_mode="points", key=f"olap-chart-{hier_name}-{depth}-{'|'.join(path)}")
        picked = None
        pts = (event or {}).get("selection", {}).get("points", []) if isinstance(event, dict) else getattr(getattr(event, "selection", None), "points", [])
        if pts:
            picked = pts[0].get("customdata")
            if isinstance(picked, list):
                picked = picked[0]
        if can_drill:
            choice = nav[-2].selectbox(f"Hoặc chọn {level_label.lower()} để đi sâu", ["—"] + children.g0.astype(str).tolist(), key=f"olap-pick-{hier_name}-{depth}")
            if choice != "—":
                picked = choice
        if depth > 0 and nav[-1].button("↑ Lên một cấp", width="stretch", key=f"olap-up-{hier_name}-{depth}", help="Roll-up"):
            st.session_state[key] = path[:-1]
            st.rerun()
        if picked and can_drill:
            st.session_state[key] = path + [str(picked)]
            st.rerun()

    with right:
        if PIVOTS[pivot_name]:
            title(f"Pivot: {level_label.lower()} × {pivot_name.lower()}", f"{measure_label}, chỉ hiện tối đa 12 {level_label.lower()} đầu bảng bên trái")
            pv = run([level_expr, PIVOTS[pivot_name]], w_now, p_now, frm, to, as_of)
            top = shown.g0.astype(str).tolist()[:12] if not time_level else shown.g0.astype(str).tolist()[-12:]
            pv = pv[pv.g0.astype(str).isin(top)]
            grid = pv.pivot(index="g0", columns="g1", values=m_col).reindex(top)
            text = grid.map(lambda x: "" if pd.isna(x) else fmt(m_col, x))
            ylab = [s[:8] if level_label == "Seller" else s for s in grid.index.astype(str)]
            fig = go.Figure(go.Heatmap(z=grid.values, x=[str(x) for x in grid.columns], y=ylab, text=text.values, texttemplate="%{text}",
                                       colorscale=[[k / (len(SEQ) - 1), col] for k, col in enumerate(SEQ)], showscale=False,
                                       hovertemplate="%{y} · %{x}<br>%{text}<extra></extra>"))
            style(fig, height=H)
            fig.update_yaxes(autorange="reversed")
            show(fig)
        else:
            title(f"Xu hướng theo tháng: {crumbs[-1][0]}", "Cùng bộ lọc, gom theo tháng mua")
            tr = run(["d.year_month"], w_now, p_now, frm, to, as_of).sort_values("g0")
            fig = go.Figure(go.Scatter(x=tr.g0, y=tr[m_col], mode="lines+markers", line=dict(color=BLUE, width=2), marker=dict(size=5),
                                       hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>"))
            style(fig, height=H)
            if m_col == "late_rate":
                fig.update_layout(yaxis_tickformat=".0%")
            show(fig)

    tbl = shown[["g0", "gmv", "n_orders", "n_sellers", "late_rate", "avg_review"]].copy()
    if not total_row.empty:
        t = total_row.iloc[0]
        tbl["share"] = tbl.gmv / t.gmv if t.gmv else None
    tbl = tbl.rename(columns={"g0": level_label, "gmv": "GMV (BRL)", "n_orders": "Số đơn", "n_sellers": "Số seller",
                              "late_rate": "Tỷ lệ trễ", "avg_review": "Review TB", "share": "% GMV cấp trên"})
    e1, e2 = st.columns(2)
    with e1.expander(f"Bảng chi tiết và dòng tổng ROLLUP ({len(children)} {level_label.lower()})"):
        shown_tbl = tbl.copy()
        for col, f in {"GMV (BRL)": lambda v: num(v), "Tỷ lệ trễ": lambda v: pct(v), "Review TB": lambda v: num(v, 2), "% GMV cấp trên": lambda v: pct(v)}.items():
            if col in shown_tbl:
                shown_tbl[col] = shown_tbl[col].map(f)
        table(shown_tbl, height=260)
        if not total_row.empty:
            t = total_row.iloc[0]
            note(f"Dòng tổng do GROUP BY ROLLUP sinh ra: GMV {num(t.gmv)} BRL, {num(t.n_orders)} đơn, {num(t.n_sellers)} seller. "
                 "Số đơn và số seller là đếm khác nhau nên tổng không bằng cộng các dòng.")
    with e2.expander("Câu SQL đang chạy (ROLAP trên lớp core)"):
        st.code(cube_sql([level_expr], w_now, rollup=True), language="sql")
        note(f"Tham số: as-of {as_of}, từ {frm} đến trước {to}" + (f", bộ lọc {params + path}" if params or path else "") + ".")
    note("Đơn mua trong khoảng đã chọn và trước as-of. Trễ hẹn chỉ tính đơn đã tới ngày hẹn trước as-of; review chỉ tính review đã có trước as-of. "
         "Seller lấy theo phiên bản SCD2 lúc bán, nên hạng sức khỏe là hạng tại thời điểm bán.")
