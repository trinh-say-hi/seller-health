"""Ba man hinh phan tich: Tong quan, Loi giao tre, Chi tiet seller. Moi man hinh vua mot khung hinh."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.app.common import (BLUE, LIGHT_BLUE, MUTED, ORANGE, SEQ, TIER_ORDER, brl, compact, kgroup, kpi, note, num, pct, points, q, short, show,
                            signed_pct, style, table, title)
from src.dss.rules import ACTION_LABEL

H1 = 184
H2 = 232


def _prev_month(as_of, n=1):
    return (pd.Timestamp(as_of) - pd.DateOffset(months=n)).strftime("%Y-%m-%d")


def overview(as_of):
    regions = ["Tất cả"] + q("SELECT DISTINCT region FROM mart.kpi_monthly WHERE region IS NOT NULL AND NOT is_all_region ORDER BY 1").region.tolist()
    cats = ["Tất cả"] + q("SELECT category_en FROM mart.kpi_monthly WHERE NOT is_all_category GROUP BY 1 ORDER BY sum(gmv) DESC").category_en.tolist()
    f1, f2, f3 = st.columns([1, 1.4, 3.6], vertical_alignment="bottom")
    region = f1.selectbox("Vùng của seller", regions)
    cat = f2.selectbox("Danh mục", cats)
    conds = ["is_all_region" if region == "Tất cả" else "NOT is_all_region AND region = ?",
             "is_all_category" if cat == "Tất cả" else "NOT is_all_category AND category_en = ?"]
    params = tuple(v for v in (region, cat) if v != "Tất cả") + (as_of,)
    df = q(f"""SELECT * FROM mart.kpi_monthly WHERE {conds[0]} AND {conds[1]} AND month >= DATE '2017-01-01'
               AND month < CAST(? AS DATE) ORDER BY month""", params)
    if df.empty:
        st.warning("Không có dữ liệu cho bộ lọc này tại mốc đã chọn.")
        return
    df["late_rate"] = df.n_late_orders / df.n_due_orders.where(df.n_due_orders > 0)
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    month_txt = pd.Timestamp(last.month).strftime("%m/%Y")
    with f3:
        note(f"Số liệu tháng {month_txt} so với tháng trước, chốt lúc đóng tháng. Bộ lọc tác động KPI tháng và các biểu đồ theo tháng.")

    cur = q("SELECT f.*, r.gmv_risk, r.p_decline, r.action FROM mart.seller_features f JOIN dss.recommendation r USING (as_of, seller_id) WHERE as_of = CAST(? AS DATE)", (as_of,))
    prev_t = q("SELECT seller_id, health_tier FROM mart.seller_features WHERE as_of = CAST(? AS DATE)", (_prev_month(as_of),))
    new_risk = cur[(cur.health_tier == "Nguy cơ") & ~cur.seller_id.isin(prev_t[prev_t.health_tier == "Nguy cơ"].seller_id)]
    n_risk = int((cur.health_tier == "Nguy cơ").sum())

    gmv_change = last.gmv / prev.gmv - 1 if prev.gmv else None
    late_change = last.late_rate - prev.late_rate if pd.notna(last.late_rate) and pd.notna(prev.late_rate) else None
    trail = df.tail(12)
    # Xu huong rui ro qua cac moc as-of: so seller hang Nguy co va tong GMV rui ro (chi co tu khi DSS bat dau cham diem)
    risk_trail = q("""SELECT f.as_of, count(*) FILTER (WHERE f.health_tier = 'Nguy cơ') AS n_risk, sum(r.gmv_risk) AS gmv_risk
                      FROM mart.seller_features f LEFT JOIN dss.recommendation r USING (as_of, seller_id)
                      WHERE f.as_of <= CAST(? AS DATE) GROUP BY 1 ORDER BY 1""", (as_of,)).tail(12)
    g = st.columns([3, 2, 2], gap="medium")
    kgroup(g[0], "Doanh số tháng", BLUE)
    kgroup(g[1], "Giao hàng và đánh giá", ORANGE)
    kgroup(g[2], "Rủi ro seller", "#b42318")
    m = g[0].columns(3, gap="small") + g[1].columns(2, gap="small") + g[2].columns(2, gap="small")
    kpi(m[0], "gmv", compact(last.gmv), signed_pct(gmv_change), chart=trail.gmv.tolist())
    kpi(m[1], "orders", num(last.n_orders), f"{int(last.n_orders - prev.n_orders):+d}".replace(",", "."), chart=trail.n_orders.tolist())
    kpi(m[2], "active_sellers_month", num(last.n_sellers), f"{int(last.n_sellers - prev.n_sellers):+d}", chart=trail.n_sellers.tolist())
    kpi(m[3], "late_rate_month", pct(last.late_rate), points(late_change), chart=trail.late_rate.tolist(), tone="inverse")
    kpi(m[4], "avg_review_month", num(last.avg_review, 2), None if pd.isna(last.avg_review - prev.avg_review) else f"{last.avg_review - prev.avg_review:+.2f}".replace(".", ","), chart=trail.avg_review.tolist())
    kpi(m[5], "new_at_risk", num(len(new_risk)), f"{n_risk} seller Nguy cơ", tone="off", chart=risk_trail.n_risk.tolist())
    kpi(m[6], "gmv_at_risk", compact(cur.gmv_risk.sum()), f"{num(len(cur))} seller hoạt động", tone="off", chart=risk_trail.gmv_risk.tolist())

    c1, c2, c3 = st.columns(3)
    with c1:
        title(f"GMV tháng {month_txt}: {'giảm' if (gmv_change or 0) < 0 else 'tăng'} {pct(abs(gmv_change or 0))} so với tháng trước")
        fig = go.Figure(go.Bar(x=df.month, y=df.gmv, marker_color=BLUE, hovertemplate="%{x|%m/%Y}<br>%{y:,.0f} BRL<extra></extra>"))
        if pd.Timestamp("2017-11-01") in pd.to_datetime(df.month).values:
            fig.add_annotation(x=pd.Timestamp("2017-11-01"), y=df[pd.to_datetime(df.month) == pd.Timestamp("2017-11-01")].gmv.iloc[0],
                               text="Black Friday", showarrow=False, yshift=9, font=dict(color=MUTED, size=10))
        show(style(fig, H1, date_x=True))
    with c2:
        word = "tăng" if (late_change or 0) > 0 else "giảm"
        title(f"Trễ hẹn {word} {num(abs(late_change or 0) * 100, 1)} điểm %, còn {pct(last.late_rate)}" if word == "giảm" else f"Trễ hẹn {word} {num(abs(late_change or 0) * 100, 1)} điểm %, lên {pct(last.late_rate)}")
        fig = go.Figure(go.Scatter(x=df.month, y=df.late_rate, mode="lines+markers", line=dict(color=ORANGE, width=2), marker=dict(size=7),
                                   hovertemplate="%{x|%m/%Y}<br>%{y:.1%}<extra></extra>"))
        fig.update_yaxes(tickformat=".0%", rangemode="tozero")
        show(style(fig, H1, date_x=True))
    with c3:
        title(f"{n_risk} seller Nguy cơ, {len(new_risk)} mới vào so với tháng trước")
        t = cur.groupby("health_tier").size().reindex(TIER_ORDER).fillna(0).reset_index(name="n")
        fig = go.Figure(go.Bar(y=t.health_tier, x=t.n, orientation="h", marker_color=BLUE, text=t.n.astype(int), textposition="outside", cliponaxis=False,
                               hovertemplate="%{y}: %{x} seller<extra></extra>"))
        fig.update_yaxes(autorange="reversed", showgrid=False)
        fig.update_xaxes(showgrid=False, showticklabels=False)
        show(style(fig, H1))

    month_last, month_prev = str(last.month)[:10], str(prev.month)[:10]
    c1, c2, c3 = st.columns(3)
    with c1:
        cat_cond = "is_all_category" if cat == "Tất cả" else "NOT is_all_category AND category_en = ?"
        cat_par = () if cat == "Tất cả" else (cat,)
        r = q(f"SELECT region, month, gmv FROM mart.kpi_monthly WHERE NOT is_all_region AND {cat_cond} AND month IN (CAST(? AS DATE), CAST(? AS DATE)) AND region <> 'Khong ro'",
              cat_par + (month_last, month_prev))
        r["month"] = pd.to_datetime(r.month).dt.strftime("%Y-%m-%d")
        pv = r.pivot(index="region", columns="month", values="gmv").reindex(columns=[month_prev, month_last]).fillna(0)
        pv["d"] = pv[month_last] / pv[month_prev].where(pv[month_prev] > 0) - 1
        pv = pv.sort_values(month_last, ascending=True)
        worst = pv.d.idxmin() if pv.d.notna().any() else None
        title(f"Vùng {worst} sụt mạnh nhất: {signed_pct(pv.d.min())}" if worst and pv.d.min() < 0 else "Không vùng nào sụt GMV so với tháng trước")
        fig = go.Figure()
        fig.add_trace(go.Bar(y=pv.index, x=pv[month_prev], orientation="h", name="Tháng trước", marker_color=LIGHT_BLUE, hovertemplate="%{y}<br>%{x:,.0f} BRL<extra>Tháng trước</extra>"))
        fig.add_trace(go.Bar(y=pv.index, x=pv[month_last], orientation="h", name="Tháng này", marker_color=BLUE, hovertemplate="%{y}<br>%{x:,.0f} BRL<extra>Tháng này</extra>"))
        fig.update_yaxes(showgrid=False)
        show(style(fig, H1, legend=True))
    with c2:
        reg_cond = "is_all_region" if region == "Tất cả" else "NOT is_all_region AND region = ?"
        reg_par = () if region == "Tất cả" else (region,)
        d = q(f"SELECT category_en, month, gmv FROM mart.kpi_monthly WHERE NOT is_all_category AND {reg_cond} AND month IN (CAST(? AS DATE), CAST(? AS DATE))",
              reg_par + (month_last, month_prev))
        d["month"] = pd.to_datetime(d.month).dt.strftime("%Y-%m-%d")
        pc = d.pivot(index="category_en", columns="month", values="gmv").reindex(columns=[month_prev, month_last]).fillna(0)
        pc["delta"] = pc[month_last] - pc[month_prev]
        top = pc.reindex(pc.delta.abs().sort_values(ascending=False).head(7).index).sort_values("delta")
        title(f"Danh mục {top.index[0]} giảm nhiều nhất: {brl(top.delta.iloc[0])}" if len(top) and top.delta.iloc[0] < 0 else "Danh mục đổi nhiều nhất so với tháng trước")
        fig = go.Figure(go.Bar(y=top.index, x=top.delta, orientation="h", marker_color=[ORANGE if v < 0 else BLUE for v in top.delta],
                               text=[f"{v:+,.0f}".replace(",", ".") for v in top.delta], textposition="outside", cliponaxis=False, hovertemplate="%{y}<br>%{x:+,.0f} BRL<extra></extra>"))
        fig.update_yaxes(showgrid=False, tickfont=dict(size=10))
        span = max(top.delta.abs().max(), 1)
        fig.update_xaxes(showticklabels=False, showgrid=False, zeroline=True, zerolinecolor=MUTED, range=[min(top.delta.min(), 0) - span * .42, max(top.delta.max(), 0) + span * .42])
        show(style(fig, H1))
    with c3:
        title("Seller mới vào Nguy cơ, GMV lớn nhất")
        top_s = new_risk.nlargest(20, "gmv_90")
        table(pd.DataFrame({"Seller": top_s.seller_id.map(short), "GMV 90 ngày": top_s.gmv_90.round(0), "Ngày chưa bán": top_s.recency.round(0),
                            "Giao VC trễ": top_s.seller_late_rate.map(pct), "Hành động": top_s.action.map(ACTION_LABEL)}), H1)


def blame(as_of):
    w = "delivered_ts < CAST(? AS DATE) AND delivered_ts >= CAST(? AS DATE) - INTERVAL 90 DAY AND NOT is_canceled AND any_seller_late IS NOT NULL"
    base = q(f"""SELECT any_seller_late AS seller_late, customer_late, count(*) AS n, avg(days_to_carrier) AS d_carrier, avg(days_in_transit) AS d_transit
                 FROM core.fact_order WHERE {w} GROUP BY 1, 2""", (as_of, as_of))
    total, late = base.n.sum(), base[base.customer_late].n.sum()
    ok, sl = base[base.customer_late & ~base.seller_late].n.sum(), base[base.seller_late].n.sum()
    rv = q("""SELECT r.customer_late, r.is_before_delivery, count(*) AS n, avg(r.review_score) AS score
               FROM core.fact_review r JOIN core.fact_order o USING (order_id)
               WHERE o.delivered_ts < CAST(? AS DATE) AND o.delivered_ts >= CAST(? AS DATE) - INTERVAL 90 DAY AND NOT o.is_canceled
                 AND r.answered_ts < CAST(? AS DATE) GROUP BY 1, 2""", (as_of, as_of, as_of))
    rl = rv[rv.customer_late]
    before_share = rl[rl.is_before_delivery].n.sum() / rl.n.sum() if rl.n.sum() else None

    m = st.columns(5)
    kpi(m[0], "delivered_orders", num(total))
    kpi(m[1], "customer_late_rate", pct(late / total), f"{num(late)} đơn", tone="off")
    kpi(m[2], "late_seller_ok", pct(ok / late if late else None), "phần trễ nằm sau khâu seller", tone="off")
    kpi(m[3], "seller_late_rate", pct(sl / total), f"{num(sl)} đơn", tone="off")
    kpi(m[4], "reviewed_before_delivery", pct(before_share), "khảo sát gửi sau ngày hẹn", tone="off")

    c1, c2, c3 = st.columns(3)
    with c1:
        s = base.assign(g=base.customer_late.map({True: "Đơn trễ", False: "Đơn đúng hẹn"}))
        s = s.groupby("g").apply(lambda x: pd.Series({"d_carrier": (x.d_carrier * x.n).sum() / x.n.sum(), "d_transit": (x.d_transit * x.n).sum() / x.n.sum()}), include_groups=False)
        extra_t, extra_c = s.d_transit.get("Đơn trễ", 0) - s.d_transit.get("Đơn đúng hẹn", 0), s.d_carrier.get("Đơn trễ", 0) - s.d_carrier.get("Đơn đúng hẹn", 0)
        title(f"Đơn trễ mất thêm {num(extra_t, 1)} ngày ở vận chuyển, {num(extra_c, 1)} ngày ở seller")
        fig = go.Figure()
        for col, name, color in [("d_carrier", "Seller giao cho vận chuyển", BLUE), ("d_transit", "Vận chuyển tới khách", ORANGE)]:
            fig.add_trace(go.Bar(y=s.index, x=s[col], orientation="h", name=name, marker_color=color, text=s[col].map(lambda v: num(v, 1)), textposition="inside",
                                 insidetextfont=dict(color="white"), hovertemplate="%{y}<br>%{x:.1f} ngày<extra>" + name + "</extra>"))
        fig.update_layout(barmode="stack")
        fig.update_yaxes(showgrid=False)
        fig.update_xaxes(title="Số ngày trung bình")
        show(style(fig, H2, legend=True))
    with c2:
        g = lambda late_, before: rv[(rv.customer_late == late_) & (rv.is_before_delivery == before)]
        groups = [("Đúng hẹn", rv[rv.customer_late == False]), ("Trễ, chấm sau khi nhận", g(True, False)), ("Trễ, chấm trước khi nhận", g(True, True))]
        rows = [(n, (x.score * x.n).sum() / x.n.sum() if x.n.sum() else None, x.n.sum()) for n, x in groups]
        rdf = pd.DataFrame(rows, columns=["nhom", "score", "n"]).iloc[::-1]
        title(f"{pct(before_share, 0)} đơn trễ chấm khi chưa nhận hàng, nên điểm thấp không hẳn do sản phẩm")
        fig = go.Figure(go.Bar(y=rdf.nhom, x=rdf.score, orientation="h", marker_color=BLUE, text=rdf.score.map(lambda v: num(v, 2)), textposition="outside", cliponaxis=False,
                               customdata=rdf.n, hovertemplate="%{y}<br>Review %{x:.2f}<br>%{customdata:,} review<extra></extra>"))
        fig.update_xaxes(range=[0, 5.4], showgrid=False, showticklabels=False)
        fig.update_yaxes(showgrid=False)
        show(style(fig, H2))
    with c3:
        s = q("""WITH st AS (SELECT state, avg(lat) lat, avg(lng) lng FROM core.dim_location WHERE has_coordinates GROUP BY 1),
                 o AS (SELECT l.state AS state, count(*) n, avg(CASE WHEN f.customer_late THEN 1.0 ELSE 0.0 END) late
                       FROM core.fact_order f JOIN core.dim_location l ON l.location_key = f.customer_location_key
                       WHERE f.delivered_ts < CAST(? AS DATE) AND f.delivered_ts >= CAST(? AS DATE) - INTERVAL 90 DAY AND l.state IS NOT NULL GROUP BY 1)
                 SELECT o.*, st.lat, st.lng FROM o JOIN st USING (state)""", (as_of, as_of))
        big = s[s.n >= 30]
        worst = big.loc[big.late.idxmax()] if len(big) else None
        title(f"Bang nhận trễ nhất: {worst.state} ({pct(worst.late, 0)})" if worst is not None else "Tỷ lệ trễ theo bang nhận hàng", "Vị trí theo tọa độ, cỡ theo số đơn, bang từ 30 đơn")
        fig = go.Figure(go.Scatter(x=s.lng, y=s.lat, mode="markers+text", text=s.state, textposition="middle center", textfont=dict(size=9, color="#0b0b0b"),
                                   marker=dict(size=(s.n ** 0.5).clip(lower=13, upper=34), color=s.late, colorscale=[[i / 6, c] for i, c in enumerate(SEQ)], cmin=0,
                                               colorbar=dict(title="", tickformat=".0%", thickness=8, len=.8), line=dict(color="white", width=1)),
                                   customdata=s[["n", "late"]], hovertemplate="%{text}<br>%{customdata[0]:,} đơn<br>Trễ %{customdata[1]:.1%}<extra></extra>"))
        fig.update_xaxes(visible=False)
        fig.update_yaxes(visible=False, scaleanchor="x")
        show(style(fig, H2 - 16))

    c1, c2 = st.columns([1.25, 1])
    with c1:
        r = q("SELECT * FROM mart.route_delivery WHERE as_of = CAST(? AS DATE)", (as_of,))
        top_s = r.groupby("seller_state").n_orders.sum().nlargest(6).index.tolist()
        top_c = r.groupby("customer_state").n_orders.sum().nlargest(13).index.tolist()
        h = r[r.seller_state.isin(top_s) & r.customer_state.isin(top_c) & (r.n_orders >= 30)]
        wr = h.loc[h.late_rate.idxmax()] if len(h) else None
        title(f"Tuyến trễ nhất: {wr.route_name} ({pct(wr.late_rate, 0)}), {num(wr.late_seller_ok_share * 100, 0)}% đơn trễ có seller đúng hạn" if wr is not None else "Tỷ lệ trễ theo tuyến",
              "Hàng là bang seller, cột là bang khách. Ô trống là dưới 30 đơn trong 180 ngày.")
        piv = h.pivot(index="seller_state", columns="customer_state", values="late_rate").reindex(index=top_s, columns=top_c)
        fig = px.imshow(piv, color_continuous_scale=SEQ, text_auto=".0%", aspect="auto", labels=dict(x="", y="", color="Trễ"))
        fig.update_traces(hovertemplate="%{y} → %{x}<br>Trễ %{z:.1%}<extra></extra>", xgap=2, ygap=2, textfont=dict(size=10))
        fig.update_layout(coloraxis_colorbar=dict(tickformat=".0%", thickness=8))
        fg = style(fig, H2 - 16, top=20)
        fg.update_xaxes(side="top", showgrid=False)
        fg.update_yaxes(showgrid=False)
        show(fg)
    with c2:
        f = q("SELECT seller_id, gmv_90, seller_late_rate FROM mart.seller_features WHERE as_of = CAST(? AS DATE) AND n_limit_known >= 5", (as_of,))
        cut = f.gmv_90.quantile(.8)
        n_big_late = int(((f.gmv_90 >= cut) & (f.seller_late_rate >= .15)).sum())
        title(f"{n_big_late} seller top 20% GMV giao vận chuyển trễ từ 15%", "Mỗi chấm là một seller có từ 5 sản phẩm đã qua hạn")
        fig = go.Figure()
        for name, color, sel in [("Dưới 15%", BLUE, f.seller_late_rate < .15), ("Từ 15%", ORANGE, f.seller_late_rate >= .15)]:
            p = f[sel]
            fig.add_trace(go.Scatter(x=p.gmv_90, y=p.seller_late_rate, mode="markers", name=name, marker=dict(color=color, size=7, line=dict(color="white", width=1)),
                                     customdata=p.seller_id.map(short), hovertemplate="%{customdata}<br>GMV %{x:,.0f} BRL<br>Trễ %{y:.0%}<extra></extra>"))
        fig.update_xaxes(type="log", title="GMV 90 ngày (BRL, thang log)")
        fig.update_yaxes(tickformat=".0%")
        show(style(fig, H2 - 16, legend=True))


def seller(as_of):
    rec = q("""SELECT r.*, f.gmv_90, f.gmv_30, f.orders_90, f.trend, f.recency, f.seller_late_rate, f.cust_late_rate, f.avg_review, f.days_to_carrier, f.health_tier, d.state, d.city, d.health_tier AS stable_tier
               FROM dss.recommendation r JOIN mart.seller_features f USING (as_of, seller_id)
               JOIN core.dim_seller d ON d.seller_id = r.seller_id AND d.valid_from < CAST(? AS DATE) AND d.valid_to >= CAST(? AS DATE)
               WHERE r.as_of = CAST(? AS DATE) ORDER BY r.rank""", (as_of, as_of, as_of))
    options = rec.seller_id.tolist()
    labels = {r.seller_id: f"{short(r.seller_id)} · {ACTION_LABEL[r.action]} · {r.state} · {num(r.gmv_90)} BRL" for r in rec.itertuples()}
    c1, c2 = st.columns([1.3, 1])
    sid = c1.selectbox("Chọn seller (theo thứ tự ưu tiên)", options, format_func=labels.get)
    MEDIAN = "Trung vị toàn sàn"
    other = c2.selectbox("So với", [MEDIAN] + options[:200], format_func=lambda s: s if s == MEDIAN else labels[s])
    r = rec[rec.seller_id == sid].iloc[0]

    m = st.columns(6)
    kpi(m[0], "tier_month", r.health_tier)
    kpi(m[1], "tier_stable", r.stable_tier)
    kpi(m[2], "gmv_90", compact(r.gmv_90), f"{num(r.orders_90)} đơn", tone="off")
    kpi(m[3], "p_decline", pct(r.p_decline, 0))
    kpi(m[4], "p_dormant", pct(r.p_dormant, 0))
    kpi(m[5], "ops_score", f"{num(r.ops_score)}/100")
    st.markdown(f'<div class="rec"><b>Khuyến nghị: {ACTION_LABEL[r.action]}</b> (phân khúc {r.segment}). {r.reason} '
                f'<span style="color:#52514e">{str(r.city).title()}, {r.state}. Mã: {sid}</span></div>', unsafe_allow_html=True)

    h = q("SELECT * FROM core.fact_seller_monthly WHERE seller_id = ? AND month < CAST(? AS DATE) ORDER BY month", (sid, as_of))
    c1, c2, c3 = st.columns(3)
    with c1:
        last = h.iloc[-1] if len(h) else None
        change = last.gmv / last.gmv_prev_3m_avg - 1 if last is not None and last.gmv_prev_3m_avg else None
        title(f"GMV tháng gần nhất {signed_pct(change, 0)} so với trung bình 3 tháng trước" if change is not None else "GMV theo tháng")
        fig = go.Figure(go.Bar(x=h.month, y=h.gmv, marker_color=BLUE, hovertemplate="%{x|%m/%Y}<br>%{y:,.0f} BRL<extra></extra>"))
        show(style(fig, H1, date_x=True))
    with c2:
        recent = h.tail(3)
        title(f"3 tháng gần đây: seller {num(recent.avg_days_to_carrier.mean(), 1)} ngày, vận chuyển {num(recent.avg_days_in_transit.mean(), 1)} ngày")
        fig = go.Figure()
        for col, name, color in [("avg_days_to_carrier", "Seller giao cho vận chuyển", BLUE), ("avg_days_in_transit", "Vận chuyển tới khách", ORANGE)]:
            fig.add_trace(go.Scatter(x=h.month, y=h[col], mode="lines+markers", name=name, line=dict(color=color, width=2), marker=dict(size=7), hovertemplate="%{x|%m/%Y}<br>%{y:.1f} ngày<extra>" + name + "</extra>"))
        fig.update_yaxes(rangemode="tozero")
        show(style(fig, H1, legend=True, date_x=True))
    with c3:
        title(f"So với {'trung vị toàn sàn' if other == MEDIAN else short(other)}")
        feats = [("GMV 90 ngày", "gmv_90", lambda v: num(v)), ("Đơn 90 ngày", "orders_90", lambda v: num(v)), ("Xu hướng 30 ngày", "trend", lambda v: signed_pct(v, 0)),
                 ("Ngày chưa bán", "recency", lambda v: num(v)), ("Giao VC trễ", "seller_late_rate", lambda v: pct(v, 0)), ("Khách nhận trễ", "cust_late_rate", lambda v: pct(v, 0)),
                 ("Review", "avg_review", lambda v: num(v, 2)), ("Ngày tới VC", "days_to_carrier", lambda v: num(v, 1))]
        ref = rec.median(numeric_only=True) if other == MEDIAN else rec[rec.seller_id == other].iloc[0]
        table(pd.DataFrame({"Chỉ số": [f[0] for f in feats], short(sid): [f[2](r[f[1]]) for f in feats], "So với": [f[2](ref[f[1]]) for f in feats]}), H1)

    c1, c2 = st.columns([1, 2])
    with c1:
        t = q("""SELECT health_tier AS "Hạng ổn định", strftime(valid_from, '%d/%m/%Y') AS "Từ",
                        CASE WHEN valid_to >= CAST(? AS DATE) THEN 'hiện tại' ELSE strftime(valid_to, '%d/%m/%Y') END AS "Đến"
                 FROM core.dim_seller WHERE seller_id = ? AND valid_from < CAST(? AS DATE) ORDER BY valid_from DESC""", (as_of, sid, as_of))
        title(f"Lịch sử hạng (SCD2): {len(t)} phiên bản")
        table(t, 176)
    with c2:
        mh = q("""SELECT f.month, f.n_orders, f.gmv, f.seller_late_rate, f.customer_late_rate, f.avg_review, h.health_tier, h.size_band, h.late_band
                  FROM core.fact_seller_monthly f JOIN core.dim_seller_health h USING (health_key)
                  WHERE f.seller_id = ? AND f.month < CAST(? AS DATE) ORDER BY f.month DESC""", (sid, as_of))
        title("Theo tháng, kèm hồ sơ sức khỏe (mini-dimension)")
        table(pd.DataFrame({"Tháng": pd.to_datetime(mh.month).dt.strftime("%m/%Y"), "Đơn": mh.n_orders, "GMV": mh.gmv.round(0), "Giao VC trễ": mh.seller_late_rate.map(pct),
                            "Khách trễ": mh.customer_late_rate.map(pct), "Review": mh.avg_review.round(2), "Hạng tháng": mh.health_tier, "Nhóm đơn": mh.size_band}), 176)
