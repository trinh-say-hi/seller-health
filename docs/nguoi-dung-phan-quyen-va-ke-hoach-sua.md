# Người dùng, phân quyền và kế hoạch sửa giao diện

Ghi ngày 13/11/2026. Tài liệu này chốt **ai dùng gì để quyết định gì**, rồi quét từng thẻ của 5 màn Streamlit theo tiêu chí trong slide chương 5–8. Chưa sửa code: các mục "Đề xuất" là việc cần làm, mục 8 là thứ tự làm.

Quy ước: **Đã có** là đã chạy và kiểm tra; **Thiết kế** là mô tả trong báo cáo, chưa hiện thực.

---

## 1. Kết luận

- Hệ thống là một **Compound DSS** (chương 6, Holsapple & Whinston): phần **database-oriented** (kho + OLAP, Power BI) và phần **solver-oriented + rule-oriented** (mô hình, luật, MILP, Streamlit).
- Hai giao diện chỉ hợp lý khi có **hai nhóm người dùng khác nhau**. Vì vậy báo cáo phải bắt đầu từ người dùng và quyết định của họ, không bắt đầu từ công cụ.
- **Streamlit là sản phẩm chính**: chạy được ở mọi máy (Docker), chứa toàn bộ phần mô hình và ra quyết định. **Power BI là lớp bổ sung** cho người chỉ xem: OLAP server (MOLAP), phân quyền theo vùng (RLS).
- Màn OLAP của Streamlit **nên đưa lại vào menu**: đề yêu cầu OLAP, người chấm chạy Docker không có Power BI. Hai màn không trùng về học thuật: Streamlit là ROLAP (SQL trên DuckDB), Power BI là MOLAP (VertiPaq).

---

## 2. Người dùng và bài toán của từng người

Chương 5 yêu cầu xác định **chủ sở hữu vấn đề** (problem ownership) và **tiêu chí lựa chọn** (principle of choice). Mỗi vai trò dưới đây có đúng một loại quyết định.

| # | Vai trò | Quyết định của họ | Tần suất | Loại quyết định (ch.5) | Cần thông tin gì | Công cụ |
|---|---|---|---|---|---|---|
| R1 | **Ban điều hành marketplace** | Có tăng ngân sách hoặc nhân sự cho Seller Success không | Quý | Phi cấu trúc | Xu hướng GMV, rủi ro tăng bao nhiêu so với phần được xử lý | Power BI: KPI tháng, Kế hoạch đề xuất (toàn quốc) |
| R2 | **Quản lý vùng** (ví dụ Sudeste) | Vùng mình có vấn đề ở đâu, cần phối hợp với Seller Success về seller nào | Tháng | Bán cấu trúc | KPI, drill vùng → bang → danh mục, seller trong kế hoạch **của vùng mình** | Power BI, RLS theo vùng |
| R3 | **Trưởng nhóm Seller Success** (người ra quyết định chính) | Tháng này gọi ai, hỗ trợ ai, ai chỉ nhận email, trong ngân sách và số suất | Tháng | Bán cấu trúc | Seller mới vào Nguy cơ, vì sao, phương án tối ưu, thử kịch bản, mức tin cậy | Streamlit: Cần chú ý, Chi tiết seller, Bảng kế hoạch, Kiểm chứng |
| R4 | **Nhân viên chăm sóc seller** | Không ra quyết định, thực hiện danh sách | Tuần | Có cấu trúc | Danh sách seller, hành động, lý do | File CSV xuất từ Bảng kế hoạch |
| R5 | **Quản lý vận hành giao nhận** | Có nới ngày hẹn giao trên tuyến nào không, bao nhiêu ngày | Tháng/quý | Bán cấu trúc | Trễ do seller hay do vận chuyển, tỷ lệ trễ theo tuyến nếu hứa thêm N ngày | Power BI: Giao hàng; Streamlit: What-if tuyến |
| R6 | **Nhóm dữ liệu** | Kho có được phát hành không, mô hình có còn đáng tin không | Mỗi lần chạy | Có cấu trúc | Đối soát, test, AUC, độ nhạy | Dagster, màn Kiểm chứng |

Thay đổi so với hiện tại: **What-if tuyến thuộc về R5, không phải R3**. Trưởng nhóm Seller Success không có quyền đổi lời hẹn giao. Menu Streamlit đang xếp What-if tuyến là "bước 4" trong quy trình của R3, cần tách thành luồng riêng.

---

## 3. Phân quyền

