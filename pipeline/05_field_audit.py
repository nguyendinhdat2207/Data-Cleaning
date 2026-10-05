"""
Bước 5: bảng giám sát theo từng trường.

Chạy: python3 05_field_audit.py
Chạy CÙNG một phép kiểm tra trên raw/ và clean/, nên cột "Ban đầu" và "Sau khi sửa"
là số đo thật. Kết quả ghi vào reports/field_audit.md, file báo cáo duy nhất của bài.
"""
import re
from collections import Counter, defaultdict

from common import (
    RAW, CLEAN, REJECTS, REPORTS, TODAY, EMAIL_RE,
    load, parse_flex_date, to_float, to_int,
)

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLASH_RE = re.compile(r"^(\d{2})/(\d{2})/\d{4}$")
PHONE_RE = re.compile(r"^0\d{9}$")
JUNK = {"n/a", "na", "-", "unknown", "none", "null"}
GENDERS = {"Male", "Female"}
STATUSES = {"Pending", "Processing", "Completed", "Cancelled"}
CATEGORIES = {"Sports", "Fashion", "Home", "Electronics", "Books", "Beauty"}
PROVINCES = {"Ha Noi", "Ho Chi Minh City", "Da Nang", "Hai Phong", "Can Tho", "Bac Ninh", "Quang Ninh"}


# ---------------------------------------------------------------------------
# Hàm hỗ trợ: đọc bảng, đếm trùng, đọc ngày, các phép kiểm tra chéo giữa bảng.
# Mỗi phép kiểm tra nhận dict các bảng và trả về danh sách giá trị vi phạm.
# ---------------------------------------------------------------------------
def tables(folder):
    return {t: load(f"{t}.csv", folder) for t in ("customers", "products", "orders", "order_items")}


RAWT = tables(RAW)
CLEANT = tables(CLEAN)


def col(t, f):
    return [str(r[f]) for r in t]


def extra_dupes(values):
    return [v for v, n in Counter(values).items() for _ in range(n - 1)]


def exact_dupes(rows):
    return extra_dupes(["/".join(str(v) for v in r.values()) for r in rows])


def date_or_none(v):
    v = str(v).strip()
    return parse_flex_date(v)[0] if v else None


def implausible_birth(v):
    v = str(v).strip()
    if not v:
        return False
    dt = date_or_none(v)
    if dt is None:
        return True
    age = (TODAY - dt).days / 365.25
    return dt > TODAY or age > 100 or age < 5


def is_ambiguous(v):
    m = SLASH_RE.match(str(v).strip())
    return bool(m) and int(m.group(1)) <= 12 and int(m.group(2)) <= 12


def first_by_key(rows, key):
    out = {}
    for r in rows:
        out.setdefault(r[key], r)
    return out


def order_before_registration(T):
    reg = {k: r["registration_date"] for k, r in first_by_key(T["customers"], "customer_id").items()}
    bad = []
    for r in T["orders"]:
        od = date_or_none(r["order_date"])
        rd = reg.get(r["customer_id"].strip())
        if od and rd and od.strftime("%Y-%m-%d") < rd:
            bad.append(r["order_id"])
    return bad


def total_mismatch(T):
    sums = defaultdict(float)
    for r in T["order_items"]:
        q, p = to_float(r["quantity"]), to_float(r["unit_price"])
        if q is not None and p is not None:
            sums[r["order_id"]] += q * p
    bad = []
    for r in T["orders"]:
        stated = to_float(r["total_amount"])
        computed = sums.get(r["order_id"], 0.0)
        if stated is not None and computed and abs(stated - computed) > 1.0:
            bad.append(r["order_id"])
    return bad


def same_key_diff_values(T):
    groups = defaultdict(set)
    for r in T["order_items"]:
        groups[(r["order_id"], r["product_id"])].add((str(r["quantity"]), str(r["unit_price"])))
    return [f"{o}/{p}" for (o, p), v in groups.items() if len(v) > 1]


def profile(t, f):
    vals = col(RAWT[t], f)
    empty = sum(1 for v in vals if not v.strip())
    return f"Raw: {len(vals)} dòng, {empty} rỗng, {len(set(vals))} giá trị khác nhau"


