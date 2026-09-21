"""Shared helpers for the cleaning pipeline."""
import csv
import re
import unicodedata
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "raw"
CLEAN = ROOT / "clean"
REJECTS = ROOT / "rejects"
REPORTS = ROOT / "reports"

for d in (CLEAN, REJECTS, REPORTS):
    d.mkdir(exist_ok=True)

TODAY = datetime(2026, 9, 21)


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


def strip_accents(s):
    nfkd = unicodedata.normalize("NFD", s)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def parse_flex_date(v, default_day_first=True):
    """Parse a date that may be ISO (YYYY-MM-DD) or DD/MM/YYYY or MM/DD/YYYY.

    Returns (datetime | None, note) where note explains how it was resolved.
    Disambiguation rule (documented assumption, see README of pipeline/reports):
      - ISO strings are trusted as-is.
      - For "xx/xx/yyyy" strings, if one of the two first fields is >12 it can only
        be a day, so the format is forced unambiguously.
      - If both fields are <=12 the format is genuinely ambiguous; we default to
        DD/MM/YYYY (Vietnamese locale convention, and the majority pattern among the
        rows where the format IS unambiguous in this dataset). This is a documented
        assumption, not a certainty -- ambiguous rows are flagged in the QA log.
    """
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

    a, b, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    a_ok_as_day = 1 <= a <= 31
    b_ok_as_month = 1 <= b <= 12
    a_ok_as_month = 1 <= a <= 12
    b_ok_as_day = 1 <= b <= 31

    dmy_valid = a_ok_as_day and b_ok_as_month
    mdy_valid = a_ok_as_month and b_ok_as_day

    if dmy_valid and not mdy_valid:
        try:
            return datetime.strptime(v, "%d/%m/%Y"), "forced_dmy"
        except ValueError:
            return None, "invalid_date"
    if mdy_valid and not dmy_valid:
        try:
            return datetime.strptime(v, "%m/%d/%Y"), "forced_mdy"
        except ValueError:
            return None, "invalid_date"
    if dmy_valid and mdy_valid:
        fmt = "%d/%m/%Y" if default_day_first else "%m/%d/%Y"
        try:
            return datetime.strptime(v, fmt), "ambiguous_assumed_dmy"
        except ValueError:
            return None, "invalid_date"
    return None, "invalid_date"


EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
JUNK_TOKENS = {"n/a", "na", "-", "unknown", "none", "null", ""}


def clean_email(v):
    v = (v or "").strip()
    if v.lower() in JUNK_TOKENS:
        return "", "junk_token"
    if not EMAIL_RE.match(v):
        return "", "invalid_format"
    return v, "ok"


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


GENDER_MAP = {
    "male": "Male", "m": "Male", "nam": "Male",
    "female": "Female", "f": "Female", "nu": "Female", "nữ": "Female",
}


def clean_gender(v):
    key = strip_accents((v or "").strip().lower())
    return GENDER_MAP.get(key, "")


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


CATEGORY_MAP = {}


def clean_category(v, known_categories):
    key = (v or "").strip().lower()
    for c in known_categories:
        if c.lower() == key:
            return c
    return (v or "").strip().title()


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
