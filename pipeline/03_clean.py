"""
Reproducible data cleaning pipeline for the e-commerce dataset.

Run: python3 pipeline/03_clean.py

Reads pipeline/raw/*.csv, applies documented cleaning rules, and writes:
  pipeline/clean/*.csv      -- cleaned, analysis-ready tables
  pipeline/rejects/*.csv    -- rows removed/quarantined, with a reason column
  pipeline/reports/cleaning_log.md -- human-readable log of every rule applied
                                       and how many rows/values it affected

No raw CSV is ever modified in place.
"""
from collections import defaultdict

from common import (
    RAW, CLEAN, REJECTS, REPORTS, TODAY,
    load, save, parse_flex_date, clean_email, clean_phone, clean_gender,
    clean_province, clean_status, clean_category, to_float, to_int,
)

log_lines = []


def log(msg):
    print(msg)
    log_lines.append(msg)


def section(title):
    log("\n" + "#" * 3 + " " + title)


# ===========================================================================
section("1. CUSTOMERS")
# ===========================================================================
customers_raw = load("customers.csv")
log(f"raw rows: {len(customers_raw)}")

seen = set()
customers_dedup = []
dup_exact_removed = 0
for r in customers_raw:
    key = tuple(r.items())
    if key in seen:
        dup_exact_removed += 1
        continue
    seen.add(key)
    customers_dedup.append(r)
log(f"exact-duplicate rows removed: {dup_exact_removed} "
    f"(same customer_id + identical values in every column -> re-exported duplicate, not a real second customer)")

customers_clean = []
stats = defaultdict(int)

for r in customers_dedup:
    row = dict(r)
    row["customer_id"] = r["customer_id"].strip()

    gender = clean_gender(r["gender"])
    if gender:
        stats["gender_normalized"] += 1 if gender != r["gender"].strip() else 0
    row["gender"] = gender or r["gender"].strip()

    email, email_note = clean_email(r["email"])
    if email_note in ("junk_token", "invalid_format") and r["email"].strip():
        stats["email_cleared_junk_or_invalid"] += 1
    row["email"] = email

    phone, phone_note = clean_phone(r["phone"])
    if phone_note == "ok" and phone != r["phone"].strip():
        stats["phone_reformatted"] += 1
    elif phone_note == "nonstandard_length":
        stats["phone_nonstandard_kept_as_is"] += 1
    row["phone"] = phone

    province = clean_province(r["province"])
    if province != r["province"].strip():
        stats["province_normalized"] += 1
    row["province"] = province

    dt, note = parse_flex_date(r["birth_date"])
    row["birth_date_format_note"] = note
    if dt is None:
        stats["birth_date_unparseable"] += 1
        row["birth_date"] = ""
    else:
        age_days = (TODAY - dt).days
        age_years = age_days / 365.25
        if dt > TODAY or age_years > 100 or age_years < 5:
            stats["birth_date_out_of_range"] += 1
            row["birth_date"] = ""
            row["birth_date_format_note"] = note + "_out_of_range(raw=" + r["birth_date"] + ")"
        else:
            row["birth_date"] = dt.strftime("%Y-%m-%d")
            if note == "ambiguous_assumed_dmy":
                stats["birth_date_ambiguous_assumed_dmy"] += 1

    row["registration_date"] = r["registration_date"].strip()
    customers_clean.append(row)

log(f"gender values normalized to Male/Female: {stats['gender_normalized']}")
log(f"email cleared (placeholder/junk or invalid format -> treated as missing): {stats['email_cleared_junk_or_invalid']}")
log(f"phone reformatted to 0XXXXXXXXX: {stats['phone_reformatted']}")
log(f"phone left as-is, does not match VN 10-digit pattern after normalization: {stats['phone_nonstandard_kept_as_is']}")
log(f"province normalized via lookup table: {stats['province_normalized']}")
log(f"birth_date unparseable -> set to empty: {stats['birth_date_unparseable']}")
log(f"birth_date out of plausible range (future / age>100 / age<5) -> set to empty: {stats['birth_date_out_of_range']}")
log(f"birth_date resolved via ambiguous-format DD/MM/YYYY assumption: {stats['birth_date_ambiguous_assumed_dmy']} "
    f"(documented assumption, see common.py:parse_flex_date docstring)")

cust_fields = list(customers_raw[0].keys()) + ["birth_date_format_note"]
save(customers_clean, "customers.csv", CLEAN, cust_fields)
customer_id_set = {r["customer_id"] for r in customers_clean}

# ===========================================================================
section("2. PRODUCTS")
# ===========================================================================
products_raw = load("products.csv")
log(f"raw rows: {len(products_raw)}")

