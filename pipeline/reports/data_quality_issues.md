# Data Quality Profiling & Issue Catalog

Nguồn: `pipeline/raw/*.csv` (bản gốc, không sửa tay).
Công cụ: `pipeline/01_profile.py`, `pipeline/02_investigate.py` (thuần Python, không pandas).

Các vấn đề được phân loại theo 6 tiêu chí chất lượng dữ liệu (DAMA):
**Completeness, Uniqueness, Validity, Consistency, Accuracy, Integrity.**

---

## 1. Completeness (thiếu dữ liệu)

| Bảng | Cột | Vấn đề | Số lượng |
|---|---|---|---|
| customers | email | rỗng | 7/506 |
| customers | email | placeholder rác (`N/A`, `-`, `unknown`, `abc@`, `@mail.com`...) — thực chất là thiếu | 16/506 |
| customers | province | rỗng hoặc placeholder (`-`, `N/A`) | 15/506 |
| products | price | rỗng | 5/100 |

**Quyết định:** không suy diễn giá trị còn thiếu (không impute). Email/province rác được coi là "missing" và để trống thay vì giữ giá trị vô nghĩa. `price` rỗng giữ nguyên rỗng — không có cơ sở đáng tin cậy để ước tính giá sản phẩm (giá bán thực tế trong `order_items.unit_price` dao động rất lớn theo thời gian/khuyến mãi nên không dùng làm giá catalog).

## 2. Uniqueness (trùng lặp)

| Bảng | Vấn đề | Số lượng |
|---|---|---|
| customers | 6 `customer_id` có 2 dòng **giống hệt nhau** từng ký tự | 6 cặp |
| orders | 3 dòng `order_id` rỗng | 3 dòng |
| orders | 5 `order_id` có 2 dòng **giống hệt nhau** | 5 cặp |
| order_items | 6 cặp `(order_id, product_id, quantity, unit_price)` giống hệt nhau | 6 cặp |
| order_items | 36 cặp `(order_id, product_id)` trùng nhưng khác `quantity`/`unit_price` | 36 cặp |

**Quyết định:**
- Dòng **giống hệt nhau tuyệt đối** (mọi cột đều trùng) = bản ghi bị xuất trùng do lỗi hệ thống → xoá bản sao, giữ 1 bản.
- 36 cặp `(order_id, product_id)` trùng nhưng số liệu khác nhau **KHÔNG bị coi là lỗi** — không có bằng chứng đây là lỗi trùng lặp thay vì 2 dòng hàng hợp lệ (vd: mua cùng sản phẩm 2 đợt trong cùng đơn). Giữ nguyên theo nguyên tắc "không xoá nếu không chắc chắn có lý do".

## 3. Validity (sai định dạng / vi phạm ràng buộc miền giá trị)

| Bảng | Cột | Vấn đề | Số lượng |
|---|---|---|---|
| customers | birth_date | 2 định dạng trộn lẫn: `YYYY-MM-DD` và `DD/MM/YYYY` hoặc `MM/DD/YYYY` | 316/506 không phải ISO |
| customers | birth_date | ngày không hợp lệ: `2030-01-01` (tương lai), `1890-01-01` (quá xa/tuổi ~136), `31/02/2001` (ngày không tồn tại) | 3 |
| customers | email | sai định dạng email (không có `@`, thiếu domain...) | thuộc 16 ở mục Completeness |
| customers | phone | nhiều định dạng: số trần, có khoảng trắng, có `+84`/`84` | 353/506 không chuẩn |
| products | price | `<=0`: `-1000`, `-50000`, `0` | 3/100 |
| orders | order_date | cùng vấn đề trộn định dạng như birth_date | 988/1505 không phải ISO |
| order_items | quantity | `<=0` hoặc không nguyên | 12/3776 |
| order_items | unit_price | `<=0` | 5/3776 |

