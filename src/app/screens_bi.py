"""Man hinh phan tich cua luong A: Can chu y thang nay va Chi tiet seller. KPI, OLAP va giao hang nam o Power BI."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.app.common import (BLUE, LIGHT_BLUE, MUTED, ORANGE, brl, compact, go_to, kgroup, kpi, note, num, pct, points, q, short, show,
                            signed_pct, style, table, title)
from src.dss.rules import ACTION_LABEL, Params

H1 = 184
# Ten feature cua mo hinh, cach doc gia tri, theo dung thu tu FEATS trong src/dss/run.py
FEAT_LABEL = {"gmv_90": "GMV 90 ngày", "orders_90": "Số đơn 90 ngày", "gmv_30": "GMV 30 ngày", "orders_30": "Số đơn 30 ngày",
              "trend": "Xu hướng 30 ngày", "recency": "Ngày chưa bán", "tenure": "Thâm niên (ngày)", "n_cat": "Số danh mục",
              "seller_late_rate": "Seller giao vận chuyển trễ", "cust_late_rate": "Trễ hẹn với khách", "avg_review": "Review trung bình", "days_to_carrier": "Ngày tới vận chuyển"}
FEAT_FMT = {"trend": lambda v: signed_pct(v, 0), "seller_late_rate": lambda v: pct(v, 0), "cust_late_rate": lambda v: pct(v, 0),
            "avg_review": lambda v: num(v, 2), "days_to_carrier": lambda v: num(v, 1)}
H2 = 232


def _prev_month(as_of, n=1):
    return (pd.Timestamp(as_of) - pd.DateOffset(months=n)).strftime("%Y-%m-%d")


def _why_not(r, risk_cut, value_cut):
    """Vi sao seller Nguy co khong duoc goi hay ho tro: hang do luat gan, con ke hoach do mo hinh, nguong gia tri va ngan sach quyet."""
    if r.action in ("CALL", "OPS"):
        return "Trong kế hoạch"
    if r.p_decline < risk_cut:
        return f"Dưới ngưỡng rủi ro {pct(risk_cut, 0)}"
    if r.gmv_90 < value_cut:
        return "Ngoài top 20% GMV"
    return "Hết ngân sách/suất"


def attention(as_of):
    """Man vao cua luong giu chan seller: seller nao vua tro nen dang lo va ke hoach de xuat xu ly den dau.
    Theo doi KPI toan san, OLAP va giao hang nam o Power BI."""
    p = Params()
    kpi_rows = q("""SELECT * FROM mart.kpi_monthly WHERE is_all_region AND is_all_category AND month >= DATE '2017-01-01'
                    AND month < CAST(? AS DATE) ORDER BY month""", (as_of,))
    kpi_rows["late_rate"] = kpi_rows.n_late_orders / kpi_rows.n_due_orders.where(kpi_rows.n_due_orders > 0)
    last = kpi_rows.iloc[-1]
    prev = kpi_rows.iloc[-2] if len(kpi_rows) > 1 else last

    cur = q("""SELECT f.*, r.gmv_risk, r.p_decline, r.action, r.reason, r.cost, s.region, s.state
               FROM mart.seller_features f JOIN dss.recommendation r USING (as_of, seller_id)
               LEFT JOIN core.dim_seller s ON s.seller_id = f.seller_id AND s.is_current
               WHERE as_of = CAST(? AS DATE)""", (as_of,))
    prev_t = q("SELECT seller_id, health_tier FROM mart.seller_features WHERE as_of = CAST(? AS DATE)", (_prev_month(as_of),))
    new_risk = cur[(cur.health_tier == "Nguy cơ") & ~cur.seller_id.isin(prev_t[prev_t.health_tier == "Nguy cơ"].seller_id)].copy()
    n_risk = int((cur.health_tier == "Nguy cơ").sum())
    risk_trail = q("""SELECT f.as_of, count(*) FILTER (WHERE f.health_tier = 'Nguy cơ') AS n_risk, sum(r.gmv_risk) AS gmv_risk
                      FROM mart.seller_features f LEFT JOIN dss.recommendation r USING (as_of, seller_id)
                      WHERE f.as_of <= CAST(? AS DATE) GROUP BY 1 ORDER BY 1""", (as_of,)).tail(12)
    paid = cur[cur.action.isin(["CALL", "OPS"])]
    value_cut = cur.gmv_90.quantile(p.value_pct)
    total_risk = cur.gmv_risk.sum()
    over_risk = cur[cur.p_decline >= p.risk_threshold].gmv_risk.sum()
    new_risk["why"] = [_why_not(r, p.risk_threshold, value_cut) for r in new_risk.itertuples()]

    gmv_change = last.gmv / prev.gmv - 1 if prev.gmv else None
    late_change = last.late_rate - prev.late_rate if pd.notna(last.late_rate) and pd.notna(prev.late_rate) else None
    note(f"Mốc {pd.Timestamp(as_of).strftime('%d/%m/%Y')}. Bối cảnh tháng {pd.Timestamp(last.month).strftime('%m/%Y')} (số chốt sổ): "
         f"GMV (chốt sổ) {compact(last.gmv)} ({signed_pct(gmv_change)} so với tháng trước), tỷ lệ trễ hẹn (chốt sổ) {pct(last.late_rate)} ({points(late_change)}). "
         "Xu hướng, vùng, danh mục và giao hàng xem ở Power BI.")
    g = st.columns(2, gap="medium")
    kgroup(g[0], "Rủi ro seller", "#9C1C4A")
    kgroup(g[1], "Kế hoạch đề xuất", ORANGE)
    m = g[0].columns(2, gap="small") + g[1].columns(2, gap="small")
    kpi(m[0], "new_at_risk", num(len(new_risk)), f"{n_risk} seller Nguy cơ", tone="off", chart=risk_trail.n_risk.tolist())
    kpi(m[1], "gmv_at_risk", compact(total_risk), f"{compact(over_risk)} ở seller vượt ngưỡng {pct(p.risk_threshold, 0)}", tone="off",
        chart=risk_trail.gmv_risk.tolist())
    kpi(m[2], "plan_risk", compact(paid.gmv_risk.sum()),
        f"{pct(paid.gmv_risk.sum() / total_risk if total_risk else None, 0)} % GMV rủi ro được xử lý", tone="off")
    kpi(m[3], "plan_sellers", num(len(paid)),
        f"{(paid.action == 'CALL').sum()} Gọi ngay, {(paid.action == 'OPS').sum()} Hỗ trợ vận hành · Tiền đã dùng {brl(paid.cost.sum())}", tone="off")

    c1, c2 = st.columns([3, 1.25])
    with c1:
        title(f"{len(new_risk)} seller mới vào Nguy cơ, sắp theo GMV rủi ro 45 ngày",
              "Hạng do luật gán (lâu không bán, GMV giảm, giao trễ); kế hoạch do mô hình, ngưỡng và ngân sách chọn. Bấm một dòng để mở hồ sơ seller.")
        top_s = new_risk.sort_values("gmv_risk", ascending=False).reset_index(drop=True)
        view = pd.DataFrame({"Seller": top_s.seller_id.map(short), "Bang seller": top_s.state, "GMV rủi ro 45 ngày": top_s.gmv_risk.round(0),
                             "Khả năng sụt GMV": top_s.p_decline.map(lambda v: pct(v, 0)), "Ngày chưa bán": top_s.recency.round(0),
                             "Seller giao vận chuyển trễ": top_s.seller_late_rate.map(lambda v: pct(v, 0)),
                             "Hành động": top_s.action.map(ACTION_LABEL), "Lý do chưa gọi/hỗ trợ": top_s.why.where(top_s.why != "Trong kế hoạch", ""),
                             "Lý do": top_s.reason})
        cfg = {c: st.column_config.NumberColumn(format="localized") for c in ("GMV rủi ro 45 ngày", "Ngày chưa bán")}
        cfg["Lý do"] = st.column_config.TextColumn(width="large")
        key = f"attn-{as_of}"

        def _open():
            rows = st.session_state[key].selection.rows
            if rows:
                go_to("Chi tiết seller", top_s.seller_id.iloc[rows[0]])

        st.dataframe(view, hide_index=True, width="stretch", height=H2 + H1 + 70, column_config=cfg, key=key,
                     on_select=_open, selection_mode="single-row")
    with c2:
        title(f"{len(new_risk)} seller mới vào Nguy cơ được xử lý thế nào")
        order = ["Trong kế hoạch", f"Dưới ngưỡng rủi ro {pct(p.risk_threshold, 0)}", "Ngoài top 20% GMV", "Hết ngân sách/suất"]
        w = new_risk.groupby("why").size().reindex(order).fillna(0)
        fig = go.Figure(go.Bar(y=w.index, x=w.values, orientation="h", marker_color=[BLUE, LIGHT_BLUE, LIGHT_BLUE, "#9C1C4A"], text=w.values.astype(int),
                               textposition="outside", cliponaxis=False, hovertemplate="%{y}: %{x} seller<extra></extra>"))
        fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(size=10))
        fig.update_xaxes(showgrid=False, showticklabels=False, range=[0, max(w.max(), 1) * 1.3])
        show(style(fig, H1))
        title("GMV rủi ro 45 ngày theo hành động", "Toàn bộ seller đang bán, kế hoạch đề xuất")
        a = cur.groupby("action").agg(n=("seller_id", "size"), risk=("gmv_risk", "sum")).reindex(["CALL", "OPS", "EMAIL", "NONE"]).fillna(0)
        fig = go.Figure(go.Bar(y=[ACTION_LABEL[x] for x in a.index], x=a.risk, orientation="h", marker_color=[BLUE, "#9C1C4A", LIGHT_BLUE, "#E9D3DC"],
                               text=[f"{compact(v)} · {int(n)} seller" for v, n in zip(a.risk, a.n)], textposition="outside", cliponaxis=False,
                               hovertemplate="%{y}<br>%{x:,.0f} BRL<extra></extra>"))
        fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(size=10))
        fig.update_xaxes(showgrid=False, showticklabels=False, range=[0, max(a.risk.max(), 1) * 1.9])
        show(style(fig, H1))


def _explain(as_of, sid, p):
    """Vi sao mo hinh cham rui ro: dong gop cua tung feature vao log-odds (logistic nen cong don chinh xac)."""
    e = q("SELECT feature, value, z, contrib FROM dss.explain WHERE as_of = CAST(? AS DATE) AND seller_id = ?", (as_of, sid))
    if e.empty:
        title("Vì sao mô hình chấm như vậy")
        note("Mốc này chưa có giải thích.")
        return
    f = e[e.feature != "_intercept"].copy()
    f["abs"] = f.contrib.abs()
    top = f.nlargest(6, "abs").sort_values("contrib")
    ups = f[f.contrib > 0].nlargest(3, "contrib")
    words = "; ".join(f"{FEAT_LABEL[x]} {FEAT_FMT.get(x, num)(v) if pd.notna(v) else '—'}" for x, v in zip(ups.feature, ups.value))
    title(f"Vì sao khả năng sụt GMV {pct(p, 0)}", f"Đẩy rủi ro lên nhiều nhất: {words}." if words else "Không yếu tố nào đẩy rủi ro lên.")
    labels = [f"{FEAT_LABEL[x]} = {FEAT_FMT.get(x, num)(v) if pd.notna(v) else '—'}" for x, v in zip(top.feature, top.value)]
    fig = go.Figure(go.Bar(x=top.contrib, y=labels, orientation="h", marker_color=[ORANGE if c > 0 else BLUE for c in top.contrib],
                           customdata=top.z, hovertemplate="%{y}<br>Đóng góp vào điểm rủi ro %{x:+.2f}<br>Lệch chuẩn so với tập train %{customdata:+.1f}<extra></extra>"))
    fig.add_vline(x=0, line_color=MUTED, line_width=1)
    show(style(fig, 176))


def seller(as_of):
    rec = q("""SELECT r.*, f.gmv_90, f.gmv_30, f.orders_90, f.trend, f.recency, f.seller_late_rate, f.cust_late_rate, f.avg_review, f.days_to_carrier, f.health_tier, d.state, d.city, d.health_tier AS stable_tier
               FROM dss.recommendation r JOIN mart.seller_features f USING (as_of, seller_id)
               JOIN core.dim_seller d ON d.seller_id = r.seller_id AND d.valid_from < CAST(? AS DATE) AND d.valid_to >= CAST(? AS DATE)
               WHERE r.as_of = CAST(? AS DATE) ORDER BY r.rank""", (as_of, as_of, as_of))
    options = rec.seller_id.tolist()
    labels = {r.seller_id: f"{short(r.seller_id)} · {ACTION_LABEL[r.action]} · {r.state} · {num(r.gmv_90)} BRL" for r in rec.itertuples()}
    c1, c2 = st.columns([1.3, 1])
    picked = st.session_state.pop("seller_pick", None)
    if picked in options:
        st.session_state[f"seller-sel-{as_of}"] = picked
    sid = c1.selectbox("Chọn seller (theo thứ tự ưu tiên)", options, format_func=labels.get, key=f"seller-sel-{as_of}")
    MEDIAN = "Trung vị toàn sàn"
    other = c2.selectbox("So với", [MEDIAN] + options[:200], format_func=lambda s: s if s == MEDIAN else labels[s])
    r = rec[rec.seller_id == sid].iloc[0]

    m = st.columns(4)
    kpi(m[0], "tier_stable", r.stable_tier, f"Hạng tháng: {r.health_tier}", tone="off")
    kpi(m[1], "gmv_90", compact(r.gmv_90), f"{num(r.orders_90)} đơn", tone="off")
    kpi(m[2], "p_decline", pct(r.p_decline, 0))
    kpi(m[3], "seller_late_rate", pct(r.seller_late_rate, 0), f"Trễ hẹn với khách {pct(r.cust_late_rate, 0)}", tone="off")
    # Chan doan: loi o khau seller thi thuoc luong giu chan seller, loi o van chuyen thi thuoc luong giao nhan
    seller_poor = pd.notna(r.seller_late_rate) and r.seller_late_rate >= Params().ops_late
    carrier = not seller_poor and pd.notna(r.cust_late_rate) and r.cust_late_rate >= .10
    diag = ("Seller bàn giao cho vận chuyển trễ từ 15% trở lên: lỗi ở khâu seller, hỗ trợ vận hành có tác dụng." if seller_poor else
            "Khách nhận trễ nhưng seller bàn giao đúng hạn: lỗi ở khâu vận chuyển. Gọi seller không sửa được, nên xem lời hẹn giao của tuyến." if carrier else
            "Giao hàng không phải vấn đề chính; sụt GMV đến từ phía cầu.")
    st.markdown(f'<div class="rec"><b>Khuyến nghị: {ACTION_LABEL[r.action]}</b> (phân khúc {r.segment}). {r.reason}<br><b>Chẩn đoán:</b> {diag} '
                f'<span style="color:#52514e">{str(r.city).title()}, {r.state}. Mã: {short(sid)}</span></div>', unsafe_allow_html=True)
    if carrier:
        st.button("Mở What-if hẹn giao theo tuyến", on_click=go_to, args=("What-if tuyến",))

    h = q("SELECT * FROM core.fact_seller_monthly WHERE seller_id = ? AND month < CAST(? AS DATE) ORDER BY month", (sid, as_of))
    c1, c2, c3 = st.columns(3)
    with c1:
        last = h.iloc[-1] if len(h) else None
        change = last.gmv / last.gmv_prev_3m_avg - 1 if last is not None and last.gmv_prev_3m_avg else None
        title(f"GMV tháng gần nhất {signed_pct(change, 0)} so với trung bình 3 tháng trước" if change is not None else "GMV theo tháng",
              "Doanh số mỗi tháng của seller. Cột cuối thấp hẳn so với các tháng trước là dấu hiệu sụt.")
        fig = go.Figure(go.Bar(x=h.month, y=h.gmv, marker_color=BLUE, hovertemplate="%{x|%m/%Y}<br>%{y:,.0f} BRL<extra></extra>"))
        show(style(fig, H1, date_x=True))
    with c2:
        recent = h.tail(3)
        title(f"3 tháng gần đây: seller {num(recent.avg_days_to_carrier.mean(), 1)} ngày, vận chuyển {num(recent.avg_days_in_transit.mean(), 1)} ngày",
              "Đường hồng cao: seller bàn giao chậm (khâu seller). Đường vàng cao: hàng nằm lâu ở vận chuyển.")
        fig = go.Figure()
        for col, name, color in [("avg_days_to_carrier", "Seller giao cho vận chuyển", BLUE), ("avg_days_in_transit", "Vận chuyển tới khách", ORANGE)]:
            fig.add_trace(go.Scatter(x=h.month, y=h[col], mode="lines+markers", name=name, line=dict(color=color, width=2), marker=dict(size=7), hovertemplate="%{x|%m/%Y}<br>%{y:.1f} ngày<extra>" + name + "</extra>"))
        fig.update_yaxes(rangemode="tozero")
        show(style(fig, H1, legend=True, date_x=True))
    with c3:
        title(f"So với {'trung vị toàn sàn' if other == MEDIAN else short(other)}",
              "Đặt seller này cạnh seller ở giữa (trung vị) trong mọi seller đang bán; lệch xa là điểm bất thường.")
        feats = [("GMV 90 ngày", "gmv_90", lambda v: num(v)), ("Số đơn 90 ngày", "orders_90", lambda v: num(v)), ("Xu hướng 30 ngày", "trend", lambda v: signed_pct(v, 0)),
                 ("Ngày chưa bán", "recency", lambda v: num(v)), ("Seller giao vận chuyển trễ", "seller_late_rate", lambda v: pct(v, 0)),
                 ("Trễ hẹn với khách", "cust_late_rate", lambda v: pct(v, 0)), ("Review trung bình", "avg_review", lambda v: num(v, 2)),
                 ("Ngày tới vận chuyển", "days_to_carrier", lambda v: num(v, 1))]
        ref = rec.median(numeric_only=True) if other == MEDIAN else rec[rec.seller_id == other].iloc[0]
        ref_name = "Trung vị" if other == MEDIAN else short(other)
        table(pd.DataFrame({"Chỉ số": [f[0] for f in feats], short(sid): [f[2](r[f[1]]) for f in feats], ref_name: [f[2](ref[f[1]]) for f in feats]}), H1)

    c1, c2 = st.columns([1.15, 1.85])
    with c1:
        _explain(as_of, sid, r.p_decline)
    with c2:
        title("Dữ liệu kho của seller này", "Phần minh họa thiết kế kho: lịch sử hạng (SCD2) và hồ sơ sức khỏe theo tháng (mini-dimension)")
        t = q("""SELECT health_tier AS "Hạng ổn định", strftime(valid_from, '%d/%m/%Y') AS "Từ",
                        CASE WHEN valid_to >= CAST(? AS DATE) THEN 'hiện tại' ELSE strftime(valid_to, '%d/%m/%Y') END AS "Đến"
                 FROM core.dim_seller WHERE seller_id = ? AND valid_from < CAST(? AS DATE) ORDER BY valid_from DESC""", (as_of, sid, as_of))
        mh = q("""SELECT f.month, f.n_orders, f.gmv, f.seller_late_rate, f.customer_late_rate, f.avg_review, h.health_tier, h.size_band, h.late_band
                  FROM core.fact_seller_monthly f JOIN core.dim_seller_health h USING (health_key)
                  WHERE f.seller_id = ? AND f.month < CAST(? AS DATE) ORDER BY f.month DESC""", (sid, as_of))
        with st.expander(f"Lịch sử hạng (SCD2): {len(t)} phiên bản"):
            table(t, 140)
        with st.expander("Theo tháng, kèm hồ sơ sức khỏe (mini-dimension)"):
            table(pd.DataFrame({"Tháng": pd.to_datetime(mh.month).dt.strftime("%m/%Y"), "Số đơn": mh.n_orders, "GMV": mh.gmv.round(0),
                                "Seller giao vận chuyển trễ": mh.seller_late_rate.map(pct), "Trễ hẹn với khách": mh.customer_late_rate.map(pct),
                                "Review trung bình": mh.avg_review.round(2),
                                "Hạng tháng": mh.health_tier, "Nhóm đơn": mh.size_band}), 176)
