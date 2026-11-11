# Bàn giao Sư tử / v1

Cập nhật: 11/11/2026 (Asia/Saigon). Chủ phiên/owner: `su-tu-01a1cb4a`. Thư mục: `F:\ChatGPT Math Project\design\5bmath\linh-vat\animations\su-tu\v1`. Đã release owner sau khi lưu kết quả; chat nhận cần claim trước khi sửa.

## Phạm vi người dùng đã xác nhận

Người dùng yêu cầu tạo **Tiếng Gầm Sư Vương**, tấn công, chịu đòn và buồn khi thua; dùng đúng ảnh tham chiếu và phong cách Cáo Nâu/Mầm Sách; xuất Canvas + WebP trong thư mục riêng. Người dùng **cho phép tích hợp game, commit và triển khai local trong chính chat này**, thay phạm vi mặc định chỉ tạo demo của workshop đối với Sư tử.

Sau khi được giải thích nhiều tệp game/nền tảng còn thay đổi từ các chat khác, người dùng chọn **commit riêng các tệp Sư tử và integration.patch**, giữ các điểm nối đã tích hợp trong tệp dùng chung ở working tree. Không gom những thay đổi khác vào commit Sư tử. Không tự push hoặc phát hành website công khai. Việc cho phép tích hợp không được ghi thành phê duyệt tạo hình: job vẫn `pending_review`, chưa có phê duyệt nghệ thuật của người dùng.

## Đã hoàn thành

- Hai PNG nguồn do imagegen tích hợp tạo từ ảnh tham chiếu thật, tổng **32 tư thế**, alpha thật: `source/poses.png` cho lấy đà/tích năng/gầm/ăn mừng và `source/combat.png` cho tấn công/chịu đòn/buồn/đứng chờ. Giữ Sư tử vàng, bờm caramel tròn, hai tai tròn, bốn chi ngắn và đuôi chùm lông; không dùng lại choreography chạy của Chó.
- Ảnh tham chiếu chính: `design/5bmath/linh-vat/bo-nhan-vat-demo-2026-11-11/02-thu-va-canh.png`, hàng 1 cột 1. Tham chiếu phong cách: `design/5bmath/linh-vat/mam-sach-cao-nau-goc.png` và `STYLE.md`. Prompt và nguồn thực tế: `source/PROMPTS.json`; đầu bài: `BRIEF.md`, `prompt.txt`.
- Canvas độc lập: `demo.html`, `animation.js`, `config.js`, `poses.js`, `combat-poses.js`; có chọn đủ bốn hoạt cảnh, phát lại, dừng, kéo thời gian và tốc độ 0,5×. Chiêu cuối đứng trụ chân, bờm sáng và vòng sóng vàng; vòng cuối thành vương miện, bùng sao và kết thúc tự hào.
- WebP chạy Canvas: `assets/poses.webp` **370.108 byte**, `assets/combat.webp` **393.322 byte**. Bản sao game: `frontend/arena-art/lion-ultimate.webp`, `lion-combat.webp`; ảnh nhỏ `lion-idle.webp` **25.544 byte**. Hai sheet cộng ảnh nhỏ: **788.974 byte**; GIF/MP4 không tải trong runtime game.
- Bản xuất chiêu cuối: `exports/demo.gif` **3.376.950 byte**, `exports/demo.mp4` **2.018.019 byte**, cùng `exports/poster.png`. GIF/MP4 đều **3,000 giây, 30 fps, 90 frame**. Mốc chuẩn: tên 0,65 s, ra đòn 0,95 s, tác động 1,75 s, ăn mừng 1,90–3,00 s.
- Runtime riêng: `frontend/arena-lion.js`, `frontend/arena-lion.css`. Lựa chọn Sư tử được nhận ở server bằng `lion` ↔ `Sư tử`; nhận diện được lưu qua tài khoản, phòng đấu và bảng xếp hạng. Có tấn công/chiêu cuối/chịu đòn/thua/thắng, xử lý reduced motion, ẩn tab và dọn Canvas/timer khi rời trang. Nhịp kết thúc giữ đủ chiêu cuối trước khi chuyển sang trang kết quả. Không sửa sát thương, điểm, luật trả lời hay deadline trận.
- `integration.patch` lưu điểm nối trong **năm tệp dùng chung**: `frontend/learning.js`, `frontend/index.html`, `backend/platform_api.py`, `backend/server.py`, `scripts/build-pages.cjs`. Các điểm nối đã có trong working tree; những cập nhật của chat khác được giữ nguyên. Xem `README.md` tại thư mục này để dùng patch.

## Kiểm tra thực tế

