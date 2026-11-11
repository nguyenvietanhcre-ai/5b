# Cáo Nâu — Lốc Đuôi Tinh Quái / v1

Tạo ngày 11/11/2026 cho 5BMath. Người dùng yêu cầu bốn animation và cho phép tích hợp game, commit cục bộ, triển khai localhost; chỉ đạo mới thay phạm vi chỉ-demo trong brief chép lúc init. Chưa có phê duyệt mỹ thuật cuối hoặc yêu cầu push/phát hành công khai.

- Mở `demo.html`: Canvas + WebP, chọn chiêu cuối / tấn công / chịu đòn / buồn khi thua, phát lại, tua và tốc độ 0,5×.
- `exports/demo.gif`, `exports/demo.mp4`: chiêu cuối đúng 3,000 giây, 90 frame, 30 fps; video H.264 1280×720. GIF/MP4 chỉ để xem, game không tải chúng.
- `exports/attack.*`, `exports/hit.*`, `exports/lose.*`: ba động tác phụ, mỗi bản 90 frame/3,000 giây, có giữ tư thế cuối. Cả ba MP4 đã giải mã thành công; xem `qa/reactions-report.json`.
- Chiêu cuối: đuôi ve vẩy đánh lạc hướng → lách sau Mầm Sách → quét đuôi tạo lốc lá cam → nâng đối thủ → bung lá và chiến thắng. Tên hiện 0,65s trước động tác lao 0,95s; tác động 1,75s; thắng từ 1,90s.
- Hai sheet 4×4, 32 tư thế, giữ hai tai, bốn chi, một đuôi đầu kem và khăn xanh. PNG gốc trong `source/`; prompt và ảnh tham chiếu thật trong `source/PROMPTS.json` và `source/reference.png`.
- WebP runtime: poses 445.786 byte, reactions 439.138 byte; tổng 884.924 byte, chưa tính metadata/mã. Ảnh nén đã xem trên nền kem và xanh đậm tại `qa/webp-light-dark.png`.
- Nền và đối thủ sao chép từ workshop vào `assets/` để demo tự đủ tệp; không sửa nguồn dùng chung. Chất liệu nỉ/đất sét mềm từ ảnh Cáo Nâu/Mầm Sách.

## Tích hợp và kiểm tra

Runtime game: `frontend/fox-animation.js`, `frontend/fox-animation.css`, `frontend/arena-art/cao-nau/`. Tải khi có Cáo Nâu, bốn trạng thái theo kết quả game; chiêu cuối ba giây dùng lại khoảng giữ màn kết quả, không thay sát thương/câu hỏi/DB.

Kho có nhiều thay đổi chưa commit của các chat khác. `integration.patch` và `INTEGRATION.md` lưu chính xác các móc nối riêng Cáo Nâu trong bốn tệp chung; không gom toàn bộ game/hồ sơ đang phát triển vào commit riêng này.

`qa/qa-report.json` (exporter) kiểm GIF/MP4, timeline, WebP-only, năm viewport, controls/reduced motion. Các báo cáo trong `qa/` chỉ là kiểm tra kỹ thuật, không tự phê duyệt mỹ thuật. Chưa đo FPS/CPU trên điện thoại thật. Tất cả học sinh/đấu bot thử nghiệm chỉ dùng fixture/database QA riêng; không tạo dữ liệu thử trong volume người dùng.

Owner: `cao-nau-01a1cb4f`. Chỉ sửa job này; đọc HANDOFF trước khi claim. Công cụ dùng chung ở `tools/mascot-animation/`, không cần nó để mở demo đã xuất.

Bản game local đã xác minh tại http://127.0.0.1:32773/ (container riêng mam-toan-fox-web-1, dữ liệu riêng trong work/mascot-animation/cao-nau/v1/local-data). Cổng được cấp tự động để tránh các chat khác đang dùng8765/8794; nếu tạo lại container hãy đọc cổng bằng `docker compose -f work/mascot-animation/cao-nau/v1/compose.local.yaml port web 8000`. Báo cáo `qa/local-release.json` xác nhận HTTP200 và SHA mã/ảnh/móc game khớp nguồn.

`qa/final-local-assets-report.json` xác minh bốn chế độ và năm viewport sau khi chuyển đường dẫn nền/đối thủ sang assets riêng; nội dung hai ảnh giữ nguyên SHA-256, không sửa báo cáo exporter cũ. `qa/game-smoke/` có 10 nhóm kiểm tra runtime đạt qua request giả lập từ tệp, không chứng nhận API thật.
