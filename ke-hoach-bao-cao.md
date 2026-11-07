# Kế hoạch báo cáo BTL CO4031: Seller Health DW & DSS

**Đề tài:** Kho dữ liệu và hệ hỗ trợ quyết định chăm sóc người bán trên Olist
**Hạn nộp:** 23:59, 15/11/2026 (còn 9 ngày tính từ 06/11)
**Bám theo:** `đề warehouse.md` và `seller-health-dw-dss.md`

---

## 1. Kết quả thử trên dữ liệu thật

Script: `scripts/feasibility.py`. Kết quả: `evidence/feasibility.json`. Backtest chạy cho 5 mốc as-of từ 03/2018 đến 07/2018, không có rò rỉ dữ liệu tương lai.

Đây là bản thử nhanh bằng pandas, làm trước khi dựng hệ thống. Số đưa vào báo cáo lấy từ màn hình Kiểm chứng và `evidence/dss_evaluation.json`. Hai điểm đã đổi so với bảng dưới: kế hoạch DSS bao phủ GMV mất thấp hơn chọn theo GMV ở 4/5 tháng (trung bình 19% so với 25%), và AUC dự báo sụt GMV trên toàn bộ seller là 0,67–0,73.

| Điều cần biết | Kết quả đo | Ý nghĩa với thiết kế |
|---|---|---|
| Doanh thu có tập trung không | Gini 0,79; top 20% seller chiếm 82,5% GMV | Đúng như giả thuyết |
| Số seller đang hoạt động | 1.338–1.658 seller có bán trong 90 ngày (2018), không phải ~3.000 | Sửa con số trong bài toán |
| Không bán 45 ngày có phải đã rời bỏ không | ~31% seller rơi vào nhóm này mỗi tháng; 39–50% số đó bán lại sau đó (as-of 04/2017–01/2018) | Đây là **tạm ngừng**, chưa phải rời bỏ |
| Có bao nhiêu seller lớn ngừng bán | Chỉ 14–40 seller top 20% mỗi tháng; nhóm ngừng bán chỉ giữ 8–15% GMV | Nếu chỉ nhắm vào churn thì danh sách mỏng và ít tiền |
| Có bao nhiêu seller lớn bị sụt GMV | 78–133 seller top 20% mỗi tháng sụt quá 50% (2018) | Đây là mục tiêu đáng theo dõi hơn |
| Mô hình có hơn cách đơn giản không | Dự báo ngừng bán: AUC 0,80–0,84, sắp theo số ngày không bán đạt 0,77–0,80. Random Forest không hơn Logistic | Mô hình nhỉnh hơn một chút, Logistic là đủ |
| Chỉ số vận hành có giúp dự báo không | AUC gần như không đổi khi bỏ các chỉ số này | Dùng để **chọn hành động**, không dùng để dự báo |
| Danh sách DSS có hơn sắp theo GMV không | Cùng 50 cuộc gọi: 40–52% seller thật sự sụt GMV, sắp theo GMV chỉ 22–34%. Phần GMV mất nằm trong danh sách tương đương (27–37% so với 32–37%) | Lợi ích là **gọi trúng người hơn**, không phải bắt được nhiều tiền hơn |
| Có tách được lỗi trễ không | 72% đơn giao trễ cho khách có seller giao vận chuyển đúng hạn. Seller trễ hạn thì đơn trễ 20,8%, seller đúng hạn là 5,4% | **Phát hiện đáng giá nhất**: phạt theo tỷ lệ trễ tổng sẽ phạt oan |
| Review bị kéo xuống bởi đâu | Khách nhận trễ: ~2,27 điểm, dù ai gây ra. Seller trễ nhưng khách vẫn nhận đúng hẹn: 4,07. Cả hai đúng hạn: 4,31 | Phần lớn mức giảm do khảo sát gửi trước khi hàng tới: 70,2% review của đơn trễ được trả lời khi chưa nhận hàng (1,66 sao), trả lời sau khi nhận được 3,72 sao |
| Seller hay trễ có dễ sụt không | Seller trễ >30%: sụt 40%, ngừng bán 17%. Seller trễ ≤5%: sụt 30%, ngừng bán 9% | Chỉ là tương quan, không kết luận nhân quả |

Lưu ý về các số trên:

- "Sụt GMV" nghĩa là GMV 45 ngày tới thấp hơn 50% mức trung bình của 90 ngày trước. Chỉ số này có một phần do biến động tự nhiên.
- Tỷ lệ bán lại bị thiếu ở các mốc gần cuối dữ liệu, nên chỉ dùng các mốc đến 01/2018.
- Phần GMV mất ở mốc 06/2018 thấp hơn rõ so với sắp theo GMV (27% so với 36%).

### DSS có ý nghĩa ở đâu

