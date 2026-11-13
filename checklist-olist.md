# Checklist hệ thống Seller Health (Olist)

**Đã chốt:** Olist · DuckDB · chạy local · 6 màn hình · UI kéo thả
**Hạn nộp:** 23:59, 15/11/2026

Dấu `[x]` chỉ dùng khi đã chạy và kiểm tra thật.

**Trạng thái 07/11/2026:** xong bước 1–3 của kế hoạch nâng cấp. 126/126 test hệ thống, 102/102 trường hợp màn hình × as-of và bộ lọc, 49/49 test trình duyệt đạt. Còn lại: sửa DSS, Funnel, GitHub, thử trên máy khác, báo cáo, slide, thuyết trình.

---

## 0. Chuẩn bị

- [x] Tải Olist và Marketing Funnel (chi can de mo rong chua can ngay) bằng Kaggle CLI
- [x] Chốt đề tài, chốt venv và database ở `%LOCALAPPDATA%\seller_health`
- [x] `setup.ps1`, `run_app.ps1`, `.gitignore`
- [x] Dựng lại trên venv sạch
- [ ] `git init` và repo GitHub
- [ ] Hỏi giảng viên có chấp nhận DuckDB không

## 1. Bronze và nguồn

- [x] `data/manifest.json`: hash và số dòng 9 file; file bị đổi thì dừng ngay
- [x] 9 bảng raw giữ nguyên dữ liệu, thêm `dwh_batch`, `dwh_loaded_at`, `dwh_source_file`, `dwh_row_hash`
- [x] Số dòng khớp nguồn; `raw.orders` có 137.236 phiên bản cho 99.441 đơn
- [x] Đợt tháng che các mốc chưa xảy ra; review đến theo lúc khách trả lời
- [x] Chạy lại đợt không tạo dòng trùng; watermark bỏ qua đợt đã nạp

## 2. Silver

- [x] Làm sạch tên thành phố seller và khách, giữ tên gốc
- [x] Bỏ dấu ở geolocation; tọa độ ngoài Brazil vào cách ly
- [x] Bổ sung 2 bản dịch danh mục
- [x] Master là bảng, giao dịch là view
- [x] `ops.quarantine` có mã lỗi; `ops.dq_issue` ghi 19 quy tắc

## 3. Gold: core

- [x] `fact_order`, `fact_order_seller`, `fact_sales_item`, `fact_review`, `fact_payment`, `fact_seller_monthly`
- [x] `dim_location` nối vào fact; `dim_order_status`; `dim_seller_health`
- [x] SCD2 chỉ đổi khi hạng giữ 2 kỳ; từ 5,75 xuống 3,62 dòng mỗi seller
- [x] Tổng tiền 13.591.643,70; GMV hợp lệ 13.494.400,74; không nhân đôi
- [x] Thanh toán so với hàng + phí: 98.362 / 264 / 39
- [x] Không khóa ngoại mồ côi; 7 dimension tĩnh có khóa chính
- [ ] Khóa chính cho `dim_seller` và fact (DuckDB hạn chế xóa rồi ghi lại, hiện dùng test)

## 4. Gold: mart, OLAP, cổng chất lượng

- [x] `seller_features`, `seller_tier_monthly`, `kpi_monthly` (CUBE), `route_delivery`
- [x] 8 truy vấn OLAP có test
- [x] Cổng chất lượng: 11 phép mỗi đợt, 286/286 khớp, lệch thì dừng đợt
- [x] Đợt lỗi ghi `failed` và nội dung lỗi
- [ ] Rollback tự động (DuckDB crash khi `COMMIT` giao dịch lớn, đã ghi vào hạn chế)
- [ ] `mart.report_seller`

## 5. Tài liệu

- [x] `docs/data_catalog.md` tự sinh, 313/313 cột có mô tả
- [x] `docs/naming_conventions.md`, `docs/requirements.md`, `metrics.yml`
- [x] 4 sơ đồ trong `docs/diagrams/`
- [x] Cập nhật `docs/thiet-ke-he-thong.md`

## 6. DSS

- [x] Rủi ro sụt GMV và tạm ngừng, train cuốn, cách test ít nhất 45 ngày
- [x] Bảng luật, lý do bằng chữ, tối ưu MILP, what-if
- [x] Đánh giá tách giai đoạn chọn tham số; độ nhạy
- [ ] Ngưỡng riêng cho email (hiện 1.212/1.658 seller)
- [ ] Hiệu chỉnh xác suất hoặc hiện theo mức
- [ ] Dùng hoặc bỏ `ops_score`, `p_dormant`
- [ ] Đưa ma trận quy mô × chất lượng vào quyết định
- [ ] Marketing Funnel: `fact_seller_funnel`, làm giàu `dim_seller`