- Export chiêu cuối và kiểm timeline/90 frame/ba giây đạt; đã xem contact sheet và ảnh đại diện. `qa/qa-report.json`, `qa/contact-sheet.png`, `qa/sprite-metadata.json` lưu kết quả và metadata.
- Đủ **bốn hoạt cảnh** đã được kiểm tương tác trên **năm kích thước** 390×844, 844×390, 768×1024, 1024×768, 1440×900; phát lại/dừng/seek/0,5×/reduced motion đạt. Báo cáo: `qa/demo-actions-qa.json`; ảnh từng trạng thái: `qa/ultimate-contact.png`, `attack-contact.png`, `hit-contact.png`, `defeat-contact.png`; ảnh viewport: `qa/demo-*.png`.
- `tests/test_lion_mascot.py`: **2/2 đạt** bằng Python đi kèm Codex. Kiểm DB/lưu lựa chọn/đăng xuất rồi đăng nhập/bảng xếp hạng/phòng đấu/đối thủ, từ chối mã và kiểu dữ liệu sai, seed idempotent, không đổi XP. Dữ liệu thử tách khỏi DB thật dưới `work/lion-animation/`.
- Cuối phiên **77/77 kiểm thử Windows và 77/77 trong image Docker Sư tử đạt**. JS app/learning/content/lion đạt cú pháp; hai bản dựng GitHub/Cloudflare và kiểm SEO tám trang đạt. Báo cáo gốc trong `work/lion-animation/unittest-{windows-verified,docker-final}.log`. Các lượt trước bị sandbox chặn socket, source đang đổi song song hoặc test cần thư mục /work ghi được; đã chạy lại thành công, không sửa test của chat khác.
- QA game thực offline và HTTP với DB thử riêng đều đạt năm viewport, chọn/lưu Sư tử qua reload, đánh giảm 20HP, ngừng rAF khi chờ, chiêu cuối đủ ba giây mới đổi trang, chịu đòn/thua/thắng/reduced motion; không lỗi JS/tài nguyên. Offline đo chuyển kết quả 3.229 ms; HTTP dùng mốc điều hướng thực tế thay phép đo bị ảnh chụp làm trễ. `qa/game-offline-report.json`, `qa/game-live-report.json`.
- Docker riêng **mam-toan-lion-web-1**, image **mam-toan:lion-local-01a1cb4a**, healthy tại **http://localhost:8768/**. Trang chủ/health/Linh vật/Đấu trí trả 200; cả năm tài nguyên Sư tử trên HTTP khớp SHA-256 nguồn. Tệp nội bộ 404. Cổng 8765 đang được các chat khác triển khai nên dùng 8768 để tránh thay lẫn container. Dùng volume SQLite hiện có `mam-toan_demo-db`, không nhập tài khoản thử vào DB chính. Backup tại `work/lion-animation/local-before-lion-verify.sqlite3`, integrity ok/FK0, 27 students/22 companions khi chụp; có hoạt động đồng thời nên không coi số đếm là bất biến sau đó.
- Demo đã tự chứa bốn WebP trong assets; hai ảnh shared được sao chép nguyên byte, không thay shared. `qa/self-contained-report.json` xác nhận hash và bốn hoạt cảnh. GIF/MP4 trước bước sao chép giữ nguyên nội dung vì byte ảnh không đổi.
- Chưa đo FPS/CPU trên điện thoại thật, mạng chậm hoặc Core Web Vitals. Video xuất 30 fps không chứng minh hiệu năng thiết bị thật. Chưa có âm thanh riêng cho bộ animation.

## Git và cách tiếp tục

Nền kiểm tra đầu phiên: nhánh `main`, HEAD `a8221fac7af8ba48b16768366d130c1e7d3403a1`. **Riêng commit nền a8221fa chưa có nền tảng/game hiện nằm trong working tree**; không thể checkout nền này rồi coi patch là toàn bộ ứng dụng. `integration.patch` được tạo trên nền game cục bộ tương ứng, có các cập nhật chưa commit của các chat khác. Commit Sư tử sẽ lưu runtime/tài sản/demo/kiểm thử riêng và patch; mã game dùng chung vẫn cần nền tương ứng. Root sẽ bổ sung hash commit local và trạng thái localhost sau xác minh. Không push/CI/triển khai công khai trong phạm vi hiện tại.

Tiếp tục từ gốc `F:\ChatGPT Math Project`, đọc AGENTS và bốn tệp bộ nhớ, rồi kiểm tra thực tế trước khi dựa vào trạng thái cũ:

```powershell
git status --short --branch
node tools/mascot-animation/cli.cjs status su-tu --variant v1
git apply --reverse --check design/5bmath/linh-vat/animations/su-tu/v1/integration.patch
python -m unittest discover -s tests -p test_lion_mascot.py -v
node --check frontend/arena-lion.js
```

`--reverse --check` chỉ kiểm các điểm nối đang có; **không** chạy đảo patch vào working tree. Khi chuyển sang nền game tương ứng chưa có Sư tử, đọc diff và dùng `git apply --check` trước. Các chat khác còn sửa tệp dùng chung nên có thể cần xử lý xung đột để giữ đúng cả hai phía.

Nếu cần xuất lại chiêu cuối sau khi sửa đúng job này, dùng:

```powershell
node tools/mascot-animation/export.cjs su-tu --owner su-tu-01a1cb4a --variant v1 --replace
```

Không ghi đè PNG nguồn; không sửa catalog, shared hoặc job của chat khác. Bản xuất vẫn chờ người dùng xem. Trước khi chuyển owner, cập nhật HANDOFF và thực hiện release/claim theo workshop; không tự chiếm lease đang hoạt động.
