# Bàn giao Ong / v1

- Chủ phiên: ong-01a1cb4d
- Trạng thái: pending_review về mỹ thuật; người dùng đã yêu cầu và cho phép tích hợp game/commit/triển khai local cho riêng Ong.
- Đã có: PNG16pose do built-in imagegen dùng đúng hai ảnh tham chiếu; WebP alpha330.526byte; Canvas bốn chế độ dùng chung runtime game; GIF/MP4 chiêu cuối90frame/3s và GIF attack/hit/lose cũng90frame/3s; prompt và QA.
- Game: chọn/lưu Ong qua API, avatar, normal attack, hit, ultimate Lục Giác Hoàng Kim, result win/lose; giữ luật/XP/sát thương. Chiêu3s, tên0,65 trước đòn0,95/tác động1,75. Giảm chuyển động, dừng khi rời/ẩn trang. Tăng HTTP request_queue_size128 vì nhiều tài nguyên đồng thời gây connection refused ở mức mặc định.
- Tệp riêng: frontend/arena-bee-animation.{js,css}, frontend/arena-art/bee/poses.webp, tests/test_bee_mascot.py, thư mục job này. Các hunk tích hợp dùng chung lưu integration.patch; xem README về điều kiện áp dụng và phạm vi commit.
- Đã kiểm: nguồn/WebP sáng-tối; xuất GIF/MP4; năm viewport × bốn mode/controls/reduced motion; hai test API/persistence/arena riêng trên Windows và Docker. Không tự đánh dấu approved; chưa đo FPS điện thoại thật.
- Đã sửa giới hạn tổ lục giác/đàn ong/giọt mật theo mép sân, giữ kích thước Ong. QA game thật sau sửa8/8 đạt, zero JS/network errors; chuyển trang sau3,478s. Root đã xem ảnh điện thoại dọc/ngang và contact sheet cuối. Bản xuất lại đạt lúc16:43:45UTC ngày11/11; qa/game-report.json và game-mobile-report.json, mobile-portrait.png/mobile-landscape.png giữ bằng chứng trong job.
- Kiểm cuối: full Windows77test đạt624,270s; full imageDocker mới77test đạt68,329s với /tmp và /work tạm có quyền ghi, không gắn volumeDB thật. Log python-tests-final.log/docker-tests-final.log ở work/bee-integration/. Lượt Docker cũ75test có assertion staff và ba lỗi /work chỉ đọc; giữ log lịch sử, không dùng kết quả cũ để kết luận bản cuối.
- Xem kết quả game thực tế/localhost/build/checksum trong work/bee-integration/; trạng thái cuối và commit ghi ở docs/chat/2026-11-11-animation-ong.md.
- Bước tiếp: người dùng duyệt hình/nhịp; xem điều kiện đưa các mã game nền vào Git trước phát hành chung. Chưa push/CI/phát hành Internet.
- Nếu đổi người: giữ nguồn/exports/QA, đọc bộ nhớ rồi release/claim theo workshop; không tự ghi đè variant khác.
