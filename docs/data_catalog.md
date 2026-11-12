# Data catalog

Tự sinh từ kho bằng `python -m src.etl.catalog`, không sửa tay. Mô tả lấy từ `catalog.yml`.

| Lớp | Schema | Vai trò |
|---|---|---|
| Bronze | `raw` | Dữ liệu gốc dạng chữ, thêm cột `dwh_` |
| Silver | `stg` | Đã làm sạch: giao dịch là view, master là bảng |
| Gold | `core` | Galaxy schema: dimension và fact |
| Gold | `mart` | Tổng hợp, đóng băng lúc chốt đợt |
| DSS | `dss` | Nhãn, điểm rủi ro, kế hoạch, đánh giá |
| Vận hành | `ops` | Nhật ký, cách ly, đối soát, nguồn gốc |

## Tổng quan

| Bảng | Lớp | Loại | Grain | Số dòng |
|---|---|---|---|---:|
| `raw.category_translation` | Bronze | Dữ liệu gốc | 1 danh mục | 71 |
| `raw.customers` | Bronze | Dữ liệu gốc | 1 customer_id | 99.441 |
| `raw.geolocation` | Bronze | Dữ liệu gốc | 1 tọa độ quan sát | 1.000.163 |
| `raw.order_items` | Bronze | Dữ liệu gốc | 1 dòng hàng | 112.650 |
| `raw.order_payments` | Bronze | Dữ liệu gốc | 1 phần thanh toán | 103.886 |
| `raw.order_reviews` | Bronze | Dữ liệu gốc | 1 review theo đơn | 99.224 |
| `raw.orders` | Bronze | Dữ liệu gốc | 1 phiên bản của 1 đơn | 137.236 |
| `raw.products` | Bronze | Dữ liệu gốc | 1 sản phẩm | 32.951 |
| `raw.sellers` | Bronze | Dữ liệu gốc | 1 seller | 3.095 |
| `stg.category_translation` | Silver | Master đã sạch | 1 danh mục | 73 |
| `stg.customers` | Silver | Master đã sạch | 1 customer_id | 99.441 |
| `stg.geography` | Silver | Master đã sạch | 1 ZIP | 19.015 |
| `stg.products` | Silver | Master đã sạch | 1 sản phẩm | 32.951 |
| `stg.sellers` | Silver | Master đã sạch | 1 seller | 3.095 |
| `core.dim_customer` | Gold | Dimension | 1 customer_unique_id | 96.097 |
| `core.dim_date` | Gold | Dimension. nhiều vai trò | 1 ngày | 1.827 |
| `core.dim_location` | Gold | Dimension | 1 ZIP | 19.178 |
| `core.dim_order_status` | Gold | Dimension | 1 trạng thái | 8 |
| `core.dim_product` | Gold | Dimension | 1 sản phẩm | 32.952 |
| `core.dim_route` | Gold | Dimension | 1 cặp bang seller và bang khách | 622 |
| `core.dim_seller` | Gold | Dimension. SCD Type 2 | 1 phiên bản của seller | 11.209 |
| `core.dim_seller_health` | Gold | Mini-dimension | 1 tổ hợp hồ sơ sức khỏe | 361 |
| `core.fact_order` | Gold | Accumulating snapshot | 1 đơn | 99.441 |
| `core.fact_order_seller` | Gold | Accumulating snapshot | 1 đơn × 1 seller | 100.785 |
| `core.fact_payment` | Gold | Transaction fact | 1 phần thanh toán | 103.886 |
| `core.fact_review` | Gold | Transaction fact | 1 review × 1 đơn | 99.224 |
| `core.fact_sales_item` | Gold | Transaction fact | 1 sản phẩm trong 1 đơn | 112.650 |
| `core.fact_seller_monthly` | Gold | Periodic snapshot | 1 seller × 1 tháng | 25.487 |
| `mart.kpi_monthly` | Gold | Mart. CUBE | 1 tháng × vùng × danh mục. kèm các dòng tổng | 4.790 |
| `mart.route_delivery` | Gold | Mart. đóng băng lúc chốt đợt | 1 tuyến × 1 as-of | 6.186 |
| `mart.seller_features` | Gold | Mart. đóng băng lúc chốt đợt | 1 seller × 1 as-of | 25.487 |
| `mart.seller_tier_monthly` | Gold | Mart. đóng băng lúc chốt đợt | 1 seller × 1 as-of | 80.470 |
| `dss.default_params` | DSS | Tham số | 1 bộ tham số | 1 |
| `dss.eval_auc` | DSS | Đánh giá | 1 mục tiêu × 1 as-of | 22 |
| `dss.eval_lists` | DSS | Đánh giá | 1 cách chọn × 1 phạm vi × 1 as-of | 35 |
| `dss.explain` | DSS | Giải thích dự báo | 1 seller × 1 feature × 1 as-of. kèm 1 dòng hệ số chặn | 230.451 |
| `dss.labels` | DSS | Nhãn huấn luyện | 1 seller × 1 as-of | 18.048 |
| `dss.model_coef` | DSS | Kết quả mô hình | 1 feature × 1 mục tiêu × 1 as-of | 312 |
| `dss.recommendation` | DSS | Kế hoạch mặc định | 1 seller × 1 as-of | 17.727 |
| `dss.scores` | DSS | Kết quả mô hình | 1 seller × 1 as-of | 17.727 |
| `dss.sensitivity` | DSS | Đánh giá | 1 kịch bản × 1 as-of | 63 |
| `ops.dq_issue` | Vận hành | Chất lượng dữ liệu | 1 quy tắc | 19 |
| `ops.etl_log` | Vận hành | Nhật ký | 1 đợt | 27 |
| `ops.layer_reconciliation` | Vận hành | Cổng chất lượng | 1 phép kiểm tra × 1 đợt | 286 |
| `ops.quarantine` | Vận hành | Cách ly | 1 dòng lỗi | 42 |
| `ops.source_manifest` | Vận hành | Nguồn gốc dữ liệu | 1 file nguồn | 9 |

