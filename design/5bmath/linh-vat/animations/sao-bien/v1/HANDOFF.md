# Bàn giao Sao biển / v1 — 11/11/2026, Asia/Saigon

- Owner `sao-bien-01a1cb4e`; thư mục `F:\ChatGPT Math Project\design\5bmath\linh-vat\animations\sao-bien\v1`.
- Chỉ đạo mới cho phép tích hợp game, commit và triển khai local riêng Sao biển, thay giới hạn demo trong brief gốc. Mỹ thuật vẫn `pending_review`, approval null.

## Đã làm

- Built-in imagegen dùng đúng ảnh biển hàng2/cột3 và ảnh Cáo Nâu/Mầm Sách thật. Hai PNG alpha/32 tư thế giữ nguyên tại source; prompt/ảnh tham chiếu trong source/PROMPTS.json. Năm cánh đào–san hô bo tròn, chấm kem, mắt nâu, má cam, nỉ/đất sét mềm.
- Bốn chế độ Canvas: Ngũ Tinh Tỏa Sáng, tấn công, chịu đòn, buồn thua. Chiêu cuối đúng5 bản sao → ngôi sao → cột sáng → bung sao/ăn mừng. Tên0,65s trước đòn0,95s, tác động1,75s, thắng1,9s;90frame/30fps/3,000s.
- WebP poses592.544byte +reactions294.666byte =887.210byte; idle game25.950byte. Metadata connected components giữ toàn bộ cánh vượt ô danh nghĩa; không chỉnh PNG/WebP gốc. GIF2.503.744byte/768×432, MP4 H.2641.954.138byte/1280×720, đều90frame/3s; decode MP4 đạt. Runtime không tải GIF/MP4.
- Runtime/CSS và assets riêng `frontend/arena-starfish.*`, `frontend/arena-art/sao-bien-v1/`. Mã lựa chọn starfish lưu DB/phòng đấu; kết quả chờ chiêu cuối. Không sửa luật/sát thương/điểm.
- Hook chung áp dụng trong working tree; bản vá chính xác `integration/shared-hooks.patch`. Commit chỉ mã/tài sản/test/patch Sao biển, không gom nền game/animation chat khác. HEAD nền cũ chưa có trọn game; commit này cần nền game hiện tại để áp dụng patch.

## Kiểm tra

- Exporter đạt alpha/WebP/timeline/tên trước đòn/thắng giữ cuối,90frame/3s,5viewport không lỗi/tràn; đã mở contact sheet/ảnh pose15 nguyên cánh.
- Controls thực đạt replay/pause/resume/seek/0,5×/4mode/playonce;6viewport từ320px dọc-ngang, điều khiển>=44px; reduced không tự phát.
- Browser DB riêng8795: chọn/lưu/reload, bot thật, đáp án đúng→attack, hit/sad sheet riêng, kết liễu→tên/tác động/thắng/kết quả;5viewport không tràn/trùng sprite. Dùng fixture sessionStorage đặt điều kiện kết liễu, không ghi QA vào volume thật.
- Sửa vòng lặp MutationObserver do textContent mỗi frame: guard nhãn +lọc mutation. Regression tên1002ms/đúng2ghi, cuối không còn flight/rAF/timer, không lỗi JS.
- Docker cuối77/77 đạt. Windows77 có1 lỗi test chọn nhầm mã câu từ fuzzy search; sửa exact question_code, riêng7staff đạt lại, không sửa nghiệp vụ staff. Docker đầu3lỗi scratch/work chỉ đọc, mount scratch riêng thì77đạt.
- Cú pháp JS, hai build/SEO Cloudflare/GitHub8trang đạt. Localhost Docker healthy, health200/grade10/10,7assets SHA khớp nguồn, PNG/.git/ảnh sai404. Backup SQLite trước/sau tại work.
- Báo cáo QA bền vững trong qa/; đầy đủ công cụ/log/ảnh ở work/mascot-animation/sao-bien/v1/.

## Giới hạn và tiếp tục

- Chưa đo FPS/CPU/mạng chậm trên điện thoại thật; hidden-document được mô phỏng. Hai phía mount/reaction đã kiểm; chiêu cuối đảo phía chưa có kịch bản độc lập.
- Auto-review từ chối Compose LAN vì yêu cầu hiện tại chỉ local; đã dùng cấu hình localhost-only an toàn tại http://localhost:8765/, giữ volume. Không còn chờ phê duyệt để hoàn thành localhost.
- Xem docs/chat/2026-11-11-animation-sao-bien.md cho bộ nhớ/hash commit. Các bản ghi chi tiết, DB và work giữ cục bộ; chưa push/CI/phát hành website trong chat này.
- Mở /linh-vat/ chọn Sao biển rồi /dau-tri/; demo.html để duyệt riêng. Release job khi kết thúc, chat sau đọc HANDOFF rồi claim owner riêng; không ghi đè nguồn/chat khác.