C = "customers.csv"
P = "products.csv"
O = "orders.csv"
I = "order_items.csv"

# ---------------------------------------------------------------------------
# Danh sách dòng của bảng giám sát. Mỗi dòng gồm:
# (file, trường, đặc điểm, vấn đề, cách sửa, kiểm tra trên raw, kiểm tra trên clean
#  (None = dùng lại kiểm tra raw), ghi chú cột sau, kết luận dự kiến)
# ---------------------------------------------------------------------------
ROWS = [
    (C, "customer_id", "Chuỗi, khoá chính của khách hàng. Phải duy nhất, không rỗng.",
     "Có khách bị xuất 2 lần, mọi cột giống hệt nhau.",
     "Xoá dòng trùng hoàn toàn, giữ 1 bản. 03_clean.py mục 1.1.",
     lambda T: extra_dupes(col(T["customers"], "customer_id")), None, "", "ĐẠT"),
    (C, "name", "Chuỗi, họ tên tiếng Việt có dấu. Không có quy tắc nghiệp vụ.",
     "Không phát hiện lỗi. Tên trùng nhau là bình thường (nhiều người cùng tên).",
     "Không sửa.",
     lambda T: [v for v in col(T["customers"], "name") if not v.strip() or re.search(r"[\d@]", v)], None,
     "", "ĐẠT"),
    (C, "email", "Chuỗi, có thể rỗng. Nếu có thì phải đúng định dạng email.",
     "Giá trị rác hoặc sai định dạng: N/A, -, unknown, abc@, thiếu @.",
     "Hàm clean_email (common.py): rác hoặc sai định dạng thành rỗng. 03_clean.py mục 1.3.",
     lambda T: [v for v in col(T["customers"], "email") if v.strip() and not EMAIL_RE.match(v.strip())], None,
     "", "ĐẠT"),
    (C, "email", "(như trên)",
     "Ô email bị trống.",
     "Không điền thêm. Không có cơ sở để đoán email.",
     lambda T: [v for v in col(T["customers"], "email") if not v.strip()], None,
     "Tăng vì giá trị rác đã được đổi thành rỗng", "LƯU Ý"),
    (C, "phone", "Chuỗi số điện thoại Việt Nam, chuẩn là 0XXXXXXXXX (10 số).",
     "3 kiểu viết lẫn lộn: có khoảng trắng (0982 276 804), có +84, hoặc đã chuẩn.",
     "Hàm clean_phone (common.py): bỏ khoảng trắng, đổi +84 thành 0. 03_clean.py mục 1.4.",
     lambda T: [v for v in col(T["customers"], "phone") if not PHONE_RE.match(v.strip())], None, "", "ĐẠT"),
    (C, "gender", "Chuỗi phân loại, chỉ nên có Male / Female.",
     "8 cách viết: male, M, Nam, Nữ, F, female...",
     "Hàm clean_gender (common.py) ánh xạ theo bảng GENDER_MAP. 03_clean.py mục 1.2.",
     lambda T: [v for v in col(T["customers"], "gender") if v.strip() not in GENDERS], None, "", "ĐẠT"),
    (C, "province", "Chuỗi phân loại tỉnh/thành, 7 tỉnh.",
     "Cùng một tỉnh viết nhiều kiểu: HCMC, TP.HCM, hcm, Bắc Ninh, BN...",
     "Hàm clean_province (common.py) ánh xạ theo PROVINCE_MAP. 03_clean.py mục 1.5.",
     lambda T: [v for v in col(T["customers"], "province")
                if v.strip() and v.strip().lower() not in JUNK and v.strip() not in PROVINCES], None, "", "ĐẠT"),
    (C, "province", "(như trên)",
     "Ô trống hoặc ghi giả: -, N/A.",
     "Hàm clean_province: giá trị giả thành rỗng. Không đoán tỉnh.",
     lambda T: [v for v in col(T["customers"], "province") if not v.strip() or v.strip().lower() in JUNK], None,
     "Toàn bộ là ô trống thật", "LƯU Ý"),
    (C, "birth_date", "Ngày sinh. Phải hợp lệ, ở quá khứ, tuổi hợp lý. Chuẩn hoá về YYYY-MM-DD.",
     "Trộn định dạng YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY.",
     "Hàm parse_flex_date (common.py) đưa về ISO. 03_clean.py mục 1.6.",
     lambda T: [v for v in col(T["customers"], "birth_date") if v.strip() and not ISO_RE.match(v.strip())], None,
     "", "ĐẠT"),
    (C, "birth_date", "(như trên)",
     "Ngày đọc được 2 cách, ví dụ 09/03/1962 là 9/3 hay 3/9.",
     "parse_flex_date chọn DD/MM. Ghi cờ ambiguous_assumed_dmy ở cột birth_date_format_note.",
     lambda T: [v for v in col(T["customers"], "birth_date") if is_ambiguous(v)],
     lambda T: [r["birth_date"] for r in T["customers"] if r["birth_date_format_note"] == "ambiguous_assumed_dmy"],
     "Đã chuyển ISO theo giả định DD/MM, có gắn cờ", "LƯU Ý"),
    (C, "birth_date", "(như trên)",
     "Ngày không tồn tại (31/02/2001), ở tương lai (2030) hoặc quá già (1890).",
     "Để trống ngày sinh, cột birth_date_format_note ghi lý do (ngày vô lý thì kèm giá trị gốc). 03_clean.py mục 1.6.",
     lambda T: [v for v in col(T["customers"], "birth_date") if implausible_birth(v)], None, "", "ĐẠT"),
    (C, "registration_date", "Ngày đăng ký, định dạng ISO.",
     "Không phát hiện lỗi định dạng hay ngày tương lai.",
     "Không sửa.",
     lambda T: [v for v in col(T["customers"], "registration_date")
                if not ISO_RE.match(v.strip()) or v.strip() > TODAY.strftime("%Y-%m-%d")], None, "", "ĐẠT"),
    (P, "product_id", "Chuỗi, khoá chính sản phẩm. Phải duy nhất.",
     "Không phát hiện lỗi.", "Không sửa.",
     lambda T: extra_dupes(col(T["products"], "product_id")) + [v for v in col(T["products"], "product_id") if not v.strip()],
     None, "", "ĐẠT"),
    (P, "product_name", "Chuỗi, tên sản phẩm.",
     "Không phát hiện lỗi.", "Không sửa.",
     lambda T: extra_dupes(col(T["products"], "product_name")), None, "", "ĐẠT"),
    (P, "category", "Chuỗi phân loại, 6 nhóm sản phẩm.",
     "Viết hoa/thường khác nhau và dính khoảng trắng: FASHION, ' Sports ', sports.",
     "Hàm clean_category (common.py): bỏ khoảng trắng, so khớp không phân biệt hoa thường. 03_clean.py mục 2.1.",
     lambda T: [repr(v) for v in col(T["products"], "category") if v not in CATEGORIES], None, "", "ĐẠT"),
    (P, "price", "Số thực, giá catalog. Phải dương.",
     "Giá âm hoặc bằng 0: -1000, -50000, 0.",
     "Đặt rỗng, lưu giá gốc ở cột price_raw_invalid. 03_clean.py mục 2.2.",
     lambda T: [v for v in col(T["products"], "price") if v.strip() and (to_float(v) or 0) <= 0],
     None, "", "ĐẠT"),
    (P, "price", "(như trên)",
     "Ô giá trống.",
     "Không đoán giá. Giá bán trong order_items thay đổi theo khuyến mãi nên không dùng thay.",
     lambda T: [v for v in col(T["products"], "price") if not v.strip()], None,
     "Tăng vì 3 giá âm/0 đã được đổi thành rỗng", "LƯU Ý"),
    (O, "order_id", "Chuỗi, khoá chính đơn hàng. Phải duy nhất, không rỗng.",
     "Đơn không có mã.",
     "Cách ly vào rejects/orders_rejects.csv. 03_clean.py mục 3.1.",
     lambda T: [f"đơn của khách {r['customer_id']}" for r in T["orders"] if not r["order_id"].strip()], None, "", "ĐẠT"),
    (O, "order_id", "(như trên)",
     "Đơn bị xuất 2 lần, giống hệt nhau.",
     "Xoá dòng trùng hoàn toàn. 03_clean.py mục 3.2.",
     lambda T: extra_dupes([v for v in col(T["orders"], "order_id") if v.strip()]), None, "", "ĐẠT"),
    (O, "customer_id", "Khoá ngoại, phải có trong customers.csv.",
     "Đơn trỏ tới khách không tồn tại.",
     "Cách ly vào rejects/ (vi phạm khoá ngoại). 03_clean.py mục 3.3.",
     lambda T: [r["customer_id"] for r in T["orders"]
                if r["customer_id"].strip() not in {c["customer_id"] for c in T["customers"]}], None, "", "ĐẠT"),
    (O, "order_date", "Ngày đặt hàng. Chuẩn hoá về YYYY-MM-DD.",
     "Trộn định dạng YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY.",
     "Hàm parse_flex_date (common.py). 03_clean.py mục 3.5.",
     lambda T: [v for v in col(T["orders"], "order_date") if not ISO_RE.match(v.strip())], None, "", "ĐẠT"),
    (O, "order_date", "(như trên)",
     "Ngày đọc được 2 cách.",
     "Chọn DD/MM, ghi cờ ambiguous_assumed_dmy ở cột order_date_format_note.",
     lambda T: [v for v in col(T["orders"], "order_date") if is_ambiguous(v)],
     lambda T: [r["order_date"] for r in T["orders"] if r["order_date_format_note"] == "ambiguous_assumed_dmy"],
     "Đã chuyển ISO theo giả định DD/MM, có gắn cờ", "LƯU Ý"),
    (O, "order_date", "(như trên)",
     "Ngày đặt hàng sau hôm nay (21/09/2026).",
     "Giữ nguyên. README không cấm đơn đặt trước. Chỉ ghi vào cleaning_log.md, chưa có cột cờ riêng.",
     lambda T: [v for v in col(T["orders"], "order_date") if (date_or_none(v) or TODAY) > TODAY], None,
     "Giữ nguyên có chủ đích", "LƯU Ý"),
    (O, "order_date + customers.registration_date", "Quan hệ giữa 2 bảng: đơn hàng thường không thể có trước ngày khách đăng ký.",
     "Đơn có ngày đặt trước ngày đăng ký. Khoảng 24% đơn có ngày ISO rõ ràng cũng bị, nên lỗi nằm ở dữ liệu gốc, không phải do parse.",
     "CHƯA SỬA. README không nêu quy tắc này, và không biết ngày nào đúng.",
     order_before_registration, None, "Xung đột còn tồn tại", "XUNG ĐỘT"),
    (O, "status", "Chuỗi phân loại, 4 trạng thái: Pending, Processing, Completed, Cancelled.",
     "14 cách viết: pending, PENDING, DONE, complete, Canceled, In Progress...",
     "Hàm clean_status (common.py) ánh xạ theo STATUS_MAP. In Progress gộp vào Processing. 03_clean.py mục 3.4.",
     lambda T: [v for v in col(T["orders"], "status") if v.strip() not in STATUSES], None, "", "ĐẠT"),
    (O, "total_amount", "Số thực. Phải bằng tổng quantity × unit_price của đơn đó.",
     "Tổng tiền lệch so với chi tiết đơn hàng (chênh hơn 1 đồng).",
     "Tính lại từ order_items sạch. Giá cũ lưu ở total_amount_original. 03_clean.py mục 5.1.",
     total_mismatch, None, "", "ĐẠT"),
    (O, "total_amount", "(như trên)",
     "Đơn không còn dòng chi tiết nào sau khi làm sạch nên không kiểm chứng được tổng.",
     "Giữ nguyên tổng gốc.",
     lambda T: [r["order_id"] for r in T["orders"]
                if r["order_id"].strip() and r["order_id"] not in {i["order_id"] for i in T["order_items"]}], None,
     "Mọi dòng chi tiết của các đơn này đều bị cách ly. Giữ tổng gốc, chưa kiểm chứng", "LƯU Ý"),
    (I, "(cả dòng)", "Mỗi dòng là một mặt hàng trong đơn.",
     "Dòng trùng hoàn toàn (cùng order_id, product_id, quantity, unit_price).",
     "Xoá bản trùng. 03_clean.py mục 4.1.",
     lambda T: exact_dupes(T["order_items"]), None, "", "ĐẠT"),
    (I, "order_id", "Khoá ngoại, phải có trong orders.csv.",
     "Trỏ tới đơn không tồn tại (mã giả O995xx).",
     "Cách ly vào rejects/order_items_rejects.csv. Dòng thuộc đơn đã bị cách ly cũng bị cách ly theo (cascade). 03_clean.py mục 4.2.",
     lambda T: [r["order_id"] for r in T["order_items"]
                if r["order_id"].strip() not in {o["order_id"] for o in T["orders"]}], None, "", "ĐẠT"),
    (I, "product_id", "Khoá ngoại, phải có trong products.csv.",
     "Trỏ tới sản phẩm không tồn tại (mã giả P99x).",
     "Cách ly vào rejects/. 03_clean.py mục 4.3.",
     lambda T: [r["product_id"] for r in T["order_items"]
                if r["product_id"].strip() not in {p["product_id"] for p in T["products"]}], None, "", "ĐẠT"),
    (I, "quantity", "Số nguyên dương.",
     "Số lượng bằng 0 hoặc âm: 0, -1, -2, -3.",
     "Hàm to_int (common.py). Không hợp lệ thì cách ly, vì không biết số lượng đúng. 03_clean.py mục 4.4.",
     lambda T: [v for v in col(T["order_items"], "quantity") if (to_int(v) or 0) <= 0], None, "", "ĐẠT"),
    (I, "unit_price", "Số thực dương, giá bán tại thời điểm mua.",
     "Giá bằng 0 hoặc âm: 0, -10000.",
     "Hàm to_float (common.py). Không hợp lệ thì cách ly. 03_clean.py mục 4.5.",
     lambda T: [v for v in col(T["order_items"], "unit_price") if (to_float(v) or 0) <= 0], None, "", "ĐẠT"),
    (I, "order_id + product_id", "Một sản phẩm có thể xuất hiện nhiều lần trong một đơn.",
     "Cùng (order_id, product_id) nhưng khác số lượng hoặc giá.",
     "Giữ nguyên. Có thể là 2 lần mua hợp lệ trong cùng đơn, không có bằng chứng là lỗi.",
     same_key_diff_values, None, "Giữ nguyên có chủ đích", "LƯU Ý"),
]