### 3.1 Ma trận quyền

R = xem, W = sửa hoặc chạy, — = không có quyền.

| Tài nguyên | R1 | R2 | R3 | R4 | R5 | R6 | Trạng thái |
|---|---|---|---|---|---|---|---|
| Power BI: KPI tháng, OLAP | R toàn quốc | R **vùng mình** | R | — | R | R | Đã có (RLS 1 vùng làm mẫu) |
| Power BI: Giao hàng | R | R vùng mình | R | — | R | R | Đã có |
| Power BI: Kế hoạch đề xuất | R | R vùng mình | R | — | — | R | Đã có |
| Streamlit: Cần chú ý, Chi tiết seller, Kiểm chứng | — | — | R | — | — | R | Đã có, **chưa có đăng nhập** |
| Streamlit: Bảng kế hoạch (đổi ngân sách, giả định, kéo thả, lưu kịch bản) | — | — | **W** | — | — | R | Đã có, chưa có đăng nhập |
| Xuất CSV kế hoạch | — | — | W | R (nhận file) | — | — | Đã có |
| Streamlit: What-if tuyến | — | — | R | — | **W** | R | Đã có, chưa có đăng nhập |
| Dagster: chạy pipeline, quay lui bản kho | — | — | — | — | — | W | Đã có |
| `metrics.yml`, `catalog.yml`, tham số mặc định DSS | — | — | đề xuất | — | — | W | Đã có (qua git) |
| Đọc DuckDB trực tiếp | — | — | — | — | — | W | Đã có |

### 3.2 Hiện thực đến đâu (phải viết đúng như vậy trong báo cáo)

- **Power BI**: RLS lọc trên `dim_region`, lan qua `dim_seller` tới mọi fact và qua `kpi_monthly`. Đã kiểm bằng DAX dưới role "Quản lý vùng Sudeste": chỉ thấy Sudeste (2.287 seller, 8.236 dòng phiên bản SCD2 trong dim_seller), KPI khớp DuckDB. Các vùng khác là role cùng mẫu, chưa tạo. Khi đưa lên Power BI Service mới gán người dùng vào role.
- **Streamlit**: **không có đăng nhập**. Đây là công cụ cho một vai trò (R3), chạy trong mạng nội bộ; quyền kiểm soát bằng việc ai có đường dẫn. Không được viết là "Streamlit có phân quyền".
- **Kịch bản** lưu ở `%LOCALAPPDATA%\seller_health\scenarios.json`, theo máy, không chia sẻ được giữa nhiều người.

---

## 4. Luồng từ insight đến dữ liệu đến hành động

Hai luồng quyết định, mỗi bước ghi rõ màn hình, dữ liệu nguồn, kết quả ra. Bốn pha theo Simon (chương 5).

### Luồng A: giữ chân seller (chủ sở hữu R3)

| Pha | Câu hỏi | Màn hình | Dữ liệu | Kết quả ra |
|---|---|---|---|---|
| Nhận biết | Tháng này seller nào mới đáng lo? | Streamlit **Cần chú ý** (R2, R1 thấy bức tranh tổng ở Power BI KPI, Kế hoạch đề xuất) | `mart.seller_features`, `dss.recommendation` tại as-of | Danh sách seller mới vào Nguy cơ, sắp theo GMV rủi ro |
| Thiết kế | Seller này sụt vì đâu, nên can thiệp kiểu gì? | **Chi tiết seller** | `core.fact_seller_monthly`, `core.fact_order_seller`, hệ số mô hình | Chẩn đoán: lỗi ở khâu seller (→ hỗ trợ vận hành) hay giảm cầu (→ gọi) |
| Lựa chọn | Trong 2.000 BRL và 40 suất, làm gì với ai? | **Bảng kế hoạch** | `dss.scores`, tham số và giả định | Kế hoạch tối ưu (MILP), chỉnh tay, kịch bản đã so sánh, **file CSV** |
| Thực hiện, theo dõi | Kế hoạch có trúng không? | **Kiểm chứng** (Streamlit), **Kế hoạch đề xuất** (Power BI cho R1, R2) | `dss.eval_lists`, `dss.eval_auc`, `dss.sensitivity` | Điều chỉnh ngưỡng, ngân sách cho tháng sau |

### Luồng B: lời hẹn giao theo tuyến (chủ sở hữu R5)

