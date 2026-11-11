# Cá heo — Sóng Âm Cầu Vồng

Mở [demo.html](demo.html) để chọn **chiêu cuối, tấn công, chịu đòn, buồn khi thua**. Canvas dựng từ hai sheet WebP có alpha; không phát video thay cho game.

- Chiêu cuối: 3,000 giây / 30 fps / 90 frame. Tên 0,65 s, bật nhảy/lộn vòng 0,95 s, cầu nước tác động 1,75 s, bọt cầu vồng và ăn mừng 1,90–3 s.
- [GIF](exports/demo.gif), [MP4 H.264](exports/demo.mp4), [contact sheet](qa/contact-sheet.png).
- WebP hoạt cảnh riêng: [tấn công](exports/attack.webp), [chịu đòn](exports/hurt.webp), [buồn khi thua](exports/lose.webp); mỗi bản 3 giây/90 frame, chỉ để xem ngoài game.
- Hai sheet game: 459.542 + 495.450 = **954.992 byte**, chưa tính mã/nền; chiêu cuối tải theo nhu cầu. Giữ PNG nguồn và [prompt/tham chiếu](source/PROMPTS.json).

Người dùng yêu cầu riêng Cá heo **tích hợp game, commit cục bộ, triển khai local** ngày 11/11/2026, thay phạm vi demo cũ với nhân vật này. Chọn tại http://localhost:8765/linh-vat/ rồi vào Đấu trí. Giữ luật/sát thương/điểm; ghi mỗi câu bot vào phần xem lại một lần khi chờ chiêu kết thúc.

Đã đạt: 2 test Cá heo, toàn bộ 77 test Docker; Chrome năm kích thước dọc/ngang, bốn mode/controls/timeline/giảm chuyển động/cleanup; hai build và SEO tám trang công khai. HTTP thật trong container: mã/ảnh 200, nội bộ/URL lạ 404, mẫu chấm 10/10, DB integrity ok/FK 0. Luồng app trong trình duyệt dùng giao vận thay thế nối Python thật qua stdin với DB thử do loopback sandbox hạn chế; không gọi đó là kiểm HTTP trình duyệt ngoài sandbox. Chưa đo FPS thiết bị thật.

Các tệp dùng chung có baseline chưa commit và nhiều chat đang sửa. [Bản vá](integration.patch) chỉ ghi phần Cá heo; xem [phạm vi commit](INTEGRATION.md). Không push/CI/phát hành công khai. Tự kiểm không phải phê duyệt tạo hình của người dùng.
