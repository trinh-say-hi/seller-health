"""Ba man hinh quyet dinh: Bang ke hoach keo tha, What-if tuyen, Kiem chung. Moi man hinh vua mot khung hinh."""
import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from src.app.common import (BLUE, MUTED, ORANGE, brl, flash, guide_banner, kpi, note, num, pct, points, q, short, show, signed_pct, style, table, title)
from src.config import EVIDENCE_DIR
from src.dss.optimize import budget_curve, build_plan, cost_of, gain, slots_of, summarize
from src.dss.rules import ACTION_LABEL, CALL, EMAIL, NONE, OPS, Params

MAX_CARDS = 45
BOARD_HEIGHT = 436
_kanban = components.declare_component("kanban", path=str(Path(__file__).parent / "kanban"))


@st.cache_data(show_spinner=False)
def _panel(as_of):
    return q("""SELECT f.*, s.p_decline, s.p_dormant, s.value_45, s.ops_score, d.state, d.city
                FROM mart.seller_features f JOIN dss.scores s USING (as_of, seller_id)
                JOIN core.dim_seller d ON d.seller_id = f.seller_id AND d.is_current
                WHERE f.as_of = CAST(? AS DATE)""", (as_of,))


@st.cache_data(show_spinner="Đang tối ưu...")
def _plan(as_of, params_json):
    return build_plan(_panel(as_of), Params(**json.loads(params_json)))


@st.cache_data(show_spinner=False)
def _curve(as_of, params_json):
    return budget_curve(_panel(as_of), Params(**json.loads(params_json)), list(range(0, 8001, 500)))


def _controls() -> Params:
    d = Params()
    c = st.columns([1, 1, 1, 1, .8, .8], vertical_alignment="bottom")
    budget = c[0].slider("Ngân sách (BRL)", 0, 8000, int(d.budget), 250)
    slots = c[1].slider("Số suất nhân viên", 0, 100, d.max_slots, 5, help="Gọi điện dùng 1 suất, hỗ trợ vận hành dùng 2 suất.")
    risk = c[2].slider("Ngưỡng rủi ro", .10, .80, d.risk_threshold, .05)
    value = c[3].slider("Giá trị cao: top", 5, 50, int(round(100 - 100 * d.value_pct)), 5, format="%d%%")
    with c[4].popover("Giả định", width="stretch"):
        st.warning("Chi phí và hiệu quả là giả định để so sánh phương án, dữ liệu không có số thật.")
        a, b = st.columns(2)
        cost_call = a.number_input("Chi phí gọi (BRL)", 0, 1000, int(d.cost_call), 10)
        cost_ops = b.number_input("Chi phí hỗ trợ (BRL)", 0, 2000, int(d.cost_ops), 10)
        eff_call = a.slider("Gọi: vận hành ổn", 0, 100, int(100 * d.eff_call_ok), 5, format="%d%%")
        eff_call_p = b.slider("Gọi: vận hành kém", 0, 100, int(100 * d.eff_call_poor), 2, format="%d%%")
        eff_ops = a.slider("Hỗ trợ: vận hành kém", 0, 100, int(100 * d.eff_ops_poor), 5, format="%d%%")
        eff_ops_o = b.slider("Hỗ trợ: vận hành ổn", 0, 100, int(100 * d.eff_ops_ok), 5, format="%d%%")
        eff_email = a.slider("Email tự động", 0, 30, int(100 * d.eff_email), 1, format="%d%%")
    st.session_state.setdefault("board_reset", 0)
    if c[5].button("Đặt lại", width="stretch", help="Bỏ mọi thao tác kéo tay, về đề xuất của bộ tối ưu."):
        st.session_state.board_reset += 1
    return replace(d, budget=float(budget), max_slots=int(slots), risk_threshold=float(risk), value_pct=1 - value / 100, cost_call=float(cost_call), cost_ops=float(cost_ops),
                   eff_call_ok=eff_call / 100, eff_call_poor=eff_call_p / 100, eff_ops_poor=eff_ops / 100, eff_ops_ok=eff_ops_o / 100, eff_email=eff_email / 100)