## Schema `core`

### `core.dim_customer`

Khách theo người, không theo đơn. Vị trí lúc mua lấy từ customer_location_key trên fact.

**Loại:** Dimension. **Grain:** 1 customer_unique_id.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `customer_key` | BIGINT | Khóa thay thế, trỏ tới dim_customer. |
| `customer_unique_id` | VARCHAR | Mã người mua từ nguồn. |
| `city` | VARCHAR | Thành phố xuất hiện nhiều nhất của khách. |
| `state` | VARCHAR | Bang xuất hiện nhiều nhất của khách. |

### `core.dim_date`

Lịch từ 2016 đến 2020, dùng cho ngày mua, duyệt, bàn giao, nhận và hẹn.

**Loại:** Dimension, nhiều vai trò. **Grain:** 1 ngày.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `date_key` | INTEGER | Khóa dạng YYYYMMDD. |
| `full_date` | DATE | Ngày. |
| `year` | BIGINT | Năm. |
| `quarter` | BIGINT | Quý. |
| `month` | BIGINT | Ngày đầu tháng. |
| `year_month` | VARCHAR | Năm-tháng. |
| `week` | BIGINT | Tuần trong năm. |
| `day_of_week` | BIGINT | Thứ trong tuần, 1 là thứ Hai. |
| `is_weekend` | BOOLEAN | Thứ Bảy hoặc Chủ nhật. |
| `is_holiday_br` | BOOLEAN | Ngày lễ toàn quốc của Brazil. |
| `is_black_friday` | BOOLEAN | Ngày Black Friday. |

### `core.dim_location`

Mọi ZIP xuất hiện ở khách, seller hoặc geolocation. Dùng cho cả vị trí khách và seller.

**Loại:** Dimension. **Grain:** 1 ZIP.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `location_key` | BIGINT | Khóa thay thế của một ZIP. |
| `zip_prefix` | VARCHAR | 5 chữ số đầu của mã bưu chính. |
| `city` | VARCHAR | Tên thành phố đã chuẩn hóa. |
| `state` | VARCHAR | Mã bang. |
| `region` | VARCHAR | Vùng của Brazil. |
| `lat` | DOUBLE | Vĩ độ trung vị. |
| `lng` | DOUBLE | Kinh độ trung vị. |
| `has_coordinates` | BOOLEAN | ZIP có tọa độ hợp lệ. |

### `core.dim_order_status`

Trạng thái đơn và thứ tự trong quy trình.

**Loại:** Dimension. **Grain:** 1 trạng thái.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `status_key` | BIGINT | Trạng thái đơn, trỏ tới dim_order_status. |
| `status` | VARCHAR | Tên trạng thái. |
| `stage` | INTEGER | Thứ tự trong quy trình. |
| `is_delivered` | BOOLEAN | Trạng thái đã giao. |
| `is_canceled` | BOOLEAN | Trạng thái hủy hoặc không có hàng. |

### `core.dim_product`

Sản phẩm và thuộc tính.

**Loại:** Dimension. **Grain:** 1 sản phẩm.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `product_key` | BIGINT | Khóa thay thế, trỏ tới dim_product. |
| `product_id` | VARCHAR | Mã sản phẩm từ nguồn. |
| `category_en` | VARCHAR | Danh mục sản phẩm tiếng Anh. |
| `weight_g` | DOUBLE | Cân nặng, gram. |
| `volume_cm3` | DOUBLE | Thể tích, cm³. |
| `size_group` | VARCHAR | Nhóm kích thước theo thể tích. |
| `photos_qty` | INTEGER | Số ảnh. |

### `core.dim_route`

Tuyến giao hàng theo cặp bang, không phải một lộ trình xe cụ thể.

**Loại:** Dimension. **Grain:** 1 cặp bang seller và bang khách.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `route_key` | BIGINT | Khóa thay thế, trỏ tới dim_route. |
| `seller_state` | VARCHAR | Bang seller. |
| `customer_state` | VARCHAR | Bang khách. |
| `route_name` | VARCHAR | Tên tuyến, ví dụ SP->RJ. |
| `same_state` | BOOLEAN | Cùng một bang. |
| `distance_km` | DOUBLE | Khoảng cách giữa tâm hai bang, chỉ là xấp xỉ. |

