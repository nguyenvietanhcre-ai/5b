# Backend Python trên Cloudflare

## Cấu trúc

Cloudflare Pages phục vụ HTML dựng sẵn, ảnh, CSS và JavaScript. Các API tài khoản, quản trị, chấm bài và webhook được chuyển qua service binding `BACKEND` tới Python Worker. Trình duyệt vẫn gọi cùng tên miền, nên không phải mở CORS hay chuyển cookie qua tên miền khác. [Service bindings của Pages](https://developers.cloudflare.com/pages/functions/bindings/#service-bindings).

| Môi trường | Pages | Worker | Dữ liệu |
|---|---|---|---|
| Chính thức | `5bmath.vn` | `5bmath-api` | Tenant `5bmath-main` |
| Xem trước | Nhánh `review-20261112` | `5bmath-api-preview` | Tenant `5bmath-review`, tách biệt |
| Cục bộ | Python/Docker | Không phụ thuộc Worker | SQLite trong volume riêng |

Mỗi trường/tenant giữ các quan hệ tài khoản, người giới thiệu, học phí và sổ thanh toán trong cùng SQLite Durable Object để cập nhật nguyên tử. Tài nguyên tĩnh không đi qua object. Đây là đơn vị dữ liệu của một trường; khi mở rộng sang trường khác cần tenant riêng. [SQLite trong Durable Objects](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/).

D1 `5bmath-demo` tiếp tục dành cho API dữ liệu mẫu cũ, không phải database tài khoản. Không chạy migration hoặc nhập dữ liệu người dùng vào D1 đó để thay cho quy trình dưới đây.

## Tương thích với Python cục bộ

`backend/platform_api.connect` nhận cả đường dẫn SQLite cục bộ lẫn adapter lưu trữ. Với Durable Object, giao dịch dùng `transactionSync`, không chạy SQL `BEGIN`/`SAVEPOINT`. Runner chuẩn bị phép băm mật khẩu trước khi vào giao dịch, giữ kết quả trong phạm vi một yêu cầu, rồi kiểm lại thông tin tài khoản khi ghi. Các mốc commit nghiệp vụ được giữ khi chạy lại yêu cầu. SHA256 trên 100.000 vòng dùng PBKDF2-HMAC với context SHA256 gốc của runtime vì Web Crypto production giới hạn 100.000 vòng. Giữ nguyên 600.000 vòng, định dạng hash và mật khẩu hiện có. Bộ đối chiếu 52 vector và kiểm độc lập 100 trường hợp đạt; workerd đo khoảng 1,3–1,4 giây cho một phép dẫn xuất 600.000 vòng.

Trạng thái từng phòng Đấu trí được lưu cùng giao dịch với dữ liệu kết quả, khôi phục sau khi object được tạo lại. Tệp Zoom vẫn tối đa 10 MB, lưu thành các hàng không quá 1 MB. Tệp inline cũ tiếp tục đọc được.

`cloudflare/build_worker.py` chỉ sao chép mã và tài nguyên cần thiết vào `cloudflare/runtime/`; không quét `work/`, `.env`, sách nguồn hoặc bản sao database. Thư mục dựng và cache không đưa lên Git. Python/Docker vẫn hoạt động độc lập.

## Kiểm thử và phát hành

Cần Node 24 và Python 3.12 trở lên. Dependency Node nằm trong `package-lock.json`; SDK Python được ghim `workers-runtime-sdk==1.9.6` trong `cloudflare/pyproject.toml`. Dùng trực tiếp Wrangler đã cài trong dự án; không cần uv cho bộ dependency hiện tại. [Python Workers](https://developers.cloudflare.com/workers/languages/python/).

```text
npm ci --ignore-scripts --no-audit --no-fund
python -m pip install workers-runtime-sdk==1.9.6
python cloudflare/build_worker.py --vendor-sdk
python cloudflare/test_runtime.py
```

Bài kiểm thử runtime tạo dữ liệu và tiến trình dùng một lần, không gọi production. Trước phát hành còn phải đạt suite Python/Docker, các luồng trình duyệt, SEO và kiểm checkout sạch. `pages.yml` phụ thuộc vào cùng bộ kiểm tra; production Cloudflare phải qua:

```text
node scripts/verify-release.cjs --sha SHA_DA_PUSH
```

Lệnh kiểm này chỉ xác minh Git và CI, không triển khai. Chỉ dùng SHA vừa đạt để dựng Worker và Pages. Với Pages có backend, chọn target `cloudflare-live`; target `cloudflare` và `github` vẫn là bản trải nghiệm tĩnh. Kiểm binding preview trước khi upload để tránh nối bản thử vào dữ liệu chính thức.

## Chuyển dữ liệu và sao lưu

Làm theo [BACKUPS.md](BACKUPS.md). Tạo snapshot SQLite nhất quán, khôi phục thử trên tệp mới và so sánh từng giá trị trước khi chuyển. Chỉ nhập vào object trống, bật `TRANSFER_ENABLED` tạm thời và dùng secret `OPERATOR_TOKEN`. Khi đang chờ nhập, API tài khoản trả 503 và không tự tạo database. Sau nhập, kiểm số bản ghi, xuất ngược về SQLite độc lập và so sánh trước khi mở website.

Tắt lại cổng nhập sau khi hoàn tất. Cấu hình đã phát hành mặc định `TRANSFER_ENABLED=false` cho cả production và preview. Khi chuyển vào một tenant mới hoàn toàn, lần deploy chuẩn bị phải dùng `--var TRANSFER_ENABLED:true` để giữ API chờ nhập; sau import/export/compare phải deploy lại với cấu hình mặc định đóng. Không mở lại cổng nhập khi triển khai cập nhật thông thường. Cổng xuất sao lưu vẫn cần operator secret; secret không nằm trong mã, URL, log hoặc tin nhắn. Không dùng tài khoản thật để chạy bộ kiểm thử.

SQLite Durable Objects hỗ trợ PITR tới các mốc trong 30 ngày; bản xuất độc lập vẫn cần để phục hồi khi mất quyền truy cập tài khoản. [PITR API](https://developers.cloudflare.com/durable-objects/api/sqlite-storage-api/#pitr-point-in-time-recovery-api). Công cụ chuyển/xuất phiên bản 1 giới hạn một payload 16 MiB; nếu dữ liệu vượt mức, cần quy trình xuất phân trang trước khi tiếp tục dùng công cụ này. Không cắt bớt tệp hoặc lịch sử để làm vừa giới hạn.

## Thanh toán thật

Thông tin ngân hàng, khóa HMAC và cờ SePay đặt bằng Workers secrets; Pages không cần giữ những giá trị này. Giữ `MAM_TOAN_SEPAY_ENABLED=0` tới khi chủ ngân hàng liên kết SePay, cấu hình webhook `https://5bmath.vn/api/webhooks/sepay` và hoàn tất phép thử có đối soát. Xem [PAYMENTS.md](PAYMENTS.md). Đưa backend lên mạng không tự hoàn tất bước liên kết ngân hàng.

Phí SePay và hạn mức Cloudflare được tính riêng. Quy trình này không tự nâng cấp gói hoặc mua dịch vụ. Trạng thái triển khai thực tế, SHA và bằng chứng hiện hành được ghi trong [bảng triển khai](REVIEW_IMPLEMENTATION_2026-11-12.md).
