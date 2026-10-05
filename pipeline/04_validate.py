"""
Bước 4: chạy lại các phép kiểm tra chất lượng trên raw/ và clean/, in bảng so sánh trước/sau.

Chạy: python3 04_validate.py
"""
import re
from collections import defaultdict

from common import RAW, CLEAN, load, to_float

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# --- Kiểm tra customers: trùng khoá, giá trị phân loại, định dạng email/phone/ngày ---
def check_customers(rows):
    return {
        "rows": len(rows),
        "duplicate customer_id": len(rows) - len({r["customer_id"] for r in rows}),
        "gender not in {Male,Female}": sum(r["gender"].strip() not in ("Male", "Female") for r in rows),
        "email present but invalid format": sum(bool(r["email"].strip()) and not EMAIL_RE.match(r["email"].strip())
                                                for r in rows),
        "phone not 0XXXXXXXXX": sum(bool(r["phone"].strip()) and not re.match(r"^0\d{9}$", r["phone"].strip())
                                    for r in rows),
        "distinct province spellings": len({r["province"].strip().lower() for r in rows if r["province"].strip()}),
        "birth_date not ISO": sum(bool(r["birth_date"].strip()) and not ISO_RE.match(r["birth_date"].strip())
                                  for r in rows),
        "email missing (blank)": sum(not r["email"].strip() for r in rows),
        "province missing (blank)": sum(not r["province"].strip() for r in rows),
    }


# --- Kiểm tra products: giá thiếu, giá <= 0, số cách viết danh mục ---
def check_products(rows):
    prices = [str(r["price"]).strip() for r in rows]
    return {
        "rows": len(rows),
        "price missing": sum(not p for p in prices),
        "price <=0 / non-numeric": sum(bool(p) and (to_float(p) is None or to_float(p) <= 0) for p in prices),
        "distinct category spellings": len({r["category"].strip() for r in rows}),
    }


# --- Kiểm tra orders: khoá chính, khoá ngoại tới customers, trạng thái, định dạng ngày ---
def check_orders(rows, customer_ids):
    return {
        "rows": len(rows),
        "duplicate order_id": len(rows) - len({r["order_id"] for r in rows}),
        "blank order_id": sum(not r["order_id"].strip() for r in rows),
        "orphan customer_id (FK violation)": sum(r["customer_id"].strip() not in customer_ids for r in rows),
        "distinct status spellings": len({r["status"].strip().lower() for r in rows}),
        "order_date not ISO": sum(bool(r["order_date"].strip()) and not ISO_RE.match(r["order_date"].strip())
                                  for r in rows),
    }


# --- Kiểm tra order_items: khoá ngoại, số lượng nguyên dương, đơn giá dương, dòng trùng ---
def check_order_items(rows, order_ids, product_ids):
    def bad_qty(v):
        f = to_float(v)
        return f is None or f <= 0 or f != int(f)

    keys = [(r["order_id"], r["product_id"], str(r["quantity"]), str(r["unit_price"])) for r in rows]
    return {
        "rows": len(rows),
        "orphan order_id (FK violation)": sum(r["order_id"].strip() not in order_ids for r in rows),
        "orphan product_id (FK violation)": sum(r["product_id"].strip() not in product_ids for r in rows),
        "quantity not positive integer": sum(bad_qty(str(r["quantity"]).strip()) for r in rows),
        "unit_price <=0 / non-numeric": sum((to_float(str(r["unit_price"]).strip()) or 0) <= 0 for r in rows),
        "exact-duplicate rows": len(keys) - len(set(keys)),
    }


# --- Kiểm tra chéo: total_amount phải bằng tổng quantity × unit_price của đơn ---
def check_totals(orders, items):
    sums = defaultdict(float)
    for r in items:
        q, p = to_float(r["quantity"]), to_float(r["unit_price"])
        if q is not None and p is not None:
            sums[r["order_id"]] += q * p
    mismatch = 0
    for r in orders:
        stated, computed = to_float(r["total_amount"]), sums.get(r["order_id"], 0.0)
        if stated is not None and computed and abs(stated - computed) > 1.0:
            mismatch += 1
    return {"orders where total_amount != sum(order_items)": mismatch}


def print_table(title, before, after):
    print(f"\n--- {title} ---")
    width = max(len(k) for k in before)
    print(f"  {'metric'.ljust(width)}  {'before':>10}  {'after':>10}")
    for k in before:
        print(f"  {k.ljust(width)}  {before[k]:>10}  {after[k]:>10}")


raw = {t: load(f"{t}.csv", RAW) for t in ("customers", "products", "orders", "order_items")}
clean = {t: load(f"{t}.csv", CLEAN) for t in ("customers", "products", "orders", "order_items")}


def ids(T, table, key):
    return {r[key] for r in T[table]}


print_table("CUSTOMERS", check_customers(raw["customers"]), check_customers(clean["customers"]))
print_table("PRODUCTS", check_products(raw["products"]), check_products(clean["products"]))
print_table("ORDERS",
            check_orders(raw["orders"], ids(raw, "customers", "customer_id")),
            check_orders(clean["orders"], ids(clean, "customers", "customer_id")))
print_table("ORDER_ITEMS",
            check_order_items(raw["order_items"], ids(raw, "orders", "order_id"), ids(raw, "products", "product_id")),
            check_order_items(clean["order_items"], ids(clean, "orders", "order_id"),
                              ids(clean, "products", "product_id")))
print_table("TOTALS", check_totals(raw["orders"], raw["order_items"]),
            check_totals(clean["orders"], clean["order_items"]))