### `core.dim_seller`

Seller và hạng ổn định. Chỉ thêm phiên bản khi hạng tháng giữ nguyên 2 kỳ liên tiếp. Hạng do hệ thống tính.

**Loại:** Dimension, SCD Type 2. **Grain:** 1 phiên bản của seller.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `seller_key` | BIGINT | Khóa thay thế của phiên bản. |
| `seller_id` | VARCHAR | Mã seller, khóa tự nhiên từ nguồn. |
| `zip_prefix` | VARCHAR | 5 chữ số đầu của mã bưu chính. |
| `city` | VARCHAR | Tên thành phố đã chuẩn hóa. |
| `state` | VARCHAR | Mã bang. |
| `region` | VARCHAR | Vùng của Brazil. |
| `health_tier` | VARCHAR | Hạng ổn định. |
| `valid_from` | TIMESTAMP | Có hiệu lực từ. |
| `valid_to` | TIMESTAMP | Có hiệu lực đến, không gồm thời điểm này. |
| `is_current` | BOOLEAN | Phiên bản hiện hành. |

### `core.dim_seller_health`

Thuộc tính thay đổi nhanh được tách khỏi dim_seller. fact_seller_monthly trỏ tới đây.

**Loại:** Mini-dimension. **Grain:** 1 tổ hợp hồ sơ sức khỏe.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `health_key` | BIGINT | Hồ sơ sức khỏe, trỏ tới dim_seller_health. |
| `health_tier` | VARCHAR | Hạng tháng. |
| `size_band` | VARCHAR | Nhóm số đơn 90 ngày. |
| `late_band` | VARCHAR | Nhóm tỷ lệ giao vận chuyển trễ. |
| `review_band` | VARCHAR | Nhóm review trung bình. |

### `core.fact_order`

Vòng đời đơn, cập nhật qua các đợt. Dùng bảng này để đếm đơn và tính trễ hẹn.

**Loại:** Accumulating snapshot. **Grain:** 1 đơn.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `order_id` | VARCHAR | Mã đơn, khóa tự nhiên từ nguồn. |
| `customer_key` | BIGINT | Khóa thay thế, trỏ tới dim_customer. |
| `customer_location_key` | BIGINT | ZIP của khách, trỏ tới dim_location. |
| `status_key` | BIGINT | Trạng thái đơn, trỏ tới dim_order_status. |
| `purchase_date_key` | INTEGER | Ngày mua, trỏ tới dim_date. |
| `approved_date_key` | INTEGER | Ngày duyệt, trỏ tới dim_date. |
| `carrier_date_key` | INTEGER | Ngày bàn giao cho vận chuyển, trỏ tới dim_date. |
| `delivered_date_key` | INTEGER | Ngày khách nhận, trỏ tới dim_date. |
| `estimated_date_key` | INTEGER | Ngày hẹn giao, trỏ tới dim_date. |
| `purchase_ts` | TIMESTAMP | Thời điểm mua. |
| `approved_ts` | TIMESTAMP | Thời điểm duyệt. |
| `carrier_ts` | TIMESTAMP | Thời điểm bàn giao cho vận chuyển. |
| `delivered_ts` | TIMESTAMP | Thời điểm khách nhận. |
| `estimated_ts` | TIMESTAMP | Ngày hẹn giao. |
| `days_to_approve` | DOUBLE | Số ngày từ lúc mua đến lúc duyệt. |
| `days_to_carrier` | DOUBLE | Số ngày từ lúc mua đến lúc bàn giao vận chuyển. |
| `days_in_transit` | DOUBLE | Số ngày từ lúc bàn giao vận chuyển đến lúc khách nhận. |
| `delay_days` | INTEGER | Ngày nhận trừ ngày hẹn, dương là trễ. |
| `customer_late` | BOOLEAN | Khách nhận sau ngày hẹn, so theo ngày. |
| `any_seller_late` | BOOLEAN | Có ít nhất một seller của đơn bàn giao trễ. |
| `n_items` | INTEGER | Số dòng hàng. |
| `n_sellers` | INTEGER | Số seller trong đơn. |
| `items_price_total` | DECIMAL(14,2) | Tổng tiền hàng. |
| `freight_total` | DECIMAL(14,2) | Tổng phí vận chuyển. |
| `order_total` | DECIMAL(14,2) | Tiền hàng cộng phí vận chuyển. |
| `payment_total` | DECIMAL(14,2) | Tổng thanh toán. Có thể khác order_total do lãi trả góp. |
| `payment_count` | INTEGER | Số dòng thanh toán. |
| `review_score` | DOUBLE | Điểm trung bình các review của đơn. |
| `first_review_ts` | TIMESTAMP | Lúc khách đầu tiên trả lời review của đơn. |
| `is_canceled` | BOOLEAN | Đơn hủy hoặc không có hàng. |
| `has_status_date_mismatch` | BOOLEAN | Trạng thái và ngày nhận mâu thuẫn. |
| `has_chronology_issue` | BOOLEAN | Thứ tự các mốc bất thường. |
| `dwh_first_batch` | VARCHAR | Đợt đầu tiên thấy đơn. |
| `dwh_last_batch` | VARCHAR | Đợt gần nhất đơn thay đổi. |
| `n_versions` | INTEGER | Số phiên bản của đơn trong raw.orders. |