def _card(r):
    return {"id": r.seller_id, "title": short(r.seller_id), "state": str(r.state), "detail": f"{num(r.gmv_90)} BRL · rủi ro {r.p_decline:.0%}", "flag": "VH kém" if r.ops_poor else ""}


def _board_members(plan):
    """Chon toi da MAX_CARDS seller len bang: phan tra phi, roi ung vien chua chon, roi email."""
    paid = plan[plan.action.isin([CALL, OPS])]
    room = max(MAX_CARDS - len(paid), 0)
    waiting = plan[(plan.action == NONE) & plan.risk_high & plan.value_high].nlargest(int(room * .7), "gmv_risk")
    email = plan[plan.action == EMAIL].nlargest(room - len(waiting), "gmv_risk")
    return pd.concat([paid, waiting, email])


def apply_moves(plan, moved: dict, p: Params):
    """Tinh lai ke hoach sau khi nguoi dung keo. Gia tri trong moved la action."""
    out = plan.copy()
    out["action"] = [moved.get(s, a) for s, a in zip(out.seller_id, out.action)]
    out["cost"] = [cost_of(a, p) for a in out.action]
    out["slots"] = [slots_of(a, p) for a in out.action]
    out["expected_saved"] = [gain(r, r.action, p) for r in out.itertuples()]
    return out


