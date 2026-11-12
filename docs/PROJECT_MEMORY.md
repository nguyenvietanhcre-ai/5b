# 5BMath — bộ nhớ hiện hành

Cập nhật ngày 12/11/2026, Asia/Saigon. Mỗi phiên đọc AGENTS.md, README.md, SESSION_LOG.md và docs/chat/README.md; kiểm lại Git và runtime trước thao tác. Lịch sử bộ nhớ trước khi rút gọn giữ cục bộ trong [bản chụp](chat/2026-11-12-project-memory-before-review-release.md). Giữ nguyên SESSION_LOG.

## Công việc đang chốt

Người dùng yêu cầu triển khai [báo cáo rà soát](PROJECT_REVIEW_2026-11-12.md) và cập nhật **5bmath.vn**; xác nhận chưa có VPS và muốn tiếp tục Cloudflare. Đã hoàn tất OAuth Workers/Pages/D1. Đây là ủy quyền sửa, kiểm thử, commit/push và phát hành. Không mua gói trả phí hoặc tự bật nhận tiền thật khi chưa liên kết SePay.

Các sửa đã hoàn tất: tiến độ bài công khai đúng chủ; ví dụ/video quản trị; hoạt động ngày Việt Nam; tách đọc/ghi và băm mật khẩu ngoài writer; ngân hàng riêng từng DB; Arena published/versioned; tải mã theo trang/linh vật; manifest chung; HTML dựng sẵn cho Python; backup/restore, tệp riêng và CI chờ cùng SHA. Xem [bảng triển khai](REVIEW_IMPLEMENTATION_2026-11-12.md), [backend Cloudflare](CLOUDFLARE_BACKEND.md), [bản ghi cùng chat](chat/2026-11-12-huong-dan-thanh-toan-tu-dong.md).

**Chưa phát hành production tại mốc này:** Worker chính `5bmath-api` chưa tạo, 5bmath.vn vẫn bản công khai cũ. Còn commit/push/CI và chuyển dữ liệu cuối trước deploy chính thức. Phải chụp lại dữ liệu sau khi tạm dừng ghi localhost; người dùng vẫn đang học ở local, không dùng snapshot cũ làm dữ liệu cuối.

## Runtime đã xác minh

- Localhost được cập nhật **14:57:57 ngày 12/11** sang `mam-toan:review-20261112`, image **sha256:cf3d89cf3bc2b29eb9aa36b2642cf80d6ce65986efcd5f8e97f415a237b44bbe**, healthy. Giữ volume **mam-toan_demo-db** và LAN **192.168.1.14:8765** qua compose.override.yaml. Health/phiên vô danh/grade10/robots đạt; ngân hàng đã cấu hình, **SePay=0**.
- Backup trước/sau và rehearsal độc lập đạt integrity/FK. Bảo toàn 69 bảng cũ/không mất hàng; chỉ rút trạng thái câu đã lộ. Có thêm tiến độ học và đóng interval từ heartbeat hợp lệ trong lúc dịch vụ đang chạy. Tài khoản vẫn30; migration18→19; thêm2bài công khai,960câu riêng/marker và bảng chunk. Tệp `work/review-implementation-20261112/primary-migration-report.json` ghi rõ ngoại lệ hoạt động, không gọi mọi giá trị live là bất biến.
- Preview https://review-20261112.5bmath.pages.dev dùng Worker `5bmath-api-preview`/tenant riêng. Import/export71bảng tổng hợp đã khớp từng giá trị. Browser4luồng/6viewport/noJS đạt; admin hash CPython cũ login200/Securecookie, wall3.5s. Remote9/9kiểmtra HMAC/VIP/referral/tuition/chốngtrùng đã đạt với ngân hàng giả toàn số0, không gọi ngân hàng hoặc SePay thật.
- **Đã tắt lại preview:** version **caa2b84f-102f-4cb1-9849-34906a36dd24**, `TRANSFER_ENABLED=false`, SePay=0; GETadminreceipts xác nhận automationEnabled=false. Không còn chế độ nhận tiền thử đang bật.
- D1 `5bmath-demo` là hệ dữ liệu mẫu riêng. Python/Docker local và Cloudflare là hai DB độc lập; sau cutover, dùng website chính để học/đối soát. Không có đồng bộ hai chiều tự động.

## Kiểm thử và tính tái tạo

Root Windows **228/228,385.682s**; checkout sạch **228/228,386.837s**. Image dựng từ checkout sạch đạt **228/228,124.076s**. Cloudflareunit **13/13**, gồm52vector PBKDF; đối chiếu HMAC độc lập100ca đạt. Nativeworkerd **7nhóm+9financialassertions**,79.249s, gồm rollback nhập lỗi, file10MB và phòng Arena/answer history sau restart. Browser HTTPS preview4luồng/sáuviewport đạt. Chưa thử điện thoại vật lý.

Checkout sạch đã tự cài36dependency đúng lockfile, không dùng parentnode_modules; Node47syntax/83nickname/13theme/bankboundary và hai build SEO8trang đều đạt. SDK1.9.6 đóng gói theo allowlist; không lẫn env/DB/work/vendor vào Git. Evidence `work/review-implementation-20261112/clean-summary.log`, `work/worker-runtime-qa-iky6q7yz/report.json`, `remote-financial-result.json`, `browser-preview-final.log`.

Cloudflare thật giới hạn Web Crypto PBKDF100k nhưng localworkerd không áp cùng giới hạn. SHA256>100k dùng PBKDF2 với context SHA256 gốc, giữ600k/salt/hash cũ; không giảm iterations/reset mật khẩu hoặc thêm dependency. Local đo1.3–1.4s, remote đăng nhập cũ đã đạt. Chẩn đoán chỉ log mã/type/frames, không message hay đầu vào.

Cloudflare BIC1010 với Python mặc định đã xử lý bằng User-Agent nhận diện đúng ứng dụng `5BMath-Operator/1.0` theo tài liệu chính thức, không tắt BIC/đổi DNS/giả trình duyệt. Automaticreview từng chặn tạo thêm tệp plaintext chứa bản sao operator token; thao tác không chạy. CLI nay đọc trực tiếp JSONsecrets đã dùng để deploy, không tạo bản sao khóa. Không còn phê duyệt bị chặn.

## Giao diện và quyết định cần giữ

- Thương hiệu **5BMath**, logo02BútSáp; Vườn Toán và **04 — Vườn Khám Phá mặc định**. Tài khoản có năm phong cách, lưu theo học sinh và không đổi DOM bài đang làm. Giữ các cập nhật từ chat UI, không lùi từ snapshot cũ.
- Chat UI đã sửa bốn mẫu01/02/03/05 lúc **14:42**. CSS hiện hành **0604aec4a859fe380ab8d1368837ca6561ddeb53e7ea8ae15562a681c590367a**, ba ảnh `frontend/theme-art/clay-*.webp` tổng22.696byte; sourcePNG/prompt nằm riêng design. Index, checkout sạch và image mới đã xác minh giữ đúng CSS/baảnh. Bản UI riêng trước đó là `mam-toan:four-theme-fidelity-20261112`/164b88fc…, không có backend rà soát mới. QA không thay phê duyệt mỹ thuật của người dùng. [Bản ghi UI](chat/2026-11-12-nam-phuong-an-phong-cach-ui.md).
- Ngân hàng có960instance mẫu tự biên soạn, không phải curriculum đã duyệt. Public chỉ22ví dụ offline; giữ lịch sử câu cũ và bản sửa riêng của giáo viên. Không nhập hàng loạt Learn/Exams. Toán tiểu học theo [phương pháp](PHUONG_PHAP_GIAI_TOAN_TIEU_HOC.md).
- SePay HMAC/rawbody/ledger chống trùng và settlement chung với admin; VIP đầu tiên thưởng đúng referrer, SVip giữ customer_service; học phí không thưởng VIP. Thông tin ACB và khóa ở .env ignored; tiền thật còn tắt/chưa liên kết. [PAYMENTS.md](PAYMENTS.md).
- Zoom giữ giá/điểm danh/snapshot hóa đơn, paid khóa lịch sử và thông báo đúng chủ. Tệp10MB mới dùng chunk1MB; inline cũ đọc nguyên trạng. Backup v1 payload16MiB, PITR30ngày và bản xuất độc lập được mô tả tại [BACKUPS.md](BACKUPS.md); chưa có lịch sao lưu ngoài máy mới được tạo.

## Git và bước tiếp theo

Kho F:/ChatGPT Math Project, main/343d33061d7fc9994928eab19198465e11aa39e2 trước checkpoint mới; origin https://github.com/nguyenvietanhcre-ai/5b (public), origin/main a8221fac7af8ba48b16768366d130c1e7d3403a1 là tổ tiên. Có16commit animation local trước đợt này. Index233tệp nền ứng dụng/adapter/tài liệu đã QA; chưa commit/push mới. Giữ designWIP và SKILL_CANDIDATES ngoài phạm vi; chat chi tiết, sách, env, cache, DB/backups không push.

1. Chốt tài liệu/index, commit đúng scope rồi push main. Chờ Pagesworkflow gồm checksPython/Docker/Workers cùng SHA; chạy verify-release trước production.
2. Tạo Worker chính ở trạng thái chờ import. Upload trực tiếp secrets ngân hàng/HMAC từ .env hiện có (SePay0), operator token mới riêng trong một JSON triển khai cần thiết; không sao chép token ra thêm file. Không dùng key preview cho production.
3. Tạm dừng ghi local, snapshot nhất quán cuối, nhập object trống, xuất/restore độc lập và so sánh mọi giá trị. Sau proof, đóng import và deploy Pages main cùng SHA đã đạt.
4. Kiểm public200/404/canonical/noindex/robots/sitemap/API/grade và dữ liệu. Khởi động lại local giữ volume/LAN, thông báo Cloudflare là nguồn website chính và local là bản thử riêng.
5. Cập nhật/đọc lại bốn tệp bộ nhớ với commit/CI/deploy thật; phân biệt mọi môi trường và giữ SePay thật tắt tới khi chủ ngân hàng liên kết.
