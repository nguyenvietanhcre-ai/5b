# Tích hợp Bướm vào bản game local hiện có

Mã lưu tài khoản: `butterfly`; tên hiển thị: **Bướm**. Chiêu cuối **Vũ Điệu Ngàn Cánh**. Yêu cầu người dùng ngày 11/11/2026 cho phép tích hợp và commit local riêng nhân vật này. Không push hoặc phát hành công khai.

Tệp runtime trong `frontend/`: `butterfly-renderer.js`, `butterfly-animation.js`, `butterfly-animation.css` và `arena-art/butterfly-poses.webp`. Canvas dùng một atlas WebP 356.800 byte; không tải GIF/MP4/PNG nguồn. Atlas được tải khi Bướm xuất hiện. Điện thoại dùng 48 bóng bướm, máy lớn 128; reduced motion dùng tư thế tĩnh. Playback có điểm dừng và cleanup khi rời trang/ẩn tab.

Các tệp dùng chung đã được nối trong workspace: `backend/platform_api.py`, `backend/server.py`, `frontend/index.html`, `frontend/learning.js`, `scripts/build-pages.cjs`. Chúng đang có nhiều thay đổi chưa commit từ các chat khác, nên commit riêng bộ Bướm không bao gồm toàn bộ nội dung các tệp này. Công cụ bên dưới lưu lại đầy đủ các điểm nối cần thiết, gồm giữ màn hình trận đủ ba giây cho finale. Bộ Bướm cần nền ứng dụng Learning/Arena hiện có trong workspace; không phải một game độc lập.

Từ gốc dự án:

```powershell
node tools/mascot-animation/install-butterfly.cjs --check
# Chỉ khi cần nối lại các hook còn thiếu:
node tools/mascot-animation/install-butterfly.cjs --apply
```

Mặc định chỉ kiểm 20 điểm nối. `--apply` lập/kiểm toàn bộ kế hoạch trước khi ghi, giữ nội dung khác, kiểm anchor duy nhất, thứ tự script và thay đổi đồng thời. Không đổi luật đấu, sát thương, deadline hoặc XP. Không tự đánh dấu mỹ thuật đã được người dùng duyệt.

Kiểm chứng: full 74 kiểm thử Python trên Windows đạt; 2 kiểm thử API Bướm và 13 kiểm thử HTTP/chấm bài trong image Docker đạt; hai bản dựng/SEO Cloudflare và GitHub đạt. Các kiểm tra Canvas và video xem `qa/`, chi tiết kiểm tra tích hợp/localhost/commit trong HANDOFF và bản ghi cục bộ `docs/chat/2026-11-11-animation-buom-v1.md`.

Chưa đo FPS/CPU trên điện thoại thật. Bản GIF/MP4 dành để xem; game chạy Canvas/WebP. Demo trong thư mục này dùng nền/đối thủ tại `../../shared/` theo workshop.