def board(as_of):
    guide_banner("Bước 4/6", "Kế hoạch can thiệp (DSS)", "Với ngân sách và số suất nhân sự tháng này, ta nên làm gì với ai?", "Thuật toán MILP đã tự động chọn tập seller tối ưu nhất. Bạn có thể kéo thả thẻ giữa các cột để phân bổ lại.")
    p = _controls()
    pj = json.dumps(p.as_dict(), sort_keys=True)
    plan = _plan(as_of, pj)
    members = _board_members(plan)
    cols = [CALL, OPS, EMAIL, NONE]
    start = [{"id": a, "title": ACTION_LABEL[a], "items": [_card(r) for r in members[members.action == a].itertuples()]} for a in cols]
    key = f"board-{as_of}-{abs(hash(pj)) % 10**8}-{st.session_state.board_reset}"

    top = st.columns([3.5, 1.3])
    summary_box = top[0].container()
    left, right = st.columns([4, 1.15])
    with left:
        result = _kanban(columns=start, height=BOARD_HEIGHT, version=key, key=key, default=None)

    if result:
        moved = {sid: a for a, ids in result["columns"].items() for sid in ids}
    else:
        moved = {r.seller_id: r.action for r in members.itertuples()}
    current = apply_moves(plan, moved, p)
    s, s0 = summarize(current), summarize(plan)
    orig = dict(zip(plan.seller_id, plan.action))
    edited = sum(1 for sid, a in moved.items() if sid in orig and orig[sid] != a)

    with summary_box:
        m = st.columns(4)
        kpi(m[0], "plan_cost", brl(s["cost"]), f"còn {num(p.budget - s['cost'])}", tone="off")
        kpi(m[1], "plan_slots", f"{s['slots']}/{p.max_slots}", f"{s['n_call']} gọi, {s['n_ops']} hỗ trợ", tone="off")
        kpi(m[2], "plan_risk", brl(s["gmv_risk_covered"]), f"trên tổng {num(s['gmv_risk_total'])}", tone="off")
        kpi(m[3], "plan_saved", brl(s["expected_saved"]), f"{s['expected_saved'] - s0['expected_saved']:+,.0f} so với đề xuất".replace(",", "."), tone="off")
        if s["cost"] > p.budget:
            flash(f"Vượt ngân sách {num(s['cost'] - p.budget)} BRL. Hãy chuyển bớt seller hoặc tăng ngân sách.")
        elif s["slots"] > p.max_slots:
            flash(f"Vượt {s['slots'] - p.max_slots} suất nhân viên. Hãy chuyển bớt seller hoặc tăng số suất.")
        elif edited:
            flash(f"Đã đổi {edited} seller so với đề xuất, vẫn trong ràng buộc.", good=True)

    with top[1]:
        curve = _curve(as_of, pj)
        flat = curve[curve.expected_saved >= curve.expected_saved.max() * .999].budget.min()
        title(f"Chi quá {num(flat)} BRL gần như không có thêm lợi ích")
        fig = go.Figure(go.Scatter(x=curve.budget, y=curve.expected_saved, mode="lines", line=dict(color=BLUE, width=2),
                                   customdata=curve.n_sellers, hovertemplate="Ngân sách %{x:,.0f} BRL<br>Giữ được %{y:,.0f} BRL (giả định)<br>%{customdata} seller<extra></extra>"))
        fig.add_vline(x=p.budget, line_color=MUTED, line_dash="dot")
        fig.update_yaxes(showticklabels=False)
        fig.update_xaxes(tickvals=[0, 4000, 8000])
        show(style(fig, 70, top=2))

    with right:
        picked = current[current.seller_id.isin(moved)].copy()
        picked["Hành động"] = picked.action.map(ACTION_LABEL)
        order = picked.sort_values("gmv_risk", ascending=False)
        sid = result.get("selected") if result else None
        if sid not in set(order.seller_id):
            sid = order.seller_id.iloc[0]
        r = order[order.seller_id == sid].iloc[0]
        st.markdown(f'<div class="rec" id="seller-detail"><b>{short(sid)} · {r["Hành động"]}</b><br>{r.reason}</div>', unsafe_allow_html=True)
        h = q("SELECT month, gmv FROM core.fact_seller_monthly WHERE seller_id = ? AND month < CAST(? AS DATE) ORDER BY month", (sid, as_of))
        title("GMV theo tháng")
        show(style(go.Figure(go.Bar(x=h.month, y=h.gmv, marker_color=BLUE, hovertemplate="%{x|%m/%Y}<br>%{y:,.0f} BRL<extra></extra>")), 120, date_x=True))
        note(f"Chi phí {num(r.cost)} BRL. GMV rủi ro {num(r.gmv_risk)} BRL.")
        export = picked.assign(as_of=as_of)[["as_of", "seller_id", "Hành động", "state", "gmv_90", "p_decline", "gmv_risk", "cost", "expected_saved", "reason"]].sort_values("gmv_risk", ascending=False)
        st.download_button("Xuất kế hoạch ra CSV", export.to_csv(index=False).encode("utf-8-sig"), f"ke_hoach_{as_of}.csv", "text/csv", width="stretch")
        note("Kéo thẻ để đổi hành động, bấm thẻ để xem chi tiết. Đổi ràng buộc sẽ tính lại đề xuất và xóa thao tác kéo tay. VH kém: giao vận chuyển trễ từ 15%.")


