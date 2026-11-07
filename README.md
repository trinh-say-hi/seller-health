# Seller Health: Kho dữ liệu và Hệ hỗ trợ quyết định trên Olist

Bài tập lớn CO4031, học kỳ 261.

Hệ thống giúp trưởng nhóm Seller Success quyết định mỗi tháng: **gọi seller nào trước, làm gì với họ, và ngân sách thay đổi thì danh sách đổi ra sao**.

Thiết kế và báo cáo chi tiết: [docs/thiet-ke-he-thong.md](docs/thiet-ke-he-thong.md).

## Chạy nhanh

Cần Windows, Python 3.13 và dữ liệu trong `data/olist/raw` (xem [data/README.md](data/README.md)).

```powershell
.\setup.ps1      # tạo venv ngoài OneDrive, cài thư viện, dựng kho và DSS, chạy test
.\run_app.ps1    # mở app tại http://localhost:8501
```

Dựng lại mất khoảng 2 phút. Hãy tắt app trước khi dựng lại, vì app đang giữ file database.

Venv và database nằm ở `%LOCALAPPDATA%\seller_health`, ngoài OneDrive, để việc đồng bộ không khóa file. Đặt biến `OLIST_DB` nếu muốn đổi vị trí database.

## Kiến trúc

Medallion cho các lớp, Kimball cho mô hình trong Gold.

![Kiến trúc](docs/diagrams/01_kien_truc.png)

| Lớp | Schema | Vai trò |
|---|---|---|
| Bronze | `raw` | Dữ liệu gốc dạng chữ, thêm cột `dwh_`; đơn hàng có nhiều phiên bản |
| Silver | `stg` | Ép kiểu, sửa tên thành phố, lọc tọa độ, gộp review. Giao dịch là view, master là bảng |
| Gold | `core` | Galaxy schema: 8 dimension, 6 fact |
| Gold | `mart` | Chốt cuối mỗi đợt: feature seller, KPI bằng CUBE, thống kê tuyến |
| | `dss` | Nhãn, điểm rủi ro, kế hoạch tối ưu, kết quả đánh giá |
| | `ops` | Nhật ký, cách ly, đối soát, nguồn gốc |

CSV chỉ có trạng thái cuối của đơn. Vì vậy mỗi đợt che đi các mốc chưa xảy ra trước ngày chốt, và feature được tính ngay lúc chốt đợt, khi kho chưa có dữ liệu tương lai. Mỗi đợt có 11 phép đối soát số dòng và số tiền giữa các lớp; lệch thì dừng đợt.

## Mô hình dữ liệu

| Bảng | Loại | Grain |
|---|---|---|
| `dim_date` | Dimension, nhiều vai trò | 1 ngày |
| `dim_seller` | Dimension, SCD Type 2 theo hạng ổn định | 1 phiên bản của seller |
| `dim_seller_health` | Mini-dimension | 1 tổ hợp hồ sơ sức khỏe |
| `dim_customer` | Dimension | 1 `customer_unique_id` |
| `dim_product` | Dimension | 1 sản phẩm |
| `dim_location` | Dimension | 1 ZIP |
| `dim_route` | Dimension | 1 cặp bang seller → bang khách |
| `dim_order_status` | Dimension | 1 trạng thái |
| `fact_sales_item` | Transaction | 1 sản phẩm trong 1 đơn |
| `fact_order` | Accumulating snapshot | 1 đơn |
| `fact_order_seller` | Accumulating snapshot | 1 đơn × 1 seller |
| `fact_review` | Transaction | 1 review × 1 đơn |
| `fact_payment` | Transaction | 1 lần thanh toán |
| `fact_seller_monthly` | Periodic snapshot | 1 seller × 1 tháng |

Tài liệu: [thiết kế và báo cáo](docs/thiet-ke-he-thong.md) · [data catalog](docs/data_catalog.md) · [quy tắc đặt tên](docs/naming_conventions.md) · [yêu cầu](docs/requirements.md) · [định nghĩa KPI](metrics.yml) · [truy vấn OLAP](src/sql/olap_examples.sql).

## Sáu màn hình

Mỗi màn hình vừa khung 1440 × 800, không phải cuộn.

| Màn hình | Câu hỏi được trả lời | Quyết định rút ra |
|---|---|---|
| Tổng quan | Tháng này có gì bất thường? GMV nào đang rủi ro? | Tập trung vào đâu |
| Lỗi giao trễ | Trễ do seller hay do vận chuyển? | Hỗ trợ seller hay sửa tuyến |
| Chi tiết seller | Seller này sụt ở đâu, vì sao? | Can thiệp kiểu gì |
| Bảng kế hoạch | Với ngân sách này thì làm gì với ai? (kéo thả) | Danh sách hành động, xuất CSV |
| What-if tuyến | Hứa thêm N ngày thì tỷ lệ trễ còn bao nhiêu? | Có đổi lời hẹn không |
| Kiểm chứng | Các tháng trước danh sách trúng bao nhiêu? | Có nên tin hệ thống không |

