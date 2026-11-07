# Tổng hợp điểm mạnh, điểm yếu và kế hoạch khắc phục

> **Cập nhật 07/11/2026:** đã làm xong gói A, B, C, D và phần Medallion (bước 1–3). Còn lại gói E (sửa DSS) và F (Funnel, `report_seller`). Bản đánh giá dưới đây giữ nguyên để đối chiếu với hiện trạng trước khi nâng cấp. Tình trạng mới nhất nằm ở `checklist-olist.md`.

Đánh giá hệ thống Seller Health sau khi đối chiếu với 5 bài công khai. Số liệu về bài mình được đo trực tiếp trên kho ngày 06/11/2026. Số liệu của các bài khác do tác giả công bố; tao đọc tài liệu và một phần code, không chạy chúng.

Phân tích từng bài: `so-sanh-bai-mau-va-de-xuat.md`. Thiết kế hiện tại: `thiet-ke-he-thong.md`.

---

## 1. Kết luận

- **Điểm mạnh nhất:** quy trình theo thời gian và lớp quyết định. Về hai mặt này, bài mình đi xa hơn các bài đã xem.
- **Điểm yếu nhất:** mô hình còn thiếu vài bảng quan trọng, làm sạch dữ liệu ở lớp staging còn nông, và gần như chưa có tài liệu quy chuẩn trong kho.
- **Hướng sửa:** toàn bộ điểm yếu sửa được trong khoảng 4,5 ngày công (gồm giao diện và phần Medallion), không cần thêm công cụ nào.

---

## 2. Bài của DataWithBaraa dạy được gì

