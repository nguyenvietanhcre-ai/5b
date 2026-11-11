# Bản vá tích hợp Cú mèo

Theo lựa chọn của người dùng trong chat ngày 11/11/2026, commit cục bộ chỉ lấy tài sản/mã runtime Cú mèo và bản vá này. Các tệp game dùng chung đang có thay đổi của nhiều chat được giữ nguyên trong working tree và không stage toàn bộ vào commit Cú mèo.

`integration.patch` mô tả riêng thay đổi Cú mèo trên sáu tệp đang dùng:

- `frontend/learning.js`: tên/id `cu-meo`, lựa chọn và lưu linh vật, dispatch hiệu ứng, mount/unmount, giữ view đủ ba giây khi Cú mèo là bên đánh hoặc bên nhận đòn cuối. Riêng trận có Cú mèo, nếu polling nhận chỉ số câu mới cùng HP đã giảm thì giữ chênh lệch HP qua lần dựng lại giao diện và phát hiệu ứng trên phần tử mới; tránh bỏ mất hoạt cảnh đòn cuối khi chưa kịp nhận đầu câu.
- `frontend/learning.css`: avatar WebP và lớp Canvas/hiệu ứng riêng.
- `backend/platform_api.py`: thêm Cú mèo vào danh mục dùng chung cho seed, xác nhận chọn linh vật và mã trả về.
- `backend/server.py`: phục vụ `owl-animation.js`, `arena-art/owl/poses.webp` và `poses.json` trong danh sách cho phép.
- `frontend/index.html`: nạp runtime Cú mèo.
- `scripts/build-pages.cjs`: sao chép runtime vào bản dựng tĩnh; thư mục arena-art đã được quy trình có sẵn sao chép.

Patch được tạo bằng cách đọc tệp mới nhất rồi bỏ đúng các dòng/block Cú mèo để dựng bản trước. Không dùng Git diff toàn thư mục, không đưa các thay đổi nhân vật khác vào các dòng thêm/bớt. Ngữ cảnh xung quanh có thể nhắc đến các nhân vật do chat khác đang làm.

## Kiểm tra và áp dụng

Chạy từ thư mục gốc dự án:

```powershell
git apply --unidiff-zero --reverse --check design/5bmath/linh-vat/animations/cu-meo/v1/integration/integration.patch
```

Lệnh trên kiểm tra rằng tất cả hunk đã có trong working tree hiện tại; không thay đổi tệp. Patch dùng context 0 để tránh các dòng xung quanh đang được chat khác sửa; vì vậy cần cờ `--unidiff-zero`. Kết quả lúc đóng gói lưu ở `verification.json`.

Khi chuyển sang bản nền tương thích chưa có Cú mèo, kiểm trước rồi mới áp dụng:

```powershell
git apply --unidiff-zero --check design/5bmath/linh-vat/animations/cu-meo/v1/integration/integration.patch
git apply --unidiff-zero design/5bmath/linh-vat/animations/cu-meo/v1/integration/integration.patch
```

`apply-owl-integration.cjs` là công cụ khôi phục riêng các hook `frontend/learning.js` khi có chỉnh sửa song song. Chạy nó từ gốc dự án. Công cụ chỉ thêm hook còn thiếu trên nội dung mới nhất; không khôi phục tệp từ bản sao cũ. Nó không thay cho việc áp/kiểm đủ sáu tệp trong `integration.patch`.

## Điều kiện của commit theo phạm vi đã chọn

Runtime `frontend/owl-animation.js` và hai tệp `frontend/arena-art/owl/poses.webp`, `poses.json` là các tệp Cú mèo riêng cần giữ cùng bộ nguồn/demo. Patch này cần bản game hiện có và các mô-đun nền mà nó tích hợp vào. Nhiều mô-đun nền đã nằm ngoài Git từ trước tác vụ này; commit riêng Cú mèo không bao gồm toàn bộ ứng dụng hiện đang chạy. Không coi một checkout chỉ có commit Cú mèo là bản phát hành hoàn chỉnh của các thay đổi game đang chờ ở working tree.

HP, sát thương, chấm đáp án, tính điểm và thời hạn trận giữ theo game/server hiện có. Giữ màn hình thêm tối đa phần còn lại của hoạt cảnh chỉ là trình diễn. Runtime dùng Canvas và WebP; không tải GIF/MP4 để chơi game. Chế độ giảm chuyển động dùng tư thế tĩnh; khi ẩn tab hoặc rời trang, runtime dọn timer/RAF/overlay và giữ tư thế kết thúc.
