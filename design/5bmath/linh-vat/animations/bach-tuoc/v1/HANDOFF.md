# Bàn giao Bạch tuộc v1

Thư mục: `F:\ChatGPT Math Project\design\5bmath\linh-vat\animations\bach-tuoc\v1`.
Owner tạo job: `bach-tuoc-01a1cb4d-root`. Nhánh bắt đầu: `main/a8221fa`.

## Đã hoàn thành

Nguồn PNG alpha 16 tư thế và WebP 415.190 byte, đúng tám tay/nhận diện lavender/mắt nâu/má cam từ ô Bạch tuộc bảng biển v3, vật liệu Cáo Nâu/Mầm Sách. Prompt đầy đủ trong `source/final-prompt.txt`, vai trò ảnh trong `source/PROMPTS.json`. Không ghi đè nguồn của job khác.

`demo.html`/`animation.js` có bốn mode 3 giây. Chiêu cuối phun mực/ẩn thân/tám tay ảo và tám bóng nước đồng quy/hiện lại thắng. Tên 0,65s, đòn 0,95s, tác động 1,75s, thắng 1,90–3s. Tấn công thường một bóng nước; chịu đòn giật mình rồi phục hồi; thua buồn/có giọt nước mắt/lời động viên. Không có âm thanh riêng.

`exports/demo.gif`/`demo.mp4` đúng 90 frame/3s, MP4 H.264 1280×720 giải mã khung đầu. Ba hoạt cảnh phụ `attack`, `hit`, `lose` có WebP động/GIF 3s. GIF90frame; WebP gộp khung giống nhau giữ đúng thời gian. Runtime Canvas dùng sprite WebP, không tải các bản xuất review.

QA animation độc lập năm kích thước dọc/ngang, bốn mode, controls≥44px, pause/replay/seek/0,5×, reduced motion, ẩn tab, phát một lần đạt; không lỗi JS/tràn ngang. Alpha WebP khớp PNG. Đã mở contact sheet/ảnh mobile và đếm đủ tám đầu tay ở cả16pose. Báo cáo xuất ở `qa/qa-report.json`; QA độc lập tại `work/mascot-animation/bach-tuoc/v1/independent-qa-report.json` và `sprite-qa-independent.json`.

Runtime riêng `frontend/octopus-animation.js/.css` cùng `frontend/arena-art/bach-tuoc-poses.webp`, `bach-tuoc-frames.json`, `bach-tuoc-idle.webp`. Hook chọn/lưu linh vật và phản ứng trong game; giữ nguyên luật/sát thương. Hai backend test Bạch tuộc đạt lưu phiên/ranking/identity server/reseed/giá trị xấu. Rà code đã sửa cắt tay khi tấn công, clipping hiệu ứng ở mục tiêu sát mép và observer tự remount sau destroy; QA mép Canvas không có pixel bị cắt và teardown dừng hết.

## Cách khôi phục phần tích hợp

Baseline Góc học tập/backend hiện tại có nhiều thay đổi cục bộ từ các chat khác, một số tệp còn untracked trước phiên. Không gom toàn bộ chúng vào commit Bạch tuộc. Bundle/asset/installer riêng có thể commit độc lập; các hook trong `frontend/learning.js`, `frontend/index.html`, `backend/server.py`, `backend/platform_api.py`, `scripts/build-pages.cjs` nằm trong working tree hỗn hợp.

Trong checkout có sẵn baseline đó, chạy:

```powershell
node tools/mascot-animation/integrate-bach-tuoc.cjs --check
node tools/mascot-animation/integrate-bach-tuoc.cjs
```

Installer chỉ thêm Bạch tuộc và bảo toàn các lựa chọn khác. Không thể dùng commit addon một mình để thay thế toàn bộ ứng dụng trên `a8221fa`; cần giữ các tệp baseline cục bộ đang có. Không reset/clean chúng. Lưu bộ nhớ không có nghĩa là push.

## Kiểm thử và bản local

Node cú pháp và build/check SEO tám trang công khai đạt. Full Windows suite72test lúc đầu chưa đạt: HTTP loopback bị sandbox chặn WinError10013 (8error), một staff test trạng thái question version kỳ vọng retired nhưng published. Chạy lại nhóm HTTP/chấm bài với quyền loopback đạt13/13; nhóm staff riêng đạt7/7, không sửa mã staff. Hai test Bạch tuộc riêng đạt. Không gọi lượt full72 đầu là pass hoặc coi đó là bằng chứng Docker/CI đạt.

Python local **http://127.0.0.1:8767/** đã trả health200, tiến trình nền ẩn PID12044, DB `work/mascot-animation/bach-tuoc/v1/local-qa.sqlite3`, PID/log cùng thư mục. Bản thử dùng dữ liệu riêng, không tự dùng tài khoản/DB Docker8765. Cổng QA8786 và các tiến trình thử cũ đã dừng đúng phiên; giữ8767 để người dùng xem. Mở lại khi cổng trống:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/mascot-animation/start-bach-tuoc-local.ps1
```

Browser thực tế8767 đã quan sát chọn/lưu Bạch tuộc và đọc lại, tấn công/chịu đòn/chiêu cuối, màn thắng/thua, năm viewport không tràn, giảm chuyển động và rời trận dọn canvas. Đã mở ảnh `game-loss-result.png`, mặt buồn và giọt nước mắt hiện đúng. Không JSerror, tài sản riêng trả200. Một assert lấy mẫu8bóng muộn sau screenshot bị hết hoạt cảnh và một lượt harness mới chờ khởi tạo profile sau reload quá hạn; giữ kết quả cũ trong work, không coi đó là pass trọn bộ.

**Probe tập trung cuối đạt:** đọc lại DB xác nhận octopus sau refresh; ghi mốc RAF tên0,655s, đúng8bóng0,955s, tác động1,755s, hiện lại1,905s; kết quả thắng có Canvas sẵn sàng; reduced motion pose13/không RAF; rời trận pets[]/flights0. Cả năm tài nguyên riêng HTTP200 và SHA256 khớp nguồn; JSerror0. Báo cáo `qa/game-qa-focused-report.json` (bản gốc `work/mascot-animation/bach-tuoc/v1/game-qa-focused-report.json`). Không sửa runtime để xử lý lỗi lấy mẫu của harness.

Docker engine truy cập mặc định bị chặn; hai bước duyệt quyền tự động hết thời gian, chưa cập nhật container8765. Commit chỉ gói Bạch tuộc cùng installer/launcher và tài sản phụ thuộc; không đưa toàn bộ baseline đang sửa vào commit. Tra hash thực tế trong Git và bộ nhớ dự án. Không push, không CI hoặc website Internet. Chưa đo FPS/CPU trên điện thoại thật, chưa có phê duyệt thẩm mỹ từ người dùng.
