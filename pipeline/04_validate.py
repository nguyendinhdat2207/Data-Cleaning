"""
Re-run data quality checks on the CLEAN tables and print a before/after
comparison against the RAW tables. This is the "chay lai cac phep kiem tra
va so sanh chat luong truoc/sau" step required by README.txt.
"""
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

from common import RAW, CLEAN, load

REPORTS = Path(__file__).parent / "reports"


def check_customers(rows):
    n = len(rows)
    dup_ids = n - len({r["customer_id"] for r in rows})
    bad_gender = sum(1 for r in rows if r["gender"].strip() not in ("Male", "Female"))
    bad_email = sum(1 for r in rows if r["email"].strip() and
                     not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", r["email"].strip()))
    bad_phone = sum(1 for r in rows if r["phone"].strip() and not re.match(r"^0\d{9}$", r["phone"].strip()))
    province_variants = len({r["province"].strip().lower() for r in rows if r["province"].strip()})
    bad_date = sum(1 for r in rows if r["birth_date"].strip() and
                    not re.match(r"^\d{4}-\d{2}-\d{2}$", r["birth_date"].strip()))
    missing_email = sum(1 for r in rows if not r["email"].strip())
    missing_province = sum(1 for r in rows if not r["province"].strip())
    return {
        "rows": n,
        "duplicate customer_id": dup_ids,
        "gender not in {Male,Female}": bad_gender,
        "email present but invalid format": bad_email,
        "phone not 0XXXXXXXXX": bad_phone,
        "distinct province spellings": province_variants,
        "birth_date not ISO / non-empty invalid": bad_date,
        "email missing (blank)": missing_email,
        "province missing (blank)": missing_province,
    }


def check_products(rows):
    n = len(rows)
    missing_price = sum(1 for r in rows if not str(r["price"]).strip())
    bad_price = 0
    for r in rows:
        v = str(r["price"]).strip()
        if v:
            try:
                if float(v) <= 0:
                    bad_price += 1
            except ValueError:
                bad_price += 1
    category_variants = len({r["category"].strip() for r in rows})
    return {
        "rows": n,
        "price missing": missing_price,
        "price <=0 / non-numeric": bad_price,
        "distinct category spellings": category_variants,
    }


def check_orders(rows, customer_ids):
    n = len(rows)
    dup_ids = n - len({r["order_id"] for r in rows})
    blank_id = sum(1 for r in rows if not r["order_id"].strip())
    orphan_customer = sum(1 for r in rows if r["customer_id"].strip() not in customer_ids)
    status_variants = len({r["status"].strip().lower() for r in rows})
    bad_date = sum(1 for r in rows if r["order_date"].strip() and
                    not re.match(r"^\d{4}-\d{2}-\d{2}$", r["order_date"].strip()))
    return {
        "rows": n,
        "duplicate order_id": dup_ids,
        "blank order_id": blank_id,
        "orphan customer_id (FK violation)": orphan_customer,
        "distinct status spellings": status_variants,
        "order_date not ISO": bad_date,
    }


def check_order_items(rows, order_ids, product_ids):
    n = len(rows)
    orphan_order = sum(1 for r in rows if r["order_id"].strip() not in order_ids)
    orphan_product = sum(1 for r in rows if r["product_id"].strip() not in product_ids)
    bad_qty = 0
    for r in rows:
        v = str(r["quantity"]).strip()
        try:
            f = float(v)
            if f <= 0 or f != int(f):
                bad_qty += 1
        except ValueError:
            bad_qty += 1
    bad_price = 0
    for r in rows:
        v = str(r["unit_price"]).strip()
        try:
            if float(v) <= 0:
                bad_price += 1
        except ValueError:
            bad_price += 1
    dup_exact = 0
    seen = set()
    for r in rows:
        key = (r["order_id"], r["product_id"], str(r["quantity"]), str(r["unit_price"]))
        if key in seen:
            dup_exact += 1
        seen.add(key)
    return {
        "rows": n,
        "orphan order_id (FK violation)": orphan_order,
        "orphan product_id (FK violation)": orphan_product,
        "quantity not positive integer": bad_qty,
        "unit_price <=0 / non-numeric": bad_price,
        "exact-duplicate rows": dup_exact,
    }


def check_totals(orders_rows, oi_rows, total_field="total_amount"):
    sums = defaultdict(float)
    for r in oi_rows:
        try:
            q = float(r["quantity"])
            p = float(r["unit_price"])
            sums[r["order_id"]] += q * p
        except ValueError:
            pass
    mismatch = 0
    for r in orders_rows:
        try:
            stated = float(r[total_field])
        except (ValueError, KeyError):
            continue
        computed = sums.get(r["order_id"], 0.0)
        if computed and abs(stated - computed) > 1.0:
            mismatch += 1
    return {"orders where total_amount != sum(order_items)": mismatch}


def print_table(title, before, after):
    print(f"\n--- {title} ---")
    keys = list(before.keys())
    width = max(len(k) for k in keys)
    print(f"  {'metric'.ljust(width)}  {'before':>10}  {'after':>10}")
    for k in keys:
        b = before.get(k, "-")
        a = after.get(k, "-")
        print(f"  {k.ljust(width)}  {str(b):>10}  {str(a):>10}")


raw_customers = load("customers.csv", RAW)
raw_products = load("products.csv", RAW)
raw_orders = load("orders.csv", RAW)
raw_oi = load("order_items.csv", RAW)

clean_customers = load("customers.csv", CLEAN)
clean_products = load("products.csv", CLEAN)
clean_orders = load("orders.csv", CLEAN)
clean_oi = load("order_items.csv", CLEAN)

out = []
def p(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)

import sys
class Tee:
    def __init__(self, *streams): self.streams = streams
    def write(self, s):
        for st in self.streams: st.write(s)
    def flush(self):
        for st in self.streams: st.flush()

report_path = REPORTS / "validation_before_after.txt"
with open(report_path, "w", encoding="utf-8") as f:
    orig_stdout = sys.stdout
    sys.stdout = Tee(orig_stdout, f)

    print_table("CUSTOMERS", check_customers(raw_customers), check_customers(clean_customers))
    print_table("PRODUCTS", check_products(raw_products), check_products(clean_products))
    print_table("ORDERS", check_orders(raw_orders, {r["customer_id"] for r in raw_customers}),
                check_orders(clean_orders, {r["customer_id"] for r in clean_customers}))
    print_table("ORDER_ITEMS",
                check_order_items(raw_oi, {r["order_id"] for r in raw_orders}, {r["product_id"] for r in raw_products}),
                check_order_items(clean_oi, {r["order_id"] for r in clean_orders}, {r["product_id"] for r in clean_products}))
    print_table("TOTALS",
                check_totals(raw_orders, raw_oi),
                check_totals(clean_orders, clean_oi))

    sys.stdout = orig_stdout

print(f"\nSaved to {report_path}")
