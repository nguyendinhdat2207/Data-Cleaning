E-COMMERCE DIRTY DATASET — BÀI THỰC HÀNH LÀM SẠCH DỮ LIỆU

Bối cảnh:

Cung cấp dữ liệu được xuất từ nhiều hệ thống khác nhau của một công ty thương mại điện tử.
Dữ liệu có thể chứa các vấn đề về chất lượng. Nhiệm vụ là khảo sát (profile), phát hiện và phân tích vấn đề, làm sạch và kiểm tra lại dữ liệu trước khi dữ liệu được sử dụng cho các hoạt động phân tích.

-------------------

Các tệp dữ liệu:

customers.csv
products.csv
orders.csv
order_items.csv


Quan hệ giữa các bảng:
customers.customer_id  1 ---- * orders.customer_id
orders.order_id        1 ---- * order_items.order_id
products.product_id    1 ---- * order_items.product_id


Một số quy tắc nghiệp vụ:
customer_id, product_id và order_id là các trường định danh và phải thỏa mãn các ràng buộc về khóa.
quantity phải là một số nguyên dương.
price của sản phẩm và unit_price phải có giá trị dương.
birth_date phải là một ngày hợp lệ trong quá khứ và có giá trị hợp lý.
email, nếu có, phải tuân theo định dạng email hợp lệ.
Các bản ghi trong order_items phải tham chiếu đến các đơn hàng và sản phẩm tồn tại.
Các bản ghi trong orders phải tham chiếu đến khách hàng tồn tại.
total_amount phải phù hợp với thông tin các mặt hàng thuộc đơn hàng.
Các trường dữ liệu phân loại (categorical fields) phải sử dụng cách biểu diễn nhất quán.

-----------------------------
Nhiệm vụ:
Thực hiện data profiling trên dữ liệu thô.
Phát hiện các vấn đề về chất lượng dữ liệu và phân loại chúng theo các tiêu chí chất lượng dữ liệu tương ứng.
Xác định các quy tắc làm sạch dữ liệu và giải thích lý do cho từng quyết định xử lý.
Xây dựng một data cleaning pipeline có khả năng tái thực hiện (reproducible). Không chỉnh sửa trực tiếp các tệp CSV bằng tay.
Chạy lại các phép kiểm tra chất lượng dữ liệu và so sánh chất lượng dữ liệu trước và sau khi làm sạch.

Lưu ý quan trọng
Không phải mọi bất thường (anomaly) đều là lỗi dữ liệu.
Không thay đổi hoặc loại bỏ một giá trị nếu bạn không thể đưa ra lý do hợp lý cho quy tắc làm sạch được áp dụng.