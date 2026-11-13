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

# Streamlit lo pha thiet ke va lua chon cua quy trinh ra quyet dinh. Theo doi KPI, OLAP va giao hang (pha nhan biet, chi doc,
# co RLS) nam o Power BI; man Tong quan, Loi giao tre, Da chieu van con trong ma nguon nhung khong con tren menu.
SCREENS = {"Cần chú ý": attention, "Chi tiết seller": seller, "Bảng kế hoạch": board, "What-if tuyến": route_whatif, "Kiểm chứng": validation}
LABELS = {"Cần chú ý": "1 · Cần chú ý tháng này", "Chi tiết seller": "2 · Chi tiết seller", "Bảng kế hoạch": "3 · Bảng kế hoạch (DSS)",
          "What-if tuyến": "4 · What-if tuyến", "Kiểm chứng": "5 · Kiểm chứng"}
# Buoc, ten, cau hoi, muc tieu cua tung man hinh: hien trong sidebar, duoi danh sach man hinh
META = {
    'Cần chú ý': ('Bước 1/5', 'Cần chú ý tháng này', 'Seller nào vừa rơi vào nhóm Nguy cơ, GMV nào đang rủi ro, kế hoạch đề xuất xử lý bao nhiêu?',
                  "Đọc danh sách seller mới vào Nguy cơ có GMV lớn nhất, rồi mở Chi tiết seller với người đáng lo nhất."),
    'Chi tiết seller': ('Bước 2/5', 'Hồ sơ seller', 'Seller này bị sụt giảm doanh số ở đâu và vì lý do gì?',
                        'Xem GMV theo tháng, số ngày ở khâu seller và khâu vận chuyển, so với trung vị toàn sàn, và lý do của khuyến nghị.'),
    'Bảng kế hoạch': ('Bước 3/5', 'Kế hoạch can thiệp (DSS)', 'Với ngân sách và số suất nhân sự tháng này, ta nên làm gì với ai?',
                      'MILP chọn tập seller có lợi ích kỳ vọng cao nhất trong ngân sách và số suất. Có thể kéo thẻ giữa các cột để điều chỉnh.'),
    'What-if tuyến': ('Bước 4/5', 'Giả lập đàm phán hẹn giao', 'Hứa thêm N ngày với khách hàng thì tỷ lệ đơn trễ trên tuyến giảm bao nhiêu?',
                      "Chọn tuyến (ví dụ SP->CE), kéo 'Hứa thêm (ngày)' để xem tỷ lệ trễ thay đổi, và đặt 'Mục tiêu tỷ lệ trễ' để biết cần hứa thêm bao nhiêu ngày."),
    'Kiểm chứng': ('Bước 5/5', 'Kiểm chứng trên dữ liệu quá khứ', 'Các tháng trước, danh sách đề xuất trúng bao nhiêu so với chọn theo GMV?',
                   'So hai tiêu chí: DSS gọi trúng seller sụt giảm nhiều hơn, nhưng chọn theo GMV bao phủ nhiều GMV mất hơn ở phần lớn các tháng.'),
}

with st.sidebar:
    st.markdown('<div class="brand">Seller Health<span>DSS giữ chân người bán · Olist 2016–2018</span></div>', unsafe_allow_html=True)
    asofs = [str(d)[:10] for d in q("SELECT DISTINCT as_of FROM dss.recommendation ORDER BY 1").as_of]
    as_of = st.select_slider("Hôm nay là ngày (as-of)", asofs, value="2018-07-01", format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
                             help="Tua thời gian: mọi màn hình chỉ thấy dữ liệu trước ngày này. Riêng Kiểm chứng dùng kết quả các tháng đã biết.")
    st.markdown('<div class="navgroup">Màn hình</div>', unsafe_allow_html=True)
    screen = st.radio("Màn hình", list(SCREENS), label_visibility="collapsed", format_func=LABELS.get)
    step, name, question, goal = META[screen]
    st.markdown(f'<div class="sidegoal"><span class="tb-step">{html.escape(step)}</span> <b>{html.escape(name)}</b><br>'
                f'<i>{html.escape(question)}</i><br><b>Mục tiêu:</b> {html.escape(goal)}</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidenote">1–2: khoanh seller · 3–4: ra quyết định · 5: kiểm chứng. Theo dõi KPI, OLAP, giao hàng: Power BI.</div>',
                unsafe_allow_html=True)
    fullscreen_button()

SCREENS[screen](as_of)
