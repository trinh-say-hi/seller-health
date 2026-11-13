# Ghi chú viết báo cáo

Ghi ngày 13/11/2026, bám nhánh `power-bi`. Mỗi mục ghi: **viết gì**, **số liệu** (đã kiểm trong kho), **câu nên dùng**, **điều không được viết**. Phân tích người dùng và phân quyền đầy đủ ở [nguoi-dung-phan-quyen-va-ke-hoach-sua.md](nguoi-dung-phan-quyen-va-ke-hoach-sua.md).

Số liệu lấy từ bản kho đang phát hành. Dựng lại kho thì số không đổi (pipeline tất định), nhưng nên chạy lại `python -m tests.test_system` trước khi chốt báo cáo.

---

## 0. Khung báo cáo theo chuẩn đầu ra (Bảng 1 của đề)

| Chương báo cáo | Chuẩn đầu ra | Nội dung chính | Slide |
|---|---|---|---|
| 1. Bài toán và người dùng | L.O.1.3, L.O.3.2 | Bài toán giữ chân seller, 6 vai trò, 2 luồng quyết định, 4 pha Simon | Ch.4, Ch.5 |
| 2. Thiết kế kho | L.O.2.1–2.3 | Medallion, star schema, SCD2, mini-dimension, 26 đợt, đối soát | Ch.2, Ch.3 |
| 3. OLAP | L.O.1.2, L.O.2.3 | ROLAP (Streamlit, SQL trên DuckDB) và MOLAP (Power BI, VertiPaq), 5 thao tác OLAP | Ch.3 |
| 4. DSS | L.O.3.1, L.O.3.3, L.O.4.1–4.2 | Compound DSS, 4 phân hệ, mô hình (3 loại biến), MILP, Monte Carlo, what-if, kịch bản | Ch.6, Ch.7 |
| 5. Giao diện và phân quyền | L.O.4.2 | Chia vai Power BI / Streamlit theo người dùng, ma trận quyền, RLS | Ch.6 |
| 6. Đánh giá | L.O.4.2 | Kiểm chứng ngược 03–07/2018, độ nhạy, Monte Carlo, kiểm thử | Ch.5, Ch.7 |
| 7. Hạn chế và hướng phát triển | — | Mục 9 dưới đây | Ch.8 |

---

## 1. Bài toán và người dùng

**Viết gì:** bắt đầu từ quyết định, không bắt đầu từ công cụ. Câu hỏi trung tâm: *mỗi tháng, với ngân sách và số nhân viên có hạn, nên gọi seller nào, hỗ trợ seller nào, và có nên nới lời hẹn giao trên tuyến nào.*

**Hai luồng quyết định, hai chủ sở hữu (problem ownership, ch.5):**
- Luồng A, giữ chân seller: Trưởng nhóm Seller Success. Tiêu chí lựa chọn (principle of choice): tối đa GMV giữ được kỳ vọng trong ngân sách và số suất.
- Luồng B, lời hẹn giao: Quản lý vận hành giao nhận. Tiêu chí: số ngày hứa thêm nhỏ nhất để tỷ lệ trễ ≤ mục tiêu.

**Loại quyết định (ch.5):** bán cấu trúc. Phần cấu trúc là tối ưu chọn seller (MILP); phần phi cấu trúc là giả định hiệu quả can thiệp và việc chỉnh tay của người quyết định.

**Bảng 6 vai trò và bảng 4 pha:** chép từ mục 2 và 4 của tài liệu người dùng.

**Câu nên dùng:** "Hệ thống có hai nhóm người dùng với hai loại việc khác nhau: nhóm xem và theo dõi (Ban điều hành, Quản lý vùng) và nhóm ra quyết định (Trưởng nhóm Seller Success, Quản lý vận hành). Mỗi nhóm có một giao diện riêng, đọc chung một kho."

---

## 2. Thiết kế kho

**Số liệu:**

| Mục | Số |
|---|---|
| Nguồn | 9 file CSV Olist, kiểm SHA-256 với `data/manifest.json` |
| Đơn hàng | 99.441 (`core.fact_order`) |
| Dòng hàng | 112.650 (`core.fact_sales_item`) |
| Seller | 3.096, với 11.209 phiên bản trong `dim_seller` (SCD2) |
| Khách | 96.097 (`dim_customer`) |
| Hồ sơ sức khỏe (mini-dimension) | 361 tổ hợp |
| Đợt nạp | 26 (09/2016 – 10/2018) |
| Đối soát giữa các lớp | 286/286 khớp |
| Dòng cách ly | 42 (tọa độ ngoài Brazil) |

