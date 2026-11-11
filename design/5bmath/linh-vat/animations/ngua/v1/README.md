# Ngựa — Vó Ngựa Cuồng Phong

Mở [demo.html](demo.html) để xem đủ bốn trạng thái: chiêu cuối, tấn công thường, chịu đòn và buồn khi thua. Canvas dùng WebP; không phát lại video để giả lập chuyển động. Có chọn trạng thái, phát lại, tạm dừng, tua và tốc độ 0,5×. Query `?action=attack`, `?action=hit`, `?action=defeat` mở từng hoạt cảnh.

## Bản xuất

- [Chiêu cuối GIF](exports/demo.gif) / [MP4](exports/demo.mp4): dấu móng U → lốc hình ngựa → Cáo xoay một vòng → Ngựa tự hào.
- [Tấn công GIF](exports/attack.gif) / [MP4](exports/attack.mp4).
- [Chịu đòn GIF](exports/hit.gif) / [MP4](exports/hit.mp4).
- [Buồn khi thua GIF](exports/defeat.gif) / [MP4](exports/defeat.mp4).

Cả tám bản xuất đều dài 3,000 giây, 90 frame. GIF 768×432; MP4 H.264 1280×720, đã giải mã khung đầu. Bản game phát tấn công/hit ngắn hơn để phù hợp lượt đấu; chiêu cuối dài ba giây và cảnh buồn giữ tư thế cuối.

## Nguồn và runtime

PNG gốc `source/poses.png`, `source/reactions.png` giữ nguyên; prompt và ảnh tham chiếu thực tế ghi ở [source/PROMPTS.json](source/PROMPTS.json). Ngựa nâu hạt dẻ/bờm và đuôi sẫm/mõm kem/bốn chân móng guốc, chất liệu Cáo Nâu/Mầm Sách. Không thêm sừng, cánh hoặc tay riêng.

Hai atlas WebP: poses **342.812 byte**, reactions **323.338 byte**, tổng **666.150 byte**. Hai JSON khung tổng 3.680 byte. Demo còn dùng nền/đối thủ nội bộ đã copy vào assets để tự chạy. Asset game ở `frontend/arena-art/horse/v1/`; chỉ tải khi cần trong lobby/Linh vật/trận, không tải PNG/GIF/MP4 nguồn.

`frontend/horse-animation.js` và CSS là module độc lập. Lựa chọn **Ngựa · ngoại hình trận đấu** lưu browser-local, không thay linh vật trong tài khoản, DB, sát thương, kết quả hoặc XP. Hook chỉ trì hoãn hiển thị màn kết quả để chiêu cuối chạy đủ ba giây. Có reduced motion, dừng RAF/timer khi ẩn/rời màn, giữ linh vật cũ nếu asset lỗi.

## Tích hợp và kiểm tra

[integration/README.md](integration/README.md) và `integration/install.cjs` ghi cách cài vào game nền hiện có. Installer nhận thư mục chứa frontend/learning.js và backend/server.py; xác định game hợp lệ trước dùng. Bản commit addon không bao gồm các phần game nền đang chưa commit ở những chat khác; demo này tự đầy đủ.

- `qa/qa-report.json`: ultimate timeline .65/.95/1.75/1.90, đúng ba giây/90 frame, WebP-only, năm viewport, không lỗi JS/tài nguyên.
- `qa/reactions-export-report.json`: ba trạng thái bổ sung, đúng thời gian/khung và MP4 decode.
- QA runtime đầy đủ lưu cục bộ tại `work/horse-animation/integration/qa-runtime.json` (30 checks) và `work/mascot-animation/ngua/v1/release/horse-game-qa.json` (bot attack→ultimate→win và hit→defeat).
- Đã xem ảnh WebP trên nền kem/tối, contact sheet và các cảnh đại diện. Chrome mô phỏng điện thoại/tablet dọc-ngang/desktop không tràn; nút >=44px.

Hình ảnh chờ người dùng xem, chưa tự approved. Demo không có âm thanh riêng; game giữ âm thanh hiện có. Chưa đo FPS/CPU trên điện thoại thật. Hidden/dispose được kiểm qua trạng thái visibility giả lập và code lifecycle; Chrome headless không xác minh được chuyển tab native.
