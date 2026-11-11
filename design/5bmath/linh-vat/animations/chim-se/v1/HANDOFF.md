# Bàn giao Chim sẻ / v1 — 11/11/2026

- Thư mục chính: `F:\ChatGPT Math Project`. Variant `chim-se/v1`, owner gốc `chim-se-01a1cb4c-root`; release khi hoàn tất để chat khác claim. Không tự giành khóa.
- Đã làm bốn animation Canvas/WebP: Lốc Xoáy Ríu Rít, tấn công vung cánh, chịu đòn, buồn khi thua. Giữ PNG nguồn 16 tư thế và prompt/tham chiếu tại source/. Đã nhìn lại alpha/nén sáng+tối.
- Demo tự chứa ảnh assets/, có chọn chế độ/replay/pause/seek/0,5×. Chiêu cuối 3,000 giây/90 frame30fps; tên0,65 → bay0,95 → tác động1,75 → thắng1,90. Đã sửa banner che mặt trong bản xuất đầu; bản cuối đã xem contact sheet. Không có âm thanh chim riêng.
- `exports/demo.gif`, `demo.mp4`, `poster.png`; `qa/qa-report.json` ghi bytes/hash cuối và giải mã MP4 frame đầu. Trạng thái job **pending_review**, chưa có duyệt mỹ thuật cuối, dù người dùng đã yêu cầu tích hợp game/local.
- Runtime `frontend/arena-sparrow-animation.js/.css`, ảnh `frontend/arena-art/chim-se/`. WebP431.226byte, chân dung21.806byte, JSON1.009byte. Hỗ trợ hai phía, reduced motion, dừng khi kết thúc/ẩn/rời sân/resize. Giữ luật sát thương/kết quả.
- Chọn **Chim sẻ** ở `/linh-vat/`, rồi vào `/dau-tri/`. API lưu mã `sparrow`, phiên mới/phòng/leaderboard/đối thủ giữ đúng. `tests/test_sparrow_animation.py` đạt Windows và Docker riêng.
- Canvas năm viewport dọc/ngang, trạng thái/cancel/hidden/reduced/removal và không tràn/JSerror đạt. E2E18947 dùng API/HTML thật, static đúng nguồn fulfill để tránh backlog: chọn/reload/attack/hit/final/win/lose đạt, kết quả sau3633ms. Main8765 tải HTML/static tự nhiên và API giả lập chỉ đọc: overlay thật có42.074pixelalpha, không lỗi tải/JS, đã nhìn ảnh. Không thêm tài khoản QA vào DB chính.
- FullWindows ngoài sandbox68tests có hai lỗi danh mục Cá heo và một lỗi countdown ngoài phần Chim sẻ; không báo toàn bộ suite xanh. BuildCloudflare/GitHub tám trang và SEO đúng target đạt. Chưa đoFPS/CPU thiết bị thật/slow network.
- Dockerlocalhost8765 healthy; năm tài nguyênChim sẻ200/MIME/SHA256 khớp nguồn. Các chat khác có thể dựng lại container; luôn xác minh lại. Auto-review từ chối compose.lan, đã dùng compose.yaml. MappingLAN có sẵn lại xuất hiện do cập nhật song song; không gọi đây là mởLAN mới. Backup /tmp đầu tiên không lấy được vì container bị thay; không xóa/thay volume.
- Git: chỉ riêng runtime/assets/demo/source/QA/test và patch; không commit toàn bộ nền game đang chưa được track. Đọc `INTEGRATION.md`, `integration.patch`, `integration-baseline.json`. Patch trên nềncục bộ, không áp trực tiếp lênHEAD cũa8221fa. Mãcommit thực tế lưu ởdocs/chat/2026-11-11-animation-chim-se.md vàbộnhớ chính. Khôngpush/CI/phát hành côngkhai.
- Báo cáo/script/ảnh/DBthử ở`work/mascot-animation/chim-se/v1/`; chỉdừngserverQA củađúngchat, giữcontainerlocal. Bộnhớbắtbuộc cậpnhật vàđọclại trước trảlờicuối.

Nếu cần sửa: claimjob sau release, kiểmtratrạngtháithật → chỉnh ownvariant → export `--replace` vớiownerđúng → xemảnh vàkiểm lạitíchhợp. Không tự đặt approved hoặc sửajob nhânvậtkhác.
