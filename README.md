# Mầm Toán — Python / GitHub / Docker

Website demo tiếng Việt cho học sinh lớp 5 theo định hướng Kết nối tri thức và luyện vào lớp 6.
Tất cả tệp dự án đặt tại F:\ChatGPT Math Project.

## Chạy bằng Python
Cần Python 3.12 trở lên. Bản hiện tại không cần cài thư viện ngoài.

    python -m backend --host 127.0.0.1 --port 8765

Mở http://127.0.0.1:8765. Trên Windows có thể chạy START-DEMO.cmd; launcher tự tìm Python cục bộ hoặc Python đi kèm ứng dụng.
Nếu cổng bận: chạy start-demo.ps1 -Port 8766. Dừng bằng Ctrl+C.
Có thể xem giao diện offline bằng frontend/index.html; khi đó việc chấm điểm chạy tại trình duyệt.

## Chạy bằng Docker
Cần Docker Desktop với Linux containers hoặc Docker Engine + Compose.

    docker compose up --build

Mở http://127.0.0.1:8765. Dừng bằng docker compose down.
Image chỉ chứa backend/frontend, chạy với người dùng không phải root. Compose chỉ mở cổng localhost.
Chưa build/run Docker trên máy hiện tại vì chưa tìm thấy Docker.

## Kiểm tra

    python -m unittest discover -s tests -v
    node --check frontend/app.js

Python phục vụ giao diện và chấm bài qua POST /api/grade; GET /api/health báo backend đang chạy.
Chỉ các tệp giao diện trong danh sách cho phép được phục vụ. README, .git và tài liệu nội bộ không công khai.

## GitHub
.github/workflows/ci.yml kiểm thử Python 3.12/3.13, cú pháp JS và build/chạy Docker rồi kiểm tra website/API.
Kho đích đã xác nhận: https://github.com/nguyenvietanhcre-ai/5b (public).
Hiện mới lưu phiên bản Git cục bộ và cấu hình origin; chưa đưa mã lên. Kết nối GitHub bị từ chối quyền ghi (403), Git trên máy chưa đăng nhập. GitHub Actions chưa chạy. Sau khi cấp quyền/đăng nhập, dùng git push -u origin main và xem tab Actions.

## Bộ nhớ cho phiên sau
AGENTS.md hướng dẫn đọc docs/PROJECT_MEMORY.md và docs/SESSION_LOG.md lúc bắt đầu.
Sau mỗi đợt công việc phải cập nhật các quyết định và kiểm tra thực tế.
docs/SKILL_CANDIDATES.md ghi các skill đề xuất; chỉ tạo sau khi người dùng xác nhận.

## Chức năng demo
Trang chủ xanh/cam có linh vật SVG tự thiết kế; bộ lọc bài học; hai bài đọc; bài luyện bốn câu; đề năm câu/15 phút; trò chơi ba vòng; tên và tiến độ lưu trong trình duyệt; tải phiếu TXT; chọn/nộp bài minh họa; kịch bản video và buổi Zoom/Meet.

## Giới hạn
Chưa có đăng nhập thật, phân quyền tài liệu, quản trị giáo viên, cơ sở dữ liệu học sinh, lưu đa thiết bị, video quay hoặc Zoom/Meet thật.
Nộp bài chỉ lưu tên tệp; không gửi tệp đến máy chủ/giáo viên.
Một hồ sơ minh họa trên mỗi trình duyệt; thoát không xóa lịch sử.
Chấm đáp án cuối, chưa chấm từng bước tự luận. Đề tự biên soạn, không phải đề chính thức hoặc đánh giá đầu vào toàn diện.
Chưa gắn số bài/trang sách giáo khoa. Đề Ams cũ chỉ là tư liệu nâng cao.
Phông Be Vietnam Pro tải từ Google Fonts, có phông hệ thống dự phòng.
Không lấy logo, ảnh hoặc mã nguồn Bigtree Land.
Máy chủ Python thư viện chuẩn phục vụ bản demo; trước khi mở dịch vụ thật cần chọn framework/triển khai phù hợp, bổ sung xác thực, lưu dữ liệu và kiểm tra chuyên môn.