Giá trị của DSS không nằm ở điểm dự báo churn, vì sắp theo số ngày không bán đã đạt gần như vậy. Giá trị nằm ở ba quyết định mà bảng xếp hạng GMV không trả lời được:

1. **Gọi ai trước:** cùng số cuộc gọi, trúng seller đang sụt nhiều hơn 1,2–1,8 lần so với sắp theo GMV.
2. **Làm gì với seller đó:** seller trễ khâu giao vận chuyển thì hỗ trợ vận hành; khâu vận chuyển trễ thì sửa tuyến hoặc lời hẹn, không phạt seller.
3. **Ngân sách có đáng không:** vì không có dữ liệu hiệu quả can thiệp, hệ thống cho thấy danh sách thay đổi ra sao khi giả định thay đổi, thay vì khẳng định "giữ được X BRL".

---

## 2. Những điểm cần sửa trong `seller-health-dw-dss.md`

| # | Hiện tại | Sửa thành | Lý do |
|---|---|---|---|
| 1 | `fact_order_fulfillment`: 1 dòng = 1 đơn, có cột seller | 1 dòng = 1 đơn × 1 seller | 1.277 đơn có nhiều seller |
| 2 | Lỗi seller suy từ `days_to_carrier` | Thêm `seller_late` = ngày giao vận chuyển > `shipping_limit_date` | Có sẵn hạn thật, không cần đoán |
| 3 | Nhãn "churn 45 ngày" | Đổi tên thành "tạm ngừng 45 ngày"; thêm mục tiêu "sụt GMV" | Gần một nửa quay lại |
| 4 | Train trên as-of trước 03/2018, test 03/2018 | Chỉ train trên as-of ≤ mốc test − 45 ngày | Nhãn của mốc 02/2018 kéo dài tới 18/03, gây rò rỉ |
| 5 | Ví dụ đơn A95 trạng thái `delivered` nhưng ngày giao "đợt sau" | Khi giả lập đợt nạp, che cả trạng thái và các mốc chưa xảy ra | CSV chỉ có trạng thái cuối cùng |
| 6 | Tối ưu ngân sách chọn có hoặc không | Mỗi seller chọn tối đa 1 hành động, mỗi hành động có chi phí riêng | Nếu chi phí bằng nhau, bài toán chỉ còn là lấy top N, không cần tối ưu |
| 7 | "GMV giữ lại được" là KPI | Báo cáo "GMV trong diện rủi ro" và dải kịch bản | Dữ liệu không có hiệu quả can thiệp thật |
| 8 | PostgreSQL, dbt, Docker | DuckDB, file SQL chạy theo thứ tự, Python | Máy chưa có các công cụ này và chỉ còn 9 ngày |
| 9 | 8 tình huống | Bắt buộc: 1, 2, 3, 7. Làm thêm nếu kịp: 4, 6. Bỏ: 5, 8 | Tập trung để làm sâu |
| 10 | Số liệu S01 trong ví dụ | Thay bằng một seller thật lấy từ kho | S01 là số minh họa, không được đưa vào báo cáo như kết quả |

`health_tier` SCD2 do chính hệ thống tính ra, vì nguồn không có lịch sử thay đổi của seller. Báo cáo phải ghi rõ điều này.

---

## 3. Dàn ý báo cáo

Đề không nêu thang điểm hay số trang. Số trang dưới đây chỉ là gợi ý; nên hỏi giảng viên nếu cần con số chính xác. Có thể tái dùng khung LaTeX trong `BTL_Data_Warehouse/main.tex`.

**Trang bìa:** tên đề tài, thành viên, link GitHub, link dữ liệu, link video (nếu thuyết trình qua video).