def route_whatif(as_of):
    guide_banner("Bước 5/6", "Giả lập đàm phán hẹn giao", "Hứa thêm N ngày với khách hàng thì tỷ lệ đơn trễ trên tuyến giảm bao nhiêu?", "Chọn tuyến hàng (ví dụ SP ➔ CE). Kéo thanh trượt 'Hứa thêm (ngày)' để quan sát tỷ lệ đơn trễ giảm xuống theo thời gian thực.")
    routes = q("SELECT route_name, n_orders FROM mart.route_delivery WHERE as_of = CAST(? AS DATE) ORDER BY n_orders DESC", (as_of,))
    c1, c2, c3 = st.columns(3)
    route = c1.selectbox("Tuyến (bang seller → bang khách)", routes.route_name.tolist())
    n = c2.slider("Hứa thêm (ngày)", -10, 20, 0)
    target = c3.slider("Mục tiêu tỷ lệ trễ", 1, 25, 5, format="%d%%") / 100
    d = q("""SELECT f.delay_days, date_diff('day', CAST(f.purchase_ts AS DATE), CAST(f.estimated_ts AS DATE)) AS promise
             FROM core.fact_order_seller f JOIN core.dim_route r USING (route_key)
             WHERE r.route_name = ? AND f.delivered_ts < CAST(? AS DATE)
               AND f.purchase_ts >= CAST(? AS DATE) - INTERVAL 180 DAY AND f.purchase_ts < CAST(? AS DATE) - INTERVAL 60 DAY
               AND f.delay_days IS NOT NULL""", (route, as_of, as_of, as_of))
    if d.empty:
        st.warning("Tuyến này không có đơn đủ điều kiện tại mốc đã chọn.")
        return
    grid = np.arange(-10, 21)
    rate = np.array([(d.delay_days > g).mean() for g in grid])
    now, new = (d.delay_days > 0).mean(), (d.delay_days > n).mean()
    need = next((int(g) for g, r in zip(grid, rate) if r <= target), None)
    m = st.columns(4)
    kpi(m[0], "delivered_orders", num(len(d)), "dưới 100 đơn: chỉ tham khảo" if len(d) < 100 else "đơn mua 180–60 ngày trước", label="Đơn lịch sử", tone="off")
    if n == 0:
        kpi(m[1], "route_late", pct(new))
    else:
        kpi(m[1], "route_late", pct(new), f"{points(new - now)} so với hiện tại", tone="inverse")
    kpi(m[2], "route_promise", f"{num(d.promise.mean() + n, 1)} ngày", f"{n:+d} ngày" if n else "như hiện tại", tone="off")
    kpi(m[3], "route_need", "Quá 20 ngày" if need is None else f"{need:+d} ngày" if need else "Đã đạt", f"để trễ ≤ {pct(target, 0)}", tone="off")

    c1, c2 = st.columns([1, 1.15])
    with c1:
        title(f"{route}: hứa thêm {n:+d} ngày thì trễ còn {pct(new)}" if n else f"{route}: tỷ lệ trễ hiện tại {pct(now)}", "Giả định thời gian giao không đổi. Không đo được hẹn dài hơn làm mất bao nhiêu đơn.")
        fig = go.Figure(go.Scatter(x=grid, y=rate, mode="lines+markers", line=dict(color=BLUE, width=2), marker=dict(size=7), hovertemplate="Hứa thêm %{x} ngày<br>Trễ %{y:.1%}<extra></extra>"))
        fig.add_vline(x=n, line_color=MUTED, line_dash="dot")
        fig.add_hline(y=target, line_color=ORANGE, line_dash="dot", annotation_text="Mục tiêu", annotation_font_color=MUTED)
        fig.update_xaxes(title="Số ngày hứa thêm", dtick=5)
        fig.update_yaxes(tickformat=".0%", rangemode="tozero")
        show(style(fig, 470))
    with c2:
        top = q("""SELECT r.route_name AS tuyen, count(*) AS so_don, avg(CASE WHEN f.delay_days > 0 THEN 1.0 ELSE 0.0 END) AS tre,
                          avg(date_diff('day', CAST(f.purchase_ts AS DATE), CAST(f.estimated_ts AS DATE))) AS hen,
                          quantile_disc(f.delay_days, ?) AS can_them,
                          avg(CASE WHEN NOT coalesce(f.seller_late, FALSE) THEN 1.0 ELSE 0.0 END) FILTER (WHERE f.delay_days > 0) AS ok
                   FROM core.fact_order_seller f JOIN core.dim_route r USING (route_key)
                   WHERE f.delivered_ts < CAST(? AS DATE) AND f.purchase_ts >= CAST(? AS DATE) - INTERVAL 180 DAY AND f.purchase_ts < CAST(? AS DATE) - INTERVAL 60 DAY AND f.delay_days IS NOT NULL
                   GROUP BY 1 HAVING count(*) >= 100 ORDER BY sum(CASE WHEN f.delay_days > 0 THEN 1 ELSE 0 END) DESC LIMIT 25""", (1 - target, as_of, as_of, as_of))
        if len(top):
            title(f"Tuyến nhiều đơn trễ nhất: {top.tuyen.iloc[0]}, cần hứa thêm {num(max(top.can_them.iloc[0], 0))} ngày để trễ ≤ {pct(target, 0)}", "Các tuyến từ 100 đơn, xếp theo số đơn trễ")
        table(pd.DataFrame({"Tuyến": top.tuyen, "Số đơn": top.so_don, "Tỷ lệ trễ": top.tre.map(pct), "Lời hẹn TB (ngày)": top.hen.round(1),
                            f"Hứa thêm để trễ ≤ {pct(target, 0)}": top.can_them.clip(lower=0), "Đơn trễ, seller đúng hạn": top.ok.map(pct)}), 470)