## Thành phần DSS

| Thành phần | Cách làm | Mã nguồn |
|---|---|---|
| Rủi ro sụt GMV và tạm ngừng 45 ngày | Logistic Regression, train cuốn theo thời gian, cách test ít nhất 45 ngày | `src/dss/run.py` |
| Điểm vận hành | Công thức có trọng số | `src/dss/run.py` |
| Bảng luật và lý do bằng chữ | Luật theo rủi ro, giá trị, vận hành | `src/dss/rules.py` |
| Tối ưu kế hoạch | MILP: mỗi seller tối đa 1 hành động, giới hạn ngân sách và số suất | `src/dss/optimize.py` |
| What-if | Tính lại kế hoạch, tính lại tỷ lệ trễ trên đơn lịch sử | `src/app/screens_dss.py` |

Ngưỡng rủi ro và ngân sách mặc định được chọn trên 09/2017–02/2018 (`scripts/tune_threshold.py`). Các tháng 03–07/2018 chỉ dùng để báo cáo kết quả.

## Kết quả (03–07/2018, cùng số seller, khoảng 30 mỗi tháng)

| Cách chọn | Gọi trúng seller thật sự sụt GMV | Phần GMV mất nằm trong danh sách |
|---|---|---|
| Kế hoạch DSS | 44–64%, trung bình 55% | 16–26%, trung bình 19% |
| Chọn theo GMV cao nhất | 21–31%, trung bình 26% | 16–31%, trung bình 25% |

Hệ thống gọi trúng nhiều hơn, nhưng bao phủ ít tiền hơn ở 4/5 tháng, vì seller rất lớn có xác suất sụt thấp. Mô hình chỉ nhỉnh hơn cách đơn giản: AUC dự báo tạm ngừng là 0,80–0,84, so với 0,77–0,80 khi chỉ dùng số ngày không bán; AUC dự báo sụt GMV là 0,67–0,73, so với 0,66–0,73.

## Hạn chế

- Việc nạp theo tháng là giả lập từ một bản CSV cuối cùng. Không có thời điểm hủy đơn, nên đơn hủy hiện trạng thái hủy ngay từ đợt của tháng mua.
- Đợt nạp lỗi không có rollback tự động, vì DuckDB 2.0 crash khi `COMMIT` giao dịch lớn. Hệ thống dừng, ghi `failed`, không tiến watermark, và chạy lại được an toàn.
- Không có dữ liệu về hiệu quả can thiệp. Chi phí và hiệu quả là giả định; "Giữ được" không phải số đã đo.
- "Gọi trúng" chỉ cho biết seller có sụt thật, không chứng minh can thiệp sẽ giữ được họ.
- Hạng do hệ thống tính ra, vì nguồn không có lịch sử thay đổi của seller. Hạng ổn định vẫn đổi ở 20% lượt chuyển tháng, hạng tháng ở 49% (seller từ 6 đơn trở lên, 01–07/2018).
- Xác suất mô hình chưa được hiệu chỉnh, nên dùng để xếp thứ tự hơn là đọc như tỷ lệ chính xác.
- Bản đồ dùng tọa độ trung bình theo bang, không có nền bản đồ và không phải khoảng cách đường bộ.
- Chỉ dùng một nguồn; bộ Marketing Funnel chưa được tích hợp.

## Kiểm thử

```powershell
python -m tests.test_system   # nguồn, các lớp, đối soát, chống rò rỉ, tối ưu, cổng chất lượng
python -m tests.test_edges    # mọi màn hình trên mọi mốc as-of
python -m tests.test_ui       # trình duyệt thật: cần chạy app ở cổng 8599 và cài requirements-dev.txt
```

Kết quả được ghi vào `evidence/`, kèm ảnh chụp giao diện trong `evidence/screenshots/`.

## Cấu trúc thư mục

```
src/etl/      điều phối các đợt nạp, kiểm tra nguồn, sinh data catalog
src/sql/      schema, staging, dimension, từng đợt, đối soát, truy vấn OLAP
src/dss/      điểm số, luật, tối ưu
src/app/      giao diện Streamlit, component kéo thả tự viết
tests/        kiểm thử
scripts/      manifest, sơ đồ, thử khả thi, chọn ngưỡng, dữ liệu mẫu
evidence/     số liệu và hình cho báo cáo
data/         dữ liệu nguồn, mẫu, manifest
docs/         thiết kế, data catalog, quy tắc đặt tên, yêu cầu, sơ đồ
catalog.yml   mô tả bảng và cột
metrics.yml   định nghĩa KPI
```
