"""
Bước 1: khảo sát (profiling) dữ liệu thô, in kết quả ra màn hình.

Chạy: python3 01_profile.py
Nội dung: số dòng, ô rỗng, khoá trùng, các cách viết của cột phân loại,
định dạng ngày/điện thoại/email, khoá ngoại, giá trị số bất thường.
"""
import re
from collections import Counter, defaultdict

from common import load


def pct(n, total):
    return f"{n}/{total} ({n/total*100:.1f}%)" if total else f"{n}/0"


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def profile_missing(rows, cols, total):
    for c in cols:
        missing = sum(1 for r in rows if r.get(c) is None or r.get(c).strip() == "")
        print(f"  {c:20s} missing: {pct(missing, total)}")


def show_counter(counter, label, top=30):
    print(f"  {label} ({len(counter)} distinct):")
    for val, cnt in counter.most_common(top):
        print(f"    {val!r:30s} {cnt}")


# --- Khảo sát customers: rỗng, trùng khoá, giới tính, ngày sinh, email, điện thoại, tỉnh ---
customers = load("customers.csv")
products = load("products.csv")
orders = load("orders.csv")
order_items = load("order_items.csv")

section(f"CUSTOMERS: {len(customers)} rows, cols={list(customers[0].keys())}")
profile_missing(customers, customers[0].keys(), len(customers))

ids = [r["customer_id"] for r in customers]
dup_ids = [k for k, v in Counter(ids).items() if v > 1]
print(f"  duplicate customer_id: {dup_ids}")

show_counter(Counter(r["gender"].strip() for r in customers), "gender values")

# birth_date formats
date_pat_counter = Counter()
for r in customers:
    v = r["birth_date"].strip()
    if not v:
        date_pat_counter["<empty>"] += 1
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        date_pat_counter["YYYY-MM-DD"] += 1
    elif re.match(r"^\d{2}/\d{2}/\d{4}$", v):
        date_pat_counter["MM/DD or DD/MM /YYYY"] += 1
    else:
        date_pat_counter[f"OTHER:{v}"] += 1
show_counter(date_pat_counter, "birth_date formats")

