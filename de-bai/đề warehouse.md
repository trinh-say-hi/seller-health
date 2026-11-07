## ĐHQG TPHCM
## TRƯỜNG ĐẠI HỌC BÁCH KHOA
### Khoa Khoa học và Kỹ thuật Máy tính
# QUY ĐỊNH BÀI TẬP LỚN
# Kho dữ liệu và Hệ hỗ trợ Quyết định
## CO4031 - Học kỳ 261
Mã học phần: CO4031
Số tín chỉ: 3 (ECTS: 6)
Học kỳ: 261 (Năm học 2026–2027)
Tỷ trọng đánh giá: 35% tổng điểm môn học
Giảng viên phụ trách: Đỗ Thanh Thái
### Tp. Hồ Chí Minh, ngày 10 tháng 09 năm 2026

---

CO4031 - Kho dữ liệu & Hệ hỗ trợ Quyết định Bài tập lớn - HK261
## Mục lục
1 Tổng quan 2
1.1 Mục tiêu bài tập lớn . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2
1.2 Đối chiếu chuẩn đầu ra học phần . . . . . . . . . . . . . . . . . . . . . . . . . 2
1.3 Hình thức và quy mô nhóm . . . . . . . . . . . . . . . . . . . . . . . . . . . . 2
2 Lịch trình và các mốc thời gian quan trọng 3
3 Đề tài và dữ liệu 3
3.1 Lựa chọn đề tài . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 3
3.2 Ví dụ lĩnh vực đề tài . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
4 Thuyết trình 4
4.1 Hình thức thuyết trình . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
4.2 Yêu cầu thuyết trình trực tiếp . . . . . . . . . . . . . . . . . . . . . . . . . . . 4
4.3 Yêu cầu video thuyết trình (cho nhóm không thuyết trình trực tiếp) . . . . . . . 5
5 Quy định nộp bài 5
5.1 Thành phần nộp . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
5.2 Cách thức nộp . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 5
6 Tài liệu tham khảo 5
Trang 1 / 6

---

CO4031 - Kho dữ liệu & Hệ hỗ trợ Quyết định Bài tập lớn - HK261
## 1 ## Tổng quan
### 1.1 ### Mục tiêu bài tập lớn
Bài tập lớn (Assignment) của môn học Kho dữ liệu và Hệ hỗ trợ Quyết định (CO4031) nhằm
mục tiêu đánh giá khả năng của sinh viên trong việc vận dụng kiến thức về kho dữ liệu (Data
Warehouse) và hệ hỗ trợ quyết định (Decision Support System) để giải quyết một bài toán thực
tế. Cụ thể, bài tập lớn yêu cầu sinh viên:
1. Phân tích yêu cầu nghiệp vụ và xác định bài toán cần giải quyết.
2. Thiết kế kho dữ liệu theo mô hình đa chiều (star schema / snowflake schema), bao gồm cả
quy trình ETL.
3. Hiện thực hệ thống hoàn chỉnh với backend (cơ sở dữ liệu, ETL, OLAP) và frontend
(dashboard / giao diện truy vấn).
4. Phát triển một thành phần hệ hỗ trợ quyết định (DSS) dựa trên kho dữ liệu đã xây dựng.
5. Đánh giá kết quả, phân tích hạn chế và đề xuất hướng phát triển.
6. Trình bày kết quả trước lớp hoặc qua video.
### 1.2 ### Đối chiếu chuẩn đầu ra học phần
Bài tập lớn đóng góp trực tiếp vào các chuẩn đầu ra (Learning Outcomes) sau đây, theo đề cương
môn học DCMH.CO4031.6.1:
Bảng 1: Đối chiếu chuẩn đầu ra và hoạt động đánh giá
Chuẩn đầu ra Mô tả Bài tập lớn
L.O.1.1 Giải thích các khái niệm cơ bản về DW và DSS ✓
L.O.1.2 Mô tả vai trò của DW trong DSS ✓
L.O.1.3 Nêu ví dụ thực tế về DW và DSS ✓
L.O.2.1 Mô tả quy trình và nguyên lý thiết kế DW ✓
L.O.2.2 Xác định các vấn đề liên quan đến thiết kế DW ✓
L.O.2.3 Thiết kế và hiện thực được hệ thống DW ✓
L.O.3.1 Giải thích khái niệm và đặc tính của MSS và DSS ✓
L.O.3.2 Giải thích các giai đoạn chính trong ra quyết định ✓
L.O.3.3 Minh họa quá trình mô hình hóa trong DSS ✓
L.O.4.1 Giải thích nguyên tắc phân tích, thiết kế DSS ✓
L.O.4.2 Phân tích, thiết kế, hiện thực một DSS đơn giản ✓
### 1.3 ### Hình thức và quy mô nhóm
• Hình thức: Làm việc theo nhóm, mỗi nhóm 2-3 sinh viên.
• Phân công: Mọi thành viên đều phải tham gia đóng góp vào công việc chung của nhóm.
Mỗi thành viên phải có vai trò rõ ràng (ví dụ: thiết kế DW, phát triển ETL, phát triển
frontend, xây dựng DSS, viết báo cáo).
Trang 2 / 6