### `core.fact_order_seller`

Trách nhiệm bàn giao của từng seller. Các mốc và review lặp lại theo seller, không dùng bảng này để đếm đơn.

**Loại:** Accumulating snapshot. **Grain:** 1 đơn × 1 seller.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `order_id` | VARCHAR | Mã đơn, khóa tự nhiên từ nguồn. |
| `seller_id` | VARCHAR | Mã seller, khóa tự nhiên từ nguồn. |
| `seller_key` | BIGINT | Khóa thay thế, trỏ tới dòng dim_seller có hiệu lực lúc mua. |
| `customer_key` | BIGINT | Khóa thay thế, trỏ tới dim_customer. |
| `route_key` | BIGINT | Khóa thay thế, trỏ tới dim_route. |
| `customer_location_key` | BIGINT | ZIP của khách, trỏ tới dim_location. |
| `seller_location_key` | BIGINT | ZIP của seller, trỏ tới dim_location. |
| `purchase_date_key` | INTEGER | Ngày mua, trỏ tới dim_date. |
| `approved_date_key` | INTEGER | Ngày duyệt, trỏ tới dim_date. |
| `carrier_date_key` | INTEGER | Ngày bàn giao cho vận chuyển, trỏ tới dim_date. |
| `delivered_date_key` | INTEGER | Ngày khách nhận, trỏ tới dim_date. |
| `estimated_date_key` | INTEGER | Ngày hẹn giao, trỏ tới dim_date. |
| `purchase_ts` | TIMESTAMP | Thời điểm mua. |
| `approved_ts` | TIMESTAMP | Thời điểm duyệt. |
| `carrier_ts` | TIMESTAMP | Thời điểm bàn giao cho vận chuyển. |
| `delivered_ts` | TIMESTAMP | Thời điểm khách nhận. |
| `estimated_ts` | TIMESTAMP | Ngày hẹn giao. |
| `shipping_limit_ts` | TIMESTAMP | Hạn bàn giao muộn nhất của seller trong đơn. |
| `order_status` | VARCHAR | Trạng thái đơn. |
| `days_to_approve` | DOUBLE | Số ngày từ lúc mua đến lúc duyệt. |
| `days_to_carrier` | DOUBLE | Số ngày từ lúc mua đến lúc bàn giao vận chuyển. |
| `days_in_transit` | DOUBLE | Số ngày từ lúc bàn giao vận chuyển đến lúc khách nhận. |
| `delay_days` | INTEGER | Ngày nhận trừ ngày hẹn, dương là trễ. |
| `seller_late` | BOOLEAN | Seller bàn giao vận chuyển sau hạn. |
| `customer_late` | BOOLEAN | Khách nhận sau ngày hẹn, so theo ngày. |
| `review_score` | DOUBLE | Điểm review, từ 1 đến 5. |
| `has_comment` | BOOLEAN | Review có nội dung. |
| `first_review_ts` | TIMESTAMP | Lúc khách đầu tiên trả lời review của đơn. |
| `order_value` | DECIMAL(14,2) | Tiền hàng của seller trong đơn. |
| `freight_total` | DECIMAL(14,2) | Phí vận chuyển của seller trong đơn. |
| `n_items` | INTEGER | Số dòng hàng của seller trong đơn. |
| `dwh_first_batch` | VARCHAR | Đợt đầu tiên thấy đơn. |
| `dwh_last_batch` | VARCHAR | Đợt gần nhất đơn thay đổi. |
| `n_versions` | INTEGER | Số phiên bản của đơn trong raw.orders. |

### `core.fact_payment`

Thanh toán. Không phân bổ về dòng hàng.

**Loại:** Transaction fact. **Grain:** 1 phần thanh toán.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `order_id` | VARCHAR | Mã đơn, khóa tự nhiên từ nguồn. |
| `payment_sequential` | INTEGER | Thứ tự thanh toán trong đơn. |
| `payment_type` | VARCHAR | Hình thức thanh toán. |
| `payment_installments` | INTEGER | Số kỳ trả góp. |
| `payment_value` | DECIMAL(12,2) | Số tiền. |
| `customer_key` | BIGINT | Khóa thay thế, trỏ tới dim_customer. |
| `purchase_date_key` | INTEGER | Ngày mua, trỏ tới dim_date. |
| `dwh_batch` | VARCHAR | Đợt nạp. |

### `core.fact_review`

Từng review. Có cờ để biết khách chấm trước hay sau khi nhận hàng.

