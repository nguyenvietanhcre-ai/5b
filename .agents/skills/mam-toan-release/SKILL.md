---
name: mam-toan-release
description: Kiểm tra bản mới của Mầm Toán, khôi phục localhost trên Windows hoặc chuẩn bị cập nhật GitHub sau khi kiểm thử Python, JavaScript và Docker.
---

# Kiểm tra và chuẩn bị phát hành Mầm Toán

## Xác định phạm vi

- Đọc `AGENTS.md` và các tệp bộ nhớ mà dự án yêu cầu. Làm việc từ kho `F:\ChatGPT Math Project`. Đối chiếu thư mục gốc, nhánh hiện tại, `git status --short --branch` và `origin` (`nguyenvietanhcre-ai/5b`). GitHub Desktop có thể đang mở bản sao khác trong `Documents\GitHub\5b`.
- Kiểm tra trạng thái thì đọc tiến trình, container và HTTP hiện tại. Kiểm thử bản mới thì chạy các bước xác minh bên dưới. Chỉ khởi động hoặc dựng lại bản demo trong phạm vi yêu cầu.

## Xác minh bản mới

1. Kiểm tra Python 3.12+ và chạy `python -m unittest discover -s tests -v`. Kiểm tra JavaScript bằng `node --check frontend/app.js`. Trên Windows, bản Python cài từ Microsoft Store có thể chạy qua alias. Dùng bộ khởi động có sẵn khi cần dò Python.
2. Khi Docker Desktop dùng Linux containers và engine sẵn sàng, chạy `docker compose config --quiet`. Khi cần kiểm tra bản mới qua Docker, dựng từ thư mục dự án bằng `START-DEMO.cmd` hoặc lệnh Compose trong `README.md`. Đối chiếu `docker compose ps` để xác nhận dịch vụ `web`, trạng thái và cổng thực tế.
3. Kiểm tra qua địa chỉ loopback trực tiếp, mặc định `http://127.0.0.1:8765/`. Xác nhận trang chủ, tài nguyên JS/CSS và `/api/health` trả về HTTP 200. Dùng dữ liệu mẫu trong `.github/workflows/ci.yml` để gọi `/api/grade` và xác nhận điểm 10/10. Nếu proxy ảnh hưởng phép thử, dùng HTTP client bỏ proxy cho loopback. Khi cần chạy bộ kiểm thử trong image, dùng lệnh gắn `tests/` chỉ đọc từ `README.md`.

## Khôi phục localhost trên Windows

- Kiểm tra engine và tiến trình đang dùng cổng `8765` trước khi chạy. Nếu container của dự án đang phục vụ đúng bản cần kiểm tra, kiểm tra HTTP trước khi quyết định dựng lại. Nếu cổng do tiến trình khác giữ, giữ tiến trình đó và dùng cổng thử khác theo `README.md` hoặc báo xung đột.
- Ưu tiên `START-DEMO.cmd` khi Docker sẵn sàng. Chạy Python trực tiếp bằng `START-PYTHON.cmd` hoặc `start-demo.ps1 -Port 8766` theo `README.md` khi Docker chưa sẵn sàng hoặc cần cổng riêng. Xác nhận lại trang chủ và API sau khi khởi động. Dừng đúng tiến trình thử tạm khi kết thúc, giữ bản demo mà người dùng muốn tiếp tục sử dụng.

## Chuẩn bị GitHub và bàn giao

- Rà soát diff và `git diff --check`. Tóm tắt những tệp thuộc bản cập nhật và để bản ghi chi tiết trong `docs/chat/` ở máy cục bộ theo `AGENTS.md`. Chuẩn bị nội dung commit, PR hoặc release theo phạm vi yêu cầu. Chỉ push, tạo PR/release trên GitHub hoặc triển khai khi người dùng đã yêu cầu hành động đó.
- Báo rõ kiểm tra đã chạy, kết quả, lỗi còn vướng, URL nếu bản demo đang chạy và trạng thái Git. Phân biệt kiểm thử tại máy với CI, commit với push và push với triển khai. Cập nhật bộ nhớ dự án và bản ghi theo `AGENTS.md`.
