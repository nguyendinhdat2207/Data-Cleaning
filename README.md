# Data-Cleaning

E-commerce dirty dataset — bài thực hành khảo sát (profiling), phát hiện và
làm sạch dữ liệu, xây dựng theo hướng **reproducible pipeline** (không sửa
tay các file CSV gốc).

## Dữ liệu

4 bảng dữ liệu thô, xuất từ nhiều hệ thống khác nhau của một công ty
thương mại điện tử (xem chi tiết quan hệ & quy tắc nghiệp vụ trong
[README.txt](README.txt)):

- `customers.csv`
- `products.csv`
- `orders.csv`
- `order_items.csv`

## Pipeline

Toàn bộ pipeline làm sạch nằm trong [pipeline/](pipeline/README.md), viết
bằng Python thuần (không phụ thuộc pandas):

```
pipeline/
  raw/       bản sao dữ liệu gốc (không bao giờ bị sửa)
  clean/     dữ liệu sau khi làm sạch, sẵn sàng cho phân tích
  rejects/   các dòng bị loại/cách ly kèm lý do (không xoá âm thầm)
  reports/   báo cáo profiling, log làm sạch, so sánh trước/sau
```

Chạy pipeline:

```bash
cd pipeline
python3 01_profile.py
python3 02_investigate.py
python3 03_clean.py
python3 04_validate.py
```

## Tài liệu chính

- [pipeline/reports/data_quality_issues.md](pipeline/reports/data_quality_issues.md) —
  catalog đầy đủ các vấn đề chất lượng dữ liệu, phân loại theo tiêu chí
  DAMA (Completeness, Uniqueness, Validity, Consistency, Accuracy,
  Integrity), kèm lý do cho từng quyết định xử lý.
- [pipeline/reports/cleaning_log.md](pipeline/reports/cleaning_log.md) —
  log tự động của từng bước làm sạch và số dòng/giá trị bị ảnh hưởng.
- [pipeline/reports/validation_before_after.txt](pipeline/reports/validation_before_after.txt) —
  so sánh chất lượng dữ liệu trước và sau khi làm sạch.