**Loại:** Transaction fact. **Grain:** 1 review × 1 đơn.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `review_id` | VARCHAR | Mã review. Một mã có thể dùng cho nhiều đơn. |
| `order_id` | VARCHAR | Mã đơn, khóa tự nhiên từ nguồn. |
| `customer_key` | BIGINT | Khóa thay thế, trỏ tới dim_customer. |
| `created_date_key` | INTEGER | Ngày gửi khảo sát, trỏ tới dim_date. |
| `answered_date_key` | INTEGER | Ngày khách trả lời, trỏ tới dim_date. |
| `created_ts` | TIMESTAMP | Ngày gửi khảo sát. |
| `answered_ts` | TIMESTAMP | Lúc khách trả lời. |
| `review_score` | INTEGER | Điểm review, từ 1 đến 5. |
| `has_title` | BOOLEAN | Review có tiêu đề. |
| `has_comment` | BOOLEAN | Review có nội dung. |
| `answer_hours` | DOUBLE | Số giờ từ lúc gửi đến lúc trả lời. |
| `customer_late` | BOOLEAN | Khách nhận sau ngày hẹn, so theo ngày. |
| `is_before_delivery` | BOOLEAN | Khách trả lời khi chưa nhận hàng hoặc đơn chưa giao. |
| `dwh_batch` | VARCHAR | Đợt nạp. |

### `core.fact_sales_item`

Doanh số. Đây là nguồn chuẩn của GMV.

**Loại:** Transaction fact. **Grain:** 1 sản phẩm trong 1 đơn.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `order_id` | VARCHAR | Mã đơn, khóa tự nhiên từ nguồn. |
| `order_item_id` | INTEGER | Thứ tự dòng hàng trong đơn. |
| `product_key` | BIGINT | Khóa thay thế, trỏ tới dim_product. |
| `seller_key` | BIGINT | Khóa thay thế, trỏ tới dòng dim_seller có hiệu lực lúc mua. |
| `seller_id` | VARCHAR | Mã seller, khóa tự nhiên từ nguồn. |
| `customer_key` | BIGINT | Khóa thay thế, trỏ tới dim_customer. |
| `route_key` | BIGINT | Khóa thay thế, trỏ tới dim_route. |
| `customer_location_key` | BIGINT | ZIP của khách, trỏ tới dim_location. |
| `seller_location_key` | BIGINT | ZIP của seller, trỏ tới dim_location. |
| `purchase_date_key` | INTEGER | Ngày mua, trỏ tới dim_date. |
| `shipping_limit_date_key` | INTEGER | Hạn bàn giao cho vận chuyển, trỏ tới dim_date. |
| `purchase_ts` | TIMESTAMP | Thời điểm mua. |
| `shipping_limit_ts` | TIMESTAMP | Hạn seller phải bàn giao cho vận chuyển. |
| `price` | DECIMAL(12,2) | Giá sản phẩm. |
| `freight_value` | DECIMAL(12,2) | Phí vận chuyển của dòng. |
| `qty` | INTEGER | Số lượng, luôn là 1 vì nguồn tách từng sản phẩm thành một dòng. |
| `is_valid_sale` | BOOLEAN | Đơn không bị hủy. |
| `dwh_batch` | VARCHAR | Đợt nạp. |

### `core.fact_seller_monthly`

Tình trạng seller, đóng băng lúc chốt tháng. Mỗi chỉ số tính theo tháng xảy ra sự kiện.

**Loại:** Periodic snapshot. **Grain:** 1 seller × 1 tháng.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `month` | DATE | Ngày đầu tháng. |
| `month_key` | INTEGER | Ngày đầu tháng, trỏ tới dim_date. |
| `seller_key` | BIGINT | Khóa thay thế, trỏ tới dòng dim_seller có hiệu lực lúc mua. |
| `health_key` | BIGINT | Hồ sơ sức khỏe, trỏ tới dim_seller_health. |
| `seller_id` | VARCHAR | Mã seller, khóa tự nhiên từ nguồn. |
| `n_orders` | BIGINT | Số đơn. |
| `n_items` | BIGINT | Số dòng hàng trong tháng. |
| `gmv` | DOUBLE | GMV trong tháng. |
| `gmv_prev_3m_avg` | DOUBLE | GMV trung bình 3 tháng trước. |
| `seller_late_rate` | DOUBLE | Tỷ lệ giao vận chuyển trễ, sản phẩm có hạn trong tháng. |
| `customer_late_rate` | DOUBLE | Tỷ lệ khách nhận trễ, sản phẩm có ngày hẹn trong tháng. |
| `avg_review` | DOUBLE | Review trung bình, review trả lời trong tháng. |
| `avg_days_to_carrier` | DOUBLE | Số ngày tới vận chuyển trung bình, bàn giao trong tháng. |
| `avg_days_in_transit` | DOUBLE | Số ngày vận chuyển trung bình, nhận trong tháng. |
| `days_since_last_sale` | DOUBLE | Số ngày từ đơn gần nhất tới lúc chốt tháng. |
| `n_categories` | BIGINT | Số danh mục đã bán trong tháng. |

## Schema `mart`

### `mart.kpi_monthly`

KPI toàn sàn tính sẵn. Mỗi thước đo theo tháng xảy ra sự kiện, đóng băng lúc chốt.

