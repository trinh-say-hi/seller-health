"""Ung dung Seller Health. Chay: python -m streamlit run src/app/app.py"""
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from src.app.common import apply_css, fit_to_page, q
from src.app.screens_bi import blame, overview, seller
from src.app.screens_dss import board, route_whatif, validation
from src.app.screens_olap import olap
from src.config import DB_PATH

st.set_page_config(page_title="Seller Health", layout="wide", initial_sidebar_state="collapsed")
apply_css()

if not DB_PATH.exists():
    st.error(f"Chưa có kho dữ liệu tại {DB_PATH}. Hãy chạy: python run_all.py")
    st.stop()

SCREENS = {"Tổng quan": overview, "Lỗi giao trễ": blame, "Chi tiết seller": seller, "Bảng kế hoạch": board, "What-if tuyến": route_whatif, "Kiểm chứng": validation, "Đa chiều": olap}
LABELS = {"Tổng quan": "1 · Tổng quan", "Lỗi giao trễ": "2 · Lỗi giao trễ", "Chi tiết seller": "3 · Chi tiết seller", "Bảng kế hoạch": "4 · Bảng kế hoạch (DSS)", "What-if tuyến": "5 · What-if tuyến", "Kiểm chứng": "6 · Kiểm chứng", "Đa chiều": "7 · Đa chiều (OLAP)"}
# Buoc, ten, cau hoi, muc tieu: hien o thanh tren cung cua tung man hinh
META = {
    'Tổng quan': ('Bước 1/6', 'Khám bệnh toàn sàn', 'Tháng này sàn có gì bất thường? Doanh số nào đang rủi ro?', "Xem 7 thẻ KPI, chú ý 'Mới vào Nguy cơ' và GMV có rủi ro, rồi xem vùng và danh mục giảm nhiều nhất."),
    'Lỗi giao trễ': ('Bước 2/6', 'Chẩn đoán nguyên nhân', 'Đơn trễ do seller giao chậm hay do khâu vận chuyển?', "Xem 'Đơn trễ, seller đúng hạn': tỷ lệ càng cao thì trễ càng nằm ở vận chuyển, nên xem chỉnh ngày hẹn ở Bước 5 trước khi xử lý seller."),
    'Chi tiết seller': ('Bước 3/6', 'Hồ sơ bệnh án seller', 'Seller này bị sụt giảm doanh số ở đâu và vì lý do gì?', 'Xem GMV theo tháng, số ngày ở khâu seller và khâu vận chuyển, so với trung vị toàn sàn, và lý do của khuyến nghị.'),
    'Bảng kế hoạch': ('Bước 4/6', 'Kế hoạch can thiệp (DSS)', 'Với ngân sách và số suất nhân sự tháng này, ta nên làm gì với ai?', 'MILP chọn tập seller có lợi ích kỳ vọng cao nhất trong ngân sách và số suất. Có thể kéo thẻ giữa các cột để điều chỉnh.'),
    'What-if tuyến': ('Bước 5/6', 'Giả lập đàm phán hẹn giao', 'Hứa thêm N ngày với khách hàng thì tỷ lệ đơn trễ trên tuyến giảm bao nhiêu?', "Chọn tuyến (ví dụ SP->CE), kéo 'Hứa thêm (ngày)' để xem tỷ lệ trễ thay đổi, và đặt 'Mục tiêu tỷ lệ trễ' để biết cần hứa thêm bao nhiêu ngày."),
    'Kiểm chứng': ('Bước 6/6', 'Kiểm chứng trên dữ liệu quá khứ', 'Các tháng trước, danh sách đề xuất trúng bao nhiêu so với chọn theo GMV?', 'So hai tiêu chí: DSS gọi trúng seller sụt giảm nhiều hơn, nhưng chọn theo GMV bao phủ nhiều GMV mất hơn ở phần lớn các tháng.'),
    'Đa chiều': ('Khám phá', 'Phân tích đa chiều (OLAP)', 'Số liệu dồn ở đâu, và đi sâu xuống tới từng seller thì thấy gì?', "Bấm vào một cột để đi sâu (drill-down), bấm tên cấp trên để quay lên (roll-up). Bộ lọc là slice/dice, 'Chia theo' là pivot."),
}

with st.sidebar:
    st.markdown('<div class="brand">Seller Health<span>DSS giữ chân người bán · Olist 2016–2018</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="navgroup">Màn hình</div>', unsafe_allow_html=True)
    screen = st.radio("Màn hình", list(SCREENS), label_visibility="collapsed", format_func=LABELS.get)
    st.markdown('<div class="sidenote">1–3: phát hiện vấn đề · 4–5: ra quyết định · 6: kiểm chứng · 7: tự khám phá dữ liệu.<br>'
                'Bấm « ở trên để thu gọn sidebar.</div>', unsafe_allow_html=True)
    fit_to_page()

step, name, question, goal = META[screen]
t1, t2 = st.columns([4.4, 1.6], vertical_alignment="center")
t1.markdown(
    f'<div class="topbar"><div class="tb-row"><span class="tb-step">{html.escape(step)}</span>'
    f'<span class="tb-title">{html.escape(name)}</span><span class="tb-q">{html.escape(question)}</span></div>'
    f'<div class="tb-goal"><b>Mục tiêu:</b> {html.escape(goal)}</div></div>', unsafe_allow_html=True)
asofs = [str(d)[:10] for d in q("SELECT DISTINCT as_of FROM dss.recommendation ORDER BY 1").as_of]
as_of = t2.select_slider("Hôm nay là ngày (as-of)", asofs, value="2018-07-01", format_func=lambda d: pd.Timestamp(d).strftime("%d/%m/%Y"),
                         help="Tua thời gian: mọi màn hình chỉ thấy dữ liệu trước ngày này. Riêng Kiểm chứng dùng kết quả các tháng đã biết.")

SCREENS[screen](as_of)