canonical_categories = ["Sports", "Fashion", "Home", "Electronics", "Books", "Beauty"]

products_clean = []
prod_stats = defaultdict(int)
for r in products_raw:
    row = dict(r)
    cat = clean_category(r["category"], canonical_categories)
    if cat != r["category"].strip():
        prod_stats["category_normalized"] += 1
    row["category"] = cat

    price = to_float(r["price"])
    if r["price"].strip() == "":
        prod_stats["price_missing"] += 1
        row["price"] = ""
    elif price is None or price <= 0:
        prod_stats["price_invalid_nulled"] += 1
        row["price_raw_invalid"] = r["price"]
        row["price"] = ""
    else:
        row["price"] = price
    products_clean.append(row)

log(f"category text normalized (case variants): {prod_stats['category_normalized']}")
log(f"price missing in source, left empty (no reliable basis to impute): {prod_stats['price_missing']}")
log(f"price <=0 (violates 'price must be positive'), nulled and flagged: {prod_stats['price_invalid_nulled']}")

prod_fields = list(products_raw[0].keys()) + (["price_raw_invalid"] if prod_stats["price_invalid_nulled"] else [])
if "price_raw_invalid" not in prod_fields:
    prod_fields = prod_fields + ["price_raw_invalid"]
save(products_clean, "products.csv", CLEAN, prod_fields)
product_id_set = {r["product_id"] for r in products_clean}
price_by_product = {r["product_id"]: r["price"] for r in products_clean}

# ===========================================================================
section("3. ORDERS")
# ===========================================================================
orders_raw = load("orders.csv")
log(f"raw rows: {len(orders_raw)}")

orders_no_id = [r for r in orders_raw if not r["order_id"].strip()]
orders_with_id = [r for r in orders_raw if r["order_id"].strip()]
log(f"rows with blank order_id (no primary key, 0 order_items, total=0) -> rejected: {len(orders_no_id)}")

seen_oid = set()
orders_dedup = []
order_dup_removed = 0
for r in orders_with_id:
    key = tuple(r.items())
    if key in seen_oid:
        order_dup_removed += 1
        continue
    seen_oid.add(key)
    orders_dedup.append(r)
log(f"exact-duplicate order rows removed (same order_id + identical values): {order_dup_removed}")

orders_clean_stage = []
order_rejects = []
order_stats = defaultdict(int)

for r in orders_dedup:
    cid = r["customer_id"].strip()
    if cid not in customer_id_set:
        order_stats["orphan_customer_fk"] += 1
        rej = dict(r)
        rej["reject_reason"] = "customer_id not found in customers.csv (FK violation)"
        order_rejects.append(rej)
        continue

    row = dict(r)
    status = clean_status(r["status"])
    if status != r["status"].strip():
        order_stats["status_normalized"] += 1
    row["status"] = status

    dt, note = parse_flex_date(r["order_date"])
    row["order_date_format_note"] = note
    if dt is None:
        order_stats["order_date_unparseable"] += 1
        rej = dict(r)
        rej["reject_reason"] = f"order_date unparseable ({note})"
        order_rejects.append(rej)
        continue
    row["order_date"] = dt.strftime("%Y-%m-%d")
    if dt > TODAY:
        order_stats["order_date_future"] += 1
    if note == "ambiguous_assumed_dmy":
        order_stats["order_date_ambiguous_assumed_dmy"] += 1

    row["total_amount_original"] = r["total_amount"]
    orders_clean_stage.append(row)

log(f"orders rejected: customer_id not found in customers.csv (FK violation): {order_stats['orphan_customer_fk']}")
log(f"orders rejected: order_date could not be parsed: {order_stats['order_date_unparseable']}")
log(f"status text normalized to Pending/Processing/Completed/Cancelled: {order_stats['status_normalized']}")
log(f"order_date resolved via ambiguous-format DD/MM/YYYY assumption: {order_stats['order_date_ambiguous_assumed_dmy']}")
log(f"order_date is after 'today' (2026-09-21) -- kept, flagged only "
    f"(no business rule forbids future/scheduled orders): {order_stats['order_date_future']}")

order_id_set_clean = {r["order_id"] for r in orders_clean_stage}

# ===========================================================================
section("4. ORDER_ITEMS")
# ===========================================================================
order_items_raw = load("order_items.csv")
log(f"raw rows: {len(order_items_raw)}")

seen_oi = set()
oi_dedup = []
oi_dup_removed = 0
for r in order_items_raw:
    key = tuple(r.items())
    if key in seen_oi:
        oi_dup_removed += 1
        continue
    seen_oi.add(key)
    oi_dedup.append(r)
