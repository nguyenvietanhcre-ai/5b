# Phạm vi tích hợp và commit Cá heo

Working tree chính đã áp dụng hook và dựng Docker local:

- `frontend/learning.js`: tên/lựa chọn/sanitize/handler, hit/ultimate, giữ kết thúc chiêu, mount/destroy; chặn ghi lặp câu bot khi chờ animation.
- `backend/platform_api.py`: mã dolphin → Cá heo, seed idempotent/lưu lựa chọn thật; không thêm migration.
- `backend/server.py`: allowlist module/CSS và hai WebP riêng.
- `frontend/index.html`, `scripts/build-pages.cjs`: nạp và đóng gói runtime.

Nhiều chat cùng sửa các tệp này. Khi bắt đầu, learning.js/platform_api.py và phần lớn backend còn chưa có trong HEAD. Commit này giữ mã/tài sản/test mới của Cá heo và **bản vá riêng cho baseline app hiện có**, giữ thay đổi các chat khác ngoài commit. Đây không phải snapshot toàn bộ app đang chạy.

integration.patch là diff bỏ riêng phần Cá heo rồi thêm lại; integration-manifest.json lưu SHA-256 trước/sau của năm tệp lúc chụp. Đã kiểm áp dụng ngược trên nguồn và áp dụng xuôi trên preimage riêng trong work/. Khi hợp nhất baseline app về sau, rà/ap dụng patch; không áp dụng lần hai trên nguồn đã có hook.

```powershell
git apply --unidiff-zero --reverse --check design/5bmath/linh-vat/animations/ca-heo/v1/integration.patch
```

Kiểm thử rộng phát hiện test snapshot tìm mã `...-1` khớp cả `...-10`/`...-11` rồi chọn dòng đầu. Đã sửa ba dòng chọn đúng mã, không sửa backend; giữ bản vá ở qa/staff-snapshot-lookup.patch. Targeted và toàn bộ Docker đạt.

Commit dùng danh sách đường dẫn riêng với `git commit --only`, không lấy các đường dẫn chat khác đang stage. Không reset index chung.
