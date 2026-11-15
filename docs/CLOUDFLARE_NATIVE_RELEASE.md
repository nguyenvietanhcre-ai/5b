# Kho học tập và chức năng localhost trên Cloudflare

Bản chuyển này giữ chức năng học tập lớp 5, Nháp theo tài khoản, PDF, quản trị
bài giảng và game mẫu đã được duyệt để tích hợp. Học liệu chưa có giáo viên độc
lập duyệt và câu game tổng hợp vẫn mang nhãn mẫu/thử nghiệm. Ví mua câu trong
kho thí điểm và các nút xác nhận thanh toán giả vẫn là mô phỏng; không phải
thanh toán thật. VIP/VIP+, mua đề chính thức và SePay tiếp tục dùng kho chính.

## Lưu trữ và quyền truy cập

- `CloudLearning` sử dụng cùng SQLite Durable Object và cùng transaction với
  tài khoản chính. Các bảng học tập có tiền tố `native_learning_`; dữ liệu, ID
  câu hỏi và lịch sử không bị trộn với bảng tài khoản chính.
- Tài khoản học tập là ánh xạ nội bộ, không có mật khẩu đăng nhập. Mọi yêu cầu
  được xác thực bằng session tài khoản chính, kiểm Origin/CSRF và quyền sở hữu.
- Nháp giữ kiểm revision và request key. Khôi phục tiến trình Worker giữ bài
  làm, Nháp, lịch sử và phòng game; không phụ thuộc tệp SQLite trên máy chủ.
- Các bài lớp 5 cũ được ngừng khám phá/cấp mới theo lựa chọn A đã duyệt. Không
  xóa câu, trạng thái, nội dung, điểm hoặc lịch sử; khối 1–4 được giữ.

## Dữ liệu riêng và kiểm thử

`pilot-inputs/`, `restructure-inputs/`, các bộ fixture riêng và
`cloudflare/learning-seed.sql` không đưa lên kho GitHub công khai. Seed chỉ được
tạo từ nguồn học liệu trên database mới có **0 tài khoản và 0 phiên đăng nhập**;
không xuất từ database localhost của người dùng.

`cloudflare/learning-source-seal.json` lưu kích thước/SHA256 của các tệp riêng.
`build_worker.py` kiểm seal trước khi đóng gói. Tệp seed và nguồn học liệu chỉ
được tải trong bundle Worker; không có trong tài sản Pages công khai.

Public CI kiểm các phần độc lập, bộ lưu trữ/rollback/namespace bằng fixture tự
tạo và workerd nền tảng. Những kiểm thử cần nguồn riêng ghi rõ lý do bỏ qua khi
không có nguồn. Phát hành đầy đủ còn phải chạy **toàn bộ suite với nguồn riêng**
và `python cloudflare/test_native_runtime.py` cục bộ. CI xanh không thay thế gate
riêng này. Không phát hành Worker bật native chỉ từ checkout thiếu nguồn.

## PDF và dung lượng

Gói WASM dùng phiên bản/checksum trong `cloudflare/pylock.toml`, phông DejaVu và
tài sản in chính thức. SVG của các tài sản đã niêm phong được chuyển bằng XML
chuẩn và parser đường nét SVG có sẵn của ReportLab. Không tải tài nguyên ngoài,
không thực thi script/CSS và từ chối loại hình chưa hỗ trợ. Python/Docker giữ
svglib của renderer hiện hành. Cần kiểm PDF thật, kể cả hình, tiếng Việt, nhãn
in đậm và đầu/chân trang khi đổi thư viện hoặc tài sản.

Gói chỉ giữ những phần thư viện được dùng; phép hash mật khẩu 600.000 vòng và
định dạng cũ được giữ nguyên. Sau mỗi thay đổi cần chạy workerd thật và đo
`wrangler deploy --dry-run`; giữ gói nén trong giới hạn tài khoản hiện hành.

## Phát hành

1. Giữ kho dữ liệu riêng và bộ nhớ chat ngoài Git. Xác minh seal và nguồn đã QA.
2. Kiểm Python/Docker, JS, browser dọc/ngang, workerd nền tảng và native, PDF/SEO.
3. Commit/push đúng nguồn; theo dõi Actions/Pages cùng SHA và chạy gate README.
4. Trước migration, thực hiện sao lưu theo `BACKUPS.md` bằng quyền đã được cấp.
   Không thay thế dữ liệu website bằng database localhost hoặc fixture QA.
5. Triển khai Worker với `--keep-vars` để giữ cấu hình vận hành, sau đó Pages
   `cloudflare-live`. Giữ secret, namespace, tenant và cổng import đang đóng.
6. Nghiệm thu website bằng GET/HEAD và các kiểm tra tài khoản đã được cho phép;
   không nhập tài khoản, video, giá bán hoặc thanh toán giả vào production.
