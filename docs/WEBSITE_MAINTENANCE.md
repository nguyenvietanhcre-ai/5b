# Công khai và ẩn website

Admin mở **Quản trị → Vận hành → Công khai hoặc ẩn website** để chọn trạng thái.
Mặc định website công khai. Khi chọn ẩn, các đường dẫn thông thường, tài nguyên,
API học tập và đường dẫn không tồn tại đều trả trang:

> Hệ thống đang được cập nhật
>
> Vui lòng quay lại sau.

Trang trả HTTP **503**, `Retry-After: 300`, `Cache-Control: no-store` và `noindex`.
Không chuyển hướng mọi URL về một URL 200, không xóa nội dung hoặc dữ liệu.
Tab đã mở kiểm tra lại khi đổi mục, quay lại tab và định kỳ 15 giây lúc tab hiện.
Các yêu cầu mới bị chặn tại máy chủ, kể cả trước khi tab cũ tải lại.

## Mở website trở lại

Giữ địa chỉ **`/quan-tri/bao-tri/`**. Trang này hoạt động cả khi website đang ẩn;
admin có thể đăng nhập bằng tài khoản quản trị hiện có, chọn **Công khai website**
và lưu. Giáo viên/học sinh không được đổi trạng thái. Các đường dẫn quản trị
thông thường cũng bị ẩn; không dựa vào chúng để khôi phục website.

Đường dẫn khôi phục không phải một khóa bí mật: đăng nhập admin, kiểm nguồn,
CSRF, phiên còn hiệu lực và quyền admin vẫn được kiểm tra. Mỗi lần đổi trạng
thái có revision chống lưu đè và được ghi nhật ký. Không có tài khoản hoặc mật
khẩu dự phòng được thêm vào hệ thống.

Trạng thái lưu ở `system_settings`, khóa `website_visibility`, trong kho chính;
đọc lần đầu không tạo dòng hoặc database mới. Khởi động lại không tự mở website.
Nếu kho trạng thái không đọc được, truy cập thông thường trả bảo trì; muốn đổi
trạng thái phải sửa kết nối database trước. Đây là công tắc vận hành, không thay
thế việc sửa lỗi máy chủ hoặc khả năng hoạt động của Cloudflare.

## Ngoại lệ vận hành

- Trang và bốn API khôi phục admin được giữ để mở lại website.
- Health probe vẫn trả kết quả để Docker không đánh dấu bảo trì là hỏng máy chủ.
- POST webhook SePay vẫn đi qua xác thực chữ ký hiện hành để không bỏ sót giao
  dịch đã phát sinh. Không công khai API thanh toán hoặc cho giả xác nhận tiền.
- Đường operator của Worker giữ xác thực bí mật riêng và cổng import vẫn theo
  cấu hình vận hành hiện hành.

## Hai môi trường

Python/Docker chặn tại HTTP handler trước khi phục vụ nội dung. Cloudflare-live
đưa `/*` qua Pages Worker và đọc trạng thái ở Durable Object trước khi trả tài
nguyên; không dùng bản cache trạng thái trong trình duyệt/KV để quyết định quyền
truy cập. Các bản static GitHub/offline không có database quản trị này.

Triển khai localhost và website công khai là hai bước riêng. Chức năng được
kiểm bằng HTTP, trình duyệt, Gateway và workerd cục bộ; chỉ bật trên tên miền
chính sau một đợt phát hành được người dùng yêu cầu.