**Quyết định:**
- **Ngày tháng:** chuẩn hoá hết về ISO `YYYY-MM-DD`. Với chuỗi `xx/xx/yyyy`, nếu một trong hai số đầu >12 thì định dạng bị ép buộc duy nhất (vd `29/01/1984` chỉ có thể là DD/MM). Với các dòng thực sự mơ hồ (cả hai số đều <=12), áp dụng **giả định có ghi chú rõ**: DD/MM/YYYY (quy ước Việt Nam, đồng thời là mẫu số đông trong các trường hợp *không* mơ hồ của chính bộ dữ liệu này — DD/MM chiếm ~54–58% các trường hợp có thể xác định chắc chắn). Giả định này được gắn cờ ở cột `*_format_note` trong bảng sạch (`ambiguous_assumed_dmy`) để có thể truy vết/xem lại, **không xoá dữ liệu**.
- Ngày không hợp lệ về mặt logic (tương lai, tuổi >100, tuổi <5, ngày không tồn tại) → set rỗng + ghi chú lý do trong `birth_date_format_note`, không xoá cả dòng khách hàng (các cột khác vẫn hữu ích).
- `price`, `quantity`, `unit_price` vi phạm ràng buộc nghiệp vụ tường minh trong README ("phải dương", "phải nguyên dương") → với `products.price` (không có bảng cha bị ảnh hưởng) nulled + gắn cờ `price_raw_invalid`; với `order_items` (có ảnh hưởng dây chuyền đến `total_amount`) → đưa vào quarantine (`rejects/order_items_rejects.csv`) vì không thể an toàn "sửa" một số lượng/giá âm/bằng 0 thành giá trị đúng.
- `phone` chuẩn hoá về dạng `0XXXXXXXXX` (bỏ khoảng trắng/gạch nối, chuyển `+84`/`84` về `0`).

## 4. Consistency (biểu diễn không nhất quán cho cùng một giá trị)

| Bảng | Cột | Số biến thể phát hiện | Ví dụ |
|---|---|---|---|
| customers | gender | 8 | `male/Male/M/Nam` → Male; `female/Female/F/Nữ` → Female |
| customers | province | 29 | `HCMC/TP.HCM/Ho Chi Minh/hcm/Ho Chi Minh City` → 1 giá trị chuẩn |
| products | category | 9 | `FASHION/sports/SPORTS` → `Fashion/Sports` |
| orders | status | 14 | `Pending/pending/PENDING` → `Pending`; `In Progress` gộp vào `Processing`; `complete/completed/DONE` → `Completed`; `Cancelled/CANCELLED/cancelled/Canceled` → `Cancelled` |

**Quyết định:** xây bảng ánh xạ (lookup table) tường minh trong `pipeline/common.py` cho từng cột phân loại, chuẩn hoá về **một** giá trị canonical duy nhất mỗi nhóm. `In Progress` được gộp với `Processing` vì cùng ý nghĩa nghiệp vụ (đơn đang xử lý), không phải trạng thái thứ 5 riêng biệt — đây là giả định nghiệp vụ hợp lý nhất với 4 trạng thái vòng đời đơn hàng chuẩn (Pending → Processing → Completed/Cancelled).

## 5. Accuracy (giá trị hợp lệ về định dạng nhưng sai về ý nghĩa/nghiệp vụ)

| Bảng | Vấn đề | Số lượng |
|---|---|---|
| orders | `total_amount` không khớp tổng `quantity * unit_price` của `order_items` | 45/1505 trước cleaning |
| orders | `order_date` sau ngày hiện tại (2026-09-21) | 22 |

