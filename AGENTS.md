# Mầm Toán — hướng dẫn bắt buộc cho mọi phiên dự án

## Bắt đầu MỖI phiên và khi tiếp tục sau khi rút gọn ngữ cảnh
1. Đọc docs/PROJECT_MEMORY.md, docs/SESSION_LOG.md, docs/chat/README.md và README.md.
2. Đọc bản ghi gần nhất/liên quan trong docs/chat/ khi cần chi tiết.
3. Kiểm tra Git/tệp thực tế. Bộ nhớ cũ không chứng minh máy chủ còn chạy hoặc kiểm thử mới đã đạt.
4. Ưu tiên chỉ đạo mới nhất của người dùng; cập nhật bộ nhớ khi có thay đổi.

## Kết thúc MỖI phiên hoặc trước câu trả lời cuối sau một đợt công việc
Lưu bộ nhớ là điều kiện hoàn thành nhiệm vụ, không chờ người dùng nhắc.
1. Tạo/cập nhật docs/chat/YYYY-MM-DD-mo-ta-phien.md. Tiếp tục cùng chat thì nối vào cùng bản ghi; không ghi đè lịch sử.
2. Lưu yêu cầu, chỉnh sửa, quyết định/phê duyệt, học liệu, lý do ảnh hưởng triển khai, tệp đã đổi, Git/commit/nhánh, kiểm tra thực tế, lỗi/giới hạn, việc còn chờ và bước tiếp theo.
3. Nếu truy xuất được lịch sử, lưu đầy đủ tin nhắn người dùng/trợ lý. Nếu chỉ có ngữ cảnh/tóm tắt, ghi rõ phạm vi; không gọi đó là bản xuất nguyên văn đầy đủ.
4. Không lưu hướng dẫn/suy luận nội bộ, mật khẩu, token hay cookie.
5. Cập nhật docs/PROJECT_MEMORY.md với trạng thái mới nhất, liên kết bản ghi, việc đã xác nhận và giả định; sửa thông tin lỗi thời.
6. Nối mục có ngày Asia/Saigon vào docs/SESSION_LOG.md. Giữ lịch sử cũ; không xóa các mục trước.
7. Cập nhật danh mục docs/chat/README.md. Kể cả công việc còn dở vẫn ghi phần đã làm và tình trạng chờ.
8. Đọc lại để xác minh các tệp đã lưu và nội dung khớp thực tế trước khi báo hoàn tất.
9. Bộ nhớ bền vững nằm trong tệp dự án, không dựa vào lời hứa bộ nhớ toàn cục. Phiên sau cần mở đúng thư mục và đọc hướng dẫn này.

## Chỉ đạo lâu dài
- Mọi mã nguồn, tài liệu, sản phẩm và tệp tạm ở dưới F:\ChatGPT Math Project. Dùng work/ cho tệp tạm.
- Python backend, Git/GitHub quản lý mã nguồn, Docker/Compose đóng gói.
- Khi soạn học liệu hoặc lời giải Toán tiểu học, đọc `docs/PHUONG_PHAP_GIAI_TOAN_TIEU_HOC.md`, tham khảo hai tập người dùng cung cấp trong `Learn/` và mở lại trang gốc khi cần. Ưu tiên cách số học/sơ đồ phù hợp khối lớp, giải thích quan hệ và từng bước, tự kiểm toàn bộ dữ kiện; không chép máy móc đáp án sách hoặc OCR. Chỉ dùng chữ thay số khi phù hợp và có giải thích.
- Thương hiệu người dùng xác nhận là `5BMath` (giữ đúng chữ hoa/thường). `5bmath.vn` là tên miền đã mua tại P.A Việt Nam. Logo chính thức là mẫu 02 Bút Sáp, gồm Mầm Sách và chữ `5BMath Gieo Mầm Toán`. PNG avatar nền trong suốt nằm tại `design/5bmath/5bmath-logo-but-sap.png`.
- Dùng phong cách Vườn Toán đã duyệt cho mọi trang: xanh lá `#1F6248` cho nút chính, cam mơ `#FFBE73` làm điểm nhấn, nền kem `#FFF9ED`, chữ xanh đậm `#203A32`. Dùng chung biến màu và thành phần trong `frontend/styles.css`, trừ khi người dùng yêu cầu đổi.
- Thiết kế mọi giao diện cho điện thoại, máy tính bảng và máy tính. Giữ đầy đủ chức năng, dễ đọc, dễ chạm, đẹp và mượt ở màn hình hẹp. Kiểm tra luồng chính ở cả chiều dọc và ngang khi thay đổi giao diện. Bố trí lại điều khiển thay vì ẩn chức năng.
- Áp dụng mục **Quy tắc thiết kế SEO** cho mọi thay đổi liên quan tới trang công khai.
- Nếu phù hợp làm skill: đề xuất rồi CHỜ xác nhận trước khi tạo/cài. Ghi đề xuất và trạng thái trong docs/SKILL_CANDIDATES.md. Đã duyệt `mam-toan-release` tại `.agents/skills/mam-toan-release/SKILL.md`.
- Phân biệt commit local, push GitHub, kiểm thử CI và triển khai website.
- Không khẳng định Docker/CI đã đạt nếu chưa chạy; không bịa tuyển sinh, video, lịch học hoặc bảo vệ tài khoản.
- Bản ghi chi tiết docs/chat/*.md và *.json chỉ lưu cục bộ, loại khỏi Git (trừ README danh mục). Chỉ công khai/đẩy các bản ghi đó khi người dùng yêu cầu rõ. Không tự push chỉ vì vừa lưu bộ nhớ.

- Mầm Sách 3D đã được duyệt ngày 11/11/2026 để dùng trên website và hình ảnh truyền thông về sau. Giữ tạo hình mầm xanh đọc sách, hai lá, má cam và chất liệu đồ chơi đất sét mềm/vải nỉ. Ảnh gốc và mô tả tham chiếu ở `design/5bmath/linh-vat/`.

## Quy tắc thiết kế SEO

Áp dụng khi lên kế hoạch, viết học liệu, thiết kế, lập trình và nghiệm thu các trang công khai của 5BMath.

1. **Lên kế hoạch nội dung.** Xác định mỗi trang phục vụ câu hỏi nào của học sinh hoặc phụ huynh. Viết nội dung có ích, kiểm tra ví dụ và lời giải. Gắn nhãn rõ học liệu tự biên soạn, nội dung demo và thông tin chưa xác nhận. Dùng cách diễn đạt tự nhiên theo chủ đề, tránh nhồi từ khóa. [Google Search Essentials](https://developers.google.com/search/docs/essentials)
2. **Thiết kế giao diện.** Dùng một H1 mô tả chủ đề và các tiêu đề phụ theo mạch đọc. Giữ nội dung chính, liên kết và thông tin mô tả tương đương trên điện thoại, máy tính bảng và máy tính. Nội dung chính phải có sẵn trong HTML để đọc được mà không cần bấm, vuốt hoặc chạy JavaScript. Viết văn bản thay thế có ý nghĩa cho ảnh minh họa mang thông tin và dùng `alt=""` cho ảnh trang trí. [Hướng dẫn mobile-first của Google](https://developers.google.com/search/docs/crawling-indexing/mobile/mobile-sites-mobile-first-indexing)
3. **Lập trình trang công khai.** Mỗi trang có URL ổn định, tiêu đề và mô tả riêng, liên kết `<a href>` với nhãn rõ đích đến và canonical HTTPS trên `5bmath.vn`. Dùng dấu `#` cho mục trong cùng trang. Khi đổi URL, duy trì liên kết cũ bằng chuyển hướng phù hợp. Sitemap chỉ chứa URL chuẩn công khai trả 200. URL không tồn tại trả 404. Dùng `noindex` cho góc học tập mẫu và bảo vệ dữ liệu học sinh bằng xác thực, phân quyền khi có tài khoản thật. [Hướng dẫn JavaScript SEO của Google](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
4. **Giữ trang nhanh và ổn định.** Dùng ảnh đúng kích thước, nén phù hợp và chừa sẵn chỗ cho ảnh, video. Ưu tiên tải nội dung quan trọng đầu trang, trì hoãn tài nguyên ngoài màn hình khi phù hợp. Kiểm tra trên màn hình hẹp, cả chiều dọc và ngang. Theo dõi Core Web Vitals khi có dữ liệu thực tế. [Core Web Vitals của Google](https://developers.google.com/search/docs/appearance/core-web-vitals)
5. **Nghiệm thu và phát hành.** Làm theo [quy trình SEO trong README](README.md#seo-và-phát-hành-tên-miền-chính) và chạy `python -m scripts.check_pages` với thư mục bản dựng phù hợp. Xem HTML, liên kết và nội dung chính trên trang đại diện khi tắt JavaScript. Sau khi phát hành, kiểm tra canonical, mã 200/404, `robots.txt` và sitemap trên tên miền chính. Dùng Google Search Console để theo dõi tình trạng lập chỉ mục khi đã xác minh quyền sở hữu.

## Quy ước “lưu tiến độ để chuyển tài khoản”

Khi người dùng nói “lưu tiến độ để chuyển tài khoản” trong bất kỳ chat nào của dự án 5BMath, thực hiện bàn giao cục bộ ngay theo phạm vi công việc của chat đó.

1. Đưa tác vụ đang sửa tệp của phiên về điểm dừng an toàn. Lưu thay đổi đã làm. Nếu còn tác vụ đang ghi hoặc chưa thể dừng an toàn, nêu rõ tình trạng trước khi báo bàn giao.
2. Kiểm tra thư mục làm việc, nhánh, HEAD, worktree và các thay đổi Git liên quan. Ghi việc đã xong, việc đang dở, kết quả kiểm tra thực tế, lỗi còn mở, tệp cần giữ và bước tiếp theo cụ thể.
3. Lưu và đọc lại bốn tệp bộ nhớ theo quy tắc kết thúc phiên. Dùng bộ nhớ trong thư mục dự án chính `F:\ChatGPT Math Project` khi có quyền ghi. Nếu phiên làm trong worktree riêng, ghi đường dẫn tuyệt đối và nhánh cần mở. Nếu thư mục chính ngoài quyền ghi, lưu trong worktree hiện tại và báo rõ vị trí.
4. Báo ngắn gọn nơi mở lại, trạng thái và bước tiếp theo để người dùng chuyển tài khoản. Chỉ báo sẵn sàng sau khi xác minh bản ghi đã lưu. Giữ bản ghi chi tiết cục bộ. Việc bàn giao không tự commit, push GitHub, triển khai hay đăng nhập tài khoản khác.

## Quy ước “đồng bộ”

Khi người dùng yêu cầu “đồng bộ” trong bất kỳ chat nào của dự án, thực hiện toàn bộ quy trình dưới đây cho bản cập nhật đã duyệt. Xác định phạm vi theo yêu cầu hiện tại và ngữ cảnh của chat, rồi đối chiếu với Git để chọn đúng các tệp cần phát hành.

1. Dùng quy trình `mam-toan-release` để dựng và chạy bản mới tại `http://localhost:8765/`. Kiểm thử và xác minh thay đổi trên localhost.
2. Khi kiểm thử đạt, commit đúng các tệp thuộc phạm vi cập nhật và push lên `origin/main`. Giữ các tệp riêng tư và bản ghi chi tiết cục bộ theo quy tắc trên.
3. Theo dõi CI và lượt triển khai GitHub Pages của bản cập nhật đến khi hoàn tất. Với thay đổi website, mở trang công khai và xác minh thay đổi đã xuất hiện. Báo trạng thái localhost, commit, CI và triển khai dựa trên kết quả thực tế.

## Phát triển
- Chạy: python -m backend --host 127.0.0.1 --port 8765
- Kiểm thử: python -m unittest discover -s tests -v
- Cú pháp JS: node --check frontend/app.js
- Docker (mặc định): docker compose up --build --wait --wait-timeout 120; hoặc START-DEMO.cmd / START-DOCKER.cmd.
- Thử trên điện thoại: START-PHONE.cmd hoặc docker-demo.ps1 -Lan. Máy này đã bật LAN bằng compose.override.yaml cục bộ (ignored); giữ localhost và volume hiện có. Khi cập nhật image bằng các tệp -f tường minh, phải nạp thêm compose.override.yaml để không vô tình tắt LAN. IP DHCP có thể đổi; launcher tự dò lại, firewall cần khớp IP mới theo README.
- Dừng Docker: STOP-DOCKER.cmd. Python trực tiếp: START-PYTHON.cmd. Kiểm tra Docker Desktop và cổng trước khi khởi chạy.
- Chỉ phục vụ danh sách frontend, không công khai .git hoặc tài liệu nội bộ.
- Tài khoản/nộp bài/lớp học hiện là demo. Đăng nhập thật, cơ sở dữ liệu, giáo viên là việc tiếp theo.

## Tạo animation linh vật từ các chat

- Khi được giao tạo/sửa animation một nhân vật, đọc `docs/ANIMATION_WORKSHOP.md`, catalog và brief tương ứng trong `design/5bmath/linh-vat/animations/` trước khi làm. Có thể nhận việc chỉ từ tên nhân vật; không cần lịch sử chat Chó.
- Người dùng đã đồng ý hướng Canvas + ảnh WebP, nhưng **chưa yêu cầu tích hợp game lúc này**. Làm demo riêng để duyệt; không tự sửa frontend/backend/DB, luật/sát thương, Docker, commit/push hoặc phát hành.
- Mỗi chat dùng owner riêng và thư mục `<id>/<variant>` do `tools/mascot-animation/cli.cjs init` tạo. Kiểm `status` trước, không ghi đè job/ảnh nguồn/brief hoặc shared của chat khác. Dùng release/claim và HANDOFF.md khi chuyển người làm; không tự giành khóa của phiên còn chạy.
- Dùng ảnh tham chiếu thật và imagegen cho tạo hình; giữ PNG nguồn, chuẩn bị WebP, sửa choreography theo đúng chiêu của từng con. Template Chó không phải chiêu hoàn chỉnh cho mọi nhân vật. Exporter không tự duyệt; gửi GIF/MP4 và HTML Canvas, lưu QA/dung lượng/giới hạn và bộ nhớ theo quy tắc chung.
