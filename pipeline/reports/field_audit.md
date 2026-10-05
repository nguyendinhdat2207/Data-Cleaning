# Báo cáo làm sạch dữ liệu: bảng giám sát chi tiết

File này được sinh tự động bởi `pipeline/05_field_audit.py`. Mọi con số trong cột "Ban đầu" và "Sau khi sửa" là kết quả của cùng một phép kiểm tra chạy trên `raw/` và `clean/`, không chép tay.

## 1. Cách chạy

```bash
cd pipeline
python3 01_profile.py      # khảo sát dữ liệu thô
python3 02_investigate.py  # điều tra sâu các bất thường
python3 03_clean.py        # làm sạch: raw/ -> clean/ + rejects/
python3 04_validate.py     # so sánh chất lượng trước / sau
python3 05_field_audit.py  # sinh báo cáo này
```

- `raw/`: dữ liệu gốc, không bao giờ bị sửa.
- `clean/`: dữ liệu sau khi làm sạch.
- `rejects/`: các dòng bị cách ly, kèm cột `reject_reason`.
- Các hàm sửa lỗi nằm trong `common.py`, các bước áp dụng nằm trong `03_clean.py`.

## 2. Dữ liệu ban đầu

| File | Số dòng | Các trường |
| --- | --- | --- |
| customers.csv | 506 | customer_id, name, email, phone, gender, birth_date, province, registration_date |
| products.csv | 100 | product_id, product_name, category, price |
| orders.csv | 1505 | order_id, customer_id, order_date, status, total_amount |
| order_items.csv | 3776 | order_id, product_id, quantity, unit_price |


Quan hệ: `customers.customer_id` 1-n `orders.customer_id`, `orders.order_id` 1-n `order_items.order_id`, `products.product_id` 1-n `order_items.product_id`.

## 3. Cách đọc bảng

Tổng cộng 33 dòng kiểm tra: 24 ĐẠT, 8 LƯU Ý, 1 XUNG ĐỘT.

- **ĐẠT**: lỗi đã về 0 sau khi sửa.
- **LƯU Ý**: giữ nguyên hoặc dùng giả định có chủ đích, có lý do ghi trong bảng.
- **XUNG ĐỘT**: mâu thuẫn còn tồn tại trong dữ liệu sạch, chưa sửa.
- Ví dụ trong ngoặc là vài giá trị vi phạm thật lấy từ dữ liệu.

## 4. Bảng giám sát theo từng file

### customers.csv (506 → 500 dòng)

