# So sánh bài mẫu Olist và đề xuất nâng cấp

Tài liệu này đối chiếu hệ thống Seller Health với các bài mẫu công khai trên cùng bộ dữ liệu, rồi đề xuất nên nâng cấp gì về kho dữ liệu và giao diện.

**Mức độ kiểm chứng:** tao đã đọc README, tài liệu thiết kế và một phần code của các bài này, nhưng **không chạy chúng**. Số liệu của họ là do tác giả công bố, trừ những chỗ ghi "đã đối chiếu".

---

## 1. Kết luận

| Câu hỏi | Trả lời |
|---|---|
| Kho của mình có đơn giản quá không? | **Không**, so với bài Nader thì sâu hơn hẳn. Nhưng so với 3 bài tốt nhất thì còn **4 điểm yếu về mô hình**, cần sửa |
| Có nên phức tạp hơn không? | **Nên sâu hơn ở mô hình dữ liệu và kiểm thử, không nên thêm hạ tầng.** Airflow, cloud, Terraform không giúp gì cho người dùng hay cho đề bài |
| Dashboard có nên làm lại không? | **Có.** Hiện mỗi màn hình phải cuộn nhiều. Nên làm mỗi màn hình vừa một khung hình, tiêu đề biểu đồ nêu luôn kết luận |
| Có phát hiện nào đổi kết luận cũ không? | **Có:** review thấp ở đơn trễ phần lớn do khảo sát được gửi trước khi hàng tới. Đã sửa trong app và tài liệu |

**Điểm mạnh riêng của bài mình:** chưa bài nào trong số đã đọc có đồng thời nạp giả lập nhiều đợt tháng, snapshot theo kỳ đóng băng đúng thời điểm, và lớp DSS tối ưu có kéo thả. Các bài kia chủ yếu dừng ở phân tích, trừ TonyLee có khuyến nghị dạng bản ghi nhớ.

---

## 2. Kho dữ liệu hiện tại

Chi tiết nằm ở `thiet-ke-he-thong.md`, mục 2–5.

```
CSV ─► raw ─► stg ─► core ─► mart ─► dss ─► app
       │                                
       └ giả lập 26 đợt tháng, watermark, chạy lại không trùng
```

| Lớp | Bảng | Ghi chú |
|---|---|---|
| **raw** | 9 bảng | Dữ liệu gốc dạng chữ; `raw.orders` có 137.236 phiên bản cho 99.441 đơn |
| **stg** | 9 view | Ép kiểu, dịch danh mục, gộp review, trung vị tọa độ |
| **core: dimension** | `dim_date` 1.827 · `dim_seller` 17.804 (SCD2) · `dim_customer` 96.097 · `dim_product` 32.952 · `dim_geography` 19.015 · `dim_route` 622 | Có dòng `-1` cho giá trị không rõ |
| **core: fact** | `fact_sales_item` 112.650 (transaction) · `fact_order_fulfillment` 100.785 (accumulating, đơn × seller) · `fact_seller_monthly` 25.487 (periodic) · `fact_payment` 103.886 (transaction) | Đủ 3 kiểu fact của Kimball |
| **mart** | `seller_features` 25.487 · `kpi_monthly` 4.726 (CUBE) · `route_delivery` 6.186 | Đóng băng lúc chốt đợt |
| **dss** | `labels`, `scores`, `recommendation`, `eval_*`, `sensitivity`, `model_coef` | |
| **ops** | `etl_log`, `rejected_row`, `dq_issue` | |

**Công nghệ:** DuckDB, SQL thuần chạy theo thứ tự, Python điều phối, Streamlit, 66 test hệ thống.

---

## 3. So sánh với các bài mẫu

| | **Bài mình** | [Nader](https://github.com/NaderHani/Olist-E-commerce-Data-Warehouse) | [clnhrn](https://github.com/clnhrn/olist-warehouse) | [TonyLee](https://github.com/TonyLee-99/marketplace-analytics) | [huy-dataguy](https://github.com/huy-dataguy/olist-sales-warehouse) |
|---|---|---|---|---|---|
| **Trọng tâm** | Quyết định chăm sóc seller | Pipeline cơ bản | Kỹ thuật dữ liệu kiểu sản phẩm | Phân tích kinh doanh | Vận hành kho |
| **Kho** | DuckDB | PostgreSQL | BigQuery, DuckDB | DuckDB | PostgreSQL |
| **Biến đổi** | SQL thuần | SQL thuần | dbt | dbt | dbt |
| **Điều phối** | Python | Airflow | Cloud Workflows | Make, CI | Airflow |
| **Mô hình** | 6 dim, 4 fact | 5 dim, 3 fact | 5 dim, 4 fact | 5 dim, 5 fact | 7 dim, 3 fact |
| **Fact mức đơn** | Đơn × seller | `dim_orders` (đơn nằm ở dimension) | `fact_orders` riêng | `fct_orders` riêng | `fct_orders` riêng |
| **Fact review** | **Không có** | Có, nhưng khóa `review_id` sẽ lỗi trùng | Có, khóa `(review_id, order_id)` | Có | Bỏ review |
| **Vị trí** | Theo bang | Không | `dim_location` theo ZIP, cả khách và seller | SCD2 địa chỉ khách | `dim_buyer_geography` |
| **SCD2** | Hạng seller, nối đúng thời điểm mua | Không | Seller, giả lập 20 seller chuyển bang | Địa chỉ khách, snapshot seller | Sản phẩm và seller |
| **Periodic snapshot** | **Có** | Không | Không | Không | Không |
| **Nạp theo đợt** | **26 đợt** | Nạp lại toàn bộ | 3 đợt giả lập | Dựng lại toàn bộ | Có `source_cut` |
| **Hợp đồng dữ liệu, cách ly** | Đơn giản | Không | **YAML theo phiên bản** | Kiểm tra hash, header | **Chặn cả đợt** |
| **Số test** | 66 + 102 + 30 | Không có | Có dbt tests, unit tests | 118 | 75 |
| **Định nghĩa KPI tập trung** | Chỉ trong tài liệu | Không | Semantic layer nhỏ | **`metrics.yml`, 17 KPI** | **MetricFlow, 8 KPI** |
| **Sơ đồ lineage** | Không | Không | dbt | dbt | dbt |
| **Dashboard** | Streamlit, 6 màn hình | Metabase, 1 màn hình | Không có, dùng agent hỏi bằng chữ | HTML, 6 trang | Superset, 6 trang |
| **Hỗ trợ quyết định** | **Mô hình, luật, tối ưu, kéo thả** | Không | Không | Khuyến nghị, backtest lời hẹn | Không |

**Đã đối chiếu:** GMV hợp lệ 13.494.400,74 BRL của mình trùng với clnhrn. Kết quả đối soát thanh toán 98.362 / 264 / 39 đơn cũng trùng với số họ công bố. Đây là thêm một kiểm chứng độc lập cho kho.

### Từng bài đáng học gì

**Nader:** bố cục gọn, 5 biểu đồ trong một màn hình. Về kho thì không nên học: đơn hàng nằm ở dimension, tiền lưu kiểu `float`, khóa chính `review_id` trùng với dữ liệu thật, nạp lại toàn bộ mỗi lần.

**clnhrn, nên học nhiều nhất về kho:**
- Tách `fact_orders` và `fact_order_items`: mốc giao hàng ở mức đơn, seller ở mức dòng hàng.
- `dim_location` theo ZIP dùng cho cả khách và seller.
- Thêm bản dịch cho 2 danh mục thiếu.
- Chứng minh chạy lại không đổi số dòng trên toàn bộ bảng.

**TonyLee, nên học nhiều nhất về phân tích và giao diện:**
- Cùng dùng DuckDB, nên cách làm áp dụng thẳng được.
- Tiêu đề biểu đồ nêu kết luận, không chỉ nêu tên chỉ số.
- Mỗi KPI ghi rõ khoảng thời gian, có đánh dấu biểu đồ nào chịu tác động của bộ lọc.
- Test nghiệp vụ: thanh toán khớp hàng + phí, chống nhân dòng.
- Phân loại seller theo **quy mô × chất lượng**: Champions, Fix-first, Grow, Watch, Long tail.

**huy-dataguy:**
- Có quy định rõ thuộc tính nào theo Type 0, 1, 2.
- Thành viên `Unknown` và `not-applicable` riêng.
- Phát hành theo phiên bản và diễn tập khôi phục. Phần này vượt quá nhu cầu của đề.

---

## 4. Điểm yếu của kho hiện tại

| # | Vấn đề | Hậu quả | Mức độ |
|---|---|---|---|
| 1 | **SCD2 sai mục đích:** hạng đổi quá nhanh. 52% lượt chuyển tháng có đổi hạng, trung bình 5,75 dòng mỗi seller. Theo Kimball đây là thuộc tính thay đổi nhanh, không hợp với Type 2 | `dim_seller` phình to, lịch sử hạng khó dùng làm cơ sở hành động | **Cao** |
| 2 | **Thiếu fact mức đơn:** chỉ có đơn × seller, nên chỉ số mức đơn bị lặp ở đơn nhiều seller | Đếm dễ dư khoảng 1%, màn Lỗi giao trễ đang bị | **Cao** |
| 3 | **Thiếu `fact_review`:** review bị gộp về đơn, mất thời điểm chấm | Không phân tích được khảo sát trước hay sau khi nhận hàng | **Cao** |
| 4 | **`dim_geography` đứng riêng:** không fact nào nối vào, chỉ có tuyến theo bang | Không thực sự là một dimension, không phân tích được dưới mức bang | **Trung bình** |
| 5 | Định nghĩa KPI chỉ có trong tài liệu | Giao diện không hiện được công thức, dễ lệch giữa các màn hình | Trung bình |
| 6 | Chưa có test thanh toán khớp hàng + phí, chưa có test chống nhân dòng theo cột | Thiếu một lớp bảo vệ | Trung bình |
| 7 | Thiếu bản dịch cho 13 sản phẩm thuộc 2 danh mục | 13 sản phẩm đang bị xếp `Unknown` | Thấp |
| 8 | Không có sơ đồ lineage | Khó trình bày trong báo cáo | Thấp |

---

## 5. Phát hiện làm đổi kết luận cũ

TonyLee chỉ ra Olist gửi khảo sát khoảng 2 ngày sau **ngày hẹn**, dù hàng đã tới hay chưa. Tao kiểm tra lại trên kho của mình:

| Khách | Seller | Review tạo | Số đơn | Điểm TB |
|---|---:|---|---:|---:|
| Đúng hẹn | Đúng hạn | Sau khi nhận | 81.139 | 4,29 |
| Đúng hẹn | Trễ | Sau khi nhận | 6.642 | 4,06 |
| **Trễ** | Đúng hạn | **Trước khi nhận** | 3.875 | **1,99** |
| **Trễ** | Đúng hạn | Sau khi nhận | 749 | 3,74 |
| **Trễ** | Trễ | **Trước khi nhận** | 1.469 | **1,94** |
| **Trễ** | Trễ | Sau khi nhận | 300 | 3,87 |

- **84%** đơn trễ có review được tạo trước khi hàng tới, so với 3% ở đơn đúng hẹn. Ngày hẹn đến ngày tạo review có trung vị 2 ngày. **Cập nhật 07/11: đo theo giờ khách trả lời thì là 70,2%, chấm trước khi nhận được 1,66 sao, sau khi nhận được 3,72 sao, sát với số TonyLee công bố. Xem `thiet-ke-he-thong.md`, mục 8.**
- So trong cùng seller và cùng tháng, đơn trễ thấp hơn **1,86 sao**. Nếu chỉ xét review tạo sau khi nhận hàng thì chỉ thấp hơn **0,41 sao**. TonyLee công bố -1,89 và -0,51 bằng phương pháp chặt hơn, tức cùng hướng.

**Điều này có nghĩa là:** câu "khách nhận trễ thì review thấp, dù ai gây ra" là đúng về số, nhưng phần lớn là khách đang chấm khi chưa nhận được hàng. Không nên diễn giải là trải nghiệm sản phẩm kém đi 2 sao.

**Giới hạn của phép kiểm tra:** ngày tạo review không có giờ, nên review tạo cùng ngày giao bị tính là "trước khi nhận", làm con số 84% cao hơn thực tế (TonyLee đo theo giờ trả lời được 70%). Nhóm chấm sau khi nhận cũng là nhóm tự chọn lọc, không đại diện cho toàn bộ.

**Một đề xuất mới cho Olist:** đổi thời điểm gửi khảo sát sau khi xác nhận đã giao. Đây là thay đổi không tốn chi phí vận hành. TonyLee đề xuất cách này, và mình có thể đưa vào màn Lỗi giao trễ.

---

## 6. Đề xuất nâng cấp kho

### Sơ đồ đích

```
                               dim_date (nhiều vai trò)
                                  │
 dim_customer ──┬── fact_order ───┤            ← MỚI: grain 1 đơn, accumulating
                │      │          │
 dim_location ──┤   dim_order_status           ← MỚI: thay dim_geography đứng riêng
 (khách, seller)│                 │
                ├── fact_order_seller          ← đổi tên từ fact_order_fulfillment
 dim_seller ────┤      (đơn × seller: bàn giao, trễ khâu seller)
 (SCD2 ổn định) │                 │
                ├── fact_sales_item ── dim_product
 dim_route ─────┤                 │
                ├── fact_review ──┤            ← MỚI: review × đơn, có cờ trước/sau khi nhận
                ├── fact_payment  │
                │                 │
 dim_seller_health ── fact_seller_monthly      ← MỚI: mini-dimension cho hạng thay đổi nhanh
```

### Việc nên làm

| Ưu tiên | Việc | Lợi ích | Công sức ước tính |
|---|---|---|---|
| **1** | Thêm `fact_review` (grain review × đơn), cờ `is_before_delivery` | Sửa được diễn giải sai, có thêm một quy trình nghiệp vụ | 2–3 giờ |
| **2** | Thêm `fact_order` (grain đơn), đổi tên fact cũ thành `fact_order_seller` | Hết đếm dư, đúng chuẩn Kimball | 3–4 giờ |
| **3** | Sửa SCD2: đưa hạng tháng vào mini-dimension `dim_seller_health`, còn `dim_seller` chỉ đổi khi hạng giữ nguyên 2 tháng liên tiếp | Lịch sử có ý nghĩa, và có thêm nội dung thiết kế để trình bày | 3–4 giờ |
| **4** | `dim_location` theo ZIP, nối vào fact bằng `customer_location_key`, `seller_location_key`; thêm `dim_order_status` | Hết dimension đứng riêng, drill được tới thành phố | 2–3 giờ |
| **5** | Thêm test: thanh toán khớp hàng + phí, chống nhân dòng, không dòng hàng nào rơi vào seller không rõ; bổ sung 2 bản dịch | Tăng độ tin cậy | 1–2 giờ |
| **6** | Danh mục KPI `metrics.yml`: định nghĩa, công thức, khoảng thời gian; giao diện đọc trực tiếp để hiện chú thích | Thuật ngữ và công thức nằm ngay trên app | 3–4 giờ |
| **7** | Sinh sơ đồ lineage và ERD đưa vào báo cáo | Dễ trình bày | 1–2 giờ |

**Phương án phân hạng tốt hơn:** thay hạng hiện tại bằng ma trận **quy mô × chất lượng** kiểu TonyLee, ổn định hơn vì không phụ thuộc biến động 30 ngày. Xu hướng ngắn hạn để cho mô hình rủi ro.

### Việc không nên làm

| Công cụ | Vì sao chưa cần |
|---|---|
| **dbt** | Có lợi về lineage và test, nhưng vòng lặp 26 đợt khó chuyển sang dbt, dễ phát sinh lỗi sát hạn. Logic đã ở SQL nên chuyển sau cũng được. Có thể ghi vào hướng phát triển |
| **Airflow** | Chỉ có một quy trình tuần tự trên một máy, `run_all.py` là đủ. Có thể vẽ sơ đồ DAG trong báo cáo |
| **Cloud, Terraform, MinIO** | Không giải quyết vấn đề nào của đề bài, tốn thời gian cài đặt |
| **Phát hành theo phiên bản, diễn tập khôi phục** | Dành cho vận hành thật. Database dựng lại được bằng một lệnh |
| **Text-to-SQL agent** | Hấp dẫn nhưng lệch trọng tâm DW và DSS |

---

## 7. Đề xuất giao diện

### Học được gì từ các bài

| Nguồn | Lấy | Không lấy |
|---|---|---|
| Nader | Mật độ thông tin: 5 biểu đồ một màn hình | Donut 10 màu, biểu đồ diện tích đè nhau, số 0 giả ở tháng chưa có dữ liệu |
| TonyLee | Tiêu đề nêu kết luận, KPI ghi khoảng thời gian, đánh dấu biểu đồ theo bộ lọc, lưới 2 × 2 | Trang dài với nhiều chữ |
| huy-dataguy | Hàng KPI dày, bảng "điểm nhấn" tóm tắt bằng chữ, thanh điều hướng theo chủ đề | Trang rất dài, nhãn ngày nghiêng khó đọc |

### Quy tắc mới

1. **Mỗi màn hình vừa 1440 × 900, không cuộn.** Đưa vào test tự động: chiều cao nội dung không vượt khung hình.
2. **Bố cục cố định:** thanh trên gồm as-of và bộ lọc → hàng KPI → lưới biểu đồ 2 × 2 hoặc 3 × 2. Phần chi tiết chuyển vào tab hoặc bảng cuộn bên trong.
3. **Tiêu đề biểu đồ nêu kết luận, tự sinh từ số liệu.** Ví dụ: "81% đơn trễ có seller đúng hạn" thay vì "Phân tích đơn trễ".
4. **Mỗi KPI đều có so sánh:** với tháng trước, kèm sparkline xu hướng nhỏ.
5. **Giảm khoảng trắng:** tiêu đề nhỏ lại, thu thanh bên, chuyển chọn màn hình thành tab ngang trên cùng.
6. **Chú thích ⓘ ở mọi trường,** lấy từ `metrics.yml`.

### Khung từng màn hình (1440 × 900)

**Tổng quan**

```
┌────────────────────────────────────────────────────────────────────────────┐
│ Seller Health │ Tổng quan │ Lỗi trễ │ Seller │ Kế hoạch │ What-if │ Kiểm chứng │
│ As-of [07/2018 ▾]  Vùng [Tất cả ▾]  Danh mục [Tất cả ▾]                    │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┤
│ GMV      │ Đơn      │ Seller   │ Trễ hẹn  │ Review   │ Nguy cơ  │ GMV rủi ro│
│ 863k ▼13%│ 6.145    │ 1.168    │ 8,4%     │ 4,12     │ +70      │ 479k     │
│ ▁▃▅▆▅▃   │ ▁▃▅▆▅▃   │ ▁▃▅▆▇█   │ ▂▁▇▂▂▂   │ ▆▆▅▆▆▅   │          │          │
├──────────┴──────────┴──┬───────┴──────────┴─┬────────┴──────────┴──────────┤
│ GMV tháng 6 giảm 13%   │ Trễ hẹn tăng 2,4   │ 89 seller Nguy cơ, 70 mới vào │
│ [cột GMV theo tháng]   │ điểm [đường]       │ [cột ngang theo hạng]         │
├────────────────────────┼────────────────────┼───────────────────────────────┤
│ Vùng nào đang sụt      │ Danh mục nào đang  │ Seller mới vào Nguy cơ        │
│ [cột ngang, so tháng   │ sụt [cột ngang, so │ [bảng 6 dòng, bấm mở chi tiết]│
│  trước]                │  tháng trước]      │                               │
└────────────────────────┴────────────────────┴───────────────────────────────┘
```

**Lỗi giao trễ**

```
│ KPI: Đơn đã giao │ Trễ hẹn │ Đơn trễ có seller đúng hạn │ Seller trễ │ Review trước khi nhận │
├──────────────────────┬──────────────────────┬──────────────────────────────┤
│ 81% đơn trễ không do │ 84% đơn trễ được chấm│ Bang nào trễ nhiều nhất      │
│ seller [thanh tách   │ trước khi nhận hàng  │ [bản đồ bong bóng]           │
│ 3 khâu]              │ [cột theo nhóm]      │                              │
├──────────────────────┴──────────┬───────────┴──────────────────────────────┤
│ Tuyến trễ có hệ thống [heatmap] │ Seller bán nhiều mà hay trễ [scatter]    │
└─────────────────────────────────┴──────────────────────────────────────────┘
```

**Bảng kế hoạch** là màn hình đổi nhiều nhất:

```
│ Ngân sách [===] Suất [===] Ngưỡng [===] Top [===]  [Giả định ▾] [Đặt lại] [CSV] │
├──────────┬──────────┬──────────┬──────────┬────────────────────────────────┤
│ Tiền     │ Suất     │ GMV rủi ro│ Giữ được │ Đáng chi thêm không?           │
│ 2.000    │ 36/40    │ 137.854  │ 36.680   │ [đường cong nhỏ]               │
├──────────┴───┬──────┴───────┬──┴──────────┼───────────────┬────────────────┤
│ Gọi ngay (28)│ Hỗ trợ (4)   │ Email       │ Chưa xử lý    │ Seller đang chọn│
│ [thẻ, cuộn   │ [thẻ, cuộn   │ [thẻ, cuộn  │ [thẻ, cuộn    │ Lý do, xu hướng │
│  trong cột]  │  trong cột]  │  trong cột] │  trong cột]   │ GMV nhỏ         │
└──────────────┴──────────────┴─────────────┴───────────────┴────────────────┘
```

Các cột cuộn bên trong, nên các số tổng hợp luôn nằm trong tầm mắt khi kéo thẻ.

**Chi tiết seller, What-if và Kiểm chứng** theo cùng khung: một hàng KPI, 2–4 biểu đồ, một bảng cuộn bên trong.

**So sánh ngay trên màn hình:** Chi tiết seller có thể chọn hai seller song song hoặc so với trung bình nhóm. Có thể bật một chế độ so sánh hai mốc as-of ở Tổng quan.

### Giới hạn cần biết

- Streamlit không có điều khiển thật sự cố định theo pixel, nên muốn gọn phải viết thêm CSS. Thẻ KPI có sparkline dùng được `chart_data` có sẵn trong `st.metric`.
- Bấm vào thẻ trong bảng kéo thả để hiện chi tiết bên phải **chưa chắc làm được** với `streamlit-sortables`, vì thành phần này chỉ trả về thứ tự thẻ. Nếu không được thì dùng ô chọn seller bên cạnh, hoặc phải tự viết component kéo thả, tốn công hơn nhiều.
- Màn hình laptop nhỏ hơn 1440 × 900 có thể vẫn phải cuộn nhẹ. Khi trình chiếu thì nên kiểm tra lại đúng độ phân giải của máy chiếu.

---

## 8. Lưu ý khi tham khảo

Các bài này công khai nhưng là bài của người khác. Có thể học ý tưởng và trích dẫn nguồn trong báo cáo, không nên chép code hay sơ đồ vào bài nộp. clnhrn và TonyLee ghi code theo giấy phép MIT, còn bài huy-dataguy tao chưa kiểm tra giấy phép. Dữ liệu Olist theo giấy phép CC BY-NC-SA 4.0.

---

## Nguồn

- [NaderHani/Olist-E-commerce-Data-Warehouse](https://github.com/NaderHani/Olist-E-commerce-Data-Warehouse)
- [clnhrn/olist-warehouse](https://github.com/clnhrn/olist-warehouse)
- [TonyLee-99/marketplace-analytics](https://github.com/TonyLee-99/marketplace-analytics)
- [huy-dataguy/olist-sales-warehouse](https://github.com/huy-dataguy/olist-sales-warehouse)
- Chưa đọc kỹ, có thể xem thêm: [Aljaser20/olist-ecommerce-data-warehouse](https://github.com/Aljaser20/olist-ecommerce-data-warehouse) (SQL Server, Bronze/Silver/Gold), [AdityaRotte/olist-elt-warehouse](https://github.com/AdityaRotte/olist-elt-warehouse), [vikash122005/olist-lakehouse-dbt-airflow](https://github.com/vikash122005/olist-lakehouse-dbt-airflow)
