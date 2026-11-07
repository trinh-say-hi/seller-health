# Yêu cầu hệ thống

## Mục tiêu

Giúp đội Seller Success của Olist quyết định mỗi tháng: gọi seller nào trước, làm gì với họ, và khi nguồn lực đổi thì danh sách đổi ra sao.

## Người dùng

**Trưởng nhóm Seller Success**, phụ trách khoảng 1.300–1.650 seller đang hoạt động, có ngân sách và số nhân viên giới hạn mỗi tháng. Đây là vai trò giả định cho đồ án, chưa phỏng vấn người thật.

## Các quyết định cần hỗ trợ

| # | Quyết định | Hệ thống đưa ra gì | Màn hình |
|---|---|---|---|
| 1 | Tháng này có gì bất thường? | KPI so với tháng trước, seller mới vào Nguy cơ | Tổng quan |
| 2 | Trễ hẹn do seller hay do vận chuyển? | Tách theo khâu, theo tuyến | Lỗi giao trễ |
| 3 | Seller này đang sụt ở đâu? | Xu hướng, số ngày từng khâu, so với trung vị hoặc seller khác | Chi tiết seller |
| 4 | Với nguồn lực này, làm gì với ai? | Kế hoạch tối ưu, sửa được bằng kéo thả | Bảng kế hoạch |
| 5 | Có nên đổi lời hẹn giao không? | Tỷ lệ trễ theo số ngày hứa thêm | What-if tuyến |
| 6 | Có nên tin hệ thống không? | So với các cách chọn đơn giản | Kiểm chứng |

## Nguồn dữ liệu

[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce): 9 file CSV, khoảng 100.000 đơn từ 09/2016 đến 10/2018, đã ẩn danh. Đối chiếu bằng hash trong `data/manifest.json`.

## Yêu cầu về kho dữ liệu

| Mã | Yêu cầu | Kiểm chứng bằng |
|---|---|---|
| K1 | Giữ dữ liệu gốc, đổi logic không cần lấy lại nguồn | Lớp `raw`, `run_all.py` |
| K2 | Biết được "tại thời điểm X, kho thấy gì" | Giả lập 26 đợt, test không đợt nào thấy mốc sau ngày chốt |
| K3 | Không mất tiền, không nhân đôi tiền qua các lớp | `ops.layer_reconciliation`, test tiền |
| K4 | Dữ liệu lỗi không đi vào Gold, nhưng không bị xóa âm thầm | `ops.quarantine`, `ops.dq_issue` |
| K5 | Lịch sử seller có ý nghĩa | SCD2 chỉ đổi khi hạng giữ 2 kỳ, mini-dimension cho biến động tháng |
| K6 | Chạy lại không tạo dòng trùng | Test chạy lại đợt cuối |
| K7 | Có đủ tài liệu: bảng, cột, KPI | `docs/data_catalog.md`, `metrics.yml` |

## Yêu cầu về DSS

| Mã | Yêu cầu | Kiểm chứng bằng |
|---|---|---|
| D1 | Mỗi khuyến nghị có hành động và lý do | Test mọi khuyến nghị có lý do |
| D2 | Kế hoạch không vượt ngân sách và số suất | Test tối ưu, bài tính tay |
| D3 | Người dùng sửa được đề xuất | Bảng kéo thả, test trình duyệt |
| D4 | Không dùng dữ liệu tương lai | Train cách test ít nhất 45 ngày, feature đóng băng lúc chốt |
| D5 | Giả định được ghi rõ, đổi được | Mục Giả định trên giao diện, phân tích độ nhạy |
| D6 | Có so sánh với cách đơn giản | Màn Kiểm chứng |

## Yêu cầu về giao diện

| Mã | Yêu cầu | Kiểm chứng bằng |
|---|---|---|
| G1 | Mỗi màn hình vừa khung 1440 × 800, không cuộn | Test đo chiều cao nội dung |
| G2 | Tiêu đề biểu đồ nêu kết luận, tự sinh từ số liệu | Xem ảnh chụp |
| G3 | Mỗi KPI có chú thích định nghĩa và công thức | `metrics.yml`, test KPI có định nghĩa |
| G4 | Đổi as-of thì mọi màn hình đổi theo, trừ Kiểm chứng | Test trình duyệt |
| G5 | Số trên giao diện khớp SQL | Test đối chiếu |

## Ngoài phạm vi

- Giữ chân khách hàng: Olist ít đòn bẩy, khách mua trên các sàn lớn.
- Nạp thời gian thực, điều phối bằng Airflow, triển khai lên cloud.
- Đo hiệu quả can thiệp thật: cần A/B test, dữ liệu không có.
- Tối ưu tuyến xe, tồn kho.
- Bộ Marketing Funnel chưa được tích hợp ở phiên bản này.
