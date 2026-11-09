# Mầm Toán — Python / GitHub / Docker

Website demo tiếng Việt cho học sinh lớp 5 theo định hướng Kết nối tri thức và luyện vào lớp 6.
Tất cả tệp dự án đặt tại F:\ChatGPT Math Project.

## Chạy bằng Python
Cần Python 3.12 trở lên. Bản hiện tại không cần cài thư viện ngoài.

    python -m backend --host 127.0.0.1 --port 8765

Mở http://127.0.0.1:8765. Trên Windows có thể chạy START-PYTHON.cmd. Launcher kiểm tra Python 3.12 trở lên trong môi trường ảo, runtime Codex hoặc PATH, kể cả Python cài từ Microsoft Store. Đã chạy thử với Python 3.13.14 trên Windows ngày 08/11/2026.
Nếu Docker đang dùng cổng 8765, dừng Docker bằng STOP-DOCKER.cmd trước khi chạy START-PYTHON.cmd, hoặc chạy PowerShell với lệnh dưới đây để dùng cổng riêng. Dừng Python bằng Ctrl+C.

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start-demo.ps1 -Port 8766
Có thể xem giao diện offline bằng frontend/index.html; khi đó việc chấm điểm chạy tại trình duyệt.

## Chạy bằng Docker (mặc định trên máy này)
Docker Desktop cần đang mở và Linux containers đang chạy.
Ngày 08/11/2026 đã dựng lại và kiểm tra bản demo sau khi cài lại Windows 11 Pro. Máy dùng Docker Engine 29.9.2 và Compose v5.6.1.

- Nhấp đôi **START-DEMO.cmd** hoặc **START-DOCKER.cmd** để build/cập nhật image và chạy nền.
- Mở **http://localhost:8765/**.
- Nhấp đôi **STOP-DOCKER.cmd** để dừng website. Docker Desktop vẫn hoạt động.
- Docker Desktop hiển thị nhóm **mam-toan**, dịch vụ **web**.
- Đóng cửa sổ chạy không dừng container.

Lệnh tương đương:

    docker compose up --build --wait --wait-timeout 120
    docker compose ps
    docker compose logs --tail 100 web
    docker compose stop web

PowerShell hỗ trợ đổi cổng hoặc xem trạng thái:

    .\docker-demo.ps1 -Port 8767
    .\docker-demo.ps1 -Action Status
    .\docker-demo.ps1 -Action Logs

Lệnh dừng bằng script:

    .\docker-demo.ps1 -Action Stop

Mặc định map 127.0.0.1:8765 vào cổng 8000 trong container. Có thể dùng biến MAM_TOAN_PORT khi chạy Compose trực tiếp.
Nếu cổng bị chiếm bởi bản Python, dừng đúng máy chủ Python hoặc chọn cổng khác. Script không tự dừng tiến trình lạ.
Image chạy với UID 65532, filesystem chỉ đọc, chỉ chứa backend/frontend; nhật ký container được giới hạn dung lượng.
Khi sửa mã nguồn, chạy START-DOCKER.cmd lại để build/cập nhật. Docker không tự đồng bộ sửa mã vào container.
Dữ liệu học sinh vẫn ở trình duyệt theo thiết kế demo; Docker chưa bổ sung cơ sở dữ liệu, đăng nhập thật hay nơi lưu bài nộp.

Kiểm thử trong đúng image (chạy tại thư mục gốc dự án trên Windows):

    docker compose run --rm --no-deps -T --volume "F:\ChatGPT Math Project\tests:/tests:ro" web python -m unittest discover -s /tests -v

Ngày 08/11/2026, container healthy, trang chủ/JS/CSS/health trả về HTTP 200, đề mẫu đạt 10/10 và 10 kiểm thử Python đều đạt trong image lẫn trên Windows. Kiểm tra cú pháp JavaScript cũng đạt.
Nguồn cách dùng Compose: https://docs.docker.com/reference/cli/docker/compose/up/

## Kiểm tra

    python -m unittest discover -s tests -v
    node --check frontend/app.js

Python phục vụ giao diện và chấm bài qua POST /api/grade; GET /api/health báo backend đang chạy.
Chỉ các tệp giao diện trong danh sách cho phép được phục vụ. README, .git và tài liệu nội bộ không công khai.

## GitHub
.github/workflows/pages.yml dựng bản thử công khai trên GitHub Pages từ ba tệp giao diện trong frontend/. Bản Pages chấm bài bằng JavaScript và lưu hồ sơ mẫu trong trình duyệt. Khi chạy bằng Python hoặc Docker, giao diện dùng API Python.
.github/workflows/ci.yml kiểm thử Python 3.12/3.13, cú pháp JS và build/chạy Docker rồi kiểm tra website/API.
Kho đích đã xác nhận: https://github.com/nguyenvietanhcre-ai/5b (public).
Đã đẩy source code lên nhánh main qua Git trên máy sau khi đăng nhập GitHub. Phiên bản source e3949a6 đã vượt qua kiểm thử Python/JS và Docker trên GitHub Actions: https://github.com/nguyenvietanhcre-ai/5b/actions/runs/42186397763.
Trong GitHub Desktop, mở kho cục bộ ở F:\ChatGPT Math Project. Nếu ứng dụng đang hiển thị bản sao 5b ở Documents\GitHub\5b, dùng File → Add local repository để thêm đúng thư mục trên ổ F. Xem thay đổi, commit các tệp cần thiết, rồi push lên origin khi có yêu cầu.
Ngày 08/11/2026, GitHub Desktop đã mở kho trên ổ F và Git đã kiểm tra kết nối tới origin. Các sửa đổi cho bản chạy thử đang ở máy cục bộ.

## Bộ nhớ cho phiên sau
AGENTS.md bắt buộc mọi phiên đọc docs/PROJECT_MEMORY.md, docs/SESSION_LOG.md và docs/chat/README.md lúc bắt đầu.
Trước khi kết thúc mỗi đợt công việc phải cập nhật bộ nhớ hiện hành, nhật ký và bản ghi phiên tương ứng, không chờ nhắc.
Bản ghi đầy đủ cuộc chat khởi tạo: docs/chat/2026-11-06-initial-project.md và JSON đồng hành, lưu cục bộ trong dự án. Bản ghi chi tiết không tự đưa lên GitHub công khai.
Skill [mam-toan-release](.agents/skills/mam-toan-release/SKILL.md) dùng để kiểm tra bản mới, khôi phục localhost và chuẩn bị cập nhật GitHub. Gọi `$mam-toan-release` trong chat Codex mở tại thư mục dự án. Xem [trạng thái các skill](docs/SKILL_CANDIDATES.md).

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