| STT | Tên trường | Đặc điểm dữ liệu | Vấn đề dữ liệu đang gặp phải | Sửa kiểu gì, ở file nào | Ban đầu (raw) | Sau khi sửa (clean) | Kiểm tra lại |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | customer_id | Chuỗi, khoá chính của khách hàng. Phải duy nhất, không rỗng. Raw: 506 dòng, 0 rỗng, 500 giá trị khác nhau. | Có khách bị xuất 2 lần, mọi cột giống hệt nhau. | Xoá dòng trùng hoàn toàn, giữ 1 bản. 03_clean.py mục 1.1. | 6 (vd: C0038, C0131, C0192) | 0 | **ĐẠT** |
| 2 | name | Chuỗi, họ tên tiếng Việt có dấu. Không có quy tắc nghiệp vụ. Raw: 506 dòng, 0 rỗng, 140 giá trị khác nhau. | Không phát hiện lỗi. Tên trùng nhau là bình thường (nhiều người cùng tên). | Không sửa. | 0 | 0 | **ĐẠT** |
| 3 | email | Chuỗi, có thể rỗng. Nếu có thì phải đúng định dạng email. Raw: 506 dòng, 7 rỗng, 485 giá trị khác nhau. | Giá trị rác hoặc sai định dạng: N/A, -, unknown, abc@, thiếu @. | Hàm clean_email (common.py): rác hoặc sai định dạng thành rỗng. 03_clean.py mục 1.3. | 16 (vd: N/A, @mail.com, -) | 0 | **ĐẠT** |
| 4 | email | (như trên) | Ô email bị trống. | Không điền thêm. Không có cơ sở để đoán email. | 7 (vd: (rỗng)) | 23 (vd: (rỗng)). Tăng vì giá trị rác đã được đổi thành rỗng | **LƯU Ý** |
| 5 | phone | Chuỗi số điện thoại Việt Nam, chuẩn là 0XXXXXXXXX (10 số). Raw: 506 dòng, 0 rỗng, 500 giá trị khác nhau. | 3 kiểu viết lẫn lộn: có khoảng trắng (0982 276 804), có +84, hoặc đã chuẩn. | Hàm clean_phone (common.py): bỏ khoảng trắng, đổi +84 thành 0. 03_clean.py mục 1.4. | 353 (vd: 0982 276 804, 0918 348 136, 0986 237 088) | 0 | **ĐẠT** |
| 6 | gender | Chuỗi phân loại, chỉ nên có Male / Female. Raw: 506 dòng, 0 rỗng, 8 giá trị khác nhau. | 8 cách viết: male, M, Nam, Nữ, F, female... | Hàm clean_gender (common.py) ánh xạ theo bảng GENDER_MAP. 03_clean.py mục 1.2. | 379 (vd: Nam, F, female) | 0 | **ĐẠT** |
| 7 | province | Chuỗi phân loại tỉnh/thành, 7 tỉnh. Raw: 506 dòng, 7 rỗng, 29 giá trị khác nhau. | Cùng một tỉnh viết nhiều kiểu: HCMC, TP.HCM, hcm, Bắc Ninh, BN... | Hàm clean_province (common.py) ánh xạ theo PROVINCE_MAP. 03_clean.py mục 1.5. | 342 (vd: HCMC, Danang, Bắc Ninh) | 0 | **ĐẠT** |
| 8 | province | (như trên) | Ô trống hoặc ghi giả: -, N/A. | Hàm clean_province: giá trị giả thành rỗng. Không đoán tỉnh. | 15 (vd: (rỗng), -, N/A) | 15 (vd: (rỗng)). Toàn bộ là ô trống thật | **LƯU Ý** |
| 9 | birth_date | Ngày sinh. Phải hợp lệ, ở quá khứ, tuổi hợp lý. Chuẩn hoá về YYYY-MM-DD. Raw: 506 dòng, 0 rỗng, 497 giá trị khác nhau. | Trộn định dạng YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY. | Hàm parse_flex_date (common.py) đưa về ISO. 03_clean.py mục 1.6. | 316 (vd: 09/03/1962, 06/11/1992, 26/10/1962) | 0 | **ĐẠT** |
| 10 | birth_date | (như trên) | Ngày đọc được 2 cách, ví dụ 09/03/1962 là 9/3 hay 3/9. | parse_flex_date chọn DD/MM. Ghi cờ ambiguous_assumed_dmy ở cột birth_date_format_note. | 116 (vd: 09/03/1962, 06/11/1992, 09/02/1998) | 116 (vd: 1962-03-09, 1992-11-06, 1998-02-09). Đã chuyển ISO theo giả định DD/MM, có gắn cờ | **LƯU Ý** |
| 11 | birth_date | (như trên) | Ngày không tồn tại (31/02/2001), ở tương lai (2030) hoặc quá già (1890). | Để trống ngày sinh, cột birth_date_format_note ghi lý do (ngày vô lý thì kèm giá trị gốc). 03_clean.py mục 1.6. | 3 (vd: 2030-01-01, 1890-01-01, 31/02/2001) | 0 | **ĐẠT** |
| 12 | registration_date | Ngày đăng ký, định dạng ISO. Raw: 506 dòng, 0 rỗng, 394 giá trị khác nhau. | Không phát hiện lỗi định dạng hay ngày tương lai. | Không sửa. | 0 | 0 | **ĐẠT** |

### products.csv (100 → 100 dòng)