**Loại:** Mart, CUBE. **Grain:** 1 tháng × vùng × danh mục, kèm các dòng tổng.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `month` | DATE | Ngày đầu tháng. |
| `region` | VARCHAR | Vùng của Brazil. |
| `category_en` | VARCHAR | Danh mục sản phẩm tiếng Anh. |
| `is_all_region` | BOOLEAN | Dòng tổng của mọi vùng. |
| `is_all_category` | BOOLEAN | Dòng tổng của mọi danh mục. |
| `gmv` | DOUBLE | GMV đơn mua trong tháng. |
| `n_orders` | BIGINT | Số đơn. |
| `n_sellers` | BIGINT | Số seller có bán. |
| `n_due_orders` | BIGINT | Số đơn đến ngày hẹn trong tháng. |
| `n_late_orders` | BIGINT | Số đơn đến hạn mà chưa giao hoặc giao trễ. |
| `avg_review` | DOUBLE | Review trung bình, trả lời trong tháng. |

### `mart.route_delivery`

Thống kê giao hàng theo tuyến, đơn đã giao mua trong 180 ngày trước as-of.

**Loại:** Mart, đóng băng lúc chốt đợt. **Grain:** 1 tuyến × 1 as-of.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `as_of` | DATE | Mốc thời gian giả lập, chỉ thấy dữ liệu trước mốc này. |
| `route_key` | BIGINT | Khóa thay thế, trỏ tới dim_route. |
| `route_name` | VARCHAR | Tên tuyến. |
| `seller_state` | VARCHAR | Bang seller. |
| `customer_state` | VARCHAR | Bang khách. |
| `n_orders` | BIGINT | Số đơn. |
| `median_days` | DOUBLE | Trung vị số ngày từ mua đến nhận. |
| `p90_days` | DOUBLE | Phân vị 90 số ngày từ mua đến nhận. |
| `avg_promise_days` | DOUBLE | Số ngày hẹn trung bình. |
| `late_rate` | DOUBLE | Tỷ lệ khách nhận trễ. |
| `late_seller_ok_share` | DOUBLE | Trong đơn trễ, tỷ lệ seller đúng hạn. |

### `mart.seller_features`

Đầu vào của DSS. Seller có đơn hợp lệ trong 90 ngày trước as-of.

**Loại:** Mart, đóng băng lúc chốt đợt. **Grain:** 1 seller × 1 as-of.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `as_of` | DATE | Mốc thời gian giả lập, chỉ thấy dữ liệu trước mốc này. |
| `seller_id` | VARCHAR | Mã seller, khóa tự nhiên từ nguồn. |
| `gmv_90` | DOUBLE | GMV 90 ngày trước as-of. |
| `orders_90` | BIGINT | Số đơn 90 ngày. |
| `gmv_30` | DOUBLE | GMV 30 ngày. |
| `orders_30` | BIGINT | Số đơn 30 ngày. |
| `trend` | DOUBLE | GMV 30 ngày so với trung bình 90 ngày. |
| `recency` | DOUBLE | Số ngày từ đơn gần nhất. |
| `tenure` | DOUBLE | Số ngày từ đơn đầu tiên. |
| `n_cat` | BIGINT | Số danh mục trong 90 ngày. |
| `seller_late_rate` | DOUBLE | Tỷ lệ sản phẩm chưa bàn giao hoặc bàn giao sau hạn. |
| `cust_late_rate` | DOUBLE | Tỷ lệ sản phẩm chưa nhận hoặc nhận sau hẹn. |
| `avg_review` | DOUBLE | Review trung bình. |
| `days_to_carrier` | DOUBLE | Số ngày tới vận chuyển trung bình. |
| `n_limit_known` | BIGINT | Số sản phẩm đã qua hạn bàn giao. |
| `n_cust_late_orders` | BIGINT | Số đơn khách trễ. |
| `n_cust_late_seller_ok` | BIGINT | Số đơn khách trễ mà seller đúng hạn. |
| `health_tier` | VARCHAR | Hạng tháng. |

### `mart.seller_tier_monthly`

Hạng tháng của mọi seller, kể cả không hoạt động. Dùng để xét điều kiện giữ hạng 2 kỳ.

**Loại:** Mart, đóng băng lúc chốt đợt. **Grain:** 1 seller × 1 as-of.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `as_of` | DATE | Mốc thời gian giả lập, chỉ thấy dữ liệu trước mốc này. |
| `seller_id` | VARCHAR | Mã seller, khóa tự nhiên từ nguồn. |
| `health_tier` | VARCHAR | Hạng tháng. |

## Schema `dss`

### `dss.default_params`

Tham số mặc định đã dùng.

**Loại:** Tham số. **Grain:** 1 bộ tham số.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `params_json` | VARCHAR | Tham số dạng JSON. |

### `dss.eval_auc`

Chất lượng mô hình so với cách đơn giản.

