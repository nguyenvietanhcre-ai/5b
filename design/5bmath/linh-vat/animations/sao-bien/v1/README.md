# Sao biển — Ngũ Tinh Tỏa Sáng

Canvas + WebP, tạo ngày 11/11/2026 cho 5BMath. Có bốn trạng thái: chiêu cuối, tấn công thường, chịu đòn và buồn khi thua.

- Mở [demo.html](demo.html), chọn trạng thái, phát lại hoặc kéo thời gian. Mỗi bản xem kéo dài ba giây; có tốc độ 0,5× và giảm chuyển động.
- Xem [GIF](exports/demo.gif), [MP4 H.264](exports/demo.mp4) hoặc [bảng khung hình](qa/contact-sheet.png) của chiêu cuối.
- Chiêu cuối: co/xòe năm cánh → đúng năm bản sao xoay quanh đối thủ → nối ngôi sao → cột sáng → bung sao và ăn mừng. Tên hiện 0,65 giây, bắt đầu đòn 0,95, tác động 1,75, thắng từ 1,90; 90 khung hình/30 fps/3,000 giây.

## Nguồn và nhận diện

Imagegen tích hợp tạo hai PNG gốc giữ nguyên tại `source/`. Prompt đầy đủ và ảnh tham chiếu thực tế ở [source/PROMPTS.json](source/PROMPTS.json). Sao biển lấy đúng hàng 2/cột 3 trong bảng `03-bien-va-ong-v3.png`; vật liệu và ánh sáng theo Cáo Nâu/Mầm Sách. Giữ năm cánh tròn màu đào–san hô, chấm kem, mắt nâu và má cam; không thêm tay/chân người.

`assets/poses.webp`: 592.544 byte, 16 tư thế chiêu cuối. `assets/reactions.webp`: 294.666 byte, 16 tư thế: hàng 1 tấn công, hàng 2 chịu đòn, hàng 3 thua buồn, hàng 4 nghỉ. Tọa độ trong `poses.js`/`reactions.js` nhận toàn bộ hình theo alpha, vượt ranh giới ô danh nghĩa khi cần để không cắt cánh. Không chỉnh sửa PNG gốc.

## Tích hợp cục bộ

Yêu cầu mới của người dùng trong chat này cho phép tích hợp game, commit và triển khai localhost, thay giới hạn demo trong brief gốc. Lựa chọn lưu với mã `starfish`, tên `Sao biển`; game tải WebP/JSON khi dùng Sao biển, không tải GIF/MP4. Runtime/CSS riêng ở `frontend/arena-starfish.*`; ảnh chạy game ở `frontend/arena-art/sao-bien-v1/`. Kết quả trận chờ chiêu cuối kết thúc; không thay sát thương, điểm hay luật.

Do nền game hiện có nhiều tệp chưa commit từ các chat khác, commit riêng Sao biển chứa mã/tài sản/kiểm thử và bản vá chính xác các hook chung trong `integration/`. Các hook đã áp dụng trong working tree cục bộ; commit này cần nền game hiện tại để áp dụng lại, không phải bản game độc lập từ HEAD cũ. Không đưa toàn bộ tệp chung chưa commit vào commit Sao biển.

Hình ảnh/choreography giữ trạng thái `pending_review`, chưa tự đánh dấu người dùng đã duyệt. Xem [HANDOFF.md](HANDOFF.md) cho kết quả kiểm thử và trạng thái bàn giao. Chưa đo FPS/CPU trên điện thoại thật.
