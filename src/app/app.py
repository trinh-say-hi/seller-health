"""Ung dung Seller Health. Chay: python -m streamlit run src/app/app.py"""
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from src.app.common import apply_css, fullscreen_button, q
from src.app.screens_bi import attention, seller
from src.app.screens_dss import board, route_whatif, validation
from src.config import current_db

st.set_page_config(page_title="Seller Health", layout="wide", initial_sidebar_state="collapsed")
apply_css()

if not current_db().exists():
    st.error(f"Chưa có kho dữ liệu tại {current_db()}. Hãy chạy: python run_all.py")
    st.stop()

# Streamlit danh cho nguoi ra quyet dinh: luong giu chan seller (Truong nhom Seller Success) va luong giao nhan (Quan ly van hanh).
# Theo doi KPI, OLAP, giao hang va ke hoach theo vung (chi doc, co RLS) nam o Power BI. Man Tong quan, Loi giao tre, Da chieu cu
# van con trong ma nguon nhung khong con tren menu. Xem docs/nguoi-dung-phan-quyen-va-ke-hoach-sua.md.
SCREENS = {"Cần chú ý": attention, "Chi tiết seller": seller, "Bảng kế hoạch": board, "Kiểm chứng": validation, "What-if tuyến": route_whatif}
LABELS = {"Cần chú ý": "1 · Cần chú ý tháng này", "Chi tiết seller": "2 · Chi tiết seller", "Bảng kế hoạch": "3 · Bảng kế hoạch",
          "Kiểm chứng": "4 · Kiểm chứng", "What-if tuyến": "What-if hẹn giao theo tuyến"}
# Luong, ten, cau hoi, muc tieu cua tung man hinh: hien trong sidebar, duoi danh sach man hinh
META = {
    'Cần chú ý': ('Giữ chân seller · 1/4', 'Nhận biết', 'Seller nào vừa rơi vào nhóm Nguy cơ và đáng lo nhất?',
                  "Đọc danh sách seller mới vào Nguy cơ, sắp theo GMV rủi ro. Bấm một dòng để mở hồ sơ seller đó."),
    'Chi tiết seller': ('Giữ chân seller · 2/4', 'Chẩn đoán', 'Seller này sụt ở đâu, lỗi ở khâu seller hay khâu vận chuyển?',
                        'Xem GMV theo tháng, số ngày ở khâu seller và khâu vận chuyển, lý do mô hình chấm rủi ro, và khuyến nghị.'),
    'Bảng kế hoạch': ('Giữ chân seller · 3/4', 'Lựa chọn', 'Với ngân sách và số suất tháng này, làm gì với ai?',
                      'Bộ tối ưu (MILP) đề xuất; đổi ràng buộc và giả định, kéo thẻ để chỉnh, lưu kịch bản để so sánh, rồi xuất CSV cho nhân viên.'),
    'Kiểm chứng': ('Giữ chân seller · 4/4', 'Theo dõi', 'Các tháng trước, danh sách đề xuất có trúng không, có nên tin không?',
                   'So DSS với cách chọn theo GMV trên 03–07/2018, và xem kế hoạch đổi bao nhiêu khi giả định đổi.'),
    'What-if tuyến': ('Giao nhận', 'Lựa chọn', 'Hứa thêm N ngày trên một tuyến thì tỷ lệ đơn trễ còn bao nhiêu?',
                      "Dành cho Quản lý vận hành. Chọn tuyến, kéo 'Hứa thêm (ngày)', đặt mục tiêu để biết cần hứa thêm bao nhiêu ngày."),
}


with st.sidebar:
    st.markdown('<div class="brand">Seller Health<span>DSS giữ chân người bán · Olist 2016–2018</span></div>', unsafe_allow_html=True)
    asofs = [str(d)[:10] for d in q("SELECT DISTINCT as_of FROM dss.recommendation ORDER BY 1").as_of]
    as_of = st.select_slider("Mốc as-of (hôm nay là ngày)", asofs, value="2018-07-01", format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
                             help="Tua thời gian: mọi màn hình chỉ thấy dữ liệu trước ngày này. Riêng Kiểm chứng dùng kết quả các tháng đã biết.")
    st.markdown('<div class="navgroup">Giữ chân seller · Seller Success</div>', unsafe_allow_html=True)
    screen = st.radio("Màn hình", list(SCREENS), label_visibility="collapsed", format_func=LABELS.get, key="screen")
    step, name, question, goal = META[screen]
    st.markdown(f'<div class="sidegoal"><span class="tb-step">{html.escape(step)}</span> <b>{html.escape(name)}</b><br>'
                f'<i>{html.escape(question)}</i><br><b>Mục tiêu:</b> {html.escape(goal)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidenote">Theo dõi KPI, OLAP, giao hàng và kế hoạch theo vùng: Power BI (powerbi/OlistSellerHealth.pbip).</div>',
                unsafe_allow_html=True)
    fullscreen_button()

SCREENS[screen](as_of)