---

CO4031 - Kho dữ liệu & Hệ hỗ trợ Quyết định Bài tập lớn - HK261
• Chấm điểm cá nhân: Điểm bài tập lớn của từng cá nhân có thể được điều chỉnh (cộng/trừ)
dựa trên mức độ đóng góp thực tế, được xác định thông qua peer review và đánh giá của
giảng viên trong buổi thuyết trình.
## 2 ## Lịch trình và các mốc thời gian quan trọng
Học kỳ 261 bắt đầu từ ngày 24/08/2026 (Tuần 1) và kết thúc ngày 06/12/2026 (Tuần 15). Học
kỳ gồm 15 tuần học và 1 tuần nghỉ giữa kỳ (Tuần 8), tổng 16 tuần.
Bảng 2: Lịch học kỳ 261
Tuần Từ ngày Đến ngày Hoạt động
1 24/08/2026 30/08/2026 Chương 1: Tổng quan DW & DSS
2 31/08/2026 06/09/2026 Chương 1 (tt): Tổng quan DW & DSS
3 07/09/2026 13/09/2026 Chương 2: Các vấn đề cơ bản trong DW (Quy
định BTL (10/09))
4 14/09/2026 20/09/2026 Chương 3: Thiết kế DW
5 21/09/2026 27/09/2026 Chương 3 (tt)
6 28/09/2026 04/10/2026 Chương 4: Hệ hỗ trợ quản lý (MSS)
7 05/10/2026 11/10/2026 Chương 5: DSS, mô hình và hỗ trợ
8 12/10/2026 18/10/2026 Nghỉ giữa kỳ
9 19/10/2026 25/10/2026 Chương 6: Chi tiết DSS
10 26/10/2026 01/11/2026 Chương 7: Mô hình hóa và phân tích
11 02/11/2026 08/11/2026 Chương 8: Phát triển DSS
12 09/11/2026 15/11/2026 Hoàn thiện dự án: Deadline nộp báo cáo (15/11)
13 16/11/2026 22/11/2026 Thuyết trình, Buổi 1
14 23/11/2026 29/11/2026 Thuyết trình, Buổi 2
15 30/11/2026 06/12/2026 Thuyết trình, Buổi 3
## 3 ## Đề tài và dữ liệu
### 3.1 ### Lựa chọn đề tài
Mỗi nhóm tự chọn đề tài và dữ liệu. Đề tài phải thỏa mãn các yêu cầu tối thiểu sau:
(a) Đề tài phải liên quan đến việc xây dựng kho dữ liệu (Data Warehouse) làm cốt lõi, phục
vụ phân tích và hỗ trợ ra quyết định.
(b) Dữ liệu nguồn có thể lấy từ: dữ liệu mở (open data), Kaggle, UCI Machine Learning
Repository, dữ liệu thực tế từ doanh nghiệp (có sự đồng ý của chủ dữ liệu) với quy mô
đủ lớn.
(c) Đề tài phải có ý nghĩa thực tế: giải quyết một bài toán phân tích hoặc ra quyết định cụ thể
trong một lĩnh vực nhất định.
Trang 3 / 6

---