def show(values, limit=3):
    if not values:
        return "0"
    ex = ", ".join(str(v) if str(v).strip() else "(rỗng)" for v in list(dict.fromkeys(values))[:limit])
    return f"{len(values)} (vd: {ex})"


# ---------------------------------------------------------------------------
# Chạy từng phép kiểm tra trên raw và clean, ghép thành bảng giám sát.
# Nếu dòng dự kiến ĐẠT mà clean vẫn còn lỗi thì tự đổi thành CHƯA ĐẠT.
# ---------------------------------------------------------------------------
HEADER = ["STT", "Tên trường", "Đặc điểm dữ liệu", "Vấn đề dữ liệu đang gặp phải",
          "Sửa kiểu gì, ở file nào", "Ban đầu (raw)", "Sau khi sửa (clean)", "Kiểm tra lại"]

table = defaultdict(list)
for i, (f, field, desc, issue, fix, check_raw, check_clean, note, verdict) in enumerate(ROWS, 1):
    t = f.replace(".csv", "")
    base = field.split(" + ")[0]
    desc_full = desc if desc.startswith("(") or base not in RAWT[t][0] else f"{desc} {profile(t, base)}."
    before = check_raw(RAWT)
    after = (check_clean or check_raw)(CLEANT)
    if verdict == "ĐẠT" and after:
        verdict = "CHƯA ĐẠT"
    table[f].append([str(i), field, desc_full, issue, fix, show(before),
                     show(after) + (f". {note}" if note else ""), f"**{verdict}**"])
