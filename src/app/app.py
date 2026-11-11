"""Ung dung Seller Health. Chay: python -m streamlit run src/app/app.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from src.app.common import apply_css, q
from src.app.screens_bi import blame, overview, seller
from src.app.screens_dss import board, route_whatif, validation
from src.config import DB_PATH

st.set_page_config(page_title="Seller Health", layout="wide", initial_sidebar_state="collapsed")
apply_css()

if not DB_PATH.exists():
    st.error(f"Chưa có kho dữ liệu tại {DB_PATH}. Hãy chạy: python run_all.py")
    st.stop()

SCREENS = {"Tổng quan": overview, "Lỗi giao trễ": blame, "Chi tiết seller": seller, "Bảng kế hoạch": board,
           "What-if tuyến": route_whatif, "Kiểm chứng": validation}

SCREEN_NAMES = {
    "Tổng quan": "1. 📊 Tổng quan",
    "Lỗi giao trễ": "2. 🚚 Lỗi giao trễ",
    "Chi tiết seller": "3. 🔍 Chi tiết seller",
    "Bảng kế hoạch": "4. 🎯 Kế hoạch (DSS)",
    "What-if tuyến": "5. ⏱️ What-if tuyến",
    "Kiểm chứng": "6. 🧪 Kiểm chứng"
}

c1, c2, c3 = st.columns([1.1, 5, 1.5], vertical_alignment="center")
c1.markdown('<div class="brand">Seller Health<span>DSS Giữ chân người bán</span></div>', unsafe_allow_html=True)
screen = c2.radio("Màn hình", list(SCREENS), horizontal=True, label_visibility="collapsed", format_func=lambda s: SCREEN_NAMES.get(s, s))
asofs = [str(d)[:10] for d in q("SELECT DISTINCT as_of FROM dss.recommendation ORDER BY 1").as_of]
as_of = c3.select_slider("Hôm nay là ngày (as-of)", asofs, value="2018-07-01", format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
                         help="Tua thời gian: mọi màn hình chỉ thấy dữ liệu trước ngày này. Riêng Kiểm chứng dùng kết quả các tháng đã biết.")

SCREENS[screen](as_of)
