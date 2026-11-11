# Bàn giao Cú mèo / v1

Cập nhật 11/11/2026, Asia/Saigon. Workspace `F:\ChatGPT Math Project`, nhánh `main`. Owner tạo: `cu-meo-01a1cb4c`.

## Kết quả và phạm vi người dùng xác nhận

Đã tạo **Ánh Mắt Đêm Trăng**, **tấn công**, **chịu đòn**, **buồn khi thua**, tích hợp game và triển khai Docker localhost theo yêu cầu mới. Người dùng chọn **commit riêng Cú mèo kèm bản vá tích hợp**; mã nền/shared và thay đổi của chat khác được giữ ngoài commit riêng. Không push, chạy CI hoặc phát hành công khai từ chat này. Job exporter giữ `pending_review`, không tự đánh dấu người dùng đã duyệt tạo hình.

Mở `demo.html` để xem bốn hoạt cảnh; bản game tại http://localhost:8765/dau-tri/ sau khi chọn Cú mèo trong Linh vật. Runtime riêng: `frontend/owl-animation.js`, `frontend/arena-art/owl/poses.webp`, `poses.json`. Bản vá hook sáu tệp và cách áp/kiểm ở `integration/README.md`.

## Nguồn và nhận diện

Built-in image_gen dùng ảnh thật `bo-nhan-vat-demo-2026-11-11/02-thu-va-canh.png`, Cú mèo hàng 2 cột 2, cùng ảnh Cáo Nâu/Mầm Sách tham chiếu vật liệu. Prompt cuối và tham chiếu tại `source/PROMPTS.json`, `prompt.txt`. PNG alpha nguồn giữ nguyên ở `source/poses.png`.

WebP alpha 1.254×1.254,16 pose,314.304 byte; crop bounds từ prepare. Mắt nâu, hai đĩa mặt kem, má cam, thân nâu vàng, hai cánh/hai chân; không thêm tay hoặc mõm mèo. Đã xem hình trên nền sáng/tối.

Chiêu cuối đúng ba nhịp: đêm/mắt khóa mục tiêu → bay và khép bóng cánh thành vầng trăng → sao/đáp/ăn mừng. Tên0,65s trước bay0,95s, impact1,75s, thắng1,90–3,00s. GIF8.424.325byte và MP4H.2642.282.067byte đúng90frame/3,000s chỉ để xem; game dùng Canvas+WebP, không tải chúng. Chưa thêm âm thanh mới.

## Kiểm tra và sửa lỗi

- Exporter/ảnh alpha/WebP/MP4 decode/timeline: `qa/qa-report.json`,contact sheet đã mở xem.
- Demo bốn mode,5viewport390×844/844×390/768×1024/1024×768/1440×900,controls>=44px,replay/pause/seek/0,5×/play-once/reduced motion: `qa/demo-checks.json`.
- Game: chọn/lưu/reload,bot và trận2người,cảhai phía,win/lose,lazy load,visibility/navigation cleanup,5viewport;0JSerror/0networkwarning. Bản sạch `qa/qa-game-summary.json`; rawreport/ảnh/DB thử giữ trong `work/mascot-animation/cu-meo/v1/`.
- Đã chặn elapsed/index âm khi replay nhanh; giữ đủ thời gian finale cho Cú mèo ở cả hai phía. Khi polling nhảy câu, giữ HP hiển thị cũ qua refresh riêng trận có Cú mèo để không bỏ animation trên DOM mới. Ca Mầm Sách→Cú mèo với polling giữ từ40HP đến0: lose ở1,7529s, rời sân3,1947s sauHP0,khôngJSerror.
- Windows74tests và Docker77tests đạt. Docker thử riêng không mount DB thật, `/work` là tmpfs. Các lỗi vòng kiểm trước do sandbox,fixtureLinux và teststaff được sửa đồng thời đã có vòng chạy lại đạt.
- JS syntax,bản dựng/SEO Cloudflare+GitHub8trang đạt. HTTP localhost healthy,asset runtime khớp nguồn,đề mẫu10/10; nguồnPNG/.git/docs404. `qa/release-checks.json` ghi kết quả; rawlog ởwork.

## Git và tiếp tục

Commit riêng lấy tài sản/demo/runtime/test Cú mèo và `integration.patch`; các hook đang áp trong working tree chung để chạy local. Nhiều mô-đun game nền còn ngoài Git từ trước task, nên commit riêng không phải toàn bộ ứng dụng độc lập. Giữ đúng thư mục chính, không khôi phục shared từ snapshot cũ. Nếu patch lệch do thay đổi song song, kiểm helper/README và chỉ tách lại thay đổi Cú mèo.

Không còn lỗi Cú mèo đang mở theo các ca đã kiểm. Chưa đo FPS/CPU trên điện thoại thật hoặc mạng chậm; chưa có phê duyệt hình ảnh toàn bộ linh vật. Bước tiếp: người dùng xem demo và thử trong game; sửa tạo hình/choreography khi có phản hồi, không tự push/phát hành. Job được release sau khi hoàn tất ghi tệp để chat sau có thể claim theo workshop.
