# Từ điển tên

Một khái niệm chỉ có một tên, dùng giống nhau trên app Streamlit, Power BI, file CSV xuất ra và báo cáo. Nhãn chỉ số lấy từ `metrics.yml` (dấu ? trên app hiện định nghĩa đầy đủ). Hai chỉ số khác định nghĩa thì phải khác tên: số chốt sổ cuối tháng có hậu tố "(chốt sổ)".

## Chỉ số

| Tên | Nghĩa ngắn | Nguồn |
|---|---|---|
| GMV (chốt sổ) | Tiền hàng đơn không hủy, chốt cuối tháng | `mart.kpi_monthly` |
| GMV | Tiền hàng đơn không hủy, số mới nhất | `core.fact_sales_item` |
| Số đơn (chốt sổ) / Số đơn | Đơn không hủy | như trên |
| Seller có bán | Seller có ít nhất 1 đơn trong tháng | `mart.kpi_monthly` |
| Số seller | Seller có bán trong lát cắt OLAP | `core.fact_sales_item` |
| Tỷ lệ trễ hẹn (chốt sổ) | Đơn trễ / đơn đến hạn, theo tháng hẹn giao | `mart.kpi_monthly` |
| Đơn trễ (chốt sổ) | Tử số của chỉ số trên | `mart.kpi_monthly` |
| Tỷ lệ trễ hẹn | Đơn trễ / đơn đến hạn, theo tháng mua | `core.fact_order_seller` |
| Review trung bình (chốt sổ) | Điểm review trả lời trong tháng | `mart.kpi_monthly` |
| Đơn đã giao | Đơn khách đã nhận | `core.fact_order_seller` |
| Trễ hẹn với khách | Khách nhận sau ngày hẹn | `core.fact_order_seller`; What-if hẹn giao tính lại khi hứa thêm N ngày |
| Seller giao vận chuyển trễ | Seller bàn giao cho vận chuyển sau hạn | `core.fact_order_seller`, `mart.seller_features` |
| Đơn trễ, seller đúng hạn | Trong đơn trễ, phần seller đúng hạn | `core.fact_order_seller` |
| Mới vào Nguy cơ | Seller vừa chuyển vào hạng Nguy cơ | `mart.seller_features` |
| Khả năng sụt GMV | Xác suất GMV 45 ngày tới dưới một nửa mức thường | `dss.scores`, `dss.recommendation` |
| GMV 90 ngày | GMV của seller trong 90 ngày trước as-of | `mart.seller_features` |
| GMV rủi ro 45 ngày | Khả năng sụt GMV × GMV 90 ngày ÷ 2 | `dss.recommendation` |
| GMV rủi ro trong kế hoạch | GMV rủi ro 45 ngày của seller được Gọi ngay hoặc Hỗ trợ vận hành | kế hoạch đề xuất hoặc đã chốt |
| % GMV rủi ro được xử lý | GMV rủi ro trong kế hoạch / GMV rủi ro 45 ngày | như trên |
| Seller trong kế hoạch | Số seller được Gọi ngay hoặc Hỗ trợ vận hành | như trên |
| Tiền đã dùng | Tổng chi phí hành động (BRL) | như trên |
| Suất đã dùng | Tổng suất nhân viên (Gọi ngay 1, Hỗ trợ vận hành 2) | app |
| Giữ được (giả định) | GMV rủi ro × hiệu quả giả định | app |
| Khoảng giữ được P10–P90 | Khoảng Monte Carlo của Giữ được (giả định) | `src/dss/simulate.py` |
| Gọi trúng / Bao phủ GMV mất | Kết quả kiểm chứng ngược | `dss.eval_lists` |

## Hành động (giá trị cột "Hành động")

Gọi ngay · Hỗ trợ vận hành · Email tự động · Chưa xử lý. Mã trong kho: CALL, OPS, EMAIL, NONE.

Cột "Lý do chưa gọi/hỗ trợ" trên app có 3 giá trị: Dưới ngưỡng rủi ro 30% · Ngoài top 20% GMV · Hết ngân sách/suất.

## Hạng

Hạng tháng (tính lại mỗi mốc) và Hạng ổn định (SCD2). Giá trị: Vàng · Ổn định · Ít đơn · Theo dõi · Nguy cơ · Tạm ngừng · Chưa hoạt động.

## Chiều

Seller (8 ký tự đầu của mã) · Vùng seller · Bang seller · Bang khách · Danh mục · Năm · Tháng · Mốc as-of.

## Kế hoạch

- **Kế hoạch đề xuất**: kế hoạch MILP với ngân sách và giả định mặc định, tính sẵn trong kho.
- **Kế hoạch đã chốt**: bản Trưởng nhóm bấm "Chốt kế hoạch" trên app (kể cả kéo tay).
- Power BI trang **Kế hoạch** dùng bản đã chốt nếu có (thẻ "Nguồn kế hoạch"), và khi chưa chọn mốc thì mở sẵn mốc vừa chốt gần nhất.
