"""
Bước 3: làm sạch dữ liệu.

Chạy: python3 03_clean.py
Đọc raw/*.csv, áp dụng các quy tắc làm sạch, rồi ghi:
  clean/*.csv    dữ liệu đã làm sạch, dùng cho phân tích
  rejects/*.csv  các dòng bị cách ly, kèm cột reject_reason
Không file gốc nào trong raw/ bị sửa.
"""
from collections import defaultdict

from common import (
    CLEAN, REJECTS, TODAY,
    load, save, parse_flex_date, clean_email, clean_phone, clean_gender,
    clean_province, clean_status, clean_category, to_float, to_int,
)


def section(title):
    print(f"\n### {title}")


# Bỏ dòng trùng hoàn toàn (mọi cột giống nhau). Trả về (danh sách còn lại, số dòng đã xoá).
def drop_exact_duplicates(rows):
    seen, kept = set(), []
    for r in rows:
        key = tuple(r.items())
        if key not in seen:
            seen.add(key)
            kept.append(r)
    return kept, len(rows) - len(kept)


def reject(row, reason):
    return dict(row, reject_reason=reason)


# ===========================================================================
section("1. CUSTOMERS")
# ===========================================================================
customers_raw = load("customers.csv")
print(f"Số dòng gốc: {len(customers_raw)}")

# --- 1.1 Xoá khách bị xuất 2 lần (mọi cột giống hệt nhau) ---
customers_dedup, n_dup = drop_exact_duplicates(customers_raw)
print(f"Xoá dòng trùng hoàn toàn: {n_dup}")

customers_clean = []
stats = defaultdict(int)

for r in customers_dedup:
    row = dict(r)
    row["customer_id"] = r["customer_id"].strip()
    row["registration_date"] = r["registration_date"].strip()

    # --- 1.2 Giới tính: đưa về Male / Female ---
    gender = clean_gender(r["gender"])
    if gender and gender != r["gender"].strip():
        stats["gender"] += 1
    row["gender"] = gender or r["gender"].strip()

    # --- 1.3 Email: rác hoặc sai định dạng -> rỗng ---
    email, note = clean_email(r["email"])
    if note != "ok" and r["email"].strip():
        stats["email"] += 1
    row["email"] = email

    # --- 1.4 Số điện thoại: đưa về 0XXXXXXXXX ---
    phone, note = clean_phone(r["phone"])
    if note == "ok" and phone != r["phone"].strip():
        stats["phone"] += 1
    elif note == "nonstandard_length":
        stats["phone_nonstandard"] += 1
    row["phone"] = phone

    # --- 1.5 Tỉnh/thành: ánh xạ về tên chuẩn, giá trị giả -> rỗng ---
    province = clean_province(r["province"])
    if province != r["province"].strip():
        stats["province"] += 1
    row["province"] = province

    # --- 1.6 Ngày sinh: đưa về YYYY-MM-DD. Ngày không đọc được hoặc vô lý
    #         (tương lai, trên 100 tuổi, dưới 5 tuổi) -> để trống, ghi lại giá trị gốc ---
    dt, note = parse_flex_date(r["birth_date"])
    row["birth_date_format_note"] = note
    if dt is None:
        stats["birth_unparseable"] += 1
        row["birth_date"] = ""
    else:
        age_years = (TODAY - dt).days / 365.25
        if dt > TODAY or age_years > 100 or age_years < 5:
            stats["birth_out_of_range"] += 1
            row["birth_date"] = ""
            row["birth_date_format_note"] = f"{note}_out_of_range(raw={r['birth_date']})"
        else:
            row["birth_date"] = dt.strftime("%Y-%m-%d")
            if note == "ambiguous_assumed_dmy":
                stats["birth_ambiguous"] += 1

    customers_clean.append(row)

print(f"Chuẩn hoá giới tính: {stats['gender']}")
print(f"Email rác/sai định dạng -> rỗng: {stats['email']}")
print(f"Chuẩn hoá số điện thoại: {stats['phone']} (còn sai độ dài: {stats['phone_nonstandard']})")
print(f"Chuẩn hoá tỉnh/thành: {stats['province']}")
print(f"Ngày sinh không đọc được -> rỗng: {stats['birth_unparseable']}")
print(f"Ngày sinh vô lý -> rỗng: {stats['birth_out_of_range']}")
print(f"Ngày sinh mơ hồ, giả định DD/MM: {stats['birth_ambiguous']}")

