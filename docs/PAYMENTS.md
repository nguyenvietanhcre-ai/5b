# Thanh toán tự động qua SePay

Luồng này nhận thông báo tiền vào và hoàn tất đơn đã được tạo trong tài khoản học sinh. Không tự trích tiền định kỳ. Backend Python và giao diện học sinh phải dùng cùng database; API mẫu D1 và bản Pages tĩnh không thay thế backend này.

## Kết quả khi xác nhận

| Loại đơn | Xử lý |
|---|---|
| Mua/gia hạn VIP | Cộng số tháng đã lưu trong đơn cho đúng account_id. VIP còn hạn được cộng tiếp; hết hạn tính từ lúc xác nhận, theo tháng lịch Việt Nam. |
| Mua VIP lần đầu có người giới thiệu | Trigger hiện có thưởng 1 tháng cho đúng người giới thiệu Free/VIP; gia hạn không thưởng lại. Người giới thiệu SVip giữ luồng hỗ trợ và confirm của admin. |
| Học phí Zoom | Ghi paid_at cho đúng fee_id/học sinh/lớp/tháng; giao diện hiện **Đã hoàn thành**. Không cộng VIP hoặc tạo thưởng giới thiệu từ học phí. |

Khoản 0 đồng giữ **Không phát sinh học phí**, không tạo đơn thanh toán. Một đơn chỉ hoàn tất một lần; một mã giao dịch SePay chỉ được ghi nhận một lần. Xác nhận thủ công và webhook dùng cùng hàm xử lý để tránh cấp trùng.

## Cấu hình máy chủ

Tham khảo [.env.example](../.env.example). Nếu chưa có `.env`, chép mẫu thành `.env` trong thư mục dự án; nếu đã có, chỉ bổ sung các khóa còn thiếu. `.env` được loại khỏi Git. Không lưu khóa thật vào tài liệu, mã nguồn, ảnh chụp hoặc chat.

```dotenv
MAM_TOAN_BANK_ID=ACB
MAM_TOAN_BANK_ACCOUNT=<so-tai-khoan-nhan>
MAM_TOAN_BANK_NAME=<ten-chu-tai-khoan>
MAM_TOAN_SEPAY_ENABLED=1
MAM_TOAN_SEPAY_WEBHOOK_SECRET=<khoa-ngau-nhien-it-nhat-32-ky-tu>
MAM_TOAN_PUBLIC_ORIGIN=https://5bmath.vn
```

Các giá trị trong dấu `<...>` là chỗ điền, không phải cấu hình chạy được. Khóa webhook phải khớp khóa HMAC-SHA256 trên SePay. `MAM_TOAN_SEPAY_ENABLED` mặc định **0**; thiếu khóa đủ dài hoặc thông tin ngân hàng hợp lệ thì chức năng tự động không hoạt động. Không có chế độ chấp nhận webhook không xác thực.

Để dùng HTTP localhost/LAN, để `MAM_TOAN_PUBLIC_ORIGIN` trống. Trên HTTPS chính thức, đặt đúng origin để giới hạn yêu cầu ghi và thêm `Secure` vào cookie đăng nhập. Không lấy địa chỉ công khai từ header chuyển tiếp do client gửi. Frontend và API tài khoản cần cùng origin hoặc reverse proxy dưới cùng origin; luồng này không mở CORS liên miền.

Compose đọc các biến từ `.env`. Dựng lại dịch vụ sau khi đổi cấu hình và giữ volume/cấu hình LAN theo README. Không chạy `down -v`. Khởi động Python trực tiếp cần đặt các biến vào môi trường tiến trình; Python không tự đọc `.env`.

## Cấu hình SePay

1. Liên kết đúng tài khoản ACB theo loại cá nhân/hộ kinh doanh/doanh nghiệp trên dịch vụ SePay. Chủ tài khoản tự thực hiện xác thực ngân hàng.
2. Cấu hình nhận diện mã thanh toán: tiền tố **BM**, hậu tố **20 ký tự**, loại **Số và chữ**. Đơn mới dùng `BM` + 20 ký tự chữ/số ngẫu nhiên. Mã cũ bắt đầu `5B` vẫn tra cứu chính xác trong backend; giữ cấu hình nhận diện cũ nếu còn đơn chờ, hoặc để backend tìm mã nguyên vẹn trong nội dung.
3. Tạo webhook **Có tiền vào**, chọn cụ thể tài khoản nhận; URL là `https://5bmath.vn/api/webhooks/sepay` khi backend đã thực sự được định tuyến tại địa chỉ này.
4. Chọn `application/json`, xác thực **HMAC-SHA256**, nhập cùng khóa bí mật, bật tự gửi lại khi server lỗi và cảnh báo lỗi.
5. Muốn lưu cả khoản sai/thiếu mã vào mục đối soát thì không bật bộ lọc bỏ giao dịch không có mã. Dùng tài khoản nhận học phí riêng để dễ theo dõi số lần tiền vào.

Chữ ký được kiểm tra trên **bytes gốc**, theo `HMAC-SHA256(secret, timestamp + "." + raw_body)`. Header `X-SePay-Signature` có dạng `sha256=<hex>`, `X-SePay-Timestamp` là Unix giây; độ lệch tối đa 300 giây. Đồng hồ server cần chính xác.

