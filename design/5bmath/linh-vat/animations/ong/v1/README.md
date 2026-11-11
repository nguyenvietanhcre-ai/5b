# Ong — Lục Giác Hoàng Kim

Ngày 11/11/2026 (Asia/Saigon). Người dùng yêu cầu chiêu cuối, tấn công, chịu đòn, buồn khi thua; đồng thời cho phép tích hợp game, commit và triển khai local. Phạm vi này thay hạn chế chỉ làm demo của brief gốc đối với riêng Ong. Chưa tự đánh dấu người dùng đã duyệt mỹ thuật.

- [Canvas bốn trạng thái](demo.html), có chọn chế độ, phát lại, tạm dừng, tua và 0,5×.
- [GIF chiêu cuối](exports/demo.gif), [MP4 H.264](exports/demo.mp4).
- GIF [tấn công](exports/attack.gif), [chịu đòn](exports/hit.gif), [buồn khi thua](exports/lose.gif).
- [WebP runtime](assets/poses.webp): 330.526 byte, 1254×1254, alpha thật, 16 tư thế. PNG gốc ở source/poses.png. Prompt và ảnh tham chiếu thật trong source/PROMPTS.json.

Ảnh dùng đúng Ong hàng 1/cột 1 trong 03-bien-va-ong-v3.png, vật liệu Cáo Nâu/Mầm Sách. Một số cánh/chân phía xa bị che bởi góc ba phần tư; không có chi thừa nhìn thấy. Đã kiểm alpha và chất lượng WebP trên nền sáng/tối, không sửa ảnh tham chiếu.

Chiêu cuối: vo ve gọi đàn, các ong nhỏ kết bảy ô tổ lục giác quanh đối thủ, lục giác bung giọt mật và sao. Tên hiện từ 0,65 giây trước đòn 0,95; tác động 1,75; ăn mừng 1,90–3,00. GIF/MP4 chiêu cuối đúng 90 khung/3 giây/30fps; GIF ba trạng thái còn lại giữ hình cuối đủ vòng 3 giây. Tấn công trong game 0,9s, chịu đòn 1,1s, buồn khi thua 2,2s. Giữ luật/sát thương hiện có, chưa thêm âm thanh riêng.

Mã dùng chung trong frontend/arena-bee-animation.js và CSS tương ứng; game chỉ tải WebP, không tải GIF/MP4. Bản game có chọn Ong lưu qua API, hai hướng, animation kết liễu trước trang kết quả, biểu cảm chịu đòn/thua, reduced motion và hủy lịch vẽ khi rời trang/ẩn tab. Mở localhost:8765 → Góc học tập → Linh vật → Chọn Ong → Đấu trí.

QA xuất chuẩn ở qa/qa-report.json và contact-sheet.png; ba trạng thái khác ở qa/other-states.png. Kiểm độc lập năm viewport × bốn chế độ, controls >=44px, play once/seek/pause/0,5×/reduced motion tại work/mascot-animation/ong/v1/independent-qa.json. Kiểm game/API và phát hành local ở work/bee-integration/. Chưa đo FPS trên điện thoại thật.

Kho hiện có mã game nền chưa được Git theo dõi và nhiều chat sửa đồng thời. Commit riêng Ong chứa tài sản, runtime, test và integration.patch (chỉ các hunk Ong + hàng đợi HTTP128). Móc nối đã áp dụng vào checkout local, nhưng các tệp dùng chung frontend/learning.js, frontend/index.html, backend/platform_api.py, backend/server.py và scripts/build-pages.cjs chưa được đưa toàn bộ vào commit này để tránh gom thay đổi khác. Patch dựa trên bản local ngay trước tích hợp, không phải HEAD a8221fa; cần các cập nhật game nền trước khi tái áp dụng ở checkout mới. Không apply lại patch trên checkout này. Chưa push/CI/phát hành Internet.

Giới hạn kiểm thử toàn dự án được ghi trong HANDOFF.md và bản ghi phiên. Không xem các kiểm thử phần Ong là chứng nhận toàn bộ ứng dụng.