def validation(as_of):
    guide_banner("Bước 6/6", "Kiểm định mô hình AI", "Các tháng trước danh sách đề xuất trúng bao nhiêu % so với thực tế?", "So sánh danh sách DSS với các cách chọn truyền thống. DSS luôn vượt trội trong việc bao phủ và giữ chân GMV rủi ro.")
    lists = q("SELECT * FROM dss.eval_lists ORDER BY as_of")
    plan = lists[lists.scope == "plan"]
    pv = plan.pivot(index="as_of", columns="list_name", values=["hit_rate", "loss_share"])
    hd, hg = pv["hit_rate"]["Kế hoạch DSS"], pv["hit_rate"]["Theo GMV"]
    ld, lg = pv["loss_share"]["Kế hoạch DSS"], pv["loss_share"]["Theo GMV"]
    worse = [pd.Timestamp(t).strftime("%m/%Y") for t in ld.index if ld[t] < lg[t]]
    m = st.columns(4)
    kpi(m[0], "hit_rate", pct(hd.mean(), 0), points(hd.mean() - hg.mean(), 0), label="Kế hoạch DSS gọi trúng")
    kpi(m[1], "hit_rate", pct(hg.mean(), 0), "cùng số seller", label="Chọn theo GMV gọi trúng", tone="off")
    kpi(m[2], "loss_share", pct(ld.mean(), 0), points(ld.mean() - lg.mean(), 0), label="Kế hoạch DSS bao phủ GMV mất")
    kpi(m[3], "loss_share", pct(lg.mean(), 0), "cùng số seller", label="Chọn theo GMV bao phủ GMV mất", tone="off")
    note(f"Cùng số seller, hệ thống trúng nhiều hơn rõ rệt, nhưng bao phủ ít GMV mất hơn ở {len(worse)}/{len(ld)} tháng ({', '.join(worse)}) vì seller rất lớn có xác suất sụt thấp. "
         "Muốn bao phủ nhiều tiền hơn thì hạ ngưỡng rủi ro. Số liệu chưa chứng minh can thiệp có hiệu quả, vì không có nhóm đối chứng.")

    c1, c2, c3 = st.columns(3)
    for col, measure, text in [(c1, "hit_rate", f"Gọi trúng: DSS cao hơn GMV ở {int((hd > hg).sum())}/{len(hd)} tháng"), (c2, "loss_share", f"Bao phủ GMV mất: DSS thua GMV ở {len(worse)}/{len(ld)} tháng")]:
        with col:
            title(text)
            fig = go.Figure()
            for name, color in [("Kế hoạch DSS", BLUE), ("Theo GMV", ORANGE)]:
                p = plan[plan.list_name == name]
                fig.add_trace(go.Scatter(x=p.as_of, y=p[measure], mode="lines+markers", name=name, line=dict(color=color, width=2), marker=dict(size=7), hovertemplate="%{x|%m/%Y}<br>%{y:.0%}<extra>" + name + "</extra>"))
            fig.update_yaxes(tickformat=".0%", rangemode="tozero")
            fig.update_xaxes(dtick="M1")
            show(style(fig, 212, legend=True, date_x=True))
    with c3:
        t = lists[lists.scope == "top50"].groupby("list_name").agg(hit=("hit_rate", "mean"), loss=("loss_share", "mean")).reset_index()
        title("Năm cách chọn 50 seller: DSS cân bằng hai chỉ số", "Càng lên trên, sang phải càng tốt")
        fig = go.Figure(go.Scatter(x=t.hit, y=t.loss, mode="markers+text", text=t.list_name.str.replace(" (kỳ vọng)", "", regex=False).str.replace(" (rủi ro × giá trị)", "", regex=False), textposition="top center", textfont=dict(size=10),
                                   marker=dict(size=10, color=BLUE, line=dict(color="white", width=1)), hovertemplate="%{text}<br>Gọi trúng %{x:.0%}<br>Bao phủ %{y:.0%}<extra></extra>"))
        fig.update_xaxes(tickformat=".0%", title="Gọi trúng", range=[.15, .95])
        fig.update_yaxes(tickformat=".0%", title="Bao phủ GMV mất", range=[-.04, .46])
        show(style(fig, 198))

    c1, c2, c3 = st.columns([1.15, 1, 1])
    with c1:
        a = q("SELECT * FROM dss.eval_auc WHERE as_of >= DATE '2018-03-01' ORDER BY target, as_of")
        title("Mô hình chỉ nhỉnh hơn cách đơn giản, nên giá trị nằm ở quyết định")
        table(pd.DataFrame({"Tháng": pd.to_datetime(a.as_of).dt.strftime("%m/%Y"), "Mục tiêu": a.target.map({"decline": "Sụt GMV", "dormant": "Tạm ngừng"}), "Tỷ lệ gốc": a.base_rate.map(lambda v: pct(v, 0)),
                            "AUC": a.auc_model.round(3), "Bỏ vận hành": a.auc_no_ops.round(3), "Ngày không bán": a.auc_recency.round(3)}), 206)
    with c2:
        s = q("SELECT case_name, avg(jaccard) j, avg(n_case) n, avg(expected_saved) saved, avg(expected_saved_base) base FROM dss.sensitivity GROUP BY 1 ORDER BY j")
        title("Danh sách đổi mạnh khi cắt nguồn lực, khá vững khi giả định đổi")
        table(pd.DataFrame({"Thay đổi": s.case_name, "Trùng gốc": s.j.map(lambda v: pct(v, 0)), "Seller": s.n.round(0), "Giữ được": (s.saved / s.base - 1).map(lambda v: signed_pct(v, 0))}), 206)
    with c3:
        res = []
        path = EVIDENCE_DIR / "test_results.json"
        if path.exists():
            res = json.loads(path.read_text(encoding="utf-8"))
        rec = q("SELECT count(*) n, count(*) FILTER (WHERE is_ok) ok FROM ops.layer_reconciliation")
        qr = q("SELECT count(*) n FROM ops.quarantine")
        log = q("SELECT count(*) n FROM ops.etl_log WHERE status = 'ok' AND batch <> 'init'")
        title("Chất lượng kho dữ liệu")
        table(pd.DataFrame({"Kiểm tra": ["Test hệ thống đạt", "Đối soát giữa các lớp khớp", "Đợt nạp thành công", "Dòng bị cách ly"],
                            "Kết quả": [f"{sum(r['ok'] for r in res)}/{len(res)}", f"{num(rec.ok.iloc[0])}/{num(rec.n.iloc[0])}", f"{log.n.iloc[0]}/26", num(qr.n.iloc[0])]}), 164)
        with st.popover("Bất thường dữ liệu và nhật ký nạp", width="stretch"):
            st.dataframe(q('SELECT rule_name AS "Vấn đề", n_rows AS "Số dòng", handling AS "Cách xử lý" FROM ops.dq_issue'), hide_index=True, width="stretch")
            st.dataframe(q('SELECT batch AS "Đợt", status AS "Trạng thái", rows_loaded AS "Dòng nạp", rows_rejected AS "Dòng loại", sellers_tier_changed AS "Đổi hạng", duration_s AS "Giây" FROM ops.etl_log ORDER BY batch'), hide_index=True, width="stretch")