| STT | Tên trường | Đặc điểm dữ liệu | Vấn đề dữ liệu đang gặp phải | Sửa kiểu gì, ở file nào | Ban đầu (raw) | Sau khi sửa (clean) | Kiểm tra lại |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 13 | product_id | Chuỗi, khoá chính sản phẩm. Phải duy nhất. Raw: 100 dòng, 0 rỗng, 100 giá trị khác nhau. | Không phát hiện lỗi. | Không sửa. | 0 | 0 | **ĐẠT** |
| 14 | product_name | Chuỗi, tên sản phẩm. Raw: 100 dòng, 0 rỗng, 100 giá trị khác nhau. | Không phát hiện lỗi. | Không sửa. | 0 | 0 | **ĐẠT** |
| 15 | category | Chuỗi phân loại, 6 nhóm sản phẩm. Raw: 100 dòng, 0 rỗng, 12 giá trị khác nhau. | Viết hoa/thường khác nhau và dính khoảng trắng: FASHION, ' Sports ', sports. | Hàm clean_category (common.py): bỏ khoảng trắng, so khớp không phân biệt hoa thường. 03_clean.py mục 2.1. | 8 (vd: 'FASHION', ' Fashion ', ' Home ') | 0 | **ĐẠT** |
| 16 | price | Số thực, giá catalog. Phải dương. Raw: 100 dòng, 5 rỗng, 96 giá trị khác nhau. | Giá âm hoặc bằng 0: -1000, -50000, 0. | Đặt rỗng, lưu giá gốc ở cột price_raw_invalid. 03_clean.py mục 2.2. | 3 (vd: -1000.0, -50000.0, 0.0) | 0 | **ĐẠT** |
| 17 | price | (như trên) | Ô giá trống. | Không đoán giá. Giá bán trong order_items thay đổi theo khuyến mãi nên không dùng thay. | 5 (vd: (rỗng)) | 8 (vd: (rỗng)). Tăng vì 3 giá âm/0 đã được đổi thành rỗng | **LƯU Ý** |

### orders.csv (1505 → 1485 dòng)

| STT | Tên trường | Đặc điểm dữ liệu | Vấn đề dữ liệu đang gặp phải | Sửa kiểu gì, ở file nào | Ban đầu (raw) | Sau khi sửa (clean) | Kiểm tra lại |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 18 | order_id | Chuỗi, khoá chính đơn hàng. Phải duy nhất, không rỗng. Raw: 1505 dòng, 3 rỗng, 1498 giá trị khác nhau. | Đơn không có mã. | Cách ly vào rejects/orders_rejects.csv. 03_clean.py mục 3.1. | 3 (vd: đơn của khách C0435, đơn của khách C0265, đơn của khách C0129) | 0 | **ĐẠT** |
| 19 | order_id | (như trên) | Đơn bị xuất 2 lần, giống hệt nhau. | Xoá dòng trùng hoàn toàn. 03_clean.py mục 3.2. | 5 (vd: O00472, O00548, O00639) | 0 | **ĐẠT** |
| 20 | customer_id | Khoá ngoại, phải có trong customers.csv. Raw: 1505 dòng, 0 rỗng, 487 giá trị khác nhau. | Đơn trỏ tới khách không tồn tại. | Cách ly vào rejects/ (vi phạm khoá ngoại). 03_clean.py mục 3.3. | 12 (vd: C9977, C9956, C9982) | 0 | **ĐẠT** |
| 21 | order_date | Ngày đặt hàng. Chuẩn hoá về YYYY-MM-DD. Raw: 1505 dòng, 0 rỗng, 943 giá trị khác nhau. | Trộn định dạng YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY. | Hàm parse_flex_date (common.py). 03_clean.py mục 3.5. | 988 (vd: 01/14/2025, 21/05/2025, 02/10/2025) | 0 | **ĐẠT** |
| 22 | order_date | (như trên) | Ngày đọc được 2 cách. | Chọn DD/MM, ghi cờ ambiguous_assumed_dmy ở cột order_date_format_note. | 418 (vd: 02/10/2025, 07/07/2026, 08/05/2026) | 411 (vd: 2025-10-02, 2026-07-07, 2026-05-08). Đã chuyển ISO theo giả định DD/MM, có gắn cờ | **LƯU Ý** |
| 23 | order_date | (như trên) | Ngày đặt hàng sau hôm nay (21/09/2026). | Giữ nguyên. README không cấm đơn đặt trước. Chỉ ghi vào cleaning_log.md, chưa có cột cờ riêng. | 22 (vd: 03/12/2026, 07/12/2026, 02/11/2026) | 22 (vd: 2026-12-03, 2026-12-07, 2026-11-02). Giữ nguyên có chủ đích | **LƯU Ý** |
| 24 | order_date + customers.registration_date | Quan hệ giữa 2 bảng: đơn hàng thường không thể có trước ngày khách đăng ký. Raw: 1505 dòng, 0 rỗng, 943 giá trị khác nhau. | Đơn có ngày đặt trước ngày đăng ký. Khoảng 24% đơn có ngày ISO rõ ràng cũng bị, nên lỗi nằm ở dữ liệu gốc, không phải do parse. | CHƯA SỬA. README không nêu quy tắc này, và không biết ngày nào đúng. | 379 (vd: O00001, O00007, O00009) | 378 (vd: O00001, O00007, O00009). Xung đột còn tồn tại | **XUNG ĐỘT** |
| 25 | status | Chuỗi phân loại, 4 trạng thái: Pending, Processing, Completed, Cancelled. Raw: 1505 dòng, 0 rỗng, 14 giá trị khác nhau. | 14 cách viết: pending, PENDING, DONE, complete, Canceled, In Progress... | Hàm clean_status (common.py) ánh xạ theo STATUS_MAP. In Progress gộp vào Processing. 03_clean.py mục 3.4. | 1048 (vd: Canceled, PENDING, DONE) | 0 | **ĐẠT** |
| 26 | total_amount | Số thực. Phải bằng tổng quantity × unit_price của đơn đó. Raw: 1505 dòng, 0 rỗng, 1371 giá trị khác nhau. | Tổng tiền lệch so với chi tiết đơn hàng (chênh hơn 1 đồng). | Tính lại từ order_items sạch. Giá cũ lưu ở total_amount_original. 03_clean.py mục 5.1. | 45 (vd: O00015, O00039, O00065) | 0 | **ĐẠT** |
| 27 | total_amount | (như trên) | Đơn không còn dòng chi tiết nào sau khi làm sạch nên không kiểm chứng được tổng. | Giữ nguyên tổng gốc. | 0 | 3 (vd: O00257, O00923, O01013). Mọi dòng chi tiết của các đơn này đều bị cách ly. Giữ tổng gốc, chưa kiểm chứng | **LƯU Ý** |