**Điểm cần nhấn:**
- Nạp theo tháng và che các mốc chưa xảy ra: mỗi đợt chỉ thấy quá khứ, nên đánh giá mô hình không rò rỉ tương lai.
- Ba loại fact theo Kimball: transaction (`fact_sales_item`), accumulating snapshot (`fact_order_seller`), periodic snapshot (`fact_seller_monthly`, `mart.kpi_monthly`).
- SCD2 có chủ đích: hạng ổn định chỉ đổi khi hạng tháng giữ nguyên 2 kỳ liên tiếp; dao động ngắn hạn tách ra mini-dimension.
- `dim_date` đóng nhiều vai (ngày mua, hẹn, nhận); trong Power BI là quan hệ hoạt động và không hoạt động (`USERELATIONSHIP`).

**Số chốt sổ và số mới nhất (giải thích hai trang KPI và OLAP):**
- `mart.kpi_monthly` là số chốt lúc đóng mỗi tháng; `core.fact_*` là trạng thái mới nhất.
- Với Olist, hai cách chỉ lệch ở review: 547 đơn có 2–3 review, 88 đơn có review sau đến ở tháng khác; điểm của đơn là trung bình các review nên đổi sau ngày chốt. GMV, số đơn, đơn trễ khớp hoàn toàn vì file nguồn không có ngày hủy (đơn hủy coi như hủy từ tháng mua).

**Không được viết:** "kho cập nhật thời gian thực", "mô phỏng đúng lịch sử hủy đơn".

---

## 3. OLAP

**Viết gì:** hai cách hiện thực OLAP trên cùng một kho, đặt cạnh nhau.

| | ROLAP | MOLAP |
|---|---|---|
| Ở đâu | Truy vấn SQL `GROUP BY ROLLUP` trên DuckDB (`src/app/screens_olap.py`, `src/sql/olap_examples.sql`) | Power BI chế độ Import, dữ liệu nạp vào VertiPaq |
| Dữ liệu | Đọc thẳng bảng Gold | Bản chụp Parquet do `xuat_parquet` xuất sau mỗi lần phát hành |
| Ưu | Luôn mới, không chép dữ liệu | Truy vấn nhanh, có semantic model, có RLS |
| Nhược | Mỗi lần xem là một truy vấn | Phải Refresh mới có số mới |
| HOLAP | — | Có thể đặt bảng tổng hợp Import (`kpi_monthly`) trên fact DirectQuery; chưa làm |

**5 thao tác OLAP trên Power BI trang "Doanh số dồn ở đâu?":** drill-down/roll-up bằng cây phân rã (vùng → bang → danh mục → hạng), slice bằng bộ lọc thời gian, dice bằng thời gian + hạng seller, pivot bằng cách đổi thứ tự tách trên cây.

**Kiểm chứng:** số trên Power BI khớp DuckDB từng tháng (GMV, số đơn, seller có bán, đơn đến hạn, đơn trễ, tỷ lệ trễ, review), cả toàn sàn (26/26 tháng, GMV 13.494.400,74) và dưới role Sudeste (26/26 tháng). Measure OLAP khớp truy vấn ROLAP của Streamlit, kể cả khi tách theo danh mục.

---

## 4. DSS

**Phân loại (ch.6):** Compound DSS = database-oriented (kho, OLAP) + solver-oriented (MILP qua HiGHS) + rule-oriented (bảng luật, lý do bằng chữ). Theo Alter: hệ thống ra đến mức đề xuất quyết định (suggestion), người dùng vẫn chỉnh và chốt.

**4 phân hệ (ch.6):**
- Dữ liệu: DuckDB medallion, Dagster, `catalog.yml`.
- Mô hình: `src/dss/` (logistic, luật, MILP, Monte Carlo), tham số mặc định lưu ở `dss.default_params`.
- Giao diện: Streamlit (ra quyết định), Power BI (xem, theo dõi).
- Tri thức: bảng luật hạng sức khỏe và lý do bằng chữ (`src/dss/rules.py`), định nghĩa KPI (`metrics.yml`) hiện ở dấu (?) trên giao diện.

**Mô hình theo 3 loại biến (ch.7):**

| Loại | Trong hệ thống |
|---|---|
| Biến quyết định | Mỗi seller: Gọi ngay, Hỗ trợ vận hành, Email tự động, Không làm gì |
| Biến không kiểm soát và tham số | Khả năng sụt (mô hình), GMV 90 ngày, chi phí 50/150 BRL, hiệu quả 20%/8%/30%/5%/3%, ngân sách 2.000 BRL, 40 suất, ngưỡng rủi ro 0,30, top 20% giá trị |
| Biến kết quả | GMV giữ được, tiền dùng, suất dùng, GMV rủi ro được xử lý |