**Quyết định:**
- Theo quy tắc nghiệp vụ tường minh ("total_amount phải phù hợp với thông tin các mặt hàng"), `order_items` (chi tiết dòng hàng) được coi là **nguồn sự thật**, `total_amount` được **tính lại** từ tổng các dòng `order_items` hợp lệ sau khi làm sạch. Giá trị gốc được giữ lại ở cột `total_amount_original` để audit.
- Với đơn hàng không còn `order_items` hợp lệ nào sau khi lọc (bị quarantine hết), giữ nguyên `total_amount` gốc vì không có cơ sở tính lại — không suy diễn.
- `order_date` trong tương lai **không bị xoá/sửa** vì README không có quy tắc cấm đơn hàng có ngày tương lai (có thể là đơn đặt trước hoặc lỗi đồng hồ hệ thống nguồn) — chỉ gắn cờ để người dùng dữ liệu biết, không tự ý xử lý.

## 6. Integrity (toàn vẹn tham chiếu khoá ngoại)

| Bảng | Vấn đề | Số lượng |
|---|---|---|
| orders | `customer_id` không tồn tại trong `customers.csv` | 12/1505 |
| order_items | `order_id` không tồn tại trong `orders.csv` (mã giả kiểu `O995xx`) | 6/3776 |
| order_items | `product_id` không tồn tại trong `products.csv` (mã giả kiểu `P99x`) | 10/3776 |

**Quyết định:** các bản ghi vi phạm khoá ngoại được **cách ly (quarantine)** sang `pipeline/rejects/`, không đưa vào bảng sạch dùng cho phân tích, vì không thể tự suy ra khách hàng/đơn hàng/sản phẩm "đúng" mà bản ghi lẽ ra phải trỏ tới. Khi một `order` bị loại (do FK khách hàng sai hoặc trùng lặp), các `order_items` con của nó cũng bị loại theo (cascade), kèm lý do `"parent order was rejected during orders cleaning (cascade)"` để phân biệt với lỗi FK gốc.

---

## Những gì KHÔNG bị coi là lỗi (theo lưu ý của README: "không phải mọi bất thường đều là lỗi")

- Tên khách hàng có dấu tiếng Việt, ký tự Unicode trong email (`đặng.hùng252@example.com`) — giữ nguyên, đây là dữ liệu hợp lệ của một hệ thống Việt Nam, không phải lỗi.
- 36 cặp `(order_id, product_id)` trùng khoá nhưng khác số lượng/giá — giữ nguyên (xem mục Uniqueness).
- Đơn hàng có `order_date` trong tương lai — giữ nguyên, chỉ gắn cờ (xem mục Accuracy).
- Sự khác biệt giữa `unit_price` trong `order_items` và `price` hiện tại trong `products` — đây là điều **bình thường** (giá tại thời điểm mua khác giá catalog hiện tại do khuyến mãi/biến động giá theo thời gian), không sửa.

---

## Kết quả trước/sau (tóm tắt — chi tiết đầy đủ tại `validation_before_after.txt`)

| Chỉ số | Trước | Sau |
|---|---|---|
| customers: gender không chuẩn | 379 | 0 |
| customers: birth_date không phải ISO/không hợp lệ | 316 | 0 |
| customers: số cách viết tỉnh/thành khác nhau | 27 | 7 |
| products: price <=0/non-numeric | 3 | 0 |
| orders: order_id trùng/rỗng | 10 | 0 |
| orders: customer_id mồ côi (FK) | 12 | 0 |
| orders: số cách viết status khác nhau | 14 | 4 |
| order_items: FK mồ côi (order/product) | 16 | 0 |
| order_items: quantity/unit_price không hợp lệ | 17 | 0 |
| orders: total_amount lệch so với order_items | 45 | 0 |

Số dòng bị loại khỏi bảng sạch (đưa vào `rejects/`, không bị xoá vĩnh viễn):
- `orders`: 15/1505 (0/1505 dòng bị mất dữ liệu — có thể xem lại trong `rejects/orders_rejects.csv`)
- `order_items`: 66/3776 (6 trùng lặp bị xoá hẳn + 60 quarantine trong `rejects/order_items_rejects.csv`)
