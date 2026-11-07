# Quy tắc đặt tên

Áp dụng cho mọi bảng, cột và script trong kho. Ý tưởng tham khảo từ [DataWithBaraa/sql-data-warehouse-project](https://github.com/DataWithBaraa/sql-data-warehouse-project), điều chỉnh theo bài này.

## Quy tắc chung

- Dùng `snake_case`, chữ thường.
- Tên bảng và cột bằng tiếng Anh. Giá trị hiển thị cho người dùng, như tên hạng, bằng tiếng Việt.
- Không dùng từ khóa SQL làm tên.

## Schema

| Schema | Lớp Medallion | Chứa gì |
|---|---|---|
| `raw` | Bronze | Dữ liệu gốc dạng chữ |
| `stg` | Silver | Đã làm sạch: giao dịch là view, master là bảng |
| `core` | Gold | Dimension và fact |
| `mart` | Gold | Bảng tổng hợp, đóng băng lúc chốt đợt |
| `dss` | | Nhãn, điểm rủi ro, kế hoạch, đánh giá |
| `ops` | | Nhật ký, cách ly, đối soát, nguồn gốc |

Giữ tên `raw`, `stg`, `core`, `mart` vì đây là cách gọi quen thuộc của Kimball. Báo cáo ghi rõ ánh xạ sang Bronze, Silver, Gold.

## Bảng

| Mẫu | Ý nghĩa | Ví dụ |
|---|---|---|
| `raw.<tên nguồn>` | Giữ tên theo file nguồn | `raw.order_items` |
| `stg.<thực thể>` | Thực thể đã làm sạch | `stg.sellers` |
| `core.dim_<thực thể>` | Dimension, số ít | `core.dim_seller` |
| `core.fact_<quy trình>` | Fact, đặt theo quy trình nghiệp vụ | `core.fact_order` |
| `mart.<chủ đề>` | Bảng tổng hợp | `mart.kpi_monthly` |
| `dss.<kết quả>` | Kết quả DSS | `dss.recommendation` |
| `ops.<việc vận hành>` | Vận hành | `ops.etl_log` |

## Cột

| Mẫu | Ý nghĩa | Ví dụ |
|---|---|---|
| `<thực thể>_key` | Khóa thay thế | `seller_key` |
| `<vai trò>_date_key` | Khóa tới `dim_date`, theo vai trò | `purchase_date_key` |
| `<thực thể>_id` | Khóa tự nhiên từ nguồn | `seller_id` |
| `<sự kiện>_ts` | Thời điểm | `delivered_ts` |
| `is_`, `has_`, `any_` | Cờ đúng hoặc sai | `is_canceled`, `has_comment` |
| `n_` | Số đếm | `n_items` |
| `days_` | Số ngày | `days_to_carrier` |
| `<chỉ số>_rate` | Tỷ lệ từ 0 đến 1 | `seller_late_rate` |
| `<chỉ số>_90`, `_30` | Tính trong cửa sổ 90 hoặc 30 ngày | `gmv_90` |
| `dwh_` | Cột kỹ thuật do kho sinh ra | `dwh_batch` |

## Cột kỹ thuật

| Cột | Có ở | Ý nghĩa |
|---|---|---|
| `dwh_batch` | `raw`, fact transaction | Đợt nạp |
| `dwh_loaded_at` | `raw` | Thời điểm nạp |
| `dwh_source_file` | `raw` | File nguồn |
| `dwh_row_hash` | `raw` | Hash của dòng |
| `dwh_first_batch`, `dwh_last_batch` | Fact accumulating | Đợt đầu và đợt gần nhất đơn thay đổi |

## Dòng đặc biệt

- Khóa `-1` trong dimension là thành viên không rõ, để fact không có khóa ngoại mồ côi.
- `valid_to = 9999-12-31` là phiên bản SCD2 hiện hành.

## Mã lỗi trong `ops.quarantine`

| Mã | Ý nghĩa |
|---|---|
| `GEO_OUTSIDE_BRAZIL` | Tọa độ ngoài khung lãnh thổ Brazil |
| `INVALID_PRICE` | Giá sản phẩm không hợp lệ |
| `INVALID_PAYMENT` | Số tiền thanh toán không hợp lệ |
| `INVALID_REVIEW` | Điểm hoặc thời điểm trả lời không hợp lệ |

## File

| Thư mục | Mẫu tên | Ý nghĩa |
|---|---|---|
| `src/sql/` | `00–02_` chạy một lần, `10–13_` chạy mỗi đợt | Số đầu tên là thứ tự chạy |
| `catalog.yml` | | Mô tả bảng và cột, nạp vào kho bằng `COMMENT ON` |
| `metrics.yml` | | Định nghĩa KPI, giao diện đọc để hiện chú thích |