**Công thức:**
- GMV rủi ro = khả năng sụt × GMV 90 ngày ÷ 2 (ước tính dựa trên dữ liệu và mô hình).
- Giữ được = GMV rủi ro × hiệu quả của hành động (hiệu quả là giả định).
- MILP: tối đa Σ giữ được, ràng buộc Σ chi phí ≤ ngân sách, Σ suất ≤ số suất, mỗi seller tối đa 1 hành động trả phí.

**Ra quyết định dưới rủi ro (ch.7) và Monte Carlo:** `src/dss/simulate.py`.
- Hai nguồn bất định: seller có sụt thật không (Bernoulli theo khả năng sụt), hiệu quả thật của từng loại hành động (tam giác quanh giả định ± độ bất định, dùng chung cho cả nhóm).
- Mốc 01/07/2018, kế hoạch mặc định, độ bất định ±50%, 2.000 lần: kỳ vọng 36.683 BRL (khớp đúng bộ tối ưu), khoảng P10–P90 khoảng 27,6k – 46,2k BRL. Không có lần nào giữ được ít hơn 2.000 BRL tiền chi, nhưng đó là hệ quả của giả định hiệu quả, không phải bằng chứng.
- Đã test: kỳ vọng mô phỏng bằng kỳ vọng của bộ tối ưu; độ bất định lớn hơn thì khoảng rộng hơn.

**Tương tác và kịch bản (ch.6 đặc tính 1):** Bảng kế hoạch cho đổi ngân sách, số suất, ngưỡng, top giá trị, mọi giả định chi phí và hiệu quả, độ bất định; kéo thẻ để chỉnh tay; lưu nhiều kịch bản và so sánh. Khác với "hard code công thức": tham số được đưa ra ngoài, mỗi lần đổi thì máy giải lại bài toán và cho ra **quyết định mới** (ai được gọi), không chỉ một con số mới.

**Vì sao phần này không làm trên Power BI:** DAX không có bộ giải tối ưu; Power BI chỉ đọc, không lưu thao tác kéo thả hay kịch bản; what-if của Power BI chỉ là nhân một hệ số, không đổi được danh sách seller.

**Influence diagram (ch.7):** cần vẽ: Ngân sách, Số suất, Ngưỡng → Tập ứng viên → MILP → Hành động → (× Hiệu quả giả định, × Khả năng sụt từ mô hình ← Feature từ kho) → GMV giữ được; Chi phí → Tiền dùng.

**Static và dynamic (ch.7):** mỗi mốc as-of là một bài toán tĩnh; chuỗi 13 mốc (09/2017 – 09/2018) cho thấy rủi ro tăng 2,5 lần trong khi ngân sách cố định.

---

## 5. Giao diện và phân quyền

**Chia vai:** chép bảng từ README mục "Hai giao diện, một kho" và tài liệu người dùng mục 2–3.

**Streamlit (5 màn, 2 luồng):**
- Giữ chân seller: 1 Cần chú ý tháng này → 2 Chi tiết seller → 3 Bảng kế hoạch → 4 Kiểm chứng.
- Giao nhận: What-if hẹn giao theo tuyến.

**Power BI (4 trang):** KPI tháng; Doanh số dồn ở đâu?; Giao hàng; Kế hoạch đề xuất.

**Điểm nối giữa hai luồng:** màn Chi tiết seller chẩn đoán lỗi ở khâu seller (→ hỗ trợ vận hành, luồng A) hay khâu vận chuyển (→ nút mở What-if hẹn giao, luồng B). Trang Giao hàng cho thấy 72,24% đơn trễ có seller đúng hạn.

**Phân quyền:** ma trận ở tài liệu người dùng mục 3.1.
- Đã có: RLS trên Power BI, role "Quản lý vùng Sudeste" lọc `dim_region`, lan qua `dim_seller` tới mọi fact và `kpi_monthly`. Kiểm bằng DAX: chỉ thấy Sudeste (2.287 seller), số khớp DuckDB, kế hoạch Sudeste 14 gọi + 4 hỗ trợ.
- Chưa có: đăng nhập cho Streamlit. Viết là thiết kế: Streamlit phục vụ một vai trò, triển khai nội bộ; muốn nhiều vai trò thì thêm xác thực (ví dụ OIDC) và kiểm quyền theo màn.

**Không được viết:** "Streamlit có phân quyền", "RLS đã cấu hình cho mọi vùng".

---

## 6. Đánh giá

**Kiểm chứng ngược 03–07/2018, cùng số seller (khoảng 30 mỗi tháng):**

| Cách chọn | Gọi trúng seller thật sự sụt | Phần GMV mất nằm trong danh sách |
|---|---|---|
| Kế hoạch DSS | 44–64%, trung bình 55% | 16–26%, trung bình 19% |
| Chọn theo GMV cao nhất | 21–31%, trung bình 26% | 16–31%, trung bình 25% |

