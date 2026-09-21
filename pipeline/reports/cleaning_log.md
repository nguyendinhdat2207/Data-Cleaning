# Cleaning log


### 1. CUSTOMERS
raw rows: 506
exact-duplicate rows removed: 6 (same customer_id + identical values in every column -> re-exported duplicate, not a real second customer)
gender values normalized to Male/Female: 375
email cleared (placeholder/junk or invalid format -> treated as missing): 16
phone reformatted to 0XXXXXXXXX: 350
phone left as-is, does not match VN 10-digit pattern after normalization: 0
province normalized via lookup table: 347
birth_date unparseable -> set to empty: 1
birth_date out of plausible range (future / age>100 / age<5) -> set to empty: 2
birth_date resolved via ambiguous-format DD/MM/YYYY assumption: 116 (documented assumption, see common.py:parse_flex_date docstring)

### 2. PRODUCTS
raw rows: 100
category text normalized (case variants): 3
price missing in source, left empty (no reliable basis to impute): 5
price <=0 (violates 'price must be positive'), nulled and flagged: 3

### 3. ORDERS
raw rows: 1505
rows with blank order_id (no primary key, 0 order_items, total=0) -> rejected: 3
exact-duplicate order rows removed (same order_id + identical values): 5
orders rejected: customer_id not found in customers.csv (FK violation): 12
orders rejected: order_date could not be parsed: 0
status text normalized to Pending/Processing/Completed/Cancelled: 1034
order_date resolved via ambiguous-format DD/MM/YYYY assumption: 411
order_date is after 'today' (2026-09-21) -- kept, flagged only (no business rule forbids future/scheduled orders): 22

### 4. ORDER_ITEMS
raw rows: 3776
exact-duplicate order_item rows removed (same order_id+product_id+quantity+unit_price): 6
NOTE: rows that share (order_id, product_id) but differ in quantity/unit_price are KEPT as separate line items -- no evidence they are erroneous duplicates rather than two legitimate order lines.
order_items rejected: order_id FK violation or cascade from rejected order: 33
order_items rejected: product_id not found in products.csv: 10
order_items rejected: quantity not a positive integer: 12
order_items rejected: unit_price not positive: 5

total_amount recomputed from clean order_items (line items = source of truth): 49 orders changed
orders with no remaining valid order_items -> original total_amount kept, unverifiable: 3

Total orders rejected: 15 / 1505
Total order_items rejected: 60 / 3776