**Loại:** Đánh giá. **Grain:** 1 mục tiêu × 1 as-of.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `target` | VARCHAR | Mục tiêu dự báo. |
| `n` | BIGINT | Số seller. |
| `base_rate` | DOUBLE | Tỷ lệ gốc. |
| `auc_model` | DOUBLE | AUC của mô hình. |
| `auc_no_ops` | DOUBLE | AUC khi bỏ chỉ số vận hành. |
| `auc_recency` | DOUBLE | AUC khi chỉ dùng số ngày không bán. |
| `train_n` | BIGINT | Số dòng train. |
| `train_max_as_of` | TIMESTAMP | Mốc train mới nhất. |
| `as_of` | DATE | Mốc thời gian giả lập, chỉ thấy dữ liệu trước mốc này. |

### `dss.eval_lists`

So sánh các cách chọn seller trên kết quả thật.

**Loại:** Đánh giá. **Grain:** 1 cách chọn × 1 phạm vi × 1 as-of.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `scope` | VARCHAR | Phạm vi, top50 hoặc plan. |
| `list_name` | VARCHAR | Tên cách chọn. |
| `k` | BIGINT | Số seller được chọn. |
| `hit_rate` | DOUBLE | Tỷ lệ gọi trúng. |
| `dormant_rate` | DOUBLE | Tỷ lệ tạm ngừng trong danh sách. |
| `loss_share` | DOUBLE | Phần GMV mất nằm trong danh sách. |
| `loss` | DOUBLE | Tổng GMV mất trong danh sách. |
| `as_of` | DATE | Mốc thời gian giả lập, chỉ thấy dữ liệu trước mốc này. |

### `dss.explain`

Đóng góp của từng feature vào log-odds của mục tiêu sụt GMV. Cộng mọi dòng của một seller được log-odds, đổi ra xác suất đúng bằng p_decline.

**Loại:** Giải thích dự báo. **Grain:** 1 seller × 1 feature × 1 as-of, kèm 1 dòng hệ số chặn.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `seller_id` | VARCHAR | Mã seller. |
| `feature` | VARCHAR | Tên feature; _intercept là hệ số chặn. |
| `value` | DOUBLE | Giá trị gốc của feature tại as-of, trước khi lấy log và chuẩn hóa. |
| `z` | DOUBLE | Giá trị đã chuẩn hóa theo trung bình và độ lệch chuẩn của tập train. |
| `contrib` | DOUBLE | Đóng góp vào log-odds bằng hệ số nhân z. Dương làm tăng rủi ro. |
| `as_of` | DATE | Mốc thời gian giả lập, chỉ thấy dữ liệu trước mốc này. |

### `dss.labels`

Kết quả 45 ngày sau as-of, chỉ có khi nhìn lại quá khứ. Không phải feature.

**Loại:** Nhãn huấn luyện. **Grain:** 1 seller × 1 as-of.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `as_of` | DATE | Mốc thời gian giả lập, chỉ thấy dữ liệu trước mốc này. |
| `seller_id` | VARCHAR | Mã seller, khóa tự nhiên từ nguồn. |
| `gmv_next45` | DOUBLE | GMV 45 ngày sau as-of. |
| `dormant` | BOOLEAN | Không có GMV trong 45 ngày. |
| `decline` | BOOLEAN | GMV 45 ngày thấp hơn một nửa mức bình thường. |
| `loss` | DOUBLE | Phần GMV thiếu so với mức bình thường. |
| `returned_later` | BOOLEAN | Có bán lại sau cửa sổ 45 ngày. |

### `dss.model_coef`

Hệ số Logistic Regression trên feature đã chuẩn hóa.

**Loại:** Kết quả mô hình. **Grain:** 1 feature × 1 mục tiêu × 1 as-of.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `target` | VARCHAR | Mục tiêu dự báo. |
| `feature` | VARCHAR | Tên feature. |
| `coef` | DOUBLE | Hệ số. |
| `as_of` | DATE | Mốc thời gian giả lập, chỉ thấy dữ liệu trước mốc này. |

### `dss.recommendation`

Phân khúc, hành động và lý do với tham số mặc định.

**Loại:** Kế hoạch mặc định. **Grain:** 1 seller × 1 as-of.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `seller_id` | VARCHAR | Mã seller, khóa tự nhiên từ nguồn. |
| `segment` | VARCHAR | Phân khúc theo bảng luật. |
| `action` | VARCHAR | Hành động, gồm CALL, OPS, EMAIL, NONE. |
| `reason` | VARCHAR | Lý do bằng chữ. |
| `rank` | BIGINT | Thứ tự ưu tiên. |
| `cost` | DOUBLE | Chi phí hành động. |
| `expected_saved` | DOUBLE | GMV kỳ vọng giữ được theo giả định hiệu quả. |
| `gmv_risk` | DOUBLE | GMV rủi ro, bằng p_decline × gmv_90 / 2. |
| `p_decline` | DOUBLE | Xác suất sụt GMV do mô hình dự báo, chưa hiệu chỉnh. |
| `p_dormant` | DOUBLE | Xác suất tạm ngừng 45 ngày do mô hình dự báo, chưa hiệu chỉnh. |
| `ops_score` | DOUBLE | Điểm vận hành 0-100, chỉ để hiển thị. |
| `as_of` | DATE | Mốc thời gian giả lập, chỉ thấy dữ liệu trước mốc này. |

### `dss.scores`