### order_items.csv (3776 → 3710 dòng)

| STT | Tên trường | Đặc điểm dữ liệu | Vấn đề dữ liệu đang gặp phải | Sửa kiểu gì, ở file nào | Ban đầu (raw) | Sau khi sửa (clean) | Kiểm tra lại |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 28 | (cả dòng) | Mỗi dòng là một mặt hàng trong đơn. | Dòng trùng hoàn toàn (cùng order_id, product_id, quantity, unit_price). | Xoá bản trùng. 03_clean.py mục 4.1. | 6 (vd: O00153/P082/2/3808000.0, O00267/P067/1/1425000.0, O01024/P051/4/3671000.0) | 0 | **ĐẠT** |
| 29 | order_id | Khoá ngoại, phải có trong orders.csv. Raw: 3776 dòng, 0 rỗng, 1503 giá trị khác nhau. | Trỏ tới đơn không tồn tại (mã giả O995xx). | Cách ly vào rejects/order_items_rejects.csv. Dòng thuộc đơn đã bị cách ly cũng bị cách ly theo (cascade). 03_clean.py mục 4.2. | 6 (vd: O99532, O99894, O99405) | 0 | **ĐẠT** |
| 30 | product_id | Khoá ngoại, phải có trong products.csv. Raw: 3776 dòng, 0 rỗng, 107 giá trị khác nhau. | Trỏ tới sản phẩm không tồn tại (mã giả P99x). | Cách ly vào rejects/. 03_clean.py mục 4.3. | 10 (vd: P995, P992, P999) | 0 | **ĐẠT** |
| 31 | quantity | Số nguyên dương. Raw: 3776 dòng, 0 rỗng, 9 giá trị khác nhau. | Số lượng bằng 0 hoặc âm: 0, -1, -2, -3. | Hàm to_int (common.py). Không hợp lệ thì cách ly, vì không biết số lượng đúng. 03_clean.py mục 4.4. | 12 (vd: -1, 0, -2) | 0 | **ĐẠT** |
| 32 | unit_price | Số thực dương, giá bán tại thời điểm mua. Raw: 3776 dòng, 0 rỗng, 382 giá trị khác nhau. | Giá bằng 0 hoặc âm: 0, -10000. | Hàm to_float (common.py). Không hợp lệ thì cách ly. 03_clean.py mục 4.5. | 5 (vd: 0.0, -10000.0) | 0 | **ĐẠT** |
| 33 | order_id + product_id | Một sản phẩm có thể xuất hiện nhiều lần trong một đơn. Raw: 3776 dòng, 0 rỗng, 1503 giá trị khác nhau. | Cùng (order_id, product_id) nhưng khác số lượng hoặc giá. | Giữ nguyên. Có thể là 2 lần mua hợp lệ trong cùng đơn, không có bằng chứng là lỗi. | 30 (vd: O00075/P100, O00120/P030, O00123/P052) | 29 (vd: O00075/P100, O00120/P030, O00123/P052). Giữ nguyên có chủ đích | **LƯU Ý** |