all_rows = [r for rows in table.values() for r in rows]
verdicts = Counter(r[-1].strip("*") for r in all_rows)

# ---------------------------------------------------------------------------
# Đối soát số dòng: mỗi dòng gốc phải về đúng một nơi (clean, xoá trùng, hoặc rejects).
# ---------------------------------------------------------------------------
REJECT_FILES = {"orders": "orders_rejects.csv", "order_items": "order_items_rejects.csv"}
REJECTED = {t: load(name, REJECTS) for t, name in REJECT_FILES.items()}
steps = []
for t in ("customers", "products", "orders", "order_items"):
    raw_n, clean_n = len(RAWT[t]), len(CLEANT[t])
    dup = len(exact_dupes([r for r in RAWT[t] if t != "orders" or r["order_id"].strip()]))
    rej = len(REJECTED.get(t, []))
    ok = "**ĐẠT**" if raw_n == clean_n + dup + rej else "**LỆCH**"
    steps.append([f"{t}.csv", str(raw_n), str(dup), str(rej), str(clean_n),
                  f"{clean_n} + {dup} + {rej} = {clean_n + dup + rej}", ok])


# Gom lý do cách ly về dạng ngắn để đếm (bỏ giá trị cụ thể sau dấu phẩy).
def reason_counts(rows):
    return Counter(r["reject_reason"].split(",")[0].split(" (")[0] for r in rows)


