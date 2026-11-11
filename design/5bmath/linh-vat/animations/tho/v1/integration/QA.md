# Kiểm tra tích hợp Thỏ — 11/11/2026 (Asia/Saigon)

## Đã đạt

- Kiểm thử API `tests.test_platform_api.PlatformTests.test_rabbit_companion_persists_and_reaches_opponent_and_leaderboard`: 1 bài, 3,585 giây, OK. Tạo SQLite thử riêng; chọn Thỏ → đăng nhập lại giữ Thỏ → xếp hạng → phòng công khai → đối thủ nhận đúng `rabbit`; từ chối mã sai và dữ liệu kiểu danh sách. Không dùng database thật.
- Cú pháp `frontend/rabbit-animation.js` và `frontend/learning.js` đạt. Dựng bản Cloudflare và GitHub thành công; checker xác minh tám trang công khai, canonical và 404 của cả hai bản. Kiểm SEO dùng bản dựng trước thay đổi vị trí nhãn; thay đổi cuối chỉ liên quan CSS/Canvas.
- Chrome headless: game tĩnh dùng HTML từ bản dựng, **toàn bộ** JavaScript/CSS/WebP/JSON từ đúng nguồn workspace qua Playwright route. Có các module nhân vật khác, không thay chúng bằng stub. Danh sách phòng lobby trả fixture rỗng; trận với bot chạy logic thật ở trình duyệt.
- Luồng chọn Thỏ → tải lại giữ lựa chọn → bot → năm câu trả lời đúng → chiêu cuối → kết quả thắng. Luồng chịu đòn/thua dùng trận bot riêng được đặt trước ở 20 máu; đồng hồ bot thực sự xử lý đòn cuối, không thay giả kết quả.
- Năm kích thước 390×844, 844×390, 768×1024, 1024×768, 1440×900 không tràn ngang. Bốn kích thước điện thoại/tablet còn được dựng lại trận riêng để xem apex chiêu cuối; đủ bốn đáp án có thể thao tác, cuộn tới điều khiển được, một Canvas cho Thỏ.
- Reduced motion: kết quả thua dùng tư thế cuối tĩnh; ảnh Canvas không đổi giữa hai lần lấy mẫu. Runtime không tải GIF/MP4, chỉ tải WebP và JSON của Thỏ; không lỗi JavaScript hoặc tệp thiếu trong lần kiểm cuối.
- Đã mở xem ảnh thật desktop/điện thoại dọc/ngang sau sửa nhãn lên 12% chiều cao stage: không còn che tai/mặt ở cú nhảy; không cắt tai ở đỉnh nhảy. Giữ nhãn chung của các chiêu khác.

## Lỗi đã tìm và sửa

1. Khung hình đầu của `requestAnimationFrame` có thể mang timestamp sớm hơn thời điểm bắt đầu; thời gian âm sinh chỉ số pose −1 và dừng chiêu. Đã chặn thời gian tại 0, kiểm lại luồng thắng đạt.
2. Cần giữ cảnh cuối khi nhận kết quả PvP. Đã nối thời gian giữ cảnh 3,1 giây hiện có, không đổi kết quả/sát thương.
3. Các renderer đặc biệt có thể trả về sớm trước hook chịu đòn. Đã thêm `notifyVictim` tại bộ điều phối chung và chống khởi động lại action đang phát.
4. Quỹ đạo trước sửa có thể đưa tai ra ngoài stage. Đã giới hạn kích thước, chừa ít nhất 24 đơn vị Canvas trên tư thế cao nhất và căn trăng theo thân.

## Phạm vi và giới hạn

Máy chủ QA 8791 với SQLite `work/rabbit-game-integration/qa.sqlite3` đã thực hiện đăng ký/chọn Thỏ/tải lại giữ lựa chọn; sau đó gặp kết nối cục bộ gián đoạn và lỗi host `WinError 10053`. Bản QA đầy đủ vì vậy dùng cách nạp nguồn cục bộ như mô tả, không gọi đó là kiểm end-to-end Python hoàn chỉnh. Máy chủ QA đã dừng bằng đúng session sau khi xong. Nhật ký lỗi thử và script còn ở `work/rabbit-game-integration/`; không lưu thông tin đăng nhập vào bản giao.

Kết quả chi tiết/screenshot cuối: `../qa/game-focused-report.json` và các ảnh `game-*.png`. Nghiệm thu Docker/localhost hiện hành, hash tệp phục vụ, kết quả review PvP và commit do phiên chính lưu ở HANDOFF/bộ nhớ. Chưa đo FPS/CPU trên điện thoại thật hoặc mạng chậm; video xuất sẵn không chứng minh hiệu năng thiết bị.
