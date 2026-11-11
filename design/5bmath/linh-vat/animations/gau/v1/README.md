# Gấu — Chưởng Gấu Đại Lực · v1

Mở `demo.html` để xem bốn hoạt cảnh Canvas: **chiêu cuối**, **tấn công**, **chịu đòn** và **buồn khi thua**. Có chọn hoạt cảnh, phát lại, tạm dừng, tua và tốc độ 0,5×. Bản Canvas chỉ tải WebP, không tải GIF/MP4 hoặc PNG nguồn.

Chiêu cuối: Gấu đứng vững, nâng hai chân trước, chưởng xuống sân; sóng đá bo tròn lan sang Cáo Nâu, bụi hình bàn chân bung sao rồi Gấu ăn mừng. Tên chiêu hiện từ 0,65 giây, trước động tác chính; tác động đối thủ lúc 1,75 giây; chiến thắng 1,90–3,00 giây. Không thay đổi luật hay lượng sát thương trong game.

## Tệp

- `source/poses.png`, `source/reactions.png`: ảnh PNG alpha do imagegen tích hợp tạo từ đúng ảnh Gấu ở hàng 1/cột 2, bảng `02-thu-va-canh.png`, tham chiếu style gốc Cáo Nâu/Mầm Sách.
- `source/PROMPTS.json`: prompt và nguồn thực tế do phiên gốc lưu.
- `assets/poses.webp`, `assets/reactions.webp`, `poses.js`, `reactions.js`: ảnh chạy và tọa độ 16 tư thế mỗi sheet; giữ nguồn PNG.
- `animation.js`, `config.js`, `demo.html`: bản xem Canvas độc lập, không dùng choreography Chó.
- `exports/demo.gif`, `exports/demo.mp4`: chiêu cuối 3,000 giây / 90 khung / 30 fps.
- `exports/attack.*`, `exports/hit.*`, `exports/defeat.*`: ba hoạt cảnh bổ sung, mỗi bản xem dài 3 giây.
- `qa/contact-sheet.png`, `qa/reactions-contact-sheet.png`: hình các mốc chính để đối chiếu.
- `qa/qa-report.json`, `qa/demo-controls-report.json`: kết quả xuất/kiểm tra thực tế.

Demo có bản sao nền và Cáo Nâu trong `assets/garden.webp`, `assets/opponents.webp`, giống từng byte với nguồn chung, để thư mục Gấu tự mở độc lập. Không sửa tài sản chung. Không có âm thanh. GIF/MP4 chỉ để xem và duyệt; Canvas/WebP là tài sản chạy. Giảm chuyển động khởi đầu ở trạng thái tạm dừng, vẫn có nút phát thủ công. Chưa đo FPS trên điện thoại thật.

Yêu cầu mới trong chat Gấu đã cho phép tích hợp game, commit và triển khai **local**; trạng thái `pending_review` của bộ công cụ không có nghĩa người dùng đã duyệt chất lượng từng ảnh. Việc tích hợp/game/local được phiên gốc ghi riêng, không tự suy ra đã phát hành website công khai.
