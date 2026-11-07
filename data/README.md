# Dữ liệu

Nguồn: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce) trên Kaggle. Dữ liệu là các đơn hàng từ 09/2016 đến 10/2018 đã được Olist ẩn danh.

Tải bằng Kaggle CLI, chạy từ thư mục gốc của dự án:

```powershell
kaggle datasets download -d olistbr/brazilian-ecommerce -p data/olist
Expand-Archive data/olist/brazilian-ecommerce.zip -DestinationPath data/olist/raw
```

| Thư mục | Nội dung | Có đưa lên GitHub không |
|---|---|---|
| `olist/raw/` | 9 CSV gốc, đầu vào của hệ thống | Có (repo private) |
| `funnel/raw/` | Bộ Marketing Funnel, hiện chưa dùng | Có (repo private) |
| `sample/` | 200 dòng đầu mỗi file, để xem cấu trúc | Có |
| `manifest.json` | Hash và số dòng của 9 CSV, kiểm tra khi dựng kho | Có |

Bản zip đã dùng có SHA-256 `967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784`.