Điểm rủi ro train cuốn theo thời gian.

**Loại:** Kết quả mô hình. **Grain:** 1 seller × 1 as-of.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `seller_id` | VARCHAR | Mã seller, khóa tự nhiên từ nguồn. |
| `p_decline` | DOUBLE | Xác suất sụt GMV do mô hình dự báo, chưa hiệu chỉnh. |
| `p_dormant` | DOUBLE | Xác suất tạm ngừng 45 ngày do mô hình dự báo, chưa hiệu chỉnh. |
| `value_45` | DOUBLE | Mức GMV 45 ngày bình thường, bằng gmv_90 / 2. |
| `ops_score` | DOUBLE | Điểm vận hành 0-100, chỉ để hiển thị. |
| `as_of` | DATE | Mốc thời gian giả lập, chỉ thấy dữ liệu trước mốc này. |

### `dss.sensitivity`

Danh sách thay đổi thế nào khi giả định đổi.

**Loại:** Đánh giá. **Grain:** 1 kịch bản × 1 as-of.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `case_name` | VARCHAR | Tên kịch bản. |
| `n_base` | BIGINT | Số seller của phương án gốc. |
| `n_case` | BIGINT | Số seller của kịch bản. |
| `jaccard` | DOUBLE | Mức trùng với phương án gốc. |
| `expected_saved` | DOUBLE | GMV kỳ vọng giữ được theo giả định hiệu quả. |
| `expected_saved_base` | DOUBLE | GMV kỳ vọng giữ của phương án gốc. |
| `as_of` | DATE | Mốc thời gian giả lập, chỉ thấy dữ liệu trước mốc này. |

## Schema `ops`

### `ops.dq_issue`

Bất thường đã phát hiện và cách xử lý.

**Loại:** Chất lượng dữ liệu. **Grain:** 1 quy tắc.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `rule_name` | VARCHAR | Tên quy tắc. |
| `table_name` | VARCHAR | Tên bảng liên quan. |
| `n_rows` | BIGINT | Số dòng hoặc số đơn liên quan. |
| `handling` | VARCHAR | Cách xử lý. |

### `ops.etl_log`

Kết quả từng đợt nạp. Đợt không ở trạng thái ok sẽ được chạy lại.

**Loại:** Nhật ký. **Grain:** 1 đợt.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `batch` | VARCHAR | Đợt nạp. |
| `watermark` | TIMESTAMP | Mốc đã nạp tới. |
| `orders_versions` | BIGINT | Số phiên bản đơn nạp trong đợt. |
| `items` | BIGINT | Số dòng hàng nạp. |
| `payments` | BIGINT | Số dòng thanh toán nạp. |
| `reviews` | BIGINT | Số review nạp. |
| `rows_loaded` | BIGINT | Tổng số dòng nạp. |
| `rows_rejected` | BIGINT | Số dòng bị cách ly. |
| `sellers_tier_changed` | BIGINT | Số seller đổi hạng ổn định. |
| `run_at` | TIMESTAMP | Thời điểm chạy. |
| `duration_s` | DOUBLE | Số giây. |
| `status` | VARCHAR | Trạng thái, ok hoặc failed. |
| `error_message` | VARCHAR | Nội dung lỗi nếu có. |

### `ops.layer_reconciliation`

Đối soát số dòng và số tiền giữa các lớp, lũy kế tới đợt. Lệch thì đợt bị dừng.

**Loại:** Cổng chất lượng. **Grain:** 1 phép kiểm tra × 1 đợt.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `batch` | VARCHAR | Đợt nạp. |
| `check_name` | VARCHAR | Tên phép kiểm tra. |
| `layer_from` | VARCHAR | Bảng gốc. |
| `layer_to` | VARCHAR | Bảng đích. |
| `value_from` | DOUBLE | Giá trị ở bảng gốc. |
| `value_to` | DOUBLE | Giá trị ở bảng đích. |
| `difference` | DOUBLE | Chênh lệch. |
| `is_ok` | BOOLEAN | Khớp. |

### `ops.quarantine`

Dòng không qua được kiểm tra hợp lệ, không đi tiếp vào Gold.

**Loại:** Cách ly. **Grain:** 1 dòng lỗi.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `dwh_batch` | VARCHAR | Đợt nạp. |
| `table_name` | VARCHAR | Tên bảng liên quan. |
| `row_key` | VARCHAR | Khóa của dòng lỗi. |
| `reason_code` | VARCHAR | Mã lỗi. |
| `reason` | VARCHAR | Mô tả lỗi. |

### `ops.source_manifest`

Hash và số dòng của file nguồn đã kiểm tra khi nạp.

**Loại:** Nguồn gốc dữ liệu. **Grain:** 1 file nguồn.

| Cột | Kiểu | Mô tả |
|---|---|---|
| `file_name` | VARCHAR | Tên file. |
| `table_name` | VARCHAR | Tên bảng liên quan. |
| `sha256` | VARCHAR | Hash SHA-256. |
| `n_rows` | BIGINT | Số dòng. |
| `verified_at` | TIMESTAMP | Thời điểm kiểm tra. |
