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
/* Mau va khoang cach theo boi so 8px: trang xam nhat, moi the va moi bieu do la mot o trang rieng */
:root {
  --sh-page: #f3f5f8; --sh-card: #ffffff; --sh-line: #e1e5ec; --sh-ink: #0f1722; --sh-muted: #5b6472;
  --sh-blue: #2a78d6; --sh-blue-ink: #184f95; --sh-blue-soft: #eaf2fc; --sh-shadow: 0 1px 2px rgba(16, 24, 40, .06);
}
footer {display: none !important;}
header[data-testid="stHeader"] {background: transparent !important; height: 2.75rem; pointer-events: none;}
header[data-testid="stHeader"] * {pointer-events: auto;}
[data-testid="stMainMenu"], [data-testid="stToolbarActions"], [data-testid="stAppDeployButton"], [data-testid="stDecoration"], [data-testid="stStatusWidget"] {display: none !important;}
[data-testid="stExpandSidebarButton"] {background: var(--sh-card); border: 1px solid var(--sh-line); border-radius: 8px; box-shadow: var(--sh-shadow);}
.stApp {background: var(--sh-page);}
.block-container, [data-testid="stMainBlockContainer"] {padding: 2.75rem clamp(0.75rem, 1.3vw, 1.5rem) 0.25rem clamp(0.75rem, 1.3vw, 1.5rem) !important; max-width: 100% !important;}
[data-testid="stVerticalBlock"] {gap: 0.5rem;}
[data-testid="stHorizontalBlock"] {gap: clamp(0.5rem, 0.8vw, 0.9rem);}
[data-testid="stMarkdown"], [data-testid="stMarkdownContainer"] {margin-bottom: 0 !important;}