| Chương | Nội dung chính | Hình và bảng cần có | Đề (mục 1.1) | Chuẩn đầu ra | Trang |
|---|---|---|---|---|---|
| 1. Bài toán | Bối cảnh Olist, người dùng, 3 câu hỏi quyết định, KPI, vì sao chọn seller thay vì khách hàng (mua lại 3,12%) | Bảng người dùng → quyết định → đầu ra | Mục tiêu 1 | L.O.1.3 | 3–4 |
| 2. Cơ sở lý thuyết | DW, vai trò của DW trong DSS, mô hình đa chiều, các kiểu fact, SCD, MSS/DSS, 4 pha của Simon. Chỉ nêu phần có dùng | Sơ đồ vai trò DW–DSS | Nền tảng | L.O.1.1, 1.2, 2.1, 3.1, 3.2 | 4–5 |
| 3. Dữ liệu | Nguồn, quy mô, grain từng bảng, vấn đề chất lượng và cách xử lý, phát hiện khảo sát | Bảng số dòng và lỗi; biểu đồ GMV theo tháng; đường Lorenz | Mục tiêu 1 | L.O.2.2 | 4–5 |
| 4. Thiết kế kho | Kiến trúc nhiều lớp, galaxy schema, lý do chọn grain, role-playing date, SCD2, các phương án đã cân nhắc | Sơ đồ kiến trúc; sơ đồ sao; bảng dim/fact; bus matrix | Mục tiêu 2 | L.O.2.1, 2.2, 2.3 | 5–6 |
| 5. Quy trình ELT | Giải thích vì sao là ELT, giả lập nạp theo tháng, watermark, cập nhật accumulating snapshot, kiểm tra chất lượng, đối soát | Sơ đồ luồng; bảng `etl_log`; bảng đối soát raw → core | Mục tiêu 2, 3 | L.O.2.3 | 4–5 |
| 6. OLAP và giao diện | Truy vấn roll-up, drill-down, slice, dice, pivot; CUBE; hiệu năng; các trang dashboard | SQL mẫu; ảnh chụp giao diện | Mục tiêu 3 | L.O.2.3 | 4–5 |
| 7. DSS | Phân loại DSS, 4 pha Simon, các mô hình, bảng luật, tối ưu, what-if, ví dụ một seller từ đầu đến cuối | Sơ đồ DSS; bảng luật; công thức tối ưu; ảnh what-if | Mục tiêu 4 | L.O.3.2, 3.3, 4.1, 4.2 | 6–8 |
| 8. Đánh giá | Backtest theo thời gian, so với cách đơn giản, độ nhạy theo giả định, kiểm chứng số liệu dashboard | Bảng AUC và precision; biểu đồ độ nhạy | Mục tiêu 5 | L.O.4.2 | 3–4 |
| 9. Hạn chế và hướng phát triển | Dữ liệu cũ, giả lập, thiếu hiệu quả can thiệp, chỉ là tương quan; A/B test, nạp gần thời gian thực | | Mục tiêu 5 | | 1–2 |
| Phụ lục | Phân công, cách chạy, tài liệu tham khảo | Bảng đóng góp | Mục 1.3 | | 1–2 |

**Câu chốt của chương 8, theo số từ kho:** cùng số cuộc gọi, hệ thống gọi trúng seller đang sụt 44–64% so với 21–31% khi chọn theo GMV, đổi lại bao phủ ít GMV mất hơn ở 4/5 tháng (trung bình 19% so với 25%). Người dùng chỉnh được đánh đổi này bằng ngưỡng rủi ro.

---

## 4. Phân công đề xuất

Đề yêu cầu 2–3 người, mỗi người có vai trò rõ ràng và ai cũng phải thuyết trình.

| Vai trò | Phần code | Chương báo cáo | Phần thuyết trình |
|---|---|---|---|
| A: DW/ETL | `src/ingest`, `src/sql` | 3, 4, 5 | Dữ liệu và kho |
| B: DSS | `src/dss` | 7, 8 | DSS và đánh giá |
| C: Giao diện/BI | `src/app` | 1, 6 | Bài toán và demo |
| Cả nhóm | | 2, 9, phụ lục | Hỏi đáp |

Nhóm 2 người: gộp C vào A và B, trong đó người làm DSS làm trang DSS, người làm DW làm dashboard.

---

## 5. Lịch làm việc

| Ngày | Việc | Kết quả phải có |
|---|---|---|
| 06–07/11 | Setup; chốt các điểm ở mục 2; vẽ schema; **đăng ký thuyết trình trực tiếp hay video** | Repo chạy được; schema đã chốt |
| 07–09/11 | Nạp raw theo đợt; staging, core, mart; kiểm tra chất lượng | Chạy một lệnh dựng lại được toàn bộ kho; số liệu đối soát khớp |
| 08/11 | Viết chương 1, 2, 3 | Bản nháp |
| 09–11/11 | Điểm M1, M2, M3; bảng luật; tối ưu; what-if | `dss_recommendation` có dữ liệu cho mọi mốc as-of |
| 10–12/11 | Streamlit: 6 trang hoặc ít nhất 4 trang lõi | Demo đi hết một tình huống |
| 11–12/11 | Viết chương 4, 5, 6 | Bản nháp |
| 12–13/11 | **Chốt code**; chạy đánh giá cuối; chụp hình; viết chương 7, 8, 9 | Số liệu không đổi nữa |
| 13–14/11 | Soát báo cáo; làm slide; quay video nếu cần | PDF báo cáo và slide |
| 15/11 | Chạy lại từ đầu trên máy khác; đóng ZIP; nộp sớm, không chờ tới 23:59 | Đã nộp lên LMS |

Nếu thuyết trình qua video, video phải xong trước hạn nộp, vì link nằm trên bìa báo cáo. Nếu trực tiếp, các buổi là 19/11, 26/11 và 03/12, với 15 phút trình bày và 5 phút hỏi đáp.

