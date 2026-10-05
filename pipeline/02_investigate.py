"""
Bước 2: điều tra sâu các bất thường tìm thấy ở bước 1, in kết quả ra màn hình.

Chạy: python3 02_investigate.py
Mục đích: quyết định cách xử lý dựa trên bằng chứng, ví dụ dòng trùng là trùng
hoàn toàn hay mâu thuẫn, ngày nào đọc được 2 cách, khoảng ngày có hợp lý không.
"""
import re
from collections import Counter
from datetime import datetime

from common import TODAY, load


def section(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


customers = load("customers.csv")
orders = load("orders.csv")
order_items = load("order_items.csv")

# --- Khách trùng mã: trùng hoàn toàn (xoá được) hay khác nội dung (không được xoá)? ---
section("Duplicate customer_id rows — are they exact dupes or conflicting?")
by_id = {}
for r in customers:
    by_id.setdefault(r["customer_id"], []).append(r)
for cid, rows in by_id.items():
    if len(rows) > 1:
        print(f"-- {cid} ({len(rows)} rows) --")
        for r in rows:
            print(f"   {r}")

# --- Ngày sinh không đọc được, ở tương lai, quá già hoặc dưới 5 tuổi ---
section("birth_date sanity: parse both formats, check range")
today = TODAY
bad_birth = []
for r in customers:
    v = r["birth_date"].strip()
    dt = None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(v, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        bad_birth.append((r["customer_id"], v, "unparseable"))
    elif dt > today:
        bad_birth.append((r["customer_id"], v, "future"))
    elif dt.year < 1920:
        bad_birth.append((r["customer_id"], v, "too old"))
    elif (today - dt).days / 365.25 < 5:
        bad_birth.append((r["customer_id"], v, "age<5"))
print(f"birth_date issues: {len(bad_birth)}")
for b in bad_birth[:30]:
    print(f"  {b}")

# --- Đếm ngày chỉ đọc được 1 cách (một số > 12) và ngày đọc được 2 cách (cả hai <= 12) ---
section("MM/DD/YYYY vs DD/MM/YYYY ambiguity check (day>12 disambiguates)")
ambiguous = Counter()
for r in customers:
    v = r["birth_date"].strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", v)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if a > 12 and b <= 12:
            ambiguous["first>12 => DD/MM/YYYY"] += 1
        elif b > 12 and a <= 12:
            ambiguous["second>12 => MM/DD/YYYY"] += 1
        elif a <= 12 and b <= 12:
            ambiguous["both<=12 ambiguous"] += 1
        else:
            ambiguous["both>12 invalid"] += 1
print(ambiguous)

for r in orders:
    v = r["order_date"].strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", v)
    if m:
        a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if a > 12 and b <= 12:
            ambiguous["order:first>12 => DD/MM/YYYY"] += 1
        elif b > 12 and a <= 12:
            ambiguous["order:second>12 => MM/DD/YYYY"] += 1
        elif a <= 12 and b <= 12:
            ambiguous["order:both<=12 ambiguous"] += 1
        else:
            ambiguous["order:both>12 invalid"] += 1
print(ambiguous)

# --- Đơn trùng mã hoặc thiếu mã ---
section("Duplicate/blank order_id rows in orders.csv")
by_oid = {}
for r in orders:
    by_oid.setdefault(r["order_id"], []).append(r)
for oid, rows in by_oid.items():
    if len(rows) > 1:
        print(f"-- {oid!r} ({len(rows)} rows) --")
        for r in rows:
            print(f"   {r}")

# --- Khoảng ngày đăng ký và ngày đặt hàng ---
section("registration_date vs birth_date / order_date range")
reg_dates = [r["registration_date"] for r in customers]
print("min/max registration_date:", min(reg_dates), max(reg_dates))
order_dates_iso = []
for r in orders:
    v = r["order_date"].strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            order_dates_iso.append(datetime.strptime(v, fmt))
            break
        except ValueError:
            continue
print("order_date range:", min(order_dates_iso), max(order_dates_iso))

# --- Mẫu các dòng thiếu email hoặc tỉnh ---
section("Sample rows with missing email/province")
for r in customers:
    if not r["email"].strip() or not r["province"].strip():
        print(r)