Nguồn chính thức: [liên kết ACB](https://docs.sepay.vn/ket-noi-acb.html), [tạo webhook](https://developer.sepay.vn/vi/sepay-webhooks/tao-webhook), [xác thực](https://developer.sepay.vn/vi/sepay-webhooks/xac-thuc), [payload và phản hồi](https://developer.sepay.vn/vi/sepay-webhooks/tich-hop-webhook).

## Đơn và trạng thái

- `POST /api/v1/payments` dùng phiên học sinh/CSRF; `{}` cho VIP hoặc `{feeId: ...}` cho khoản phí của chính học sinh. Client không quyết định số tiền, người nhận VIP hoặc người giới thiệu.
- `GET /api/v1/payments/:id` chỉ chủ tài khoản đọc được; trả 404 nếu là đơn của người khác. Đọc trạng thái không tạo đơn hoặc thay đổi thanh toán.
- Trang thanh toán và chi tiết học phí kiểm tra đơn chờ khoảng 5 giây một lần khi đang hiển thị và có mạng; có nút **Kiểm tra thanh toán**. Rời trang/đóng popup/đổi tài khoản dừng ngữ cảnh cũ. Chỉ kết quả backend xác nhận mới hiện thành công, cập nhật hạn VIP và thông tin học phí.
- Trang VIP giữ `?order=<id>` trong URL để tải lại đúng đơn/biên nhận bằng GET. Tải lại đơn đã trả không tạo một đơn gia hạn mới; muốn mua tiếp, đi từ **Nâng cấp gói** để chủ động tạo lần mua mới. Mã không hợp lệ hoặc thuộc người khác không tự tạo đơn thay thế.
- Chuyển khoản thiếu/thừa, mã không khớp/không có, đơn hủy/đã hoàn tất, ngân hàng/tài khoản nhận khác snapshot hoặc hóa đơn đã thay đổi không tự cấp quyền. Admin xem **Đối soát → Giao dịch ngân hàng** để kiểm tra.
- `GET /api/staff/payment-receipts` chỉ admin, hỗ trợ phân trang và lọc. Sổ nhận giao dịch chỉ phục vụ đối soát, không cấp quyền từ một nút trên client. Lịch sử không bị xóa khi gửi lại webhook.

Đơn chụp lại loại gói, số tháng, tiền và thông tin nhận tiền tại thời điểm tạo/cấu hình. Đổi ngân hàng về sau không chuyển đơn cũ sang tài khoản mới. Đơn lịch sử thiếu snapshot tài khoản nhận phải được học sinh mở lại để gắn cấu hình trước khi tự xử lý; không suy đoán ngân hàng nhận tiền trong quá khứ. Sửa học phí tiếp tục hủy đơn pending cũ theo quy tắc tính học phí.

## Vận hành và đối soát

Webhook trả **201** với `{"success":true}` sau khi giao dịch đã được lưu bền vững. Lỗi xác thực trả 401, nội dung không hợp lệ trả 400/415/413; lỗi database trả 503 để SePay có thể gửi lại. Lần gửi lại cùng giao dịch không cộng thêm quyền hoặc thông báo. Giao dịch mẫu ID 0 chỉ xác minh kết nối, không tạo thanh toán.

Nếu tiền đã về nhưng quyền chưa được ghi nhận, kiểm tra lịch sử gửi trên SePay, cấu hình/đồng hồ/URL và sổ **Giao dịch ngân hàng**. Sau khi sửa lỗi tạm thời, gửi lại webhook từ SePay. Với khoản đã ghi **Cần đối soát**, admin kiểm chứng giao dịch ngân hàng và xác nhận đúng đơn bằng luồng thủ công hiện có; hệ thống không tự gán khoản thiếu mã cho một học sinh. Giữ sổ nhận cũ làm bằng chứng, không sửa/xóa để thử lại.

Test mode và Live phải dùng webhook secret, database và URL tách biệt. Không gửi mẫu vào backend đang giữ dữ liệu học sinh thật. Trước bật thu tiền, kiểm tra mua lần đầu/gia hạn, thưởng giới thiệu, học phí đúng học sinh/lớp/tháng, gửi lặp, hai giao dịch cùng mã, sai tiền và khôi phục sau lỗi. Sau đó chủ tài khoản thử giao dịch thật có kiểm soát.

Tích hợp này chưa tự hoàn tiền, thu định kỳ hoặc tự truy vấn sao kê theo lịch. Nếu webhook bị bỏ lỡ lâu, dùng lịch sử SePay/ngân hàng để đối soát và gửi lại hoặc xác nhận thủ công. Hoàn tiền cần quy trình riêng, không xóa lịch sử VIP/thanh toán để đảo ngược.

## Khi chuyển backend lên Cloudflare

Tạo đơn và nhận webhook phải dùng cùng database trên website chính. Python/Dockerlocalhost, D1demo và DurableObjectproduction là các database riêng; không tự đồng bộ đơn/tiến độ hai chiều. Sau cutover, dùng `https://5bmath.vn` cho học và đối soát, webhook ở `https://5bmath.vn/api/webhooks/sepay`. Không chuyển tiền theo QR của một database thử rồi chờ database khác tự cấp quyền. Giữ SePay thật tắt tới khi đã liên kết ACB, cấu hình HMAC và thực hiện phép thử có đối soát. [Quy trình Cloudflare](CLOUDFLARE_BACKEND.md).