# ---------------------------------------------------------------------------
# Bằng chứng cho phần "còn lại": giả định DD/MM và xung đột ngày đăng ký.
# ---------------------------------------------------------------------------
notes = Counter(r["order_date_format_note"] for r in CLEANT["orders"])
conflict_ids = set(order_before_registration(CLEANT))
iso_orders = [r for r in CLEANT["orders"] if r["order_date_format_note"] == "iso"]
iso_conflict = sum(r["order_id"] in conflict_ids for r in iso_orders)


def md_row(cells):
    return "| " + " | ".join(str(c).replace("|", "/").replace("\n", " ") for c in cells) + " |"


def md_table(header, rows):
    return "\n".join([md_row(header), md_row(["---"] * len(header))] + [md_row(r) for r in rows]) + "\n"


# ---------------------------------------------------------------------------
# Ghi báo cáo Markdown
# ---------------------------------------------------------------------------
out = []
w = out.append

w("# Báo cáo làm sạch dữ liệu: bảng giám sát chi tiết\n")
w("File này được sinh tự động bởi `pipeline/05_field_audit.py`. Mọi con số trong cột "
  "\"Ban đầu\" và \"Sau khi sửa\" là kết quả của cùng một phép kiểm tra chạy trên `raw/` và `clean/`, "
  "không chép tay.\n")