# email validity
email_bad = [r["email"] for r in customers if r["email"].strip() and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", r["email"].strip())]
print(f"  invalid-looking emails: {len(email_bad)} e.g. {email_bad[:5]}")

# phone formats
phone_pat_counter = Counter()
for r in customers:
    v = r["phone"].strip()
    digits = re.sub(r"\D", "", v)
    if not v:
        phone_pat_counter["<empty>"] += 1
    elif re.match(r"^0\d{9}$", digits) and " " not in v and "-" not in v:
        phone_pat_counter["plain 10-digit"] += 1
    elif " " in v or "-" in v:
        phone_pat_counter["has separators"] += 1
    else:
        phone_pat_counter[f"OTHER len={len(digits)}"] += 1
show_counter(phone_pat_counter, "phone formats")

show_counter(Counter(r["province"].strip() for r in customers), "province values", top=50)

reg_date_bad = [r["registration_date"] for r in customers if r["registration_date"].strip() and not re.match(r"^\d{4}-\d{2}-\d{2}$", r["registration_date"].strip())]
print(f"  registration_date not YYYY-MM-DD: {len(reg_date_bad)} e.g. {reg_date_bad[:5]}")

# --- Khảo sát products: trùng khoá, danh mục, giá <= 0 ---
section(f"PRODUCTS: {len(products)} rows, cols={list(products[0].keys())}")
profile_missing(products, products[0].keys(), len(products))
pids = [r["product_id"] for r in products]
dup_pids = [k for k, v in Counter(pids).items() if v > 1]
print(f"  duplicate product_id: {dup_pids}")
show_counter(Counter(r["category"].strip() for r in products), "category values", top=50)

price_bad = []
for r in products:
    v = r["price"].strip()
    if v:
        try:
            f = float(v)
            if f <= 0:
                price_bad.append((r["product_id"], v))
        except ValueError:
            price_bad.append((r["product_id"], v))
print(f"  price <=0 or non-numeric: {price_bad}")

# --- Khảo sát orders: trùng khoá, trạng thái, định dạng ngày, khoá ngoại tới customers ---
section(f"ORDERS: {len(orders)} rows, cols={list(orders[0].keys())}")
profile_missing(orders, orders[0].keys(), len(orders))
oids = [r["order_id"] for r in orders]
dup_oids = [k for k, v in Counter(oids).items() if v > 1]
print(f"  duplicate order_id: {dup_oids}")

show_counter(Counter(r["status"].strip() for r in orders), "status values", top=50)

order_date_pat = Counter()
for r in orders:
    v = r["order_date"].strip()
    if not v:
        order_date_pat["<empty>"] += 1
    elif re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        order_date_pat["YYYY-MM-DD"] += 1
    elif re.match(r"^\d{2}/\d{2}/\d{4}$", v):
        order_date_pat["MM/DD/YYYY or DD/MM/YYYY"] += 1
    else:
        order_date_pat[f"OTHER:{v}"] += 1
show_counter(order_date_pat, "order_date formats")

cust_id_set = set(ids)
orphan_orders = [r["order_id"] for r in orders if r["customer_id"].strip() not in cust_id_set]
print(f"  orders referencing missing customer_id: {len(orphan_orders)} e.g. {orphan_orders[:10]}")

total_amount_bad = []
for r in orders:
    v = r["total_amount"].strip()
    if v:
        try:
            f = float(v)
            if f < 0:
                total_amount_bad.append((r["order_id"], v))
        except ValueError:
            total_amount_bad.append((r["order_id"], v))
print(f"  total_amount negative/non-numeric: {total_amount_bad}")

# --- Khảo sát order_items: khoá ngoại, số lượng, đơn giá, cặp (order_id, product_id) trùng ---
section(f"ORDER_ITEMS: {len(order_items)} rows, cols={list(order_items[0].keys())}")
profile_missing(order_items, order_items[0].keys(), len(order_items))

order_id_set = set(oids)
prod_id_set = set(pids)
orphan_oi_order = [i for i, r in enumerate(order_items) if r["order_id"].strip() not in order_id_set]
orphan_oi_prod = [i for i, r in enumerate(order_items) if r["product_id"].strip() not in prod_id_set]
print(f"  order_items referencing missing order_id: {len(orphan_oi_order)}")
print(f"  order_items referencing missing product_id: {len(orphan_oi_prod)}")

qty_bad = []
for r in order_items:
    v = r["quantity"].strip()
    try:
        f = float(v)
        if f <= 0 or f != int(f):
            qty_bad.append((r["order_id"], r["product_id"], v))
    except ValueError:
        qty_bad.append((r["order_id"], r["product_id"], v))
print(f"  quantity not positive integer: {len(qty_bad)} e.g. {qty_bad[:10]}")

price_bad2 = []
for r in order_items:
    v = r["unit_price"].strip()
    if v:
        try:
            f = float(v)
            if f <= 0:
                price_bad2.append((r["order_id"], r["product_id"], v))
        except ValueError:
            price_bad2.append((r["order_id"], r["product_id"], v))
print(f"  unit_price <=0 or non-numeric: {len(price_bad2)} e.g. {price_bad2[:10]}")

dup_oi = Counter((r["order_id"], r["product_id"]) for r in order_items)
dup_oi_list = [k for k, v in dup_oi.items() if v > 1]
print(f"  duplicate (order_id, product_id) pairs in order_items: {len(dup_oi_list)} e.g. {dup_oi_list[:10]}")

# --- Kiểm tra chéo: total_amount so với tổng quantity × unit_price ---
section("CROSS-CHECK: total_amount vs sum(order_items)")
sums = defaultdict(float)
for r in order_items:
    try:
        q = float(r["quantity"])
        p = float(r["unit_price"])
        sums[r["order_id"]] += q * p
    except ValueError:
        pass

mismatch = []
for r in orders:
    oid = r["order_id"]
    try:
        stated = float(r["total_amount"])
    except ValueError:
        continue
    computed = sums.get(oid, 0.0)
    if abs(stated - computed) > 1.0:
        mismatch.append((oid, stated, computed))
print(f"  orders with total_amount != sum(items): {len(mismatch)} / {len(orders)}")
for m in mismatch[:15]:
    print(f"    {m}")

no_items = [r["order_id"] for r in orders if r["order_id"] not in sums]
print(f"  orders with zero order_items rows: {len(no_items)} e.g. {no_items[:10]}")
