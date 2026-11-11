# Bàn giao Đại bàng / v1

- Owner tạo: `dai-bang-01a1cb4c`. Mã nhân vật workshop `dai-bang`; mã tài khoản/game `eagle`.
- Trạng thái mỹ thuật: `pending_review`, không tự đặt approved. Yêu cầu mới đã cho phép tích hợp và triển khai local riêng Đại bàng.
- Người dùng chốt commit riêng bộ Đại bàng và `integration.patch`; không gom nền game đang được các chat khác sửa, không push.
- Đã có: 32 tư thế từ đúng ảnh Eagle/style Cáo Nâu/Mầm Sách, nguồn PNG/prompt/revision, hai WebP alpha tổng918.490byte, Canvas năm mode, GIF/MP4 chiêu cuối3giây/90frame và ba GIF trạng thái phụ. Nguồn states spacing lỗi được giữ riêng, không chạy.
- Chiêu: cất cánh → bổ nhào theo vệtV → xòe cánh hãm/hai luồng gió hợp bão lông vũ → đáp/thắng. Tên.65s, đòn.95s, impact1.75s, thắng1.9–3s. Banner demo ở dưới vùng hành động tránh che đầu tại mọi mốc đã kiểm.
- Game runtime: `frontend/eagle-animation.js`, CSS và `frontend/arena-art/eagle/`. Canvas finite, idle không chạy RAF, attack/hit về idle, thua/thắng giữ cuối; reduced motion/ẩn trang/tháo Canvas. Chỉ dùng WebP, không tải review media.
- Các hook trong năm tệp chung đang áp dụng ở working tree; đọc `INTEGRATION.md` và patch trước khi chuyển checkout. Patch không tự bổ sung toàn bộ nền Góc học tập/Đấu trí chưa có trong commit gốc a8221fa. Không đổi luật/sát thương/XP/deadline/schema.
- QA: alpha/32pose/WebP sáng-tối, demo và module năm viewport dọc-ngang, controls>=44px, seek/pause/0,5×/playonce/reduced/visibility, API chọn→đăng nhập lại và invalid rejection đạt. Báo cáo ở `qa/`.
- Windows full suite tại snapshot đã chạy:72tests/678.015s PASS; JS/build/SEO8trang PASS. Các chat khác tiếp tục thêm tests sau snapshot. Không nhận kết quả của chat khác làm kiểm thử mới cho job này.
- Docker Compose mặc định đã build/recreate/Healthy thực tế; tại lần kiểm cuối chỉ127.0.0.1:8765. Healthok, đề mẫu10/10,4tài nguyên Eagle200/SHA256khớp nguồn. `qa/local-verification.json`. Giữ volume dữ liệu, không thêm hồ sơ thử vào DB thật.
- Auto-review từ chối lệnh giữLAN192.168.1.2; dùng localhost mặc định an toàn. QA nguồn port8794 gặp sandbox/networktimeout, đã chuyển kiểm game source bằng mock-route và giữ giới hạn trong báo cáo; không tự dừng tiến trình không thuộc job.
- Chưa đo FPS/CPU trên điện thoại thật hoặc mạng chậm; GIF/video30fps không chứng minh hiệu năng thiết bị. Không chạy CI hoặc phát hành Internet.
- Sau commit đọc bộ nhớ `docs/chat/2026-11-11-animation-dai-bang.md` để lấy mãcommit/trạng thái cuối; trước sửa tiếp kiểm Git, job và lease thực tế. Nếu đã release, dùng CLI claim owner mới, không giành job đang có lease.