| Pha | Câu hỏi | Màn hình | Dữ liệu | Kết quả ra |
|---|---|---|---|---|
| Nhận biết | Trễ tăng ở đâu? | Power BI **KPI tháng** (tỷ lệ trễ theo tháng hẹn) | `mart.kpi_monthly` | Tháng, vùng có trễ cao |
| Thiết kế | Trễ do seller hay do vận chuyển? | Power BI **Giao hàng** | `core.fact_order_seller` | 72% đơn trễ có seller đúng hạn, tức là lỗi chủ yếu ở khâu vận chuyển |
| Lựa chọn | Tuyến nào cần hứa thêm bao nhiêu ngày? | Streamlit **What-if tuyến** | `core.fact_order_seller`, `core.dim_route` | Số ngày cần hứa thêm theo tuyến để trễ ≤ mục tiêu |
| Theo dõi | Sau khi đổi, trễ có giảm không? | Power BI **Giao hàng** tháng sau | như trên | Thiết kế, dữ liệu Olist không có thay đổi chính sách thật để đo |

Điểm nối giữa hai luồng: nếu seller bị đánh dấu "VH kém" thì là luồng A (hỗ trợ seller); nếu trễ nằm ở vận chuyển thì là luồng B. Màn Chi tiết seller và trang Giao hàng phải dẫn người dùng sang đúng luồng.

---

## 5. Đối chiếu tiêu chí trong slide

| Tiêu chí | Nguồn | Hệ thống | Đánh giá |
|---|---|---|---|
| Interactive: đổi giả định, thử kịch bản | Ch.6 đặc tính 1 | Bảng kế hoạch: thanh trượt, Giả định, kéo thả, Kịch bản; What-if tuyến | **Đạt** |
| Adaptability | Ch.6 đặc tính 2 | Tham số và giả định đổi được; nhưng ngưỡng mặc định cố định trong code | Đạt một phần |
| Data handling từ kho | Ch.6 đặc tính 3 | Kho medallion, star schema, 26 đợt | **Đạt** |
| 4 phân hệ: dữ liệu, mô hình, giao diện, tri thức | Ch.6 đặc tính 4 | Dữ liệu: DuckDB; mô hình: logistic + MILP; giao diện: Streamlit, Power BI; tri thức: bảng luật và lý do bằng chữ | **Đạt** |
| Tích hợp OLAP, data mining, AI | Ch.6 đặc tính 5 | OLAP (ROLAP ở Streamlit, MOLAP ở Power BI), hồi quy logistic | **Đạt** |
| Security: access control | Ch.6 Data Management mục 6 | RLS ở Power BI; Streamlit chưa có đăng nhập | Đạt một phần, phải ghi rõ |
| Metadata quản lý | Ch.6 Data Management mục 4 | `catalog.yml`, COMMENT ON, `docs/data_catalog.md` | **Đạt** |
| Customization theo loại người dùng | Ch.6 UI subsystem | Hai giao diện cho hai nhóm; RLS | Đạt khi tài liệu này được đưa vào báo cáo |
| Phân loại DSS | Ch.6 | Compound DSS (database + solver + rule) | Cần viết vào báo cáo |
| 3 thành phần mô hình: biến quyết định, biến không kiểm soát, biến kết quả | Ch.7 mục 5 | Hành động mỗi seller / khả năng sụt, hiệu quả, chi phí / GMV giữ được, tiền, suất | Cần viết thành bảng trong báo cáo |
| Certainty, risk, uncertainty | Ch.7 mục 3 | Hiệu quả can thiệp là bất định nhưng đang dùng một con số | **Thiếu**: cần khoảng giá trị (Monte Carlo) hoặc ít nhất nói rõ là giả định |
| Sensitivity, what-if | Ch.7 tóm tắt | `dss.sensitivity`, đường ngân sách, What-if tuyến | **Đạt** |
| Simulation | Ch.7 mục 8 | Chưa có | **Thiếu** (Monte Carlo) |
| Influence diagram | Ch.7 mục 4 | Chưa có | **Thiếu**, vẽ cho báo cáo |
| Static vs dynamic model | Ch.7 mục 2 | Mỗi mốc as-of là một bài toán tĩnh; chuỗi mốc là động | Viết vào báo cáo |
| Model base management | Ch.7 mục 9 | `src/dss/` + `dss.default_params` + Dagster | Đạt một phần |
| 4 pha Simon, problem ownership, principle of choice | Ch.5 | Mục 2 và 4 của tài liệu này; principle of choice = tối đa GMV giữ được kỳ vọng | Cần viết vào báo cáo |
| Measuring outcomes | Ch.5 | Gọi trúng, bao phủ GMV mất, so với cách chọn theo GMV | **Đạt** |
| User buy-in, client participation | Ch.8 | Không có người dùng thật | Ghi là hạn chế |

