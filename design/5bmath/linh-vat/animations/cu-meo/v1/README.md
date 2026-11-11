# Cú mèo — Ánh Mắt Đêm Trăng

Bộ animation riêng cho 5BMath, tạo ngày 11/11/2026 theo yêu cầu tích hợp game và triển khai local. Bản này không phải phê duyệt tạo hình của tất cả linh vật.

Mở [demo.html](demo.html), chọn **Chiêu cuối / Tấn công / Chịu đòn / Buồn khi thua**. Canvas dùng WebP, có phát lại, tạm dừng, tua và tốc độ 0,5×. Bản game dùng `frontend/owl-animation.js` và `frontend/arena-art/owl/`.

- **Chiêu cuối:** dịu ánh sân thành đêm → mắt sáng khóa mục tiêu → lướt bằng hai cánh → bóng cánh khép vầng trăng quanh đối thủ → lóe sao → đáp và ăn mừng. Tên lúc 0,65 giây, bay từ 0,95, tác động 1,75, thắng từ 1,90 đến 3,00.
- **Tấn công:** mở cánh, lướt tới rồi hạ cánh. **Chịu đòn:** ngạc nhiên, lùi nhẹ và nhắm mắt. **Thua:** cúi đầu, rũ cánh và ngồi buồn; không thương tích.
- **Tài sản:** `source/poses.png` giữ PNG nguồn alpha; `assets/poses.webp` 1.254×1.254, 16 tư thế, 314.304 byte. `poses.js` và JSON runtime chứa ranh giới crop. Bốn hoạt cảnh dùng chung một sheet.
- **Xem trước:** [GIF](exports/demo.gif), [MP4](exports/demo.mp4), [contact sheet](qa/contact-sheet.png). GIF/MP4 chiêu cuối đúng 90 frame/3,000 giây; chỉ để xem, game không tải các tệp này.

Ảnh tham chiếu: Cú mèo ở hàng 2 cột 2 của `bo-nhan-vat-demo-2026-11-11/02-thu-va-canh.png`; vật liệu theo ảnh gốc Cáo Nâu/Mầm Sách. Tạo bằng **built-in image_gen**, prompt đầy đủ và nguồn tại [source/PROMPTS.json](source/PROMPTS.json). Giữ thân nâu vàng tròn, hai đĩa mặt kem, mắt nâu, má cam, mỏ nhỏ, hai cánh, hai chân và chùm lông tai.

Runtime chỉ xử lý hình ảnh; kết quả, sát thương, thời gian câu hỏi và quyền tài khoản vẫn do game quyết định. Tải sheet khi có Cú mèo; dừng lịch vẽ khi kết thúc, thu dọn khi rời game, hoàn tất trình diễn khi ẩn tab và dùng tư thế tĩnh khi giảm chuyển động.

Người dùng chọn **commit riêng Cú mèo kèm bản vá tích hợp**, vì mã game nền và các chat khác còn chưa commit. [integration/](integration/) chứa bản vá các hook chung; các hook đang áp dụng ở working tree để chạy local, được giữ ngoài commit riêng. Bản vá cần mã game hiện có trong workspace này; commit không phải toàn bộ ứng dụng độc lập.

QA: [qa/qa-report.json](qa/qa-report.json) kiểm bản xuất; [qa/demo-checks.json](qa/demo-checks.json) kiểm bốn hoạt cảnh và điều khiển ở năm kích thước. Báo cáo game, kiểm thử và triển khai được ghi trong [HANDOFF.md](HANDOFF.md). Chưa đo FPS/CPU trên điện thoại thật hoặc mạng chậm. Không có âm thanh mới trong bộ tài sản; game dùng hiệu ứng sẵn có.
