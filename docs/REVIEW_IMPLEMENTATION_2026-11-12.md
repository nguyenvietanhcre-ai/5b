# Triển khai đề xuất rà soát ngày 12/11/2026

Yêu cầu: áp dụng [báo cáo rà soát](PROJECT_REVIEW_2026-11-12.md) và cập nhật 5bmath.vn. Người dùng chọn tiếp tục Cloudflare và chưa có VPS. Không mua gói trả phí hoặc tự bật SePay khi chưa liên kết ngân hàng.

## Kết quả triển khai

Đã phát hành lên **https://5bmath.vn** ngày **12/11/2026, khoảng15:49 Asia/Saigon**, từ SHA `3b0570637a9f26af042d06258bf3447a1857e987`. [CI43185138175](https://github.com/nguyenvietanhcre-ai/5b/actions/runs/43185138175) đạt Python3.12/3.13, Docker/Chrome, Workers, build và GitHubPages; gate exactSHA đạt trước production. Pages `9a0386c4.5bmath.pages.dev` nối Worker `5bmath-api`, version `b491cbe4-7dd3-4339-aac2-88e915df1a92`.

Nguồn local ngừng ghi khi chụp bản cuối: **30accounts/30students/19migrations,71bảng**. Import vào object trống rồi export/restore độc lập đạt integrity/FK và khớp mọi giá trị dòng. Sau khởi tạo website, bản xuất có72bảng; chỉ thêm `cloudflare_arena_rooms`, toàn bộ71bảng nguồn vẫn khớp. Cổng import đã đóng/HTTP404; export sau khi đóng vẫn khôi phục SQLite độc lập đạt. Localhost/LAN được khởi động lại, giữ volume cũ nhưng là DB độc lập với website chính.

Nghiệm thu tên miền chính đạt25HTTPchecks,8trang200/canonical/SSR,404đúng,noindextrangriêng,robots/sitemap,guest/protected401/grade10/no-store; Chrome390×844/844×390/noJS/login sẵn sàng/errors[]. HashCSS và3clayWebP giữ đúng bản UI; haiAPI D1mẫu200/tách khỏi tài khoản. **SePay=0**, chưa liên kết ngân hàng/dịch vụ. Học liệu/ngân hàng mẫu vẫn cần biên tập và duyệt trước dùng như chương trình chính thức.

| Đề xuất | Kết quả mã nguồn và nghiệm thu |
|---|---|
| Lưu tiến độ bài công khai | Dùng mã ổn định `public-decimal`/`public-percent`; POST lưu đúng chủ trước khi thông báo; khôi phục khi đăng nhập/tải lại. API và trình duyệt đã đạt. |
| Ví dụ bài admin | Cho phép thiếu ví dụ trong schema; nhập ví dụ thật qua giao diện biên soạn. Bài thiếu ví dụ không còn gây lỗi đọc `example`. |
| Giữ đáp án trên server | Kho riêng mỗi database với ID không thể suy ra từ bộ offline; công khai 22 ví dụ độc lập, catalog chỉ chứa metadata. Kiểm thử ngân hàng 7/7 và Node boundary đạt. |
| Checkout tái tạo được | Checkout từ Git index sạch đã đạt228Python/13Cloudflareunit, dependency khóa phiên bản và hai build. Giữ riêng sách, tài liệu thiết kế WIP, database và chat chi tiết. |
| HTTPS và phiên | Dùng Origin đã cấu hình và cookie `Secure`; không tin `X-Forwarded-*` do client tự gửi. PreviewHTTPS đã đăng ký/đăng nhập và giữ cookieSecure; unit/runtime kiểm quyền và CSRF đạt. |
| Arena theo ngân hàng admin | Dùng chung nguồn published/versioned, chụp phiên bản khi tạo trận và chỉ gửi câu hiện tại. Arena 29/29 đạt. |
| URL video | Chuẩn hóa `videoRef`, chuyển URL an toàn tới học sinh, không tự tạo thông tin video. |
| Ngày học Việt Nam | Chia khoảng hoạt động qua nửa đêm GMT+7, giữ timestamp nguồn. Kiểm thử hồi quy đạt. |
| Khóa SQLite | GET dùng kết nối đọc; chỉ giữ khóa ghi khi có bảo trì đến hạn. PBKDF chạy ngoài khóa ghi, sau đó kiểm lại trong giao dịch. |
| Tải mã theo trang | Trang chủ tải 5 JS + 2 CSS, không có MutationObserver. Một bộ quản lý dùng chung cho 19 linh vật; chọn/quay ra và 6 kích thước màn hình đã đạt. |
| Độ đa dạng câu | Có 960 mẫu khác nhau theo cặp `(grade, prompt)`; dấu `<`, `=`, `>` cân bằng và số bước tăng theo mức. Chưa coi đây là chương trình đã kiểm duyệt. |
| HTML/SEO dùng chung | Python và bản tĩnh dùng cùng renderer; kiểm 8 trang, canonical, nội dung khi tắt JS, robots/sitemap và revalidate 304. API/nội dung riêng dùng `no-store`. |
| CI gắn đúng SHA | Pages phụ thuộc checks; Python3.12/3.13, Docker/Chrome và Workers cùng SHA đạt trên CI43185138175. `verify-release` đạt trước production. |
| Kiểm JS/Docker/trình duyệt | Mốc đã ghi nhận: 213/213 trên Windows trong 384,956 giây và Docker trong 129,959 giây; 4 luồng Chrome ở 6 kích thước màn hình; thêm 14 kiểm thử phục vụ tài nguyên đạt. Các kiểm thử mới được ghi riêng bên dưới. |
| Sao lưu và khôi phục | Công cụ tạo ảnh nhất quán, manifest, giữ số bản theo cấu hình và khôi phục vào tệp mới; 7/7 kiểm thử đạt. Đợt diễn tập đã giữ 69 bảng/30 tài khoản, integrity đạt và không có lỗi FK. Xem [BACKUPS.md](BACKUPS.md). |
| Chuyển dữ liệu Cloudflare | Giao thức v1 dùng SQL schema và binding có kiểu; 8/8 kiểm thử cục bộ đạt, gồm schema đầy đủ và lịch sử VIP/giới thiệu/thông báo tổng hợp. Chưa suy ra đã nhập dữ liệu thật hoặc sao lưu remote thành công. |
| Tách tệp riêng | Loại cache/database/sách/brief/chat chi tiết khỏi Git; phát hành theo danh sách, không đẩy `.env` hoặc bản sao lưu. |
| Bộ nhớ và README | Rút gọn bộ nhớ hiện hành, trỏ tới bản lưu trữ cục bộ và giữ lịch sử SESSION_LOG. README phân biệt 5 môi trường. |
| Asset/schema/tệp tạm | Dùng manifest chung cho trình duyệt/Python/build và migration làm nguồn schema. Giữ PNG, QA và dữ liệu thuộc công việc khác. |

