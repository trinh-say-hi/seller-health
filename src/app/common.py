"""Ket noi, dinh dang, chu thich KPI va phong cach bieu do dung chung."""
import html

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yaml

from src.config import DB_PATH, ROOT

BLUE, ORANGE, AQUA, LIGHT_BLUE = "#2a78d6", "#eb6834", "#1baf7a", "#9ec5f4"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e8e7e3"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
TIER_ORDER = ["Vàng", "Ổn định", "Ít đơn", "Theo dõi", "Nguy cơ", "Tạm ngừng"]

CSS = """
<style>
header[data-testid="stHeader"], [data-testid="stSidebarCollapsedControl"], footer {display: none !important;}
.block-container, [data-testid="stMainBlockContainer"] {padding: 0.45rem 1.1rem 0.3rem 1.1rem !important; max-width: 100% !important;}
[data-testid="stVerticalBlock"] {gap: 0.35rem;}
[data-testid="stMarkdown"], [data-testid="stMarkdownContainer"] {margin-bottom: 0 !important;}
[data-testid="stHorizontalBlock"] {gap: 0.55rem;}
[data-testid="stMetric"] {background: #ffffff; border: 1px solid #e8e7e3; border-radius: 8px; padding: 4px 10px 3px 10px;}
[data-testid="stMetric"] > div {gap: 0;}
[data-testid="stMetricLabel"] {font-size: 12px; color: #52514e; min-height: 0;}
[data-testid="stMetricLabel"] p {font-size: 12px;}
[data-testid="stMetricValue"] {font-size: 21px; line-height: 1.25; font-weight: 600;}
[data-testid="stMetricDelta"] {font-size: 11.5px;}
[data-testid="stWidgetLabel"] {margin-bottom: 0; min-height: 0;}
[data-testid="stWidgetLabel"] p {font-size: 12px; color: #52514e;}
[data-testid="stSliderTickBar"] {display: none;}
[data-testid="stElementContainer"]:has(.brand) {margin-top: 6px;}
.brand {font-size: 17px; font-weight: 700; line-height: 1.1;}
.brand span {display: block; font-size: 11px; font-weight: 400; color: #52514e;}
.ct {font-size: 13.5px; font-weight: 600; line-height: 1.25; margin: 2px 0 0 2px;}
.cs {font-size: 11.5px; font-weight: 400; color: #52514e; line-height: 1.25; margin: 0 0 0 2px;}
p.note {font-size: 12px !important; color: #52514e; line-height: 1.3; margin: 0;}
[data-testid="stSlider"] [data-testid="stWidgetLabel"] {margin-bottom: 7px;}
.rec {background: #eef4fc; border-radius: 8px; padding: 6px 10px; font-size: 13px; line-height: 1.35;}
.rec b {color: #184f95;}
.flash {border-radius: 6px; padding: 2px 10px; font-size: 12.5px; line-height: 1.4; margin: 0;}
.flash.bad {background: #fdecec; color: #a32020;}
.flash.good {background: #eaf6ea; color: #006300;}
div[data-testid="stRadio"] [role="radiogroup"] {gap: 0; flex-wrap: nowrap;}
[data-testid="stRadioOption"] {padding: 5px 13px; margin: 0; border-bottom: 2px solid #e8e7e3; cursor: pointer;}
[data-testid="stRadioOption"] > div > div:first-child {display: none;}
[data-testid="stRadioOption"] p {font-size: 14px; white-space: nowrap;}
[data-testid="stRadioOption"][data-selected="true"] {border-bottom-color: #2a78d6;}
[data-testid="stRadioOption"][data-selected="true"] p {font-weight: 600; color: #184f95;}
[data-testid="stMetric"] {gap: 0 !important;}
[data-testid="stMetricChart"] {height: 30px !important; overflow: hidden; margin-top: 1px;}
[data-testid="stMetricChart"] svg {height: 30px !important; width: 100%;}
</style>
"""


def apply_css():
    st.markdown(CSS, unsafe_allow_html=True)


@st.cache_resource
def _con():
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data(show_spinner=False)
def q(sql: str, params: tuple = ()) -> pd.DataFrame:
    return _con().cursor().execute(sql, list(params)).df()