## 7. Giao diện

- [x] 6 màn hình vừa 1440 × 800, không cuộn, kể cả mốc as-of sớm nhất
- [x] Tab trên cùng, KPI có so sánh, sparkline, chú thích từ `metrics.yml`
- [x] Tiêu đề biểu đồ nêu kết luận, tự sinh
- [x] Lỗi giao trễ có phần review trước và sau khi nhận
- [x] Chi tiết seller so sánh được với trung vị hoặc seller khác
- [x] Bảng kéo thả: cuộn trong cột, số thẻ cập nhật, bấm thẻ xem chi tiết, vượt ràng buộc có cảnh báo, xuất CSV
- [x] What-if tuyến, Kiểm chứng
- [x] Số trên giao diện khớp SQL

## 8. Nghiệm thu toàn hệ thống

- [x] Chạy từ đầu trên venv sạch, gồm cả app
- [ ] Mở app trên máy của ít nhất 2 thành viên
- [ ] Nhóm tự đi hết một kịch bản bằng seller thật để chọn ví dụ cho báo cáo và demo

## 9. Báo cáo và nộp bài

Chi tiết các chương nằm trong `ke-hoach-bao-cao.md`.

- [ ] Báo cáo PDF; mỗi chuẩn đầu ra trong Bảng 1 của đề có chỗ thể hiện
- [ ] Có bảng phân công và mức đóng góp
- [x] `src/` có SQL, Python, frontend, ETL
- [ ] GitHub mở được khi không đăng nhập
- [x] `data/` có link và dữ liệu mẫu
- [ ] Slide PDF
- [ ] Đăng ký hình thức thuyết trình; mọi thành viên đều trình bày
- [ ] Nếu làm video: 10–15 phút, mọi thành viên xuất hiện, link trên bìa, đã thử mở khi không đăng nhập
- [ ] Không có credentials hay file lớn trong repo
- [ ] Đã mở thử ZIP và nộp LMS trước 23:59 ngày 15/11/2026

## 10. Power BI và Streamlit: việc còn treo (ghi 13/11/2026)

Người dùng, phân quyền, luồng insight → hành động và kết quả quét từng thẻ Streamlit: [docs/nguoi-dung-phan-quyen-va-ke-hoach-sua.md](docs/nguoi-dung-phan-quyen-va-ke-hoach-sua.md).

Nhánh `power-bi` (local, chưa push). Sửa file report thì phải đóng Power BI Desktop trước, vì Desktop lưu đè lên.

**Phần thời gian trên Power BI (đã chốt cách làm, chưa sửa):**
- [ ] Ô lọc thời gian đổi từ chỉ Năm sang cây Năm → Tháng (dropdown) ở trang KPI, OLAP, Giao hàng, Theo dõi kế hoạch
- [ ] Khóa khoảng 01/2017 – 08/2018 cho trang KPI, OLAP, Giao hàng (2016 quá ít đơn, 09–10/2018 dữ liệu đã hết nên GMV rơi về 0). Trang Theo dõi kế hoạch giữ nguyên vì as-of cuối là 01/09/2018
- [ ] Thêm ô "Kỳ đang xem" cạnh tiêu đề trang (không lọc: 01/2017 – 08/2018; bấm cột 2018-06: 06/2018)
- [ ] Đổi tên thẻ trang KPI: "GMV (chốt sổ)", "Số đơn (chốt sổ)", "Tỷ lệ trễ hẹn (chốt sổ)", "Đơn trễ (chốt sổ)"; bỏ chữ "tháng" gây hiểu nhầm
- [ ] Trục biểu đồ "Seller có bán theo tháng" đang hiện chữ "nghìn" mà mất số: tắt đơn vị hiển thị

**Lỗi thấy ở trang OLAP drill-down:**
- [ ] Ma trận địa lý đang mở thẳng ở cấp Thành phố (mất ngữ cảnh vùng, bang); phải mặc định ở cấp Vùng, bấm + mới xuống Bang, Thành phố
- [ ] Có một thanh cuộn xám ở giữa phần tiêu đề: ô tiêu đề thấp quá so với 2 dòng chữ, cần tăng chiều cao hoặc bỏ thanh cuộn