Số kiểm thử không thay cho việc người dùng duyệt lại mỹ thuật. Giữ giao diện **04 — Vườn Khám Phá**, bộ chọn 5 phong cách và các chỉnh sửa bám mẫu của công việc giao diện.

## Cloudflare

Cloudflare Pages của dự án `5bmath` phục vụ bản tĩnh. API đi qua service binding `BACKEND` tới Python Worker `5bmath-api`. SQLite Durable Object được tách theo trường/tenant để tài khoản, giới thiệu và học phí cùng nằm trong một giao dịch. Worker preview `5bmath-api-preview` và nhánh `review-20261112` dùng database riêng. D1 demo tiếp tục tách biệt, không làm nguồn tài khoản.

Runtime thử thực đã xác minh Python Durable Object/SQL, `transactionSync` và PBKDF2-SHA256 600.000 vòng tương thích hash cũ qua context SHA256 gốc, tránh giới hạn Web Crypto production 100.000 vòng; giới hạn hàng dữ liệu là 8 MiB. Tệp bài tập Zoom được chia chunk 1 MB để giữ hạn mức tải lên 10 MB. Adapter/runtime, preflight/replay đã đạt trên preview; chuyển dữ liệu và bản xuất độc lập production đã đạt như mốc trên.

Công cụ `scripts/cloudflare-data.py` tạo snapshot nhất quán dưới `work/`, bảo toàn BLOB/số nguyên64bit/textNUL và đặt trigger sau dữ liệu để không cộng lại lịch sử. Import chỉ dành cho object trống và cần cổng vận hành/operator secret. Export/restore độc lập rồi so sánh mọi giá trị dòng đã đạt trên cả preview tổng hợp và snapshot production; xem [BACKUPS.md](BACKUPS.md#chuyển-dữ-liệu-và-xuất-sao-lưu-cloudflare--giao-thức-v1).

## Vận hành tiếp theo

Tiếp tục xuất bản sao độc lập vào nơi bảo vệ ngoài máy; chưa tạo lịch sao lưu ngoài máy mới. Người dùng cần liên kết ACB/SePay và cấu hình webhook/HMAC trước phép thử tiền thật có đối soát; SePay vẫn tắt tới khi hoàn tất. Dùng5bmath.vn làm nguồn học/đối soát chính; localhost không tự đồng bộ hai chiều. Checkout sạch, preview browser4luồng/6viewport và9ca tài chính tổng hợp đạt; chế độ thử preview đã tắt lại.

Bằng chứng không chứa secret nằm tại `work/review-implementation-20261112/`; database/secrets/bản ghi chi tiết riêng không đưa lên Git. Mốc phát hành trên là kết quả thực tế.

Mốc QA nền: Windows/checkout sạch228, Docker từcheckout sạch228/124.076s; Cloudflareunit13/native7nhóm+9financial đạt. CI đầu gặp Compose cũ thiếu run--tmpfs và probeLinuxTIME_WAIT; sửa bằng compose.test.yaml/Unixreuse+listen rồi đạt CI43184711467 và43185138175. Nghiệm thu production không tạo tài khoản, bài nộp hoặc giao dịch thử trong dữ liệu thật.
