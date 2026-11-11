# Cua biển — Song Càng Khóa Sóng

Mở [demo.html](demo.html), chọn **Chiêu cuối / Tấn công / Chịu đòn / Thua cuộc**. Canvas chỉ tải ba ảnh WebP. Có nút phát lại, tạm dừng, thanh tua và tốc độ 0,5×. Khi thiết bị bật chế độ giảm chuyển động (reduced motion), demo không tự phát.

- [GIF chiêu cuối](exports/demo.gif): 768 × 432 px, 90 khung, 3,000 giây, 2.195.277 byte.
- [MP4 chiêu cuối](exports/demo.mp4): 1280 × 720 px, H.264, 90 khung, 3,000 giây, 1.974.402 byte.
- [WebP 16 tư thế](assets/poses.webp): 1247 × 1261 px, alpha thật, 298.234 byte. PNG cuối trong `source/` và bản đầu bị sát ô được giữ riêng để truy vết.
- [Prompt chính](source/PROMPTS.json) và [prompt sửa khoảng cách](source/PROMPT-SPACING.json). Cả hai dùng built-in imagegen.

Ảnh tham chiếu: đúng Cua biển ở hàng 2, cột 2 của `bo-nhan-vat-demo-2026-11-11/03-bien-va-ong-v3.png`; phong cách từ `mam-sach-cao-nau-goc.png`. Giữ hai càng, tám chân đi, hai mắt trên cuống, mai cam san hô và chất liệu nỉ/đất sét mềm.

Nhịp chiêu cuối:

- 0–0,65 giây: lấy đà.
- 0,65 giây: hiện tên chiêu.
- 0,95 giây: lướt ngang, để lại bóng cua; hai càng ánh sáng ép sóng thành bong bóng quanh Cáo Nâu.
- 1,75 giây: tác động chính.
- 1,90–3,00 giây: bong bóng bật tung thành sao, Cua biển ăn mừng chiến thắng.

Các trạng thái bổ sung dùng tư thế 13 để chịu đòn, 14 để hồi phục và 15 để buồn khi thua; tư thế 12 dành cho chiến thắng. Giữ nguyên luật tính kết quả, sát thương và XP.

## Tích hợp local

Người dùng đã yêu cầu tích hợp game, commit và triển khai local trong chat này. Mã runtime ở `frontend/arena-crab-animation.js/.css`, ảnh game ở `frontend/arena-art/cua-bien-poses.webp`; mã tài khoản là `crab`, tên hiển thị **Cua biển**. Runtime tải WebP khi có Cua biển, phát một lần rồi dừng vòng vẽ RAF. Trận giữ ba giây trước khi chuyển sang kết quả khi Cua biển tung chiêu cuối.

Các tệp nền của game đang được nhiều chat sửa và chưa commit từ trước. [INTEGRATION.patch](INTEGRATION.patch) lưu riêng các thay đổi Cua biển trong `frontend/index.html`, `frontend/learning.js`, `backend/server.py`, `backend/platform_api.py` và `scripts/build-pages.cjs`; các thay đổi này đã được áp dụng trong checkout local. Bản vá chỉ chứa thay đổi của Cua biển. Nếu mã nền đã có hook Cua biển thì không áp dụng lần nữa. Phạm vi commit riêng gồm tài sản, runtime và bản vá; giữ các thay đổi đang dở của chat khác.

## Kiểm tra

Bản vá dùng định dạng không có dòng ngữ cảnh; khi kiểm hoặc áp dụng bằng Git, thêm `--unidiff-zero`. Đã kiểm trên checkout hiện tại bằng `git apply --unidiff-zero --reverse --check INTEGRATION.patch` (chạy từ gốc dự án với đường dẫn đầy đủ đến bản vá).

Đã kiểm tra:

- Alpha và vùng cắt của 16 ô trên nền kem và xanh đậm. Sheet v2 đủ chi, không cắt hình, khoảng trống giữa hình và mép ô ít nhất 22 px.
- Demo với bốn chế độ trên năm kích thước màn hình: điện thoại, máy tính bảng dọc/ngang và máy tính. Điều khiển có kích thước tối thiểu 44 px; tua, tốc độ, reduced motion và phát một lần hoạt động; không tràn ngang hoặc lỗi JavaScript.
- GIF/MP4 được kiểm độc lập về thời lượng, số khung và khả năng giải mã.
- Chín ca runtime game: tải khi cần, chịu đòn, tấn công, chiêu cuối, buồn, dọn tài nguyên, hướng hai phía và reduced motion.
- Bộ kiểm thử Python: **75 bài đạt trên Windows, 77 bài đạt trong Docker**.
- Giao diện qua HTTP từ container QA ở cổng **8798**: đủ luồng chơi; thời gian từ chiêu cuối đến màn kết quả đo được **3,558 giây**.
- Cơ sở dữ liệu thật trước và sau đợt kiểm tra: số bản ghi ở các bảng cốt lõi không đổi.

Hồi quy xoay màn hình/ngắt chiêu đã đạt: dọn hiệu ứng chịu đòn, overlay, trạng thái ẩn và lịch vẽ; kiểm cả hai hướng, reduced motion và destroy. Tên chiêu được đặt phía trên sân để không bị nhân vật che.

Báo cáo exporter ở `qa/`; báo cáo giao diện, nguồn và Docker local ở `work/mascot-animation/cua-bien/v1/`.

Chưa đo FPS/CPU trên điện thoại thật hoặc Core Web Vitals. Game dùng hiệu ứng âm thanh hiện có; bộ Cua biển chưa có âm thanh riêng. Trạng thái artwork là `pending_review`, đang chờ người dùng duyệt. Chưa push hoặc phát hành công khai.