## 5. Giám sát số dòng qua từng bước

Mỗi dòng gốc phải đi về đúng một nơi: `clean/`, bị xoá vì trùng hoàn toàn, hoặc nằm trong `rejects/`.

| File | Raw | Xoá trùng | Cách ly | Clean | Đối soát | Kết quả |
| --- | --- | --- | --- | --- | --- | --- |
| customers.csv | 506 | 6 | 0 | 500 | 500 + 6 + 0 = 506 | **ĐẠT** |
| products.csv | 100 | 0 | 0 | 100 | 100 + 0 + 0 = 100 | **ĐẠT** |
| orders.csv | 1505 | 5 | 15 | 1485 | 1485 + 5 + 15 = 1505 | **ĐẠT** |
| order_items.csv | 3776 | 6 | 60 | 3710 | 3710 + 6 + 60 = 3776 | **ĐẠT** |


Lý do cách ly trong `rejects/orders_rejects.csv`:

| Lý do | Số dòng |
| --- | --- |
| customer_id not found in customers.csv | 12 |
| blank order_id | 3 |


Lý do cách ly trong `rejects/order_items_rejects.csv`:

| Lý do | Số dòng |
| --- | --- |
| parent order was rejected during orders cleaning | 27 |
| quantity must be a positive integer | 12 |
| product_id not found in products.csv | 10 |
| order_id not found in orders.csv | 6 |
| unit_price must be positive | 5 |

## 6. Phần còn lại: xung đột và lưu ý

**Xung đột ngày đặt hàng trước ngày đăng ký.** 378/1485 đơn trong `clean/` có `order_date` sớm hơn `registration_date` của khách. Trong 514 đơn có ngày ISO rõ ràng (không phụ thuộc cách đọc) vẫn có 127 đơn (25%) bị lệch, nên lỗi nằm ở dữ liệu gốc chứ không phải do code đọc ngày sai. Chưa sửa vì đề bài không nêu quy tắc này và không có cơ sở biết ngày nào đúng. Cần hỏi bên cung cấp dữ liệu.

**Rủi ro của giả định DD/MM.** Trong các ngày đặt hàng chỉ đọc được một cách, có 307 ngày kiểu DD/MM và 253 ngày kiểu MM/DD, tức nguồn dùng lẫn cả hai. 411 ngày đặt hàng mơ hồ được đọc theo DD/MM và gắn cờ `ambiguous_assumed_dmy` để xem lại khi có thêm thông tin.

**Giữ nguyên có chủ đích** (theo lưu ý của đề bài: không phải bất thường nào cũng là lỗi):

- Đơn có ngày ở tương lai: có thể là đơn đặt trước, đề bài không cấm.
- Cùng sản phẩm trong một đơn nhưng khác số lượng hoặc giá: có thể là 2 lần mua hợp lệ.
- Đơn không còn dòng chi tiết sau khi lọc: giữ tổng gốc, chưa kiểm chứng được.
- Ô trống tăng lên (email, giá sản phẩm): do giá trị rác đã được đổi thành rỗng, không mất dữ liệu thật.
- Tên có dấu tiếng Việt, email có ký tự Unicode: dữ liệu hợp lệ.
