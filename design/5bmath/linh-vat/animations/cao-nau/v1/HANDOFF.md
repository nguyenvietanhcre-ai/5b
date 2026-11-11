# Bàn giao Cáo Nâu / v1

- Owner: `cao-nau-01a1cb4f`; job riêng, không sửa job khác. Mỹ thuật vẫn `pending_review`.
- Người dùng cho phép bốn animation, tích hợp game, commit và triển khai local ngày 11/11/2026. Quy tắc demo-only trong BRIEF chép lúc init là lịch sử. Không push hay phát hành công khai.
- Hoàn thành: 32 tư thế trong hai PNG alpha, hai WebP tổng 884.924 byte và metadata; prompt/ảnh tham chiếu thật tại source. Canvas đủ ultimate/attack/hit/lose, replay/tua/0,5×/reduced motion; nền/đối thủ tự đủ trong assets.
- Bốn cặp GIF/MP4, mỗi bản 90 frame/3s. Ultimate 2216053/2103759 byte; attack 844176/1526136, hit 790534/1516935, lose 932425/1528188 byte. MP4 H.264 1280×720 đã giải mã thực tế.
- Chiêu cuối: ve vẩy đuôi, lách sau Mầm Sách, quét đuôi tạo lốc lá cam, nâng đối thủ, pháo lá/thắng; tên .65/đòn .95/impact1.75/thắng1.9s.
- Runtime: frontend/fox-animation.js + CSS, frontend/arena-art/cao-nau; móc game/index/server/build trong working tree. `integration.patch` lưu đúng phần Cáo Nâu ở bốn tệp chung, đã kiểm reverse apply. Không áp lần hai; commit riêng không gom toàn bộ game chưa theo dõi của chat khác.
- QA: standalone/bốn GIF/MP4/timeline/alpha/năm viewport/controls đạt; runtime 10 nhóm qua request giả lập không lỗi JS/overflow, lazyload/noRAF idle/cleanup/reduced motion. Đã sửa timestamp RAF âm, guard/reset/cleanup và chờ WebP trước đồng bộ đòn. Xem qa và bản ghi phiên.
- Python: Windows bị sandbox socket và Cá Heo sửa đồng thời; Docker chạy 75 test, ba lỗi hạ tầng /app/work chỉ đọc. Chạy lại đúng Gấu/Chim sẻ/Voi với tmpfs, cả bốn test đạt. Không coi đây là một lượt full suite xanh. Các bài HTTP trong lượt Docker đã đạt. Không đổi luật/HP/câu hỏi/XP/DB thật.
- Local hoàn tất: container riêng `mam-toan-fox-web-1`, image `mam-toan:fox-local-01a1cb4f`, healthy tại http://127.0.0.1:32773/. Cổng 8765/8794 do chat khác dùng; bản riêng được Docker cấp cổng tự động. Dữ liệu riêng ở work/mascot-animation/cao-nau/v1/local-data. HTTP200 và SHA renderer/CSS/hai WebP/metadata/móc Cáo Nâu trong learning đều khớp nguồn; qa/local-release.json. Không tự xóa container/volume của chat khác. Trạng thái commit cuối ở docs/chat/2026-11-11-animation-cao-nau.md.
- Đã sửa mép tai trên mobile bằng giới hạn chính xác khung hình sau xoay; kiểm 21 lần vẽ trên sân352px và ảnh cuối đạt, xem qa/game-flow/ultimate-bounds-390.png. Các ảnh overlay cũ giữ để truy vết, không phải bản cuối.
- Giới hạn: chưa duyệt thẩm mỹ cuối/chưa đo FPS/CPU điện thoại thật; API QA8793 timeout, frontend fixture không chứng nhận API thật. Không CI/push/public deployment.
- Tiếp tục: mở đúng F:\ChatGPT Math Project, đọc bộ nhớ/bản ghi, kiểm Git/container thực tế; xem demo rồi sửa đúng job. Chuyển người làm dùng release/claim, không tự xóa lease.