log(f"exact-duplicate order_item rows removed (same order_id+product_id+quantity+unit_price): {oi_dup_removed}")
log("NOTE: rows that share (order_id, product_id) but differ in quantity/unit_price are KEPT as separate "
    "line items -- no evidence they are erroneous duplicates rather than two legitimate order lines.")

oi_clean = []
oi_rejects = []
oi_stats = defaultdict(int)

for r in oi_dedup:
    oid = r["order_id"].strip()
    pid = r["product_id"].strip()

    if oid not in order_id_set_clean:
        # either the FK never existed, or the parent order was rejected/removed above
        reason = "order_id not found in orders.csv (FK violation)" if oid not in {x["order_id"] for x in orders_raw} \
            else "parent order was rejected during orders cleaning (cascade)"
        oi_stats["orphan_order_fk"] += 1
        rej = dict(r)
        rej["reject_reason"] = reason
        oi_rejects.append(rej)
        continue

    if pid not in product_id_set:
        oi_stats["orphan_product_fk"] += 1
        rej = dict(r)
        rej["reject_reason"] = "product_id not found in products.csv (FK violation)"
        oi_rejects.append(rej)
        continue

    qty = to_int(r["quantity"])
    if qty is None or qty <= 0:
        oi_stats["invalid_quantity"] += 1
        rej = dict(r)
        rej["reject_reason"] = f"quantity must be a positive integer, got {r['quantity']!r}"
        oi_rejects.append(rej)
        continue

    price = to_float(r["unit_price"])
    if price is None or price <= 0:
        oi_stats["invalid_unit_price"] += 1
        rej = dict(r)
        rej["reject_reason"] = f"unit_price must be positive, got {r['unit_price']!r}"
        oi_rejects.append(rej)
        continue

    row = dict(r)
    row["quantity"] = qty
    row["unit_price"] = price
    oi_clean.append(row)

log(f"order_items rejected: order_id FK violation or cascade from rejected order: {oi_stats['orphan_order_fk']}")
log(f"order_items rejected: product_id not found in products.csv: {oi_stats['orphan_product_fk']}")
log(f"order_items rejected: quantity not a positive integer: {oi_stats['invalid_quantity']}")
log(f"order_items rejected: unit_price not positive: {oi_stats['invalid_unit_price']}")

# ---------------------------------------------------------------------------
# Recompute orders.total_amount from the now-clean order_items (source of truth
# per business rule: "total_amount phai phu hop voi thong tin cac mat hang").
# ---------------------------------------------------------------------------
sums = defaultdict(float)
has_items = defaultdict(bool)
for r in oi_clean:
    sums[r["order_id"]] += r["quantity"] * r["unit_price"]
    has_items[r["order_id"]] = True

recomputed = 0
no_items_kept_original = 0
for row in orders_clean_stage:
    oid = row["order_id"]
    if has_items[oid]:
        computed = round(sums[oid], 2)
        original = to_float(row["total_amount_original"]) or 0.0
        if abs(computed - original) > 1.0:
            recomputed += 1
        row["total_amount"] = computed
    else:
        no_items_kept_original += 1
        row["total_amount"] = row["total_amount_original"]

log(f"\ntotal_amount recomputed from clean order_items (line items = source of truth): {recomputed} orders changed")
log(f"orders with no remaining valid order_items -> original total_amount kept, unverifiable: {no_items_kept_original}")

order_fields = list(orders_raw[0].keys()) + ["order_date_format_note", "total_amount_original"]
save(orders_clean_stage, "orders.csv", CLEAN, order_fields)

oi_fields = list(order_items_raw[0].keys())
save(oi_clean, "order_items.csv", CLEAN, oi_fields)

# ---------------------------------------------------------------------------
# Rejects
# ---------------------------------------------------------------------------
order_reject_fields = list(orders_raw[0].keys()) + ["reject_reason"]
oi_reject_fields = list(order_items_raw[0].keys()) + ["reject_reason"]

all_order_rejects = (
    [dict(r, reject_reason="blank order_id (no primary key)") for r in orders_no_id]
    + order_rejects
)
save(all_order_rejects, "orders_rejects.csv", REJECTS, order_reject_fields)
save(oi_rejects, "order_items_rejects.csv", REJECTS, oi_reject_fields)

log(f"\nTotal orders rejected: {len(orders_no_id) + len(order_rejects)} / {len(orders_raw)}")
log(f"Total order_items rejected: {len(oi_rejects)} / {len(order_items_raw)}")

with open(REPORTS / "cleaning_log.md", "w", encoding="utf-8") as f:
    f.write("# Cleaning log\n\n")
    f.write("\n".join(log_lines))

log("\nDone. Clean tables -> pipeline/clean/, rejects -> pipeline/rejects/, log -> pipeline/reports/cleaning_log.md")
