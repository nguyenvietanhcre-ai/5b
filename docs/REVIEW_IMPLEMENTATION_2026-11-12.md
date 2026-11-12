# Triển khai đề xuất rà soát ngày 12/11/2026

Yêu cầu: áp dụng [báo cáo rà soát](PROJECT_REVIEW_2026-11-12.md) và cập nhật 5bmath.vn. Người dùng chọn tiếp tục Cloudflare và chưa có VPS. Không mua gói trả phí hoặc tự bật SePay khi chưa liên kết ngân hàng.

## Tình trạng đang chốt

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
| CI gắn đúng SHA | Pages phụ thuộc bước checks; kiểm Python, Docker và Chrome. Script `verify-release` chặn khi chưa đủ điều kiện. CI từ xa còn chờ push. |
| Kiểm JS/Docker/trình duyệt | Mốc đã ghi nhận: 213/213 trên Windows trong 384,956 giây và Docker trong 129,959 giây; 4 luồng Chrome ở 6 kích thước màn hình; thêm 14 kiểm thử phục vụ tài nguyên đạt. Các kiểm thử mới được ghi riêng bên dưới. |
| Sao lưu và khôi phục | Công cụ tạo ảnh nhất quán, manifest, giữ số bản theo cấu hình và khôi phục vào tệp mới; 7/7 kiểm thử đạt. Đợt diễn tập đã giữ 69 bảng/30 tài khoản, integrity đạt và không có lỗi FK. Xem [BACKUPS.md](BACKUPS.md). |
| Chuyển dữ liệu Cloudflare | Giao thức v1 dùng SQL schema và binding có kiểu; 8/8 kiểm thử cục bộ đạt, gồm schema đầy đủ và lịch sử VIP/giới thiệu/thông báo tổng hợp. Chưa suy ra đã nhập dữ liệu thật hoặc sao lưu remote thành công. |
| Tách tệp riêng | Loại cache/database/sách/brief/chat chi tiết khỏi Git; phát hành theo danh sách, không đẩy `.env` hoặc bản sao lưu. |
| Bộ nhớ và README | Rút gọn bộ nhớ hiện hành, trỏ tới bản lưu trữ cục bộ và giữ lịch sử SESSION_LOG. README phân biệt 5 môi trường. |
| Asset/schema/tệp tạm | Dùng manifest chung cho trình duyệt/Python/build và migration làm nguồn schema. Giữ PNG, QA và dữ liệu thuộc công việc khác. |

Số kiểm thử không thay cho việc người dùng duyệt lại mỹ thuật. Giữ giao diện **04 — Vườn Khám Phá**, bộ chọn 5 phong cách và các chỉnh sửa bám mẫu của công việc giao diện.

## Cloudflare

Cloudflare Pages của dự án `5bmath` phục vụ bản tĩnh. API đi qua service binding `BACKEND` tới Python Worker `5bmath-api`. SQLite Durable Object được tách theo trường/tenant để tài khoản, giới thiệu và học phí cùng nằm trong một giao dịch. Worker preview `5bmath-api-preview` và nhánh `review-20261112` dùng database riêng. D1 demo tiếp tục tách biệt, không làm nguồn tài khoản.

Runtime thử thực đã xác minh Python Durable Object/SQL, `transactionSync` và PBKDF2-SHA256 600.000 vòng tương thích hash cũ qua context SHA256 gốc, tránh giới hạn Web Crypto production 100.000 vòng; giới hạn hàng dữ liệu là 8 MiB. Tệp bài tập Zoom được chia chunk 1 MB để giữ hạn mức tải lên 10 MB. Adapter/runtime, preflight/replay, chuyển dữ liệu và bản xuất độc lập đã đạt trên preview; production chính thức còn chờ CI và cutover dữ liệu cuối.

Công cụ `scripts/cloudflare-data.py` tạo snapshot nhất quán trước khi chuẩn bị JSON dưới `work/`, bảo toàn BLOB/số nguyên 64 bit/text có NUL và đặt trigger sau dữ liệu để không cộng lại lịch sử. Import chỉ dành cho Durable Object trống và cần cổng vận hành được bật cùng operator secret. Bản xuất remote có thể khôi phục thành SQLite độc lập rồi đối chiếu mọi giá trị dòng; xem [quy trình chuyển dữ liệu và sao lưu](BACKUPS.md#chuyển-dữ-liệu-và-xuất-sao-lưu-cloudflare--giao-thức-v1). Preview thực đã import/export71bảng tổng hợp khớp mọi giá trị. Cần lặp lại với snapshot chính thức ở bước cutover; không gọi preview là dữ liệu production.

## Việc còn chờ

Chốt commit/push/Actions cùng SHA; sao lưu cuối và chuyển dữ liệu có kiểm toàn vẹn; triển khai Worker + Pages, rồi kiểm tra trên5bmath.vn. Checkout sạch, preview browser4luồng/6viewport và9ca tài chính đã đạt; tiền thử preview đã tắt lại. SePay thật tiếp tục tắt tới khi người dùng liên kết và cấu hình dịch vụ.

Bằng chứng không chứa secret nằm tại `work/review-implementation-20261112/`; các artefact riêng không đưa lên Git. Trạng thái này sẽ được cập nhật sau khi có kết quả thực tế.

Mốc trước phát hành: localhost14:57:57đã dùng image cf3d89cf… với migration19, giữ30accounts/volume/LAN và bốn phong cách UI mới. Windows/checkout sạch đều228; Docker từcheckout sạch228/124.076s; Cloudflareunit13/native7nhóm+9financial đạt. Root đang chốt Git/CI/cutover, chưa gọi là đã cập nhật website chính.