save(customers_clean, "customers.csv", CLEAN, list(customers_raw[0].keys()) + ["birth_date_format_note"])
customer_ids = {r["customer_id"] for r in customers_clean}

# ===========================================================================
section("2. PRODUCTS")
# ===========================================================================
products_raw = load("products.csv")
print(f"Số dòng gốc: {len(products_raw)}")

CATEGORIES = ["Sports", "Fashion", "Home", "Electronics", "Books", "Beauty"]

products_clean = []
pstats = defaultdict(int)
for r in products_raw:
    row = dict(r)

    # --- 2.1 Danh mục: bỏ khoảng trắng, thống nhất hoa thường ---
    cat = clean_category(r["category"], CATEGORIES)
    if cat != r["category"].strip():
        pstats["category"] += 1
    row["category"] = cat

    # --- 2.2 Giá: rỗng thì giữ rỗng (không đoán). Giá <= 0 vi phạm quy tắc
    #         "giá phải dương" -> để trống, lưu giá gốc ở price_raw_invalid ---
    price = to_float(r["price"])
    if r["price"].strip() == "":
        pstats["price_missing"] += 1
        row["price"] = ""
    elif price is None or price <= 0:
        pstats["price_invalid"] += 1
        row["price_raw_invalid"] = r["price"]
        row["price"] = ""
    else:
        row["price"] = price
    products_clean.append(row)

print(f"Chuẩn hoá danh mục: {pstats['category']}")
print(f"Giá bị thiếu, giữ rỗng: {pstats['price_missing']}")
print(f"Giá <= 0 -> rỗng, gắn cờ: {pstats['price_invalid']}")

save(products_clean, "products.csv", CLEAN, list(products_raw[0].keys()) + ["price_raw_invalid"])
product_ids = {r["product_id"] for r in products_clean}

# ===========================================================================
section("3. ORDERS")
# ===========================================================================
orders_raw = load("orders.csv")
print(f"Số dòng gốc: {len(orders_raw)}")

# --- 3.1 Đơn không có order_id: không có khoá chính -> cách ly ---
order_rejects = [reject(r, "blank order_id (no primary key)") for r in orders_raw if not r["order_id"].strip()]
orders_with_id = [r for r in orders_raw if r["order_id"].strip()]
print(f"Đơn thiếu order_id -> cách ly: {len(order_rejects)}")

# --- 3.2 Xoá đơn bị xuất 2 lần ---
orders_dedup, n_dup = drop_exact_duplicates(orders_with_id)
print(f"Xoá dòng trùng hoàn toàn: {n_dup}")

orders_clean = []
ostats = defaultdict(int)

for r in orders_dedup:
    # --- 3.3 Khoá ngoại: customer_id phải có trong customers -> nếu không thì cách ly ---
    if r["customer_id"].strip() not in customer_ids:
        ostats["orphan_customer"] += 1
        order_rejects.append(reject(r, "customer_id not found in customers.csv (FK violation)"))
        continue

    row = dict(r)

    # --- 3.4 Trạng thái: đưa về 4 giá trị chuẩn ---
    status = clean_status(r["status"])
    if status != r["status"].strip():
        ostats["status"] += 1
    row["status"] = status

    # --- 3.5 Ngày đặt hàng: đưa về YYYY-MM-DD. Không đọc được -> cách ly.
    #         Ngày ở tương lai: giữ nguyên, chỉ đếm (đề bài không cấm đơn đặt trước) ---
    dt, note = parse_flex_date(r["order_date"])
    row["order_date_format_note"] = note
    if dt is None:
        ostats["date_unparseable"] += 1
        order_rejects.append(reject(r, f"order_date unparseable ({note})"))
        continue
    row["order_date"] = dt.strftime("%Y-%m-%d")
    if dt > TODAY:
        ostats["date_future"] += 1
    if note == "ambiguous_assumed_dmy":
        ostats["date_ambiguous"] += 1

    row["total_amount_original"] = r["total_amount"]
    orders_clean.append(row)

print(f"Khách không tồn tại -> cách ly: {ostats['orphan_customer']}")
print(f"Ngày đặt hàng không đọc được -> cách ly: {ostats['date_unparseable']}")
print(f"Chuẩn hoá trạng thái: {ostats['status']}")
print(f"Ngày đặt hàng mơ hồ, giả định DD/MM: {ostats['date_ambiguous']}")
print(f"Ngày đặt hàng ở tương lai (giữ nguyên): {ostats['date_future']}")