w("## 1. Cách chạy\n")
w("```bash\ncd pipeline\npython3 01_profile.py      # khảo sát dữ liệu thô\n"
  "python3 02_investigate.py  # điều tra sâu các bất thường\n"
  "python3 03_clean.py        # làm sạch: raw/ -> clean/ + rejects/\n"
  "python3 04_validate.py     # so sánh chất lượng trước / sau\n"
  "python3 05_field_audit.py  # sinh báo cáo này\n```\n")
w("- `raw/`: dữ liệu gốc, không bao giờ bị sửa.\n- `clean/`: dữ liệu sau khi làm sạch.\n"
  "- `rejects/`: các dòng bị cách ly, kèm cột `reject_reason`.\n"
  "- Các hàm sửa lỗi nằm trong `common.py`, các bước áp dụng nằm trong `03_clean.py`.\n")

w("## 2. Dữ liệu ban đầu\n")
w(md_table(["File", "Số dòng", "Các trường"],
           [[f"{t}.csv", str(len(RAWT[t])), ", ".join(RAWT[t][0].keys())] for t in RAWT]))
w("\nQuan hệ: `customers.customer_id` 1-n `orders.customer_id`, `orders.order_id` 1-n `order_items.order_id`, "
  "`products.product_id` 1-n `order_items.product_id`.\n")

