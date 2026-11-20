# Đồng bộ bản localhost ngày 20/11/2026

Bản phát hành đưa các tính năng đang chạy trên localhost lên Cloudflare: Gia đình và hồ sơ con, trải nghiệm, giỏ hàng, gói câu hỏi, giới hạn game, bài giảng/video, khung câu hỏi dùng chung, sáu module học tập và thanh điều hướng dưới. Giao diện giữ bộ màu Vườn Toán và bố trí trên điện thoại, máy tính bảng, máy tính.

Mã nguồn và migration được lưu trên GitHub. Ngân hàng câu hỏi, lời giải, bài giảng riêng và khóa dịch vụ được đóng gói riêng cho máy chủ, không đưa vào kho công khai. Gói học liệu gồm 2.475 câu trong kho học tập (1.500 Free và 975 Paid); kho chính nhận 1.500 câu Free. Cài thêm học liệu theo hash, không nhập tài khoản, tiến độ hoặc giao dịch localhost vào production.

Trước migration, máy chủ tạm ngừng API ghi và lưu mốc Cloudflare PITR cùng mã băm từng bản ghi cũ ngay trong Durable Object. Chỉ mở lại khi đối chiếu toàn bộ giá trị cũ và khóa ngoại đạt. Thông tin trả về máy vận hành chỉ gồm số lượng và kết quả kiểm tra. Dữ liệu localhost và production độc lập.

Adapter Cloudflare tính hash PIN và gọi Bunny ngoài giao dịch SQL, lưu kết quả theo request để phát lại an toàn. Tạo video bị lặp không tạo thêm video; cài lại danh mục giữ metadata mới từ nhà cung cấp. Không tạo video hoặc chuyển khoản thật trong kiểm thử phát hành.

Kiểm thử cục bộ gồm 822 kiểm thử Python trong Docker với đầu vào học liệu riêng, 38 kiểm thử adapter, actual workerd cho Family/Free/Paid/Trial và video hiện có; Chrome và Edge mỗi trình duyệt 48 tổ hợp trang/vai trò/kích thước. CI công khai bỏ qua rõ các trường hợp cần đầu vào riêng; cổng phát hành riêng vẫn chạy đủ. Điện thoại dùng viewport mô phỏng; chưa kiểm điện thoại vật lý hoặc Safari.