Nói thẳng: DSS trúng nhiều hơn nhưng bao phủ ít tiền hơn ở 4/5 tháng, vì seller rất lớn có khả năng sụt thấp.

**Mô hình:** AUC dự báo sụt GMV 0,67–0,73, so với 0,66–0,73 khi chỉ dùng số ngày không bán. Kết luận: giá trị nằm ở việc chọn ai trong giới hạn nguồn lực và lý do đọc được, không ở độ chính xác dự báo.

**Độ nhạy (`dss.sensitivity`, trung bình các mốc):**

| Thay đổi | Danh sách trùng gốc | GMV giữ được |
|---|---|---|
| Ngân sách 1.000 BRL | 47% | −23% |
| Số suất 20 | 51% | −19% |
| Hiệu quả gọi điện 10% | 65% | −24% |
| Hiệu quả hỗ trợ 15% / 45% | 82% / 83% | −15% / +17% |
| Ngân sách 4.000 BRL | 87% | +5% |
| Hiệu quả gọi điện 30% | 88% | +26% |
| Số suất 80 | 100% | 0% |

Đọc: danh sách đổi mạnh khi cắt nguồn lực, khá vững khi giả định hiệu quả đổi; tăng ngân sách gấp đôi chỉ thêm 5% vì số suất là giới hạn thật.

**Kiểm thử:** test hệ thống (nguồn, các lớp, đối soát, chống rò rỉ, tối ưu, mô phỏng, cổng chất lượng), 65 trường hợp màn hình × mốc as-of, 15 test phát hành, đối chiếu DAX với DuckDB. Lấy số test mới nhất từ `evidence/test_results.json` khi viết.

---

## 7. Insight đáng đưa vào báo cáo (đã kiểm)

- Sàn tăng nhanh 2017 (GMV khoảng 120k tháng 01/2017 lên đỉnh 1 triệu tháng 11/2017, Black Friday), đi ngang 2018 quanh 0,85–1 triệu mỗi tháng.
- Số seller có bán tăng từ 226 (01/2017) lên khoảng 1.270 (08/2018), nhanh hơn GMV.
- Trễ hẹn tăng vọt 12/2017 (14,4%, đơn Black Friday dồn hẹn giao) và 03/2018 (17,5%); review tụt đúng hai tháng đó (3,88 và 3,71).
- 72,24% đơn khách nhận trễ có seller bàn giao đúng hạn: phần lớn trễ nằm ở vận chuyển.
- Bang Đông Bắc xa São Paulo (AL, MA) có tỷ lệ trễ cao nhất.
- GMV rủi ro tăng từ khoảng 175k (09/2017) lên 444k (09/2018), phần kế hoạch xử lý đi ngang 50–140k vì ngân sách cố định.

---

## 8. Câu được claim và không được claim

Chép mục 7 của tài liệu người dùng. Thêm:
- Được: "Khoảng giữ được P10–P90 phản ánh bất định của giả định."
- Không được: "Hệ thống giữ được 36.683 BRL", "Monte Carlo chứng minh kế hoạch có lãi".

---

## 9. Hạn chế và hướng phát triển

- Không có dữ liệu hiệu quả can thiệp thật; cần thí nghiệm có nhóm đối chứng (A/B) để đo.
- Nạp theo tháng là giả lập từ một bản CSV cuối; không có ngày hủy đơn.
- Streamlit chưa có đăng nhập; RLS mới có một vùng.
- Kế hoạch đã chốt ở Streamlit chưa chảy về kho, nên trang Kế hoạch đề xuất của Power BI hiện đề xuất mặc định, chưa phải quyết định cuối.
- What-if hẹn giao giả định thời gian giao không đổi, không đo được hẹn dài hơn làm mất bao nhiêu đơn.
- Power BI cần Windows và phải đổi tham số `ThuMucParquet` trên máy khác.
- DuckDB 2.0 không chịu được giao dịch lớn, nên đợt lỗi không rollback tự động; hệ thống dừng, ghi `failed`, chạy lại an toàn.
- Hướng phát triển: ghi kế hoạch đã chốt ra kho để khép vòng; xác thực và phân quyền cho Streamlit; HOLAP với DirectQuery; hiệu chỉnh xác suất của mô hình.

---

## 10. Hình nên chụp cho báo cáo

- Streamlit: 5 màn ở mốc 01/07/2018 (ảnh trong `evidence/screenshots/` sau khi chạy test UI, hoặc chụp tay).
- Power BI: 4 trang; trang KPI khi bấm một cột tháng (thấy "Kỳ đang xem" đổi); trang Kế hoạch đề xuất dưới "Xem dưới dạng" role Sudeste.
- Dagster: đồ thị asset và một lần chạy thành công.
- Sơ đồ: kiến trúc tổng thể, influence diagram, luồng A và B.
