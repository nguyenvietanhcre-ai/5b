# Tích hợp Cáo Nâu cục bộ

Người dùng đã yêu cầu riêng trong chat Cáo Nâu ngày 11/11/2026: tạo chiêu cuối, tấn công, chịu đòn, buồn khi thua; tích hợp game, commit và triển khai local. Đây là phạm vi mới thay hướng demo-only trong workshop. Không có yêu cầu push hoặc phát hành website công khai.

## Tệp chạy

- `frontend/fox-animation.js`, `frontend/fox-animation.css`.
- `frontend/arena-art/cao-nau/poses.webp`: 16 tư thế chiêu cuối, bốn hàng lấy đà/di chuyển/quét đuôi/ăn mừng.
- `frontend/arena-art/cao-nau/reactions.webp`: bốn hàng tấn công/chịu đòn/thua/thắng.
- `frontend/arena-art/cao-nau/frames.json`: giới hạn pixel từng tư thế, hai mục `ultimate.frames` và `reactions.frames`, mỗi mục 16 phần tử `{left,top,width,height}`.

Runtime tự gắn Canvas khi có `.battle-pet.fox`. Chỉ tải hai WebP và JSON khi Cáo Nâu xuất hiện trong trận hoặc kết quả. Tấn công/chịu đòn/thua/thắng phát hữu hạn, idle không giữ vòng vẽ. Chiêu cuối dài ba giây, tên xuất hiện ở 0,65 giây, tác động ở 1,75 giây. Reduced motion giữ tư thế tĩnh. Dừng lịch vẽ khi ẩn tab, rời trang hoặc tháo DOM. Không đổi luật, HP, thời hạn câu hỏi, kết quả, database hay XP.

## Các móc chung

`integration.patch` chỉ lưu phần Cáo Nâu thêm vào bốn tệp dùng chung: index nạp JS/CSS, server cho phép đúng ba asset và hai module, builder sao chép module, learning dùng hoạt cảnh riêng khi Cáo là nguồn đánh. Kết thúc đòn thường trả đối thủ về idle; đòn cuối giữ pose thua và chờ hoạt cảnh kết thúc trước màn kết quả.

Các móc đã có trong working tree local. Không áp patch lần hai vào cây hiện tại. Kho trước phiên có nhiều sửa đổi và game chưa được theo dõi Git; vì vậy commit riêng Cáo Nâu có thể mang patch này để tránh gom cả phần việc của chat khác. Khi ghép vào cây khác đã có game hiện tại, kiểm trước bằng `git apply --check` rồi mới `git apply`. Nếu game đã thay đổi, ghép các hunk tương ứng và giữ nguyên tích hợp nhân vật khác. Bản patch yêu cầu nền Góc học tập/Đấu trí hiện hành; không tự chứa toàn bộ ứng dụng từ commit cũ.

## Kiểm tra

`node work/fox-integration-smoke.cjs` chạy Chrome headless với toàn bộ request thử được Playwright đáp từ tệp dự án, không cần truy cập mạng; báo cáo/ảnh ở `work/fox-integration/`. Cần runtime Playwright/Chrome đi kèm môi trường dự án. Kiểm tra này xác minh runtime và bố cục; HTTP/allowlist thật được kiểm riêng khi triển khai local. Xem HANDOFF và bộ nhớ phiên để biết kết quả thực tế, không suy ra đạt từ việc chỉ có script.
