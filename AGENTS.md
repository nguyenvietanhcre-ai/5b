# Mầm Toán — hướng dẫn bắt buộc cho mọi phiên dự án

## Bắt đầu MỖI phiên và khi tiếp tục sau khi rút gọn ngữ cảnh
1. Đọc docs/PROJECT_MEMORY.md, docs/SESSION_LOG.md, docs/chat/README.md và README.md.
2. Đọc bản ghi gần nhất/liên quan trong docs/chat/ khi cần chi tiết.
3. Kiểm tra Git/tệp thực tế. Bộ nhớ cũ không chứng minh máy chủ còn chạy hoặc kiểm thử mới đã đạt.
4. Ưu tiên chỉ đạo mới nhất của người dùng; cập nhật bộ nhớ khi có thay đổi.

## Kết thúc MỖI phiên hoặc trước câu trả lời cuối sau một đợt công việc
Lưu bộ nhớ là điều kiện hoàn thành nhiệm vụ, không chờ người dùng nhắc.
1. Tạo/cập nhật docs/chat/YYYY-MM-DD-mo-ta-phien.md. Tiếp tục cùng chat thì nối vào cùng bản ghi; không ghi đè lịch sử.
2. Lưu yêu cầu, chỉnh sửa, quyết định/phê duyệt, học liệu, lý do ảnh hưởng triển khai, tệp đã đổi, Git/commit/nhánh, kiểm tra thực tế, lỗi/giới hạn, việc còn chờ và bước tiếp theo.
3. Nếu truy xuất được lịch sử, lưu đầy đủ tin nhắn người dùng/trợ lý. Nếu chỉ có ngữ cảnh/tóm tắt, ghi rõ phạm vi; không gọi đó là bản xuất nguyên văn đầy đủ.
4. Không lưu hướng dẫn/suy luận nội bộ, mật khẩu, token hay cookie.
5. Cập nhật docs/PROJECT_MEMORY.md với trạng thái mới nhất, liên kết bản ghi, việc đã xác nhận và giả định; sửa thông tin lỗi thời.
6. Nối mục có ngày Asia/Saigon vào docs/SESSION_LOG.md. Giữ lịch sử cũ; không xóa các mục trước.
7. Cập nhật danh mục docs/chat/README.md. Kể cả công việc còn dở vẫn ghi phần đã làm và tình trạng chờ.
8. Đọc lại để xác minh các tệp đã lưu và nội dung khớp thực tế trước khi báo hoàn tất.
9. Bộ nhớ bền vững nằm trong tệp dự án, không dựa vào lời hứa bộ nhớ toàn cục. Phiên sau cần mở đúng thư mục và đọc hướng dẫn này.

## Chỉ đạo lâu dài
- Mọi mã nguồn, tài liệu, sản phẩm và tệp tạm ở dưới F:\ChatGPT Math Project. Dùng work/ cho tệp tạm.
- Python backend, Git/GitHub quản lý mã nguồn, Docker/Compose đóng gói.
- Giữ giao diện xanh/cam vui nhộn đã duyệt, trừ khi được yêu cầu đổi.
- Thiết kế mọi giao diện cho điện thoại, máy tính bảng và máy tính. Giữ đầy đủ chức năng, dễ đọc, dễ chạm, đẹp và mượt ở màn hình hẹp. Kiểm tra luồng chính ở cả chiều dọc và ngang khi thay đổi giao diện. Bố trí lại điều khiển thay vì ẩn chức năng.
- Nếu phù hợp làm skill: đề xuất rồi CHỜ xác nhận trước khi tạo/cài. Ghi đề xuất và trạng thái trong docs/SKILL_CANDIDATES.md. Đã duyệt `mam-toan-release` tại `.agents/skills/mam-toan-release/SKILL.md`.
- Phân biệt commit local, push GitHub, kiểm thử CI và triển khai website.
- Không khẳng định Docker/CI đã đạt nếu chưa chạy; không bịa tuyển sinh, video, lịch học hoặc bảo vệ tài khoản.
- Bản ghi chi tiết docs/chat/*.md và *.json chỉ lưu cục bộ, loại khỏi Git (trừ README danh mục). Chỉ công khai/đẩy các bản ghi đó khi người dùng yêu cầu rõ. Không tự push chỉ vì vừa lưu bộ nhớ.

## Phát triển
- Chạy: python -m backend --host 127.0.0.1 --port 8765
- Kiểm thử: python -m unittest discover -s tests -v
- Cú pháp JS: node --check frontend/app.js
- Docker (mặc định): docker compose up --build --wait --wait-timeout 120; hoặc START-DEMO.cmd / START-DOCKER.cmd.
- Dừng Docker: STOP-DOCKER.cmd. Python trực tiếp: START-PYTHON.cmd. Kiểm tra Docker Desktop và cổng trước khi khởi chạy.
- Chỉ phục vụ danh sách frontend, không công khai .git hoặc tài liệu nội bộ.
- Tài khoản/nộp bài/lớp học hiện là demo. Đăng nhập thật, cơ sở dữ liệu, giáo viên là việc tiếp theo.