@st.cache_data(show_spinner=False)
def metric_defs() -> dict:
    return yaml.safe_load((ROOT / "metrics.yml").read_text(encoding="utf-8"))


def help_for(metric_id: str) -> str:
    m = metric_defs()[metric_id]
    parts = [m["definition"], f"**Công thức:** {m['formula']}", f"**Khoảng:** {m['window']}", f"**Nguồn:** `{m['source']}`"]
    if m.get("caveat"):
        parts.append(f"**Lưu ý:** {m['caveat']}")
    return "\n\n".join(parts)


def kpi(col, metric_id, value, delta=None, *, label=None, chart=None, tone="normal"):
    """The KPI co chu thich tu metrics.yml. tone: normal, inverse (giam la tot), off (trung tinh)."""
    args = {"delta_color": tone, "help": help_for(metric_id)}
    if tone == "off":
        args["delta_arrow"] = "off"
    values = [float(x) for x in (chart if chart is not None else []) if pd.notna(x)]
    if len(values) > 1:
        args["chart_data"] = values
        args["chart_type"] = "line"
    col.metric(label or metric_defs()[metric_id]["label"], value, delta, height="stretch", **args)


def num(x, digits=0):
    """So kieu Viet Nam: 1.234.567,8"""
    if x is None or pd.isna(x):
        return "—"
    return f"{x:,.{digits}f}".replace(",", "§").replace(".", ",").replace("§", ".")


def brl(x):
    return f"{num(x)} BRL"


def compact(x):
    """Rut gon cho the KPI: 863k, 1,2 tr."""
    if x is None or pd.isna(x):
        return "—"
    if abs(x) >= 1_000_000:
        return f"{num(x / 1_000_000, 2)} tr"
    if abs(x) >= 10_000:
        return f"{num(x / 1000)}k"
    return num(x)


def pct(x, digits=1):
    return "—" if x is None or pd.isna(x) else f"{num(100 * x, digits)}%"


def signed_pct(x, digits=1):
    if x is None or pd.isna(x):
        return None
    return f"{'+' if x >= 0 else ''}{num(100 * x, digits)}%"


def points(x, digits=1):
    if x is None or pd.isna(x):
        return None
    return f"{'+' if x >= 0 else ''}{num(100 * x, digits)} điểm %"


def short(seller_id):
    return str(seller_id)[:8]


def title(text, sub=None):
    """Tieu de bieu do neu ket luan, co the them mot dong phu."""
    st.markdown(f'<div class="ct">{html.escape(text)}</div>' + (f'<div class="cs">{html.escape(sub)}</div>' if sub else ""), unsafe_allow_html=True)


def flash(text, good=False):
    """Thong bao mot dong, chiem it cho hon st.error. Co dau hieu bang chu, khong chi dua vao mau."""
    st.markdown(f'<p class="flash {"good" if good else "bad"}">{"✓" if good else "⚠"} {html.escape(text)}</p>', unsafe_allow_html=True)


def note(text):
    st.markdown(f'<p class="note">{html.escape(text)}</p>', unsafe_allow_html=True)


def style(fig: go.Figure, height=220, legend=False, date_x=False, top=None):
    fig.update_layout(
        height=height, template="none", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="system-ui, sans-serif", size=12, color=INK), margin=dict(l=4, r=8, t=top if top is not None else (24 if legend else 6), b=4),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, title_text="", font=dict(color=MUTED, size=11)),
        bargap=0.3, barcornerradius=4, hoverlabel=dict(bgcolor="white", font_color=INK, bordercolor=GRID),
        separators=",.",
    )
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickcolor=GRID, tickfont=dict(color=MUTED, size=11), title_font=dict(color=MUTED, size=11), automargin=True)
    if date_x:
        fig.update_xaxes(tickformat="%m/%y")
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID, tickfont=dict(color=MUTED, size=11), title_font=dict(color=MUTED, size=11), automargin=True)
    return fig


def show(fig):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def table(df: pd.DataFrame, height=200):
    st.dataframe(df, hide_index=True, width="stretch", height=height)