CO4031 - Kho dữ liệu & Hệ hỗ trợ Quyết định Bài tập lớn - HK261
### 3.2 ### Ví dụ lĩnh vực đề tài
Dưới đây là một số gợi ý lĩnh vực (sinh viên không giới hạn trong danh sách này):
Bảng 3: Gợi ý lĩnh vực và đề tài
Lĩnh vực Gợi ý đề tài
Bán lẻ / Thương mại DW phân tích doanh số bán hàng đa kênh, hỗ trợ quyết định nhập hàng,
khuyến mãi
Ngân hàng / Tài chính DW phân tích rủi ro tín dụng, phát hiện gian lận, hỗ trợ cấp tín dụng
Y tế DW phân tích dịch bệnh, chất lượng điều trị, quản lý thuốc
Giáo dục DW phân tích kết quả học tập, dự báo sinh viên có nguy cơ bỏ học
Logistics DW phân tích hiệu suất vận tải, tối ưu tuyến đường, quản lý kho bãi
Thương mại điện tử DW phân tích hành vi người dùng, gợi ý sản phẩm, dự báo nhu cầu
Nông nghiệp DW phân tích năng suất cây trồng, dự báo thời tiết & giá cả nông sản
Viễn thông DW phân tích churn rate (tỷ lệ rời mạng), phân khúc khách hàng
Giao thông đô thị DW phân tích lưu lượng giao thông, hỗ trợ quy hoạch hạ tầng
## 4 ## Thuyết trình
### 4.1 ### Hình thức thuyết trình
Do số lượng nhóm lớn (dự kiến 21-30 nhóm), mỗi buổi học có 4-5 nhóm thuyết trình trực tiếp.
Các nhóm không thuyết trình trực tiếp phải quay video thuyết trình và upload lên YouTube
(chế độ unlisted) hoặc Google Drive, sau đó đính kèm link và trang bìa của báo cáo.
Bảng 4: Phân bổ thuyết trình
Buổi Tuần Ngày (Thứ 5) Hình thức
1 13 19/11/2026 4-5 nhóm thuyết trình trực tiếp
2 14 26/11/2026 4-5 nhóm thuyết trình trực tiếp
3 15 03/12/2026 4-5 nhóm thuyết trình trực tiếp
• Các nhóm còn lại nộp video thuyết trình (thời lượng 10-15 phút) cùng với báo cáo.
• Thuyết trình trực tiếp / video: sinh viên đăng ký với giảng viên.
### 4.2 ### Yêu cầu thuyết trình trực tiếp
• Thời lượng: 15 phút thuyết trình + 5 phút Q&A.
• Tất cả thành viên trong nhóm phải tham gia trình bày (chia phần rõ ràng).
Trang 4 / 6

---

CO4031 - Kho dữ liệu & Hệ hỗ trợ Quyết định Bài tập lớn - HK261
### 4.3 ### Yêu cầu video thuyết trình (cho nhóm không thuyết trình trực tiếp)
• Thời lượng: 10-15 phút.
• Tất cả thành viên trong nhóm phải xuất hiện và trình bày trong video.
• Chất lượng: hình ảnh rõ, âm thanh rõ ràng.
• Upload lên YouTube (unlisted) hoặc Google Drive, set quyền xem.
• Đính kèm link video vào trang bìa báo cáo khi nộp.
Bắt buộc
Tất cả các thành viên trong nhóm đều phải tham gia thuyết trình, kể cả trực tiếp lẫn
qua video, thì mới được tính điểm. Thành viên không tham gia thuyết trình sẽ bị trừ điểm
cá nhân hoặc không được tính điểm bài tập lớn.
## 5 ## Quy định nộp bài
### 5.1 ### Thành phần nộp
Mỗi nhóm nộp một file ZIP chứa:
1. Báo cáo (file PDF).
2. Mã nguồn (thư mục src/): bao gồm SQL scripts, Python/R code, frontend code, ETL
scripts (ưu tiên github, có thể access được)
3. Dữ liệu mẫu (thư mục data/): github/Google Drive.
4. Slide thuyết trình (file PDF): slide dùng để thuyết trình trực tiếp hoặc trong video.
5. Link video (nếu là nhóm thuyết trình qua video): trang bìa báo cáo.
### 5.2 ### Cách thức nộp
• Kênh 1: Nộp qua hệ thống e-learning (LMS) của môn học.
• Deadline: 23:59, ngày 15/11/2026 (Chủ nhật, cuối Tuần 12).
## 6 ## Tài liệu tham khảo
Sinh viên tham khảo các tài liệu sau (theo đề cương môn học DCMH.CO4031.6.1):
[1] W. H. Inmon, Building the Data Warehouse, 4th ed. Wiley, 2005.
[2] R. Kimball, M. Ross, The Data Warehouse Toolkit, 3rd ed. Wiley, 2013.
[3] E. Turban, J. E. Aronson, T.-P. Liang, Decision Support Systems and Intelligent Systems,
7th ed. Prentice-Hall, 2005.
[4] R. Elmasri, S. B. Navathe, Fundamentals of Database Systems, 7th ed. Addison-Wesley,
2016.
[5] R. Sharda, D. Delen, E. Turban, Analytics, Data Science, & Artificial Intelligence: Systems
for Decision Support, 7th ed. Pearson, 2020.
[6] J. Han, M. Kamber, J. Pei, Data Mining: Concepts and Techniques, 3rd ed. Morgan Kaufmann,
2012.
[7] F. Burstein, C. W. Holsapple, Handbook on Decision Support Systems. Springer, 2008.
Trang 5 / 6

---

CO4031 - Kho dữ liệu & Hệ hỗ trợ Quyết định Bài tập lớn - HK261
[8] Trần Minh Quang et al., Cơ sở dữ liệu: khái niệm, phương pháp, và kỹ thuật phân tích thiết
kế. NXB ĐHQG-HCM, 2025.
Tài liệu này được phát hành kèm theo học kỳ 261. Mọi thay đổi sẽ được thông báo qua kênh
lớp học.
Trang 6 / 6