---

## 6. Quét từng thẻ của 5 màn Streamlit

Ký hiệu cột "Kết luận": **Giữ**, **Sửa**, **Bỏ**, **Chuyển** (sang Power BI), **Thu gọn** (đưa vào mục mở rộng).

### 6.1 Cần chú ý tháng này (R3, pha Nhận biết của luồng A)

| Thành phần | Vai trò | Vấn đề | Kết luận |
|---|---|---|---|
| Dòng chữ đầu trang | Mốc đang đứng, nguồn số | Dài, nhắc tên file Power BI | Sửa: một câu "Mốc 01/07/2018 · tháng 06/2018 đã chốt" |
| Thẻ GMV | Bối cảnh doanh số | Trùng Power BI KPI; R3 không ra quyết định dựa trên GMV toàn sàn | Bỏ, thay bằng một dòng chữ bối cảnh |
| Thẻ Tỷ lệ đơn trễ hẹn | Bối cảnh giao hàng | Trùng Power BI; thuộc luồng B | Bỏ (gộp vào dòng chữ bối cảnh) |
| Thẻ Mới vào Nguy cơ | Câu trả lời chính của màn | — | Giữ |
| Thẻ GMV rủi ro 45 ngày | Quy mô vấn đề | Tổng tính trên **mọi** seller (479k), còn Bảng kế hoạch ghi "trên tổng 377.524" là chỉ seller vượt ngưỡng rủi ro. Hai "tổng" khác nhau, không ghi rõ | Sửa: thống nhất một định nghĩa, hoặc ghi rõ "toàn bộ seller" và "seller vượt ngưỡng" |
| Thẻ GMV rủi ro trong kế hoạch | Kế hoạch đủ tầm tới đâu | Không ghi đây là kế hoạch **mặc định**, có thể khác khi R3 chỉnh | Sửa nhãn: "trong kế hoạch đề xuất" |
| Thẻ Tiền đề xuất | — | Luôn bằng ngân sách, không thêm thông tin | Bỏ |
| Thẻ Seller cần xử lý | Khối lượng việc | — | Giữ |
| Bảng 70 seller mới vào Nguy cơ | Danh sách hành động | (1) Hạng "Nguy cơ" do luật, "Đề xuất" do mô hình + MILP: nhiều seller Nguy cơ có Đề xuất "Chưa xử lý" mà không giải thích; (2) cột Lý do bị khuất; (3) sắp theo GMV 90 ngày, trong khi kế hoạch ưu tiên theo GMV rủi ro; (4) không bấm được sang Chi tiết seller | Sửa: thêm cột "Vì sao chưa xử lý" (dưới ngưỡng rủi ro / không thuộc top giá trị / hết ngân sách), sắp theo GMV rủi ro, cho Lý do xuống dòng, bấm dòng mở Chi tiết seller |
| Biểu đồ phân bố hạng | Bối cảnh | Không dẫn tới hành động; là số liệu theo dõi | Chuyển sang Power BI (trang Kế hoạch đề xuất hoặc KPI) |
| Biểu đồ GMV rủi ro theo hành động | Cho thấy ngân sách chỉ chạm phần nhỏ | Trùng ý với thẻ GMV rủi ro trong kế hoạch | Giữ, có thể chuyển sang Bảng kế hoạch |

### 6.2 Chi tiết seller (R3, pha Thiết kế)

| Thành phần | Vai trò | Vấn đề | Kết luận |
|---|---|---|---|
| Chọn seller (theo thứ tự ưu tiên) | Đi từ danh sách | Không nhận seller từ màn Cần chú ý | Sửa: nhận seller được chọn ở màn trước |
| So với (trung vị toàn sàn) | Chuẩn so sánh | — | Giữ |
| Thẻ Hạng tháng + Hạng ổn định | Tình trạng seller | Hai thẻ hạng gây rối; khác nhau là chi tiết kỹ thuật (SCD2) | Sửa: một thẻ "Hạng" (ổn định), hạng tháng để ở dòng phụ |
| Thẻ GMV 90 ngày | Quy mô | — | Giữ |
| Thẻ Khả năng sụt GMV | Đầu vào quyết định | — | Giữ |
| Thẻ Khả năng tạm ngừng | Tham khảo | `metrics.yml` ghi không tham gia quyết định | Bỏ (hoặc đưa vào dòng phụ) |
| Thẻ Điểm vận hành 82/100 | Tham khảo | Mâu thuẫn tín hiệu: seller trong ảnh bị gắn "VH kém" (18% giao trễ) mà điểm vẫn 82 | Bỏ |
| Ô Khuyến nghị | Kết luận cho người dùng | Tốt; mã seller đầy đủ dài | Giữ, rút gọn mã |
| GMV theo tháng | Sụt từ khi nào | — | Giữ |
| Ngày ở khâu seller và khâu vận chuyển | Chẩn đoán lỗi thuộc luồng A hay B | Chưa có câu kết luận dẫn sang What-if tuyến khi lỗi ở vận chuyển | Sửa: thêm câu dẫn |
| Bảng so với trung vị | Đối chiếu | Cột "So với" khó hiểu | Sửa tiêu đề cột: "Trung vị toàn sàn" |
| Lịch sử hạng (SCD2) | Minh họa kho | Người dùng không cần; giá trị cho báo cáo | Thu gọn |
| Vì sao rủi ro (log-odds) | Giải thích mô hình (phân hệ tri thức) | Thuật ngữ "log-odds"; yếu tố đứng đầu là "số đơn 90 ngày = 349 đẩy lên mạnh nhất", khó hiểu với người dùng | Sửa: 3 lý do bằng chữ, biểu đồ để ở mục mở rộng |
| Theo tháng kèm hồ sơ sức khỏe (mini-dimension) | Minh họa kho | Trùng với GMV theo tháng; giá trị cho báo cáo | Thu gọn |

### 6.3 Bảng kế hoạch (R3, pha Lựa chọn) — trung tâm của DSS

| Thành phần | Vai trò | Vấn đề | Kết luận |
|---|---|---|---|
| Thanh trượt Ngân sách, Số suất | Ràng buộc nguồn lực (biến không kiểm soát) | — | Giữ |
| Thanh trượt Ngưỡng rủi ro, Giá trị cao: top | Tham số luật | Người dùng không biết đổi để làm gì | Sửa: dòng giải thích ngắn khi rê chuột |
| Nút Giả định | Chi phí, hiệu quả (giả định) | Chưa có khoảng bất định; chưa ghi nguồn của mỗi con số | Sửa: ghi "giả định, không có số đo" cạnh từng ô; thêm Monte Carlo (mục 8) |
| Nút Đặt lại, Kịch bản | Thử và so sánh phương án | Kịch bản lưu theo máy | Giữ, ghi hạn chế |
| Thẻ Tiền đã dùng | Biến kết quả | — | Giữ |
| Thẻ Suất đã dùng | Biến kết quả | — | Giữ |
| Thẻ GMV rủi ro trong kế hoạch | Biến kết quả | "trên tổng 377.524" khác định nghĩa với màn Cần chú ý | Sửa (cùng mục 6.1) |
| Thẻ Giữ được (giả định) | Mục tiêu tối ưu | Một con số duy nhất trong khi đầu vào là giả định | Sửa: thêm khoảng P10–P90 sau Monte Carlo |
| Đường ngân sách | Độ nhạy theo ngân sách | Không nói vì sao phẳng (số suất đã chạm trần) | Sửa: câu giải thích |
| Kanban 4 cột | Chỉnh tay quyết định | Chỉ hiện tối đa 45 thẻ, số trên cột Email là 4 trong khi thật có 1.233 seller email: đọc sai | Sửa: "4 trên bảng / 1.233" |
| Khung chi tiết thẻ | Xem nhanh | — | Giữ |
| Xuất CSV | Chuyển giao cho R4 (pha Thực hiện) | Chưa có cột lý do, người phụ trách | Sửa: thêm lý do, ngày as-of |
| (chưa có) Chốt kế hoạch | Khép vòng sang Power BI | — | Thêm nếu còn thời gian |

### 6.4 What-if tuyến (R5, pha Lựa chọn của luồng B)

