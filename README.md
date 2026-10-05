# Data-Cleaning

Bài thực hành khảo sát, phát hiện và làm sạch bộ dữ liệu thương mại điện tử bị lỗi, bằng một pipeline Python chạy lại được (chỉ dùng thư viện chuẩn, không pandas). Không file CSV gốc nào bị sửa tay.

**Báo cáo chính:** [pipeline/reports/field_audit.md](pipeline/reports/field_audit.md). File này có bảng giám sát từng trường (đặc điểm, vấn đề, cách sửa, trước/sau, kiểm tra lại), đối soát số dòng và các xung đột còn lại.

## Cấu trúc

```
customers.csv, products.csv, orders.csv, order_items.csv   dữ liệu gốc được giao
pipeline/
  raw/        bản sao dữ liệu gốc, không bao giờ bị sửa
  clean/      dữ liệu sau khi làm sạch
  rejects/    các dòng bị cách ly, kèm cột reject_reason
  reports/    field_audit.md
  common.py           các hàm sửa lỗi dùng chung (ngày, email, điện thoại, ánh xạ phân loại...)
  01_profile.py       khảo sát dữ liệu thô
  02_investigate.py   điều tra sâu các bất thường
  03_clean.py         làm sạch: raw/ -> clean/ + rejects/
  04_validate.py      so sánh chất lượng trước / sau
  05_field_audit.py   sinh báo cáo field_audit.md
```

## Cách chạy

```bash
cd pipeline
python3 01_profile.py
python3 02_investigate.py
python3 03_clean.py
python3 04_validate.py
python3 05_field_audit.py
```

Chạy lại `03_clean.py` bao nhiêu lần cũng cho cùng kết quả trong `clean/` và `rejects/`.

## Slide

Slide trình bày: https://claude.ai/artifact/55DyGBJyYMCQuPZAFJKdDB
