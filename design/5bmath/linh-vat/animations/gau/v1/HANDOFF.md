# Bàn giao Gấu / v1

- Chủ phiên: gau-01a1cb4b
- Trạng thái bộ công cụ: `pending_review`; chưa tự ghi approved.
- Hai sheet PNG nguồn, WebP và metadata đã có: 16 tư thế chiêu cuối + 16 tư thế tấn công/chịu đòn/thua/idle/thắng. Prompt và hai ảnh tham chiếu thực tế ở `source/PROMPTS.json`.
- Demo riêng `demo.html` dùng Canvas/WebP, bốn lựa chọn hoạt cảnh, replay/pause/seek/0,5×. Không sửa shared/template/catalog hoặc job khác.
- Đóng gói độc lập: `assets/garden.webp`, `assets/opponents.webp` là bản sao cùng byte của shared; config dùng đường dẫn trong job, không cần commit các thư mục chat khác. Smoke sau đổi đường dẫn ở `qa/portability-report.json`.
- Choreography Gấu đứng vững, hai chân trước giơ cao, chưởng xuống đất, sóng đá bo tròn và bụi hình bàn chân ở Cáo Nâu; ăn mừng cuối. Đã sửa nhịp cho khớp runtime game: overhead đến 1,36; hạ chân đến 1,58; chạm đất 1,58–1,75; sóng lan 1,55–1,75; mục tiêu chịu tác động 1,75; thắng từ 1,90.
- `exports/demo.gif` (1.414.250 byte) và `demo.mp4` (1.910.214 byte): exporter chuẩn sau chỉnh nhịp, 90 khung/3,000 giây, MP4 H.264 giải mã khung đầu 1280×720, QA đạt. `exports/attack.*`, `hit.*`, `defeat.*` đã hoàn thành, mỗi bản 90 khung/3 giây. Video bổ sung giải mã đủ metadata/khung đầu 1280×720, không lỗi.
- QA đã đạt: cú pháp JS; timeline/name-before-attack; request chỉ ảnh WebP; năm viewport dọc/ngang × bốn hoạt cảnh không tràn ngang, controls >=44px; replay/pause/seek/0,5×/play-once; reduced-motion khởi đầu tạm dừng và có phát thủ công. Đã mở xem `qa/contact-sheet.png`, `qa/reactions-contact-sheet.png` và WebP.
- Báo cáo: `qa/qa-report.json`, `qa/demo-controls-report.json`, `qa/reaction-video-probe.json`; công cụ riêng ở `work/mascot-animation/gau/v1/{demo-qa,probe-reactions}.cjs`.
- Người dùng đã yêu cầu tích hợp game, commit và triển khai local trong chat này. Phiên gốc phụ trách game/runtime/Git/Docker/bộ nhớ; trạng thái thực tế và commit cần đối chiếu bản ghi chat Gấu. Chưa suy ra đã push hoặc phát hành public.
- Giới hạn: chưa có âm thanh, chưa đo FPS trên điện thoại thật hoặc mạng chậm. Bản GIF/MP4 là để xem, không chạy trong game.
- Trước khi bàn giao chat khác, phiên gốc hoàn tất ghi trạng thái tích hợp/QA/local/commit, rồi release bằng owner trên. Không tự giành lease của phiên còn chạy.

## Hoàn tất gói và tích hợp

- Đã release owner đúng quy trình. Không còn tác vụ đang ghi job.
- Gấu đã nối registry/persist/API/selector/Canvas ở bản làm việc local; sát thương/XP/deadline giữ nguyên. Tên chiêu trong khoảng giữa sân, có giữ đủ ba giây trước kết quả. Bộ giảm chuyển động/ẩn tab/cleanup/fallback ảnh đạt.
- Người dùng chọn **chỉ commit gói Gấu và bản vá tích hợp**. `integration/` có patch năm tệp dùng chung, test lưu lựa chọn và hash sáu tệp runtime. Các tệp nền game/chỉnh sửa chung vẫn ngoài commit gói này; đọc integration/README trước áp dụng vào nền khác.
- QA thực tế: hai test Gấu Windows; 13 test HTTP Windows chạy ngoài sandbox đạt. Lượt native full69 có lỗi socket sandbox nên không gọi là full xanh. Docker image `mam-toan:gau-20261111-v1` đạt full77 tests/61,661s sau cấp vùng tạm /work cho test; lần đầu phát hiện fixture test ghi filesystem chỉ đọc, đã sửa test Gấu dùng /tmp trong Docker và chạy lại toàn bộ.
- Game UI trên DB thử riêng: chọn Gấu/reload/lưu; đánh20HP/chịu20HP; chiêu cuối hai phía rồi đúng win/lose, kết quả Gấu ngồi buồn; năm viewport dọc/ngang/desktop, không tràn/JS/request error; điều hướng dọn runtime. Nguồn không đổi trong lượt QA đạt. Báo cáo đã sao vào qa/.
- Build static/SEO tám trang đạt. Docker đã dựng/healthy; nhiều chat cùng thay container8765 nên phải đọc lần HTTP/hash cuối trong bản ghi chat để biết image đang phục vụ. Phiên Gấu chỉ triển khai loopback; xét duyệt tự động đã từ chối bindLAN vì phạm vi yêu cầu hiện tại.
- Backup DB nhất quán `work/mascot-animation/gau/v1/gau-before.sqlite3`, integrityOK. Không tạo người dùng thử trong database8765 của người dùng. Local release/sổ hash ở work/mascot-animation/gau/v1/local-release/. Không push/CI/public.
