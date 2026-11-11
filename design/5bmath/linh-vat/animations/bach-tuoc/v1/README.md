# Bạch tuộc — Tám Tay Ảo Thuật

Mở [demo.html](demo.html) để chọn **Chiêu cuối / Tấn công / Chịu đòn / Buồn khi thua**, phát lại, kéo thời gian hoặc xem chậm. Canvas chỉ tải ba WebP; GIF/MP4 dùng để xem trước.

- [Chiêu cuối GIF](exports/demo.gif), [MP4](exports/demo.mp4), [poster](exports/poster.png).
- Ba hoạt cảnh bổ sung có WebP động và GIF trong `exports/` sau khi xuất.
- 16 tư thế: `source/poses.png` (2.119.411 byte), `assets/poses.webp` (415.190 byte, alpha thật); khung cắt tại `poses.js`.
- 0–0,65 s thu tay/lấy đà; tên hiện 0,65 s; mực tím che nhân vật; 0,95–1,90 s tám tay ảo với giác hút và tám bóng nước quanh đối thủ, hội tụ 1,75 s; sau 1,90 s hiện lại và ăn mừng. Đúng 3 giây/90 frame/30 fps.
- Tấn công thường tung một bóng nước. Chịu đòn giật mình rồi bình tĩnh. Thua dùng hai nét mặt buồn riêng và lời động viên. Không có vết thương.

Người dùng đã yêu cầu **tích hợp game, commit và triển khai local** trong chat Bạch tuộc ngày 11/11/2026. Phạm vi này thay phần demo-only trong bản đầu bài đã sao chép của job này. Không mở rộng quyền đó sang các nhân vật khác hoặc phát hành Internet.

Runtime riêng: `frontend/octopus-animation.js`, `frontend/octopus-animation.css`; ba tài sản `frontend/arena-art/bach-tuoc-{poses.webp,frames.json,idle.webp}`. Installer `tools/mascot-animation/integrate-bach-tuoc.cjs` thêm các hook vào bản Góc học tập hiện có, bảo toàn các linh vật khác. Các tệp nền ứng dụng đang có nhiều thay đổi trước phiên; commit Bạch tuộc giữ bundle/installer riêng để không đưa toàn bộ công việc song song vào cùng commit. Hướng dẫn và tình trạng thực tế cuối cùng ở [HANDOFF.md](HANDOFF.md).

Giữ nguyên luật, sát thương, chấm điểm và ngân hàng câu hỏi. Chưa có âm thanh riêng. Chưa đo FPS/CPU trên điện thoại thật. Tạo hình/animation vẫn chờ phản hồi thẩm mỹ của người dùng; không tự gắn nhãn approved.

Bản game Python riêng đang ở `http://127.0.0.1:8767/`, DB thử riêng với Docker8765. Lệnh mở lại khi cổng trống: `powershell -NoProfile -ExecutionPolicy Bypass -File tools/mascot-animation/start-bach-tuoc-local.ps1`. Xem các kiểm tra thực tế và giới hạn ở HANDOFF.

Nguồn tạo: built-in image_gen với đúng ô Bạch tuộc ở bảng biển v3 và ảnh gốc Cáo Nâu/Mầm Sách. Xem `source/PROMPTS.json`. Nền/đối thủ WebP được tái dùng từ `../../shared/`. Các trang này chỉ để local/review, có noindex.