| Thành phần | Vai trò | Vấn đề | Kết luận |
|---|---|---|---|
| Vị trí trong menu | — | Đang là "bước 4" của R3 | Sửa: tách nhóm "Giao nhận" riêng trong menu |
| Chọn tuyến, Hứa thêm, Mục tiêu | Biến quyết định và mục tiêu | — | Giữ |
| Thẻ Đơn lịch sử | Độ tin cậy | — | Giữ |
| Thẻ Tỷ lệ trễ, Lời hẹn TB, Cần hứa thêm | Biến kết quả | — | Giữ |
| Đường tỷ lệ trễ theo số ngày hứa thêm | What-if | Giả định thời gian giao không đổi đã ghi | Giữ |
| Bảng tuyến nhiều đơn trễ nhất | Ưu tiên tuyến | Cột "Đơn trễ, seller đúng hạn" là bằng chứng vận chuyển, chưa nói ra | Sửa: tiêu đề phụ nêu ý này |
| (thiếu) Đánh đổi | Ch.7: hứa dài hơn có thể mất đơn | Không đo được từ dữ liệu | Ghi hạn chế, không claim |

### 6.5 Kiểm chứng (R3 và R6, pha Theo dõi)

| Thành phần | Vai trò | Vấn đề | Kết luận |
|---|---|---|---|
| 4 thẻ gọi trúng, bao phủ GMV mất | Measuring outcomes (ch.5) | — | Giữ |
| Hai đường theo tháng | So DSS với cách chọn theo GMV | — | Giữ |
| Tán xạ "Năm cách chọn 50 seller" | Đặt DSS cạnh các cách đơn giản | — | Giữ |
| Bảng AUC | Chất lượng mô hình | Dành cho R6, thuật ngữ khó | Thu gọn |
| Bảng độ nhạy | Sensitivity (ch.7) | — | Giữ |
| Chất lượng kho dữ liệu | Độ tin cậy dữ liệu | Thuộc R6; Dagster đã hiển thị | Thu gọn thành một dòng "Kho đạt 127/127 test, 286/286 đối soát" |

### 6.6 Màn OLAP (đang ẩn)

| Kết luận | Lý do |
|---|---|
| Đưa lại vào menu, nhóm "Khám phá dữ liệu" | Đề yêu cầu OLAP; người chấm chạy Docker không có Power BI; ROLAP (Streamlit) và MOLAP (Power BI) là cặp so sánh cho chương 3 |

---

## 7. Những câu được claim và không được claim

**Được claim** (đã có số chứng minh):
- Kho nạp 26 đợt theo tháng, mỗi đợt che dữ liệu tương lai và đối soát giữa các lớp; 127/127 test hệ thống.
- Số trên Power BI khớp DuckDB từng tháng, cả toàn sàn và dưới role Sudeste.
- Trên 03–07/2018, cùng số seller, DSS gọi trúng 55% so với 26% khi chọn theo GMV; nhưng bao phủ GMV mất 19% so với 25%.
- 72% đơn trễ có seller đúng hạn.

**Không được claim**:
- "Giữ được X BRL": là giả định, chưa đo.
- "Streamlit có phân quyền": chưa có đăng nhập.
- "Hệ thống làm seller quay lại": không có nhóm đối chứng.
- "Mô hình dự báo tốt": AUC 0,67–0,73 chỉ nhỉnh hơn dùng số ngày không bán.

---

## 8. Thứ tự làm (hạn 15/11)

| Ưu tiên | Việc | Ước lượng |
|---|---|---|
| 1 | Báo cáo: mục 2, 3, 4, 5, 7 của tài liệu này; bảng 3 loại biến (ch.7); phân loại Compound DSS; ROLAP vs MOLAP | lớn nhất |
| 2 | Streamlit: đưa OLAP lại menu, tách nhóm Giao nhận, bỏ 5 thẻ thừa (GMV, Tỷ lệ trễ, Tiền đề xuất ở Cần chú ý; Khả năng tạm ngừng, Điểm vận hành ở Chi tiết seller) | nhỏ |
| 3 | Streamlit: thống nhất "tổng GMV rủi ro", số trên cột Kanban, cột "Vì sao chưa xử lý" | vừa |
| 4 | Power BI: các mục đã ghi ở mục 10 của `checklist-olist.md` (thời gian, tên thẻ, tiêu đề) | vừa |
| 5 | Monte Carlo cho hiệu quả can thiệp, hiện khoảng P10–P90 ở thẻ Giữ được | vừa |
| 6 | Thu gọn các phần minh họa kho (SCD2, mini-dimension, AUC) vào mục mở rộng | nhỏ |
| 7 | Slide, video | lớn |
| Sau hạn | Đăng nhập cho Streamlit, chốt kế hoạch sang Power BI, cây phân rã và tán xạ ở trang OLAP Power BI | — |
