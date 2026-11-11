# Sư tử — Canvas + WebP

Mở `demo.html` để xem bốn hoạt cảnh: **Tiếng Gầm Sư Vương**, tấn công, chịu đòn và buồn khi thua. Ảnh PNG nguồn nằm trong `source/`; Canvas dùng WebP trong `assets/`. Bản GIF/MP4 trong `exports/` dành cho xem và duyệt. Kết quả kiểm tra hình ảnh, tương tác và màn hình nằm trong `qa/`; xem thêm `HANDOFF.md` về trạng thái bàn giao.

Bản demo tự chứa toàn bộ tài nguyên cần chạy trong thư mục `v1/`. Nền `assets/garden.webp` và ảnh đối thủ `assets/opponents.webp` là các bản sao nguyên vẹn từ tài sản chung; SHA-256 đã đối chiếu trong `qa/self-contained-report.json`. Có thể giữ hoặc chuyển riêng thư mục này để xem demo mà không cần thư mục `shared/`. Việc sao chép và đổi đường dẫn được thực hiện sau khi xuất GIF/MP4, với nội dung ảnh giữ nguyên nên hình ảnh trong bản xuất không đổi.

## Patch tích hợp game

`integration.patch` lưu riêng các điểm nối Sư tử trong năm tệp dùng chung:

- `frontend/learning.js`: tên và lựa chọn linh vật, lưu lựa chọn, phát hoạt cảnh, giữ nhịp chiêu cuối và vòng đời Canvas.
- `frontend/index.html`: tải mã và CSS Sư tử.
- `backend/platform_api.py`: ánh xạ mã `lion` với tên Sư tử.
- `backend/server.py`: cho phép phục vụ mã và CSS Sư tử.
- `scripts/build-pages.cjs`: sao chép mã và CSS Sư tử vào bản dựng.

Patch được tạo từ **nền game đang có trong thư mục làm việc**, bao gồm những cập nhật nền tảng và các nhân vật khác chưa commit. Cần có nền game tương ứng trước khi áp dụng patch; commit cũ `a8221fa` riêng lẻ chưa có nền này. Các tệp runtime, tài sản và demo riêng của Sư tử được lưu trực tiếp cùng bản cập nhật, nên patch chỉ chứa các điểm nối trong tệp dùng chung.

Các điểm nối Sư tử đã hiện diện trong thư mục làm việc lúc tạo patch. Có thể kiểm tra điều đó từ gốc dự án mà không sửa tệp:

```powershell
git apply --reverse --check design/5bmath/linh-vat/animations/su-tu/v1/integration.patch
```

Khi chuyển sang nền tương ứng chưa có Sư tử, đọc diff và kiểm tra trước:

```powershell
git apply --check design/5bmath/linh-vat/animations/su-tu/v1/integration.patch
```

Các chat khác có thể tiếp tục sửa cùng tệp, vì vậy patch có thể xung đột và cần được rà lại trước khi áp dụng. Giữ nguyên cập nhật của các nhân vật khác khi xử lý xung đột. Patch không tự commit, push hay triển khai. Việc kiểm tra patch trong phiên này chỉ dùng `--check`, không áp dụng hoặc đảo thay đổi trên các tệp dùng chung.

## Chạy game local riêng

Bản đã kiểm thử chạy tại http://localhost:8768/linh-vat/ — chọn **Sư tử**, rồi vào **Đấu trí → Với máy**. Container `mam-toan-lion-web-1` dùng image `mam-toan:lion-local-01a1cb4a`, tái dùng volume SQLite `mam-toan_demo-db`. Cổng 8765 đang được các chat khác cập nhật.

Khi cần dựng lại từ nền game hiện có trong working tree, chạy từ gốc dự án:

```powershell
powershell -ExecutionPolicy Bypass -File tools/mascot-animation/start-su-tu-local.ps1
```

Script chụp backend/frontend vào một thư mục mới dưới `work/lion-animation/`, tạo Compose riêng và dựng tại 8768; không xóa hay dừng container của project khác. Phải giữ nền ứng dụng hiện tại vì commit riêng Sư tử và patch không chứa toàn bộ nền tảng chưa commit.