w("## 3. Cách đọc bảng\n")
w(f"Tổng cộng {len(all_rows)} dòng kiểm tra: "
  + ", ".join(f"{v} {k}" for k, v in verdicts.most_common()) + ".\n")
w("- **ĐẠT**: lỗi đã về 0 sau khi sửa.\n"
  "- **LƯU Ý**: giữ nguyên hoặc dùng giả định có chủ đích, có lý do ghi trong bảng.\n"
  "- **XUNG ĐỘT**: mâu thuẫn còn tồn tại trong dữ liệu sạch, chưa sửa.\n"
  "- Ví dụ trong ngoặc là vài giá trị vi phạm thật lấy từ dữ liệu.\n")

w("## 4. Bảng giám sát theo từng file\n")
for f, rows in table.items():
    t = f.replace(".csv", "")
    w(f"### {f} ({len(RAWT[t])} → {len(CLEANT[t])} dòng)\n")
    w(md_table(HEADER, rows))

w("## 5. Giám sát số dòng qua từng bước\n")
w("Mỗi dòng gốc phải đi về đúng một nơi: `clean/`, bị xoá vì trùng hoàn toàn, hoặc nằm trong `rejects/`.\n")
w(md_table(["File", "Raw", "Xoá trùng", "Cách ly", "Clean", "Đối soát", "Kết quả"], steps))
for t, rows in REJECTED.items():
    w(f"\nLý do cách ly trong `rejects/{REJECT_FILES[t]}`:\n")
    w(md_table(["Lý do", "Số dòng"], [[k, str(v)] for k, v in reason_counts(rows).most_common()]))

w("## 6. Phần còn lại: xung đột và lưu ý\n")
w(f"**Xung đột ngày đặt hàng trước ngày đăng ký.** {len(conflict_ids)}/{len(CLEANT['orders'])} đơn trong "
  f"`clean/` có `order_date` sớm hơn `registration_date` của khách. Trong {len(iso_orders)} đơn có ngày ISO "
  f"rõ ràng (không phụ thuộc cách đọc) vẫn có {iso_conflict} đơn ({iso_conflict / len(iso_orders):.0%}) bị lệch, "
  "nên lỗi nằm ở dữ liệu gốc chứ không phải do code đọc ngày sai. Chưa sửa vì đề bài không nêu quy tắc này "
  "và không có cơ sở biết ngày nào đúng. Cần hỏi bên cung cấp dữ liệu.\n")
w(f"**Rủi ro của giả định DD/MM.** Trong các ngày đặt hàng chỉ đọc được một cách, có {notes['forced_dmy']} ngày "
  f"kiểu DD/MM và {notes['forced_mdy']} ngày kiểu MM/DD, tức nguồn dùng lẫn cả hai. "
  f"{notes['ambiguous_assumed_dmy']} ngày đặt hàng mơ hồ được đọc theo DD/MM và gắn cờ "
  "`ambiguous_assumed_dmy` để xem lại khi có thêm thông tin.\n")
w("**Giữ nguyên có chủ đích** (theo lưu ý của đề bài: không phải bất thường nào cũng là lỗi):\n")
w("- Đơn có ngày ở tương lai: có thể là đơn đặt trước, đề bài không cấm.\n"
  "- Cùng sản phẩm trong một đơn nhưng khác số lượng hoặc giá: có thể là 2 lần mua hợp lệ.\n"
  "- Đơn không còn dòng chi tiết sau khi lọc: giữ tổng gốc, chưa kiểm chứng được.\n"
  "- Ô trống tăng lên (email, giá sản phẩm): do giá trị rác đã được đổi thành rỗng, không mất dữ liệu thật.\n"
  "- Tên có dấu tiếng Việt, email có ký tự Unicode: dữ liệu hợp lệ.\n")

(REPORTS / "field_audit.md").write_text("\n".join(out), encoding="utf-8")

for r in all_rows:
    print(f"{r[0]:>2}. {r[1]:<28} {r[5][:38]:<40} -> {r[6][:40]:<42} {r[7]}")
print()
for r in steps:
    print(" | ".join(r))
print(f"\nĐã ghi {REPORTS / 'field_audit.md'}")
