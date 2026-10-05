"""Các hàm dùng chung cho pipeline: đọc/ghi CSV và các hàm làm sạch từng loại giá trị."""
import csv
import re
import unicodedata
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Đường dẫn thư mục. raw/ là dữ liệu gốc, không bao giờ bị ghi đè.
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent
RAW = ROOT / "raw"
CLEAN = ROOT / "clean"
REJECTS = ROOT / "rejects"
REPORTS = ROOT / "reports"

for d in (CLEAN, REJECTS, REPORTS):
    d.mkdir(exist_ok=True)

# Ngày "hôm nay" cố định để chạy lại lúc nào cũng ra cùng kết quả.
TODAY = datetime(2026, 9, 21)


# ---------------------------------------------------------------------------
# Đọc / ghi CSV
# ---------------------------------------------------------------------------
def load(name, folder=RAW):
    with open(folder / name, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def save(rows, name, folder, fieldnames):
    path = folder / name
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})
    return path


# Bỏ dấu tiếng Việt để so khớp: "Nữ" -> "Nu", "Hà Nội" -> "Ha Noi".
def strip_accents(s):
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


# ---------------------------------------------------------------------------
# SỬA NGÀY THÁNG (birth_date, order_date)
# Dữ liệu trộn 3 định dạng: YYYY-MM-DD, DD/MM/YYYY, MM/DD/YYYY.
# Trả về (ngày | None, ghi chú cách đọc). Ghi chú được lưu vào cột *_format_note.
#   - "iso"                    : đã đúng YYYY-MM-DD
#   - "forced_dmy"/"forced_mdy": một trong hai số > 12 nên chỉ có một cách đọc
#   - "ambiguous_assumed_dmy"  : cả hai số <= 12, đọc được 2 cách -> GIẢ ĐỊNH DD/MM
#                                (quy ước Việt Nam). Có gắn cờ để xem lại sau.
#   - "invalid_*", "empty"...  : không đọc được -> trả về None
# ---------------------------------------------------------------------------
def parse_flex_date(v, default_day_first=True):
    v = v.strip()
    if not v:
        return None, "empty"

    if re.match(r"^\d{4}-\d{2}-\d{2}$", v):
        try:
            return datetime.strptime(v, "%Y-%m-%d"), "iso"
        except ValueError:
            return None, "invalid_iso"

    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", v)
    if not m:
        return None, "unrecognized_format"

    a, b = int(m.group(1)), int(m.group(2))
    dmy_valid = 1 <= a <= 31 and 1 <= b <= 12
    mdy_valid = 1 <= a <= 12 and 1 <= b <= 31

    if dmy_valid and not mdy_valid:
        fmt, note = "%d/%m/%Y", "forced_dmy"
    elif mdy_valid and not dmy_valid:
        fmt, note = "%m/%d/%Y", "forced_mdy"
    elif dmy_valid and mdy_valid:
        fmt = "%d/%m/%Y" if default_day_first else "%m/%d/%Y"
        note = "ambiguous_assumed_dmy"
    else:
        return None, "invalid_date"

    # strptime báo lỗi với ngày không tồn tại, ví dụ 31/02/2001.
    try:
        return datetime.strptime(v, fmt), note
    except ValueError:
        return None, "invalid_date"


# ---------------------------------------------------------------------------
# SỬA EMAIL: giá trị rác (N/A, -, unknown) hoặc sai định dạng -> rỗng.
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
JUNK_TOKENS = {"n/a", "na", "-", "unknown", "none", "null", ""}


def clean_email(v):
    v = (v or "").strip()
    if v.lower() in JUNK_TOKENS:
        return "", "junk_token"
    if not EMAIL_RE.match(v):
        return "", "invalid_format"
    return v, "ok"


