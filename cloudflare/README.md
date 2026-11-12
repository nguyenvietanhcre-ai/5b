# Python API trên Cloudflare

GitHub/Pages phục vụ trang tĩnh. Pages chuyển các API cùng origin sang service
binding `BACKEND`; Worker `5bmath-api` dùng SQLite Durable Object cho một đơn vị
trường/lớp cần chung giao dịch tài khoản, giới thiệu, thanh toán và học phí.
Preview dùng Worker/namespace riêng `5bmath-api-preview`.

## Đóng gói và kiểm thử

Cần Python từ 3.12, Node24 và Wrangler4.160.1 từ package-lock của dự án.
Runtime Cloudflare do compatibility date chọn; bản thử thực tế dùng Python3.14.2.

```sh
npm ci
python -m pip install workers-runtime-sdk==1.9.6
python cloudflare/build_worker.py --vendor-sdk
python -m unittest discover -s cloudflare -p test_storage.py -v
python cloudflare/test_runtime.py --port 8895
```

`build_worker.py` chỉ sao chép danh sách mã backend, migration, hai JSON công khai
và SVG ví dụ cần thiết vào `cloudflare/runtime/`. Thư mục `work`, SQLite, mật khẩu,
các tệp `.env` và tệp kiểm thử không nằm trong bundle. SDK được ghim trong
`pyproject.toml`; có thể quản lý môi trường bằng uv, nhưng không cần một framework
web hay SQLite WASM riêng.

Kiểm tra gói preview trước khi phát hành:

```sh
node node_modules/wrangler/bin/wrangler.js deploy --config cloudflare/wrangler.jsonc --env preview --dry-run
```

Lệnh phát hành tương ứng là lệnh trên bỏ `--dry-run`. Production bỏ `--env preview`.
Việc này cần tài khoản Cloudflare đã xác thực; dry-run không chứng minh namespace
remote hay giao dịch thật hoạt động.

## Nhập dữ liệu và sao lưu

Đặt `OPERATOR_TOKEN` qua secret Wrangler. Không đưa giá trị vào Git hoặc chat.
`TRANSFER_ENABLED=true` là trạng thái khởi tạo: API học sinh trả503 khi DB trống,
`/api/health` trả `ready:false` và không tạo bảng trước khi nhập.

Các endpoint `/__ops/import` (POST), `/__ops/export` (GET) và `/__ops/status` (GET)
yêu cầu `Authorization: Bearer ...`. Import còn yêu cầu `TRANSFER_ENABLED=true`
và một DB hoàn toàn trống; không ghi đè DB đã có bảng. Sau nhập và nghiệm thu,
đặt cờ này thành `false`: import đóng, sao lưu/status vẫn yêu cầu token.

Dùng `scripts/cloudflare-data.py` để tạo snapshot SQLite độc lập, kiểm toàn vẹn,
khóa ngoại và fingerprint trước khi gửi. Định dạng chuyển dùng các hàng có tham
số, mã hóa BLOB base64 và số nguyên64bit dưới dạng chuỗi có kiểu; không ghép một
INSERT BLOB dài vượt giới hạn SQL. Import remote kiểm constraint, khóa ngoại,
checksum và số lượng từng bảng trong cùng transaction. API DO không cho chạy
`PRAGMA integrity_check`; lần kiểm này thực hiện trên snapshot/restore SQLite
cục bộ. Bản xuất được công cụ khôi phục vào DB QA mới để kiểm lại mọi giá trị.

Giới hạn một payload chuyển là16MiB. DO hiện cho một BLOB/hàng tối đa8MiB; bài nộp
10MiB được lưu bằng các chunk1MiB trong migration0018. Không hạ kích thước hoặc
cắt dữ liệu âm thầm khi không đáp ứng các giới hạn này.

## Giao dịch và mật khẩu

`StorageDatabase.run` chạy preflight trước khi mở giao dịch ghi, rồi chạy phần
đồng bộ trong `transactionSync`. Hash/verify mật khẩu và giới hạn đăng nhập dùng
cache ContextVar chỉ trong request để không lặp PBKDF hoặc tính hai lượt qua
replay. Pyodide không có `hashlib.pbkdf2_hmac`; Cloudflare thật giới hạn Web Crypto ở 100.000 vòng, trong khi workerd cục bộ không áp cùng giới hạn. SHA256 trên 100.000 vòng dùng PyCryptodome 3.23.0 native WASM đã ghim và kiểm SHA256 tại `vendor/`; giữ nguyên 600.000 vòng, salt và định dạng hash cũ. `build_worker.py` đóng gói thư viện, không tải lúc chạy. Mất thư viện native trên Worker sẽ báo lỗi thay vì âm thầm chạy vòng lặp Python. Đường Web Crypto còn dùng cho mức không vượt giới hạn. Bridge từ chối suspend khi đang ghi SQL. CPython/Docker tiếp tục dùng OpenSSL có sẵn.

Commit độc lập của kết quả Arena được giữ trước khi xét lượt vào phòng tiếp theo.
Trạng thái phòng được lưu từng hàng cùng giao dịch điểm/duel và khôi phục khi DO
được tạo lại; lỗi giao dịch khôi phục snapshot RAM của chính đoạn đồng bộ đó.
`connection.atomic(callback)` giữ rollback lồng nhau cho bài nộp nhiều chunk.

Tham khảo chính thức: [Python](https://developers.cloudflare.com/workers/languages/python/),
[WSGI/run_sync](https://developers.cloudflare.com/workers/languages/python/packages/flask/),
[SQLite API](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/),
[giới hạn DO](https://developers.cloudflare.com/durable-objects/platform/limits/).