**Thứ tự bỏ bớt nếu trễ:** tình huống 4 và 6 → trang "Hiệu quả khuyến nghị" gộp vào trang DSS → `fact_payment`. Không bỏ: backtest, what-if, SCD2 và đối soát số liệu.

---

## 6. Setup

Đã làm xong trên máy của m, các thành viên khác chạy theo `README.md`:

```powershell
.\setup.ps1      # tạo venv, cài thư viện, dựng kho và DSS, chạy test
.\run_app.ps1    # mở app
```

Code nằm trong workspace `olist_dw_dss`. Venv và database nằm ở `%LOCALAPPDATA%\seller_health`, ngoài OneDrive. Công cụ là DuckDB, Python, Streamlit, không cần PostgreSQL, Docker hay dbt. Hình cho báo cáo có sẵn ở `docs/diagrams/` và `evidence/screenshots/`, mô tả bảng ở `docs/data_catalog.md`.

---

## 7. Checklist hoàn thành

Bản đầy đủ theo từng lớp của hệ thống nằm trong `checklist-olist.md`.

### Kho dữ liệu và ETL
- [ ] Một lệnh dựng lại toàn bộ kho từ CSV
- [ ] Nạp được từng đợt theo tháng; chạy lại một đợt không tạo dòng trùng
- [ ] `etl_log` ghi đủ đợt, watermark, số dòng nạp và số dòng loại
- [ ] Đối soát khớp: số dòng và tổng tiền raw → core (tổng giá dòng hàng toàn bộ phải bằng nguồn)
- [ ] Không có giá trị trùng khóa hay khóa ngoại mồ côi; 775 đơn không có dòng hàng vẫn được tính
- [ ] Đơn nhiều seller không bị nhân đôi tiền
- [ ] Mỗi seller chỉ có 1 dòng `is_current`; khoảng hiệu lực SCD2 không chồng nhau
- [ ] Accumulating snapshot có mốc được cập nhật qua các đợt nạp
- [ ] Có đủ truy vấn cho 5 thao tác OLAP, kèm một truy vấn CUBE

### DSS
- [ ] Feature tại as-of chỉ dùng dữ liệu trước as-of; có test tự động kiểm tra
- [ ] Khoảng cách train–test ít nhất 45 ngày
- [ ] Mỗi khuyến nghị có hành động, lý do bằng chữ và số liệu đi kèm
- [ ] Đổi ngân sách, ngưỡng hoặc giả định hiệu quả thì danh sách thay đổi ngay
- [ ] Kết quả tối ưu không vượt ngân sách và số cuộc gọi
- [ ] Mọi giả định (chi phí, hiệu quả can thiệp) được ghi rõ là giả định, trên cả giao diện

### Giao diện
- [ ] Mở từ đầu chạy được, không lỗi, trên máy của ít nhất 2 thành viên
- [ ] Đổi as-of date thì mọi trang đổi theo
- [ ] Số KPI trên giao diện khớp truy vấn SQL kiểm chứng
- [ ] Demo đi được hết: phát hiện → xem chi tiết → khuyến nghị → what-if → xuất CSV

### Đánh giá
- [ ] Backtest nhiều mốc, so với luật đơn giản, số ngày không bán và sắp theo GMV
- [ ] Mọi số trong báo cáo lấy lại từ kho và lưu trong `evidence/`
- [ ] Nêu cả các tháng kết quả không tốt
- [ ] Phân tích độ nhạy theo giả định hiệu quả can thiệp

### Báo cáo và nộp bài (đề mục 5)
- [ ] Báo cáo PDF đủ các chương; mỗi chuẩn đầu ra trong Bảng 1 của đề có chỗ thể hiện
- [ ] Có bảng phân công và mức đóng góp
- [ ] `src/` có SQL, Python, frontend và ETL; GitHub truy cập được khi không đăng nhập
- [ ] `data/` có link và dữ liệu mẫu; link mở được
- [ ] Slide PDF
- [ ] Đã đăng ký hình thức thuyết trình; mọi thành viên đều trình bày
- [ ] Nếu làm video: 10–15 phút, mọi thành viên xuất hiện, hình và tiếng rõ, link trên bìa, đã thử mở ở chế độ không đăng nhập
- [ ] ZIP đã mở thử và kiểm tra lại, nộp LMS trước 23:59 ngày 15/11/2026
- [ ] Không có credentials hay file dữ liệu lớn trong repo

---

## 8. Việc cần chốt

1. Thuyết trình trực tiếp hay qua video?
2. Nhóm có 2 hay 3 người, và ai nhận vai trò nào?
3. Giảng viên có yêu cầu riêng về công cụ không (ví dụ có chấp nhận DuckDB thay vì một hệ quản trị dạng server)? Đề không quy định công cụ, nhưng nên hỏi vì báo cáo mẫu trong thư mục dùng Pentaho.