# ---------------------------------------------------------------------------
# SỬA SỐ ĐIỆN THOẠI: bỏ khoảng trắng/dấu gạch, đổi +84 hoặc 84 thành 0,
# kết quả chuẩn là 0XXXXXXXXX (10 số).
# ---------------------------------------------------------------------------
def clean_phone(v):
    v = (v or "").strip()
    if not v:
        return "", "empty"
    digits = re.sub(r"[^\d+]", "", v)
    if digits.startswith("+84"):
        digits = "0" + digits[3:]
    elif digits.startswith("84") and len(digits) == 11:
        digits = "0" + digits[2:]
    if re.match(r"^0\d{9}$", digits):
        return digits, "ok"
    return digits, "nonstandard_length"


# ---------------------------------------------------------------------------
# SỬA GIỚI TÍNH: 8 cách viết (male, M, Nam, Nữ, F...) -> Male / Female.
# ---------------------------------------------------------------------------
GENDER_MAP = {
    "male": "Male", "m": "Male", "nam": "Male",
    "female": "Female", "f": "Female", "nu": "Female",
}


def clean_gender(v):
    key = strip_accents((v or "").strip().lower())
    return GENDER_MAP.get(key, "")


# ---------------------------------------------------------------------------
# SỬA TỈNH/THÀNH: nhiều cách viết (HCMC, TP.HCM, hcm...) -> 1 tên chuẩn.
# Giá trị giả (-, N/A) -> rỗng.
# ---------------------------------------------------------------------------
PROVINCE_MAP = {}


def _add_province(canonical, variants):
    for v in variants:
        PROVINCE_MAP[strip_accents(v.strip().lower())] = canonical


_add_province("Ha Noi", ["Ha Noi", "Hà Nội", "hanoi", "Hanoi", "HN"])
_add_province("Ho Chi Minh City", ["Ho Chi Minh City", "Ho Chi Minh", "HCMC", "TP.HCM", "hcm"])
_add_province("Da Nang", ["Da Nang", "Đà Nẵng", "Danang", "DN"])
_add_province("Hai Phong", ["Hai Phong", "Hải Phòng", "HP"])
_add_province("Can Tho", ["Can Tho", "Cần Thơ", "CT"])
_add_province("Bac Ninh", ["Bac Ninh", "Bắc Ninh", "BN"])
_add_province("Quang Ninh", ["Quang Ninh", "Quảng Ninh", "QN"])


def clean_province(v):
    key = strip_accents((v or "").strip().lower())
    if key in JUNK_TOKENS:
        return ""
    return PROVINCE_MAP.get(key, (v or "").strip())


# ---------------------------------------------------------------------------
# SỬA TRẠNG THÁI ĐƠN: 14 cách viết -> Pending / Processing / Completed / Cancelled.
# "In Progress" gộp vào "Processing" vì cùng ý nghĩa nghiệp vụ.
# ---------------------------------------------------------------------------
STATUS_MAP = {
    "pending": "Pending",
    "processing": "Processing",
    "in progress": "Processing",
    "complete": "Completed",
    "completed": "Completed",
    "done": "Completed",
    "cancelled": "Cancelled",
    "canceled": "Cancelled",
}


def clean_status(v):
    key = (v or "").strip().lower()
    return STATUS_MAP.get(key, (v or "").strip())


# ---------------------------------------------------------------------------
# SỬA DANH MỤC SẢN PHẨM: bỏ khoảng trắng thừa, so khớp không phân biệt hoa thường
# với danh sách tên chuẩn (" Sports ", "SPORTS" -> "Sports").
# ---------------------------------------------------------------------------
def clean_category(v, known_categories):
    key = (v or "").strip().lower()
    for c in known_categories:
        if c.lower() == key:
            return c
    return (v or "").strip().title()


# ---------------------------------------------------------------------------
# CHUYỂN SỐ: không chuyển được thì trả về None để bước sau quyết định cách ly.
# to_int chỉ nhận số nguyên (2.0 được, 2.5 thì không).
# ---------------------------------------------------------------------------
def to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def to_int(v):
    f = to_float(v)
    if f is None or f != int(f):
        return None
    return int(f)
