# Chim sẻ — Lốc Xoáy Ríu Rít

Bộ animation 5BMath ngày 11/11/2026, theo ảnh Chim sẻ hàng 1/cột 3 của bảng `02-thu-va-canh.png` và chất liệu Cáo Nâu/Mầm Sách. Built-in image_gen tạo PNG alpha 16 tư thế; prompt và nguồn tham chiếu lưu trong [source/PROMPTS.json](source/PROMPTS.json).

Mở [demo.html](demo.html) để chọn **Chiêu cuối / Tấn công / Chịu đòn / Thua cuộc**, phát lại, tạm dừng, tua hoặc xem chậm. Thư mục chứa đủ ảnh WebP cần cho demo; không cần video để chạy Canvas. Chiêu cuối 3 giây: tên hiện 0,65 giây → đàn chim và lốc lông vũ/nốt nhạc → tác động 1,75 giây → đáp xuống ăn mừng. Tấn công dùng vung cánh, chịu đòn có giật mình và hồi phục, thua giữ tư thế cúi đầu/cụp cánh.

- [GIF duyệt](exports/demo.gif), [MP4 H.264](exports/demo.mp4), [ảnh đại diện](exports/poster.png).
- Runtime game: `frontend/arena-sparrow-animation.js`, `.css`, `frontend/arena-art/chim-se/`.
- Sprite WebP 431.226 byte, PNG nguồn 1.970.798 byte, nền trong suốt; game tải thêm chân dung WebP 21.806 byte và metadata 1.009 byte khi cần.
- [Báo cáo bản xuất](qa/qa-report.json), [bảng khung hình](qa/contact-sheet.png), [bàn giao](HANDOFF.md).
- [Phạm vi commit và patch tích hợp](INTEGRATION.md): nền game hiện vẫn có thay đổi chưa commit từ các chat khác. Không dùng commit riêng Chim sẻ để khẳng định đã lưu toàn bộ nền game.

Người dùng đã yêu cầu tích hợp game, commit và cập nhật localhost trong chat này, thay giới hạn demo cũ cho riêng Chim sẻ. Không tự coi là đã duyệt mỹ thuật cuối cùng. Giữ luật sát thương/kết quả trận hiện có. Reduced motion dùng tư thế tĩnh; Canvas ngừng vẽ khi kết thúc/ẩn tab/rời sân. Chưa đo FPS trên điện thoại thật và chưa có âm thanh ríu rít riêng.
