# Bản vá Gấu cho nền game local

Người dùng chọn **chỉ commit gói Gấu và bản vá tích hợp**, vì nền tài khoản/game và nhiều tính năng từ các chat khác chưa nằm trong Git HEAD. Commit gói này không phải commit toàn bộ ứng dụng; không triển khai riêng HEAD lên website công khai.

`bear-game.patch` ghi thay đổi cần thiết trên nền game local ngày 11/11/2026: registry `gau → Gấu`, lựa chọn/lưu linh vật, Canvas, dispatch tấn công/chịu đòn/chiêu cuối/thua, lifecycle, giữ hoạt cảnh kết liễu trước khi sang kết quả, khai báo tài nguyên Python/HTML/build. Các thay đổi này đã áp dụng vào bản làm việc hiện tại; nền game và tệp chia sẻ vẫn ở ngoài commit gói Gấu.

Tệp runtime được commit tại `frontend/bear-animation.js`, `bear-animation.css`, `bear-frames.js` và ba WebP `frontend/arena-art/gau-*`. `runtime-sha256.json` ghi hash của gói. Chỉ tải sheet khi cần Gấu; poster dùng trong danh sách. Không đổi sát thương, thời gian trả lời, kết quả hoặc XP. Trạng thái giảm chuyển động vẽ tư thế tĩnh; dừng lịch vẽ khi rời trang hoặc ẩn tab.

Khi đưa vào một bản nền game khác, đọc các hunk trong patch, đối chiếu cấu trúc mới rồi dùng `git apply --check` trước khi áp dụng. Không áp dụng lại lên cây đã có Gấu hoặc ghi đè toàn bộ learning.js bằng snapshot cũ. Ngữ cảnh danh sách nhân vật có thể khác do các chat khác cùng tích hợp. Sau đó sao chép `test_bear_mascot.py` vào `tests/` nếu chưa có, chạy kiểm thử Python/JS, dựng static/SEO và kiểm tra trình duyệt.

Kiểm thử của gói: lựa chọn Gấu giữ qua đăng nhập/reload, ranking/arena serialize đúng; seed idempotent giữ id và XP. Giao diện đã kiểm Canvas bốn trạng thái, cả hai phía, điện thoại/tablet dọc-ngang/desktop, giảm chuyển động, ẩn tab, lỗi ảnh và dọn runtime khi điều hướng. Báo cáo tích hợp đầy đủ nằm cục bộ trong `work/mascot-animation/gau/v1/qa-runtime/` và bản ghi chat Gấu.

Tùy chọn diện mạo Ngựa của chat khác có thể ghi đè hình linh vật hồ sơ trong trình duyệt. Chọn **Dùng linh vật hồ sơ** để xem Gấu khi tùy chọn đó đang bật. Chưa đo FPS trên điện thoại thật hoặc mạng chậm. Không có push, CI hoặc phát hành public trong yêu cầu này.