**Trình bày lại trang OLAP (đã chốt hướng, chưa làm):**
- [ ] Đổi tên trang thành "Doanh số dồn ở đâu?"; dòng phụ ghi "Số mới nhất của kho" (trang KPI ghi "Số chốt sổ từng tháng")
- [ ] Thay ma trận địa lý dài bằng cây phân rã (Decomposition Tree): GMV tách theo Vùng → Bang → Danh mục → Hạng, chỉ mở nhánh được bấm
- [ ] Thay bảng 71 danh mục bằng biểu đồ tán xạ: trục ngang GMV, trục dọc tỷ lệ trễ, cỡ chấm là số đơn, 2 đường kẻ trung bình chia 4 góc; góc phải trên là danh mục lớn mà hay trễ
- [ ] Nếu vẫn cần bảng: chỉ Top 10 kèm dòng "Khác", tô hồng đậm ô trễ trên 10%
- [ ] Giữ 4 thẻ số và bộ lọc; bộ lọc thời gian theo cây Năm → Tháng như các trang khác

**Ghi rõ khác biệt giữa trang KPI và OLAP (dòng phụ dưới tiêu đề):**
- [ ] KPI: "Số chốt sổ cuối mỗi tháng. Trễ hẹn xếp theo tháng hẹn giao, review theo tháng khách trả lời"
- [ ] OLAP: "Số mới nhất của kho. Trễ hẹn xếp theo tháng mua"
- [ ] Ghi chú trong báo cáo: với dữ liệu Olist chỉ review lệch giữa hai cách, vì 547 đơn có 2–3 review và 88 đơn có review sau đến ở tháng khác; điểm của đơn là trung bình các review nên đổi sau ngày chốt

**Lỗi và trình bày trang Giao hàng:**
- [ ] Dòng phụ bị cắt chữ và quá kỹ thuật ("dim_date đóng vai ngày nhận"): đổi thành "Xếp theo tháng khách nhận hàng"; tăng chiều cao ô tiêu đề, bỏ thanh cuộn xám
- [ ] Biểu đồ đường: đầu 2016 (seller trễ 87%) và cuối 09–10/2018 (trễ 100%) là tháng quá ít đơn, làm méo trục; áp khoảng 01/2017 – 08/2018
- [ ] Biểu đồ theo bang: đang xếp theo chữ cái, phải xếp từ cao xuống thấp; thêm số đơn đã giao vào tooltip để thấy bang ít đơn (AP, RR) không đáng tin; đặt nhãn % ở cuối thanh
- [ ] Thêm một dòng kết luận cạnh thẻ "Đơn trễ, seller đúng hạn": phần lớn trễ nằm ở khâu vận chuyển, xem What-if tuyến ở Streamlit

**Lỗi và trình bày trang Theo dõi kế hoạch:**
- [ ] Bộ lọc Năm vô nghĩa ở trang này: đổi thành chọn một mốc as-of (chọn đơn, mặc định mốc cuối 01/09/2018)
- [ ] Thẻ: gộp "Seller trong kế hoạch: 28 (22 gọi, 6 hỗ trợ)"; thêm thẻ "% GMV rủi ro được xử lý" (90k/444k ≈ 20%); "Tiền đã dùng" ghi đơn vị BRL và "/ 2.000"
- [ ] Bảng seller: đổi tên cột sang tiếng Việt (Seller, Vùng, Bang, Hành động, Khả năng sụt, GMV rủi ro), seller_id rút còn 8 ký tự như Streamlit, xếp theo GMV rủi ro giảm dần
- [ ] Đường: thêm dòng phụ "Rủi ro tăng gấp 2,5 lần (175k → 444k) nhưng ngân sách cố định nên phần được xử lý giữ quanh 50–140k"
- [ ] Dòng phụ bị cắt chữ, thanh cuộn xám ở tiêu đề (giống các trang khác)
- [ ] Cân nhắc: tên trang nói "theo dõi" nhưng mới chỉ hiện đề xuất. Có thể thêm phần "kết quả sau 45 ngày" (seller trong kế hoạch có thật sự sụt không) từ dss.eval_lists cho các mốc 03–07/2018, nhưng tránh trùng màn Kiểm chứng của Streamlit; hoặc đổi tên trang thành "Kế hoạch đề xuất"

**Chờ xem lại:**
- [ ] Xem 5 màn Streamlit (http://localhost:8502), ghi lỗi
- [ ] Gom mọi lỗi lại sửa một lần, chạy lại test_edges, test_system, đối chiếu DAX với DuckDB

**Để sau nếu còn thời gian:**
- [ ] Monte Carlo cho hiệu quả can thiệp
- [ ] Khép vòng: kế hoạch đã chốt ở Streamlit ghi ra Parquet để trang Theo dõi kế hoạch đọc
- [ ] Tham số `ThuMucParquet` đang ghi cứng đường dẫn máy này; ghi hướng dẫn đổi cho người chấm
- [ ] Push `dagster-dieu-phoi` và `power-bi`, mở PR vào `main`