clean_order_ids = {r["order_id"] for r in orders_clean}
raw_order_ids = {r["order_id"] for r in orders_raw}

# ===========================================================================
section("4. ORDER_ITEMS")
# ===========================================================================
items_raw = load("order_items.csv")
print(f"Số dòng gốc: {len(items_raw)}")

# --- 4.1 Xoá dòng trùng hoàn toàn. Dòng cùng (order_id, product_id) nhưng khác
#         số lượng/giá được GIỮ, vì có thể là 2 lần mua hợp lệ ---
items_dedup, n_dup = drop_exact_duplicates(items_raw)
print(f"Xoá dòng trùng hoàn toàn: {n_dup}")

items_clean = []
item_rejects = []
istats = defaultdict(int)

for r in items_dedup:
    oid, pid = r["order_id"].strip(), r["product_id"].strip()

    # --- 4.2 Khoá ngoại order_id. Phân biệt mã không tồn tại với đơn cha đã bị cách ly ---
    if oid not in clean_order_ids:
        istats["orphan_order"] += 1
        reason = ("order_id not found in orders.csv (FK violation)" if oid not in raw_order_ids
                  else "parent order was rejected during orders cleaning (cascade)")
        item_rejects.append(reject(r, reason))
        continue

    # --- 4.3 Khoá ngoại product_id ---
    if pid not in product_ids:
        istats["orphan_product"] += 1
        item_rejects.append(reject(r, "product_id not found in products.csv (FK violation)"))
        continue

    # --- 4.4 Số lượng phải là số nguyên dương. Không đoán được số đúng -> cách ly ---
    qty = to_int(r["quantity"])
    if qty is None or qty <= 0:
        istats["quantity"] += 1
        item_rejects.append(reject(r, f"quantity must be a positive integer, got {r['quantity']!r}"))
        continue

    # --- 4.5 Đơn giá phải dương -> nếu không thì cách ly ---
    price = to_float(r["unit_price"])
    if price is None or price <= 0:
        istats["unit_price"] += 1
        item_rejects.append(reject(r, f"unit_price must be positive, got {r['unit_price']!r}"))
        continue

    items_clean.append(dict(r, quantity=qty, unit_price=price))

print(f"order_id không hợp lệ hoặc đơn cha bị cách ly: {istats['orphan_order']}")
print(f"product_id không tồn tại: {istats['orphan_product']}")
print(f"Số lượng không hợp lệ: {istats['quantity']}")
print(f"Đơn giá không hợp lệ: {istats['unit_price']}")

# ===========================================================================
section("5. TOTAL_AMOUNT")
# ===========================================================================
# --- 5.1 Tính lại tổng tiền từ order_items sạch (chi tiết là nguồn đúng theo quy tắc
#         "total_amount phải phù hợp với các mặt hàng"). Tổng gốc giữ ở total_amount_original.
#         Đơn không còn dòng chi tiết nào thì giữ tổng gốc vì không kiểm chứng được ---
sums = defaultdict(float)
for r in items_clean:
    sums[r["order_id"]] += r["quantity"] * r["unit_price"]

n_changed = n_unverifiable = 0
for row in orders_clean:
    oid = row["order_id"]
    if oid in sums:
        computed = round(sums[oid], 2)
        if abs(computed - (to_float(row["total_amount_original"]) or 0.0)) > 1.0:
            n_changed += 1
        row["total_amount"] = computed
    else:
        n_unverifiable += 1
        row["total_amount"] = row["total_amount_original"]

print(f"Đơn có tổng tiền được tính lại khác giá trị gốc: {n_changed}")
print(f"Đơn không còn chi tiết, giữ tổng gốc: {n_unverifiable}")

# ===========================================================================
section("6. GHI KẾT QUẢ")
# ===========================================================================
save(orders_clean, "orders.csv", CLEAN,
     list(orders_raw[0].keys()) + ["order_date_format_note", "total_amount_original"])
save(items_clean, "order_items.csv", CLEAN, list(items_raw[0].keys()))
save(order_rejects, "orders_rejects.csv", REJECTS, list(orders_raw[0].keys()) + ["reject_reason"])
save(item_rejects, "order_items_rejects.csv", REJECTS, list(items_raw[0].keys()) + ["reject_reason"])

print(f"Tổng đơn bị cách ly: {len(order_rejects)} / {len(orders_raw)}")
print(f"Tổng dòng chi tiết bị cách ly: {len(item_rejects)} / {len(items_raw)}")
print("Xong: clean/ và rejects/ đã được ghi.")