/* Sidebar dieu huong */
[data-testid="stSidebar"] {background: #ffffff; border-right: 1px solid var(--sh-line);}
[data-testid="stSidebar"] [data-testid="stSidebarContent"] {padding-top: 0.5rem;}
.brand {font-size: 18px; font-weight: 700; line-height: 1.15; color: var(--sh-ink);}
.brand span {display: block; font-size: 11.5px; font-weight: 400; color: var(--sh-muted); margin-top: 2px;}
.navgroup {font-size: 10.5px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--sh-muted); margin: 10px 0 0 2px;}
[data-testid="stSidebar"] div[data-testid="stRadio"] [role="radiogroup"] {gap: 2px; flex-direction: column;}
[data-testid="stSidebar"] [data-testid="stRadioOption"] {padding: 7px 10px; margin: 0; border-radius: 8px; cursor: pointer; width: 100%;}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child {display: none;}
[data-testid="stSidebar"] [data-testid="stRadioOption"] p {font-size: 14px;}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {background: #f1f4f8;}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {background: var(--sh-blue-soft);}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p {font-weight: 600; color: var(--sh-blue-ink);}
.sidenote {font-size: 11.5px; color: var(--sh-muted); line-height: 1.4;}

/* Muc tieu cua man hinh dang xem, nam trong sidebar */
.sidegoal {font-size: 12px; color: #2b3340; line-height: 1.45; background: #f6f8fb; border: 1px solid var(--sh-line); border-radius: 8px; padding: 8px 10px; margin-top: 4px;}
.sidegoal i {color: var(--sh-muted);}
.tb-step {background: var(--sh-blue); color: #fff; font-weight: 700; font-size: 10px; padding: 1px 6px; border-radius: 4px; white-space: nowrap;}

/* The KPI: o trang rieng, nhan duoc xuong dong thay vi bi cat */
[data-testid="stMetric"] {background: var(--sh-card); border: 1px solid var(--sh-line); border-radius: 10px; padding: 8px 12px 6px 12px; box-shadow: var(--sh-shadow); gap: 0 !important;}
[data-testid="stMetric"] > div {gap: 0;}
[data-testid="stMetricLabel"] {font-size: 12px; color: var(--sh-muted); min-height: 0;}
[data-testid="stMetricLabel"] p, [data-testid="stMetricLabel"] div {font-size: clamp(11px, 0.85vw, 13px); white-space: normal !important; overflow: visible !important; text-overflow: clip !important; line-height: 1.25;}
[data-testid="stMetricValue"] {font-size: clamp(18px, 1.55vw, 26px); line-height: 1.25; font-weight: 650; color: var(--sh-ink);}
[data-testid="stMetricDelta"] {font-size: 11.5px;}
[data-testid="stMetricDelta"] div {white-space: normal !important; overflow: visible !important; text-overflow: clip !important;}
[data-testid="stMetricChart"] {height: 28px !important; overflow: hidden; margin-top: 2px;}
[data-testid="stMetricChart"] svg {height: 28px !important; width: 100%;}
.kgroup {font-size: 10.5px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: var(--sh-muted); display: flex; align-items: center; gap: 6px; margin: 0 0 -2px 2px;}
.kgroup i {display: inline-block; width: 8px; height: 8px; border-radius: 2px;}

/* Moi bieu do va bang co tieu de nam trong mot o trang rieng */
[data-testid="stColumn"]:has(> [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"] .ct) {background: var(--sh-card); border: 1px solid var(--sh-line); border-radius: 10px; padding: 8px 10px 6px 10px; box-shadow: var(--sh-shadow);}
.ct {font-size: clamp(12px, 0.95vw, 15px); font-weight: 600; line-height: 1.25; margin: 0 0 0 2px; color: var(--sh-ink);}
.cs {font-size: clamp(10.5px, 0.8vw, 12.5px); font-weight: 400; color: var(--sh-muted); line-height: 1.25; margin: 0 0 0 2px;}
p.note {font-size: 12px !important; color: var(--sh-muted); line-height: 1.3; margin: 0;}
.tbl {overflow: auto; max-width: 100%; border: 1px solid var(--sh-line); border-radius: 8px;}
.tbl table {width: 100%; border-collapse: collapse; font-size: clamp(11px, 0.88vw, 13.5px); font-variant-numeric: tabular-nums;}
.tbl th {position: sticky; top: 0; background: #f6f8fb; color: var(--sh-muted); font-weight: 600; text-align: left; padding: 5px 8px; border-bottom: 1px solid var(--sh-line); white-space: nowrap;}
.tbl td {padding: 4px 8px; border-bottom: 1px solid #eef1f5; color: var(--sh-ink); white-space: nowrap;}
.tbl tr:last-child td {border-bottom: none;}
.tbl tbody tr:hover td {background: #f8fafc;}
.tbl .r {text-align: right;}
[data-testid="stMain"] iframe {width: 100% !important;}

/* Dieu khien */
[data-testid="stWidgetLabel"] {margin-bottom: 0; min-height: 0;}
[data-testid="stWidgetLabel"] p {font-size: 12px; color: var(--sh-muted);}
[data-testid="stSliderTickBar"] {display: none;}
[data-testid="stSlider"] [data-testid="stWidgetLabel"] {margin-bottom: 7px;}
.rec {background: var(--sh-blue-soft); border-radius: 8px; padding: 6px 10px; font-size: 13px; line-height: 1.35;}
.rec b {color: var(--sh-blue-ink);}
.flash {border-radius: 6px; padding: 2px 10px; font-size: 12.5px; line-height: 1.4; margin: 0;}
.flash.bad {background: #fdecec; color: #a32020;}
.flash.good {background: #eaf6ea; color: #006300;}
</style>
"""



# Nut toan man hinh nho o goc phai tren. Ma chay trong trang cha (nut nam ngoai iframe) va chi cai mot lan.
_FS_PARENT = (
    "(function(){if(document.getElementById('sh-fs'))return;"
    "var ON='<svg width=\"16\" height=\"16\" viewBox=\"0 0 16 16\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.6\"><path d=\"M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4\"/></svg>';"
    "var OFF='<svg width=\"16\" height=\"16\" viewBox=\"0 0 16 16\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"1.6\"><path d=\"M6 2v4H2M14 6h-4V2M10 14v-4h4M2 10h4v4\"/></svg>';"
    "var b=document.createElement('button');b.id='sh-fs';b.type='button';"
    "b.style.cssText='position:fixed;top:calc(10px + env(safe-area-inset-top,0px));right:14px;z-index:999990;width:32px;height:32px;"
    "border-radius:8px;border:1px solid #e1e5ec;background:#fff;box-shadow:0 1px 2px rgba(16,24,40,.06);cursor:pointer;"
    "display:flex;align-items:center;justify-content:center;color:#3b4452;padding:0;';"
    "function sync(){var on=!!document.fullscreenElement;b.innerHTML=on?OFF:ON;"
    "b.title=on?'Thoát toàn màn hình (Esc)':'Toàn màn hình';b.setAttribute('aria-label',b.title);}"
    "b.onclick=function(){if(document.fullscreenElement){document.exitFullscreen();}"
    "else if(document.documentElement.requestFullscreen){document.documentElement.requestFullscreen().catch(function(){"
    "b.title='Trình duyệt chặn toàn màn hình ở đây, hãy bấm F11';});}};"
    "document.addEventListener('fullscreenchange',sync);sync();document.body.appendChild(b);})();"
)
_FS_JS = (
    "(function(){var d=window.parent.document;if(d.getElementById('sh-fs-js'))return;"
    "var s=d.createElement('script');s.id='sh-fs-js';s.textContent=%r;d.head.appendChild(s);})();"
) % _FS_PARENT


def fullscreen_button():
    """Cai nut toan man hinh. Goi trong sidebar de iframe rong khong chiem cho cua noi dung."""
    st.iframe(f"<script>{_FS_JS}</script>", height=1)


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



def kgroup(col, text, color):
    """Nhan nhom cho mot cum the KPI."""
    col.markdown(f'<div class="kgroup"><i style="background:{color}"></i>{html.escape(text)}</div>', unsafe_allow_html=True)


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


def _cell(x):
    """Dinh dang mot o bang kieu Viet Nam."""
    if x is None or (not isinstance(x, str) and pd.isna(x)):
        return "—"
    if isinstance(x, bool):
        return "Có" if x else "Không"
    if isinstance(x, (int,)) or (isinstance(x, float) and float(x).is_integer()):
        return num(x)
    if isinstance(x, float):
        return num(x, 2 if abs(x) >= 1 else 3)
    try:
        import numpy as np
        if isinstance(x, np.integer):
            return num(int(x))
        if isinstance(x, np.floating):
            return _cell(float(x))
    except ImportError:
        pass
    return str(x)


def table(df: pd.DataFrame, height=200):
    """Bang HTML co dau bang dinh, cuon trong khung. Ve bang DOM thuong nen dung ti le khi trang thu nho."""
    num_cols = {c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])}
    head = "".join(f'<th class="{"r" if c in num_cols else ""}">{html.escape(str(c))}</th>' for c in df.columns)
    rows = "".join("<tr>" + "".join(f'<td class="{"r" if c in num_cols else ""}">{html.escape(_cell(v))}</td>' for c, v in zip(df.columns, row)) + "</tr>"
                   for row in df.itertuples(index=False, name=None))
    st.markdown(f'<div class="tbl" style="max-height:{int(height)}px"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>',
                unsafe_allow_html=True)