[DataWithBaraa/sql-data-warehouse-project](https://github.com/DataWithBaraa/sql-data-warehouse-project) là bài của một khóa học, dùng SQL Server và dữ liệu CRM/ERP, **không phải Olist**. Vì vậy không so được kết quả hay mô hình dữ liệu, chỉ học được về phương pháp.

| Nên học | Bài đó làm thế nào | Bài mình hiện tại |
|---|---|---|
| **Quy tắc đặt tên** | Có tài liệu riêng: snake_case, tiền tố `dim_`, `fact_`, `report_`, hậu tố `_key`, cột kỹ thuật `dwh_` | Có làm theo nhưng chưa viết thành văn; cột kỹ thuật lẫn lộn `_batch`, `first_batch` |
| **Data catalog** | Mô tả từng cột của lớp gold | **155 cột trong core và mart, không cột nào có mô tả trong kho** |
| **Sơ đồ** | Kiến trúc, lineage theo từng bảng, tích hợp, mô hình dữ liệu | Chỉ có sơ đồ chữ |
| **Thẻ mô tả từng lớp** | Mỗi lớp ghi rõ loại đối tượng, cách nạp, phép biến đổi, mô hình | Chỉ mô tả bằng văn xuôi |
| **Làm sạch ở lớp giữa** | Chuẩn hóa giá trị, sửa dữ liệu sai, cột suy diễn | **Nông, xem mục 4** |
| **Tích hợp nhiều nguồn** | Ghép CRM và ERP thành một dimension | **Chỉ có một nguồn** |
| **Lớp báo cáo** | Quy ước `report_`: bảng phẳng cho BI | Chưa có |
| **Nhật ký** | Thời gian theo từng bảng, bắt lỗi | Chỉ theo từng đợt; đợt lỗi không được ghi lại |
| **Tài liệu yêu cầu** | Trang riêng: mục tiêu, nguồn, phạm vi | Nằm rải rác |

| Không nên học | Lý do |
|---|---|
| Xóa hết rồi nạp lại | Mất lịch sử; bài đó ghi rõ không cần lịch sử, còn DSS của mình thì cần |
| Lớp gold chỉ là view, khóa `ROW_NUMBER` | Khóa có thể đổi khi dữ liệu đổi |
| Chỉ 1 fact, không SCD2 | Đơn giản hơn bài mình nhiều |
| Test phải chạy tay và đọc kết quả | Bài mình đã tự động |
| Lọc bỏ lịch sử sản phẩm | Ngược với việc cần lịch sử |

**Cách gọi tên lớp:** bài đó và nhiều bài khác dùng Bronze, Silver, Gold. Không cần đổi tên trong code, chỉ cần ghi ánh xạ trong báo cáo: `raw` = Bronze, `stg` = Silver, `core` + `mart` = Gold.

---

## 3. Điểm mạnh

| Điểm mạnh | Bằng chứng | So với các bài khác |
|---|---|---|
| **Biết đúng theo thời gian** | 26 đợt, feature đóng băng lúc chốt, đối chiếu từng seller với CSV khớp | Các bài khác nạp lại toàn bộ, hoặc chỉ giả lập vài đợt |
| **Đủ 3 kiểu fact** | Transaction, accumulating cập nhật qua đợt, periodic | Chưa bài nào đã xem có periodic snapshot |
| **SCD2 nối đúng thời điểm mua** | Test khoảng hiệu lực, fact trỏ đúng phiên bản | clnhrn cũng làm tốt; nhiều bài chỉ minh họa |
| **Lớp quyết định** | Mô hình, luật, tối ưu MILP, what-if, kéo thả, xuất CSV | Các bài khác dừng ở phân tích hoặc bản ghi nhớ |
| **Đánh giá tách giai đoạn** | Chọn tham số trên 09/2017–02/2018, báo cáo trên 03–07/2018 | Hiếm bài làm cho quyết định; TonyLee có làm |
| **Trung thực về giới hạn** | App tự liệt kê tháng DSS thua, giả định được ghi rõ | |
| **Kiểm thử đến giao diện** | 66 test hệ thống, 102 trường hợp màn hình, 30 test trình duyệt thật | Các bài khác nhiều test dữ liệu hơn, nhưng test giao diện ít khi có |
| **Dễ chạy** | Không Docker, 2 lệnh, dựng lại khoảng 2 phút | Nhiều bài cần Docker hoặc cloud |

---

## 4. Điểm yếu và cách khắc phục

### Mô hình dữ liệu

| # | Điểm yếu | Bằng chứng | Khắc phục |
|---|---|---|---|
| M1 | SCD2 dùng cho thuộc tính đổi quá nhanh | 52% lượt chuyển tháng đổi hạng, 5,75 dòng mỗi seller | Mini-dimension `dim_seller_health`; `dim_seller` chỉ đổi khi hạng giữ 2 tháng |
| M2 | Thiếu fact mức đơn | Đếm đơn dư khoảng 1% | Thêm `fact_order`; đổi tên thành `fact_order_seller` |
| M3 | Thiếu fact review | Không phân tích được thời điểm chấm, 789 `review_id` dùng cho nhiều đơn | Thêm `fact_review`, khóa `(review_id, order_id)` |
| M4 | `dim_geography` không nối với fact nào | Không drill được dưới mức bang | `dim_location`, thêm khóa vị trí vào fact |
| M5 | Một nguồn duy nhất, trong khi "tích hợp" là đặc tính đầu tiên của DW theo Inmon | Bộ Funnel đã tải nhưng chưa dùng | Tích hợp qua `seller_id`, xem mục 5 |
| M6 | Chưa có lớp báo cáo phẳng | | `mart.report_seller`: mỗi seller một dòng cho từng as-of |

### Chất lượng dữ liệu (mới phát hiện khi kiểm tra lại)

| # | Điểm yếu | Bằng chứng | Khắc phục |
|---|---|---|---|
| D1 | **Tên thành phố seller còn bẩn** | 25 seller có tên bất thường: `04482255`, `sao paulo / sao paulo`, `rio de janeiro \\rio de janeiro`; lỗi chính tả `sao pauo`, `sao paulop`. Tên `sp` và `são paulo` cũng chưa gộp | Lấy thành phố từ ZIP; ZIP không có thì chuẩn hóa và tách phần trước dấu `/` hoặc `-` |
| D2 | **Tên thành phố ở geolocation chưa bỏ dấu** | 8.011 tên khác nhau, còn 5.969 sau khi bỏ dấu | `strip_accents` trước khi lấy mode |
| D3 | **Tọa độ ngoài lãnh thổ Brazil** | 42 dòng, làm 8 ZIP có trung vị sai | Lọc theo khung tọa độ trước khi tính trung vị |
| D4 | Mâu thuẫn và thiếu giữa các nguồn chưa được ghi nhận | 35 seller khác bang với ZIP; 278 đơn và 7 seller có ZIP không có tọa độ; 6 đơn hủy có ngày giao; 13 sản phẩm thiếu bản dịch; 4 sản phẩm nặng 0 g | Thêm vào `ops.dq_issue`, bổ sung 2 bản dịch |

Các điểm này **chưa ảnh hưởng đến số GMV hay kết quả DSS**, vì chúng dùng bang chứ không dùng thành phố. Chúng ảnh hưởng tới hiển thị và drill-down dưới mức bang. Riêng D3 ảnh hưởng nhẹ tới vị trí bong bóng trên bản đồ.

### Kiểm thử và ràng buộc

| # | Điểm yếu | Khắc phục |
|---|---|---|
| T1 | Chưa khai báo PK, FK (0 ràng buộc trong core và mart); hiện chỉ dựa vào test | Khai báo PK ở các bảng cuối pipeline nếu DuckDB cho phép với cách nạp hiện tại, cần thử. FK vẫn giữ bằng test |
| T2 | Chưa có test thanh toán khớp hàng + phí (98.362 đơn khớp, 264 trả nhiều hơn, 39 trả ít hơn) | Thêm test, ghi rõ ngoại lệ trả góp |
| T3 | Chưa có test chống nhân dòng theo từng cột | Thêm test GMV giữ nguyên qua các lớp và chống nhân dòng |
| T4 | Đợt nạp lỗi không để lại log | Bắt lỗi, ghi `status = failed` và thông báo lỗi |
| T5 | Không kiểm tra hash của file nguồn khi nạp | So hash và header với file manifest |

### Tài liệu và quy chuẩn

| # | Điểm yếu | Khắc phục |
|---|---|---|
| Q1 | Không có data catalog | `COMMENT ON` cho bảng và cột, tự sinh `docs/data_catalog.md` từ kho nên không bị lệch |
| Q2 | Quy tắc đặt tên chưa viết ra, cột kỹ thuật chưa thống nhất | `docs/naming_conventions.md`; đổi về `dwh_batch`, `dwh_first_batch`... |
| Q3 | Thiếu sơ đồ | Tự vẽ 4 sơ đồ: kiến trúc kèm thẻ từng lớp, lineage theo bảng, star schema, luồng DSS. Sơ đồ lineage sinh từ danh sách bảng để khớp code |
| Q4 | KPI chỉ định nghĩa trong tài liệu | `metrics.yml`, giao diện đọc để hiện chú thích ⓘ |
| Q5 | Yêu cầu nằm rải rác | `docs/requirements.md`: người dùng, quyết định, nguồn, phạm vi, tiêu chí nghiệm thu |

### DSS

| # | Điểm yếu | Khắc phục |
|---|---|---|
| S1 | `ops_score` và `p_dormant` chỉ để hiển thị | Dùng `p_dormant` để phân nhóm "sắp dừng hẳn"; hoặc nói rõ, hoặc bỏ `ops_score` khỏi luận điểm |
| S2 | Nhóm email quá lớn (1.211/1.658 seller) | Ngưỡng riêng cho email |
| S3 | Xác suất chưa hiệu chỉnh | Hiệu chỉnh trên giai đoạn train, hoặc hiện theo mức Cao, Vừa, Thấp |
| S4 | Hạng seller không dùng cho quyết định | Ma trận quy mô × chất lượng, ổn định hơn |
| S5 | Diễn giải review chưa tính thời điểm khảo sát | **Đã sửa câu chữ.** Sau khi có `fact_review` thì đưa thành chỉ số trên màn Lỗi giao trễ |

### Giao diện

Theo hướng đã thống nhất ở `so-sanh-bai-mau-va-de-xuat.md`, mục 7: mỗi màn hình vừa 1440 × 900, tiêu đề nêu kết luận, KPI có so sánh, thẻ kéo thả cuộn trong cột.

---

## 5. Tích hợp bộ Marketing Funnel có đáng không

| Ưu | Nhược |
|---|---|
| Có **tích hợp hai nguồn thật** qua `seller_id`, đúng đặc tính cốt lõi của DW | Chỉ 842 seller ký, 380 có đơn |
| Thêm thuộc tính seller: `business_segment`, `lead_type`, `business_type` | Seller có deal chỉ chiếm khoảng 5% GMV |
| Thêm một quy trình nghiệp vụ: lead → ký hợp đồng → đơn đầu | 92% `has_company` trống, 95% `declared_monthly_revenue` bằng 0 |
| 275/1.658 seller đang hoạt động ở mốc 01/07/2018 có thông tin này | Ngày ký tới 11/2018, sau dữ liệu đơn, nên seller ký muộn bị cắt |

**Đề xuất:** làm ở mức vừa phải. Thêm `fact_seller_funnel` (grain một lead) và làm giàu `dim_seller`, nhưng **không đưa vào mô hình rủi ro** vì quá thiếu. Trên giao diện chỉ thêm một khối nhỏ. Việc này phục vụ thiết kế kho hơn là quyết định.

---

## 6. Kế hoạch nâng cấp

Công sức là ước tính của tao, chưa tính lúc phát sinh lỗi.

| Gói | Nội dung | Công sức | Vì sao |
|---|---|---:|---|
| **A. Làm sạch và mô hình** | D1–D4, M2, M3, M4, M1 | 1 ngày | Sửa điểm yếu thật, cần làm trước vì mọi thứ khác phụ thuộc |
| **B. Tin cậy** | T2–T5, T1 nếu được | 0,5 ngày | Thêm bằng chứng cho báo cáo |
| **C. Tài liệu hóa** | Q1–Q5 | 0,5 ngày | Lấy thẳng vào báo cáo |
| **D. Giao diện** | Khung mới, chú thích từ Q4 | 1 ngày | Cần có A và Q4 trước |
| **E. DSS** | S1–S5 | 0,5 ngày | Nâng tính hợp lý của quyết định |
| **F. Tích hợp Funnel** | M5, M6 | 0,5 ngày | Nên có, cắt được nếu trễ |

**Tổng khoảng 4,5 ngày, tính cả phần Medallion ở mục 7.** Nên chốt code trước 12–13/11 để còn thời gian viết báo cáo. **Thứ tự cắt nếu trễ:** F → E → T1.

Sau mỗi gói, toàn bộ test và số đánh giá phải chạy lại. Kết quả DSS có thể đổi, nên số trong tài liệu chỉ cập nhật sau khi xong gói A và E.

**Vẫn không nên làm:** dbt, Airflow, cloud, Terraform, phát hành theo phiên bản.

### Kiến trúc đích

| Lớp | Tên tương ứng | Loại | Cách nạp | Biến đổi | Mô hình |
|---|---|---|---|---|---|
| `raw` | Bronze | Bảng | Theo đợt, nối thêm, có phiên bản | Không, thêm `dwh_` | Như nguồn |
| `stg` | Silver | View | Không nạp | Ép kiểu, **làm sạch thành phố và tọa độ**, gộp, ghi lỗi | Như nguồn, đã sạch |
| `core` | Gold | Bảng | Theo đợt: thêm, cập nhật, SCD2 | Tích hợp, khóa thay thế, số đo | **Galaxy:** `fact_order`, `fact_order_seller`, `fact_sales_item`, `fact_review`, `fact_payment`, `fact_seller_monthly`, `fact_seller_funnel` |
| `mart` | Gold | Bảng | Đóng băng lúc chốt đợt | Tổng hợp, CUBE, feature | Bảng phẳng: `report_seller`, `kpi_monthly`, `route_delivery`, `seller_features` |
| `dss` | | Bảng | Sau khi nạp | Mô hình, luật, tối ưu | Kết quả theo as-of |
| `ops` | | Bảng | Mỗi lần chạy | | Log, lỗi, danh mục |

---

## 7. Medallion nâng cấp được gì

Medallion chỉ là cách chia lớp, không thay được mô hình Kimball. Kho đã đúng tinh thần này: `raw` là Bronze, `stg` là Silver, `core` + `mart` là Gold.

| Lớp | Nâng cấp |
|---|---|
| Bronze | Thêm `dwh_source_file`, `dwh_row_hash`, kiểm tra hash file nguồn |
| Silver | Vật chất hóa master đã sạch, cách ly có mã lỗi, cờ chất lượng |
| Gold | `fact_order`, `fact_review`, `dim_location` |
| Giữa các lớp | Cổng chất lượng `ops.layer_reconciliation`: lệch thì dừng đợt |

Không đổi tên schema, không thêm lớp Platinum, không dùng lakehouse hay streaming, không vật chất hóa toàn bộ giao dịch ở Silver.

---

## Nguồn

- [DataWithBaraa/sql-data-warehouse-project](https://github.com/DataWithBaraa/sql-data-warehouse-project)
- [NaderHani/Olist-E-commerce-Data-Warehouse](https://github.com/NaderHani/Olist-E-commerce-Data-Warehouse)
- [clnhrn/olist-warehouse](https://github.com/clnhrn/olist-warehouse)
- [TonyLee-99/marketplace-analytics](https://github.com/TonyLee-99/marketplace-analytics)
- [huy-dataguy/olist-sales-warehouse](https://github.com/huy-dataguy/olist-sales-warehouse)
