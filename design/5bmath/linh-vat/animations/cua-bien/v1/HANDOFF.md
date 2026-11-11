# Bàn giao Cua biển / v1

- Chủ phiên: cua-bien-01a1cb4d
- Trạng thái: awaiting_assets
- Đã có: brief, prompt, cấu hình, template xem thử.
- Còn thiếu: source/poses.png do imagegen tạo từ đúng ảnh tham chiếu.
- Chưa được người dùng duyệt hoặc đưa vào game.
- Bước tiếp: tạo sheet alpha 4×4 → prepare → kiểm ảnh/timeline → export → gửi duyệt.
- Trước khi đổi chat: ghi tệp đang sửa, kết quả kiểm và việc còn chờ; release rồi chat mới claim.

## Cập nhật 11/11/2026 — đã tạo và kiểm bộ Cua

- Chỉ đạo mới của người dùng cho phép tích hợp game/commit/local cho Cua;quy tắc demo ban đầu phía trên chỉ là trạng thái lúc init. Không suy ra cho phép push/phát hành.
- Đã tạo16pose bằng built-in imagegen,đúng ảnh cua hàng2cột2/stylegốc. Bảnđầu sát ô được giữ `source/poses-spacing-v1.png`;bản sửa padding ở `source/poses.png`,WebP298234byte;16ôalpha khôngcắt,đủ2càng+8chân.
- `animation.js`,config/demo,poses,assets vàexports trong job riêng. Bốnmode ultimate/attack/hit/defeat;chiêucuối3s/90frames;tên0.65trướcđòn0.95,tácđộng1.75,thắng1.90.
- Export GIF2195277byte/MP41974402byte,poster/contact vàqa-reportđạt. Demo5viewport/4mode/controls/reducedmotion/seek/0.5×đạt. Runtimegame9checks/5viewport,lazyload/cleanupđạt;chưađođiệnthoạithật.
- Tíchhợp `frontend/arena-crab-animation.js/.css`,ảnhgame `frontend/arena-art/cua-bien-poses.webp`;tài khoảncrab. `INTEGRATION.patch`ghihookCua trong5tệpnềnđangsửachung,chỉcommitscopedkhôngkèmtoànbộWIPchatkhác.
- QAserver8797/databaseQAriêng;test1ca Cuađạt,fullPython/Docker/localfinalđangkiểm tại thờiđiểmghi mục này. Kếtquả cuối sẽ nối dưới vàbộnhớ dựán.
- Giữ pending_review,chưa tựapproved. Nếu chuyểnowner,dùngrelease/claim theo workshop;khôngxóa lock của chat khác.

## Kết quả kiểm tra và triển khai local

- Bộ kiểm thử đầy đủ: 75 bài trên Windows và 77 bài trong image `5bmath-crab:local` đạt. Docker dùng vùng tạm `/tmp` và `/work`, không ghi vào database thật.
- Hai bản dựng Cloudflare/GitHub đạt kiểm tra SEO, mỗi bản có tám trang công khai. Không phát hành hai bản dựng này.
- Đã cập nhật container local bằng image đã kiểm, giữ loopback 8765, LAN 192.168.1.2 và volume `mam-toan_demo-db`; `review_upgrades=0`.
- HTTP trang Linh vật, JS/CSS/WebP Cua và health trả 200; ba tài nguyên Cua khớp SHA-256 nguồn; đề mẫu đạt 10/10.
- Database trước/sau: integrity `ok`, không lỗi khóa ngoại; giữ đủ ID của 27 tài khoản, 27 học sinh và 22 companion. Catalog có đúng một Cua biển. Bản sao ở `work/mascot-animation/cua-bien/v1/db-before.sqlite3` và `db-after.sqlite3`.
- UI file thực tế đã đạt chọn/lưu Cua, bắt đầu bot, đánh/chiêu cuối/chịu đòn/thua; chuyển kết quả sau 3.308 giây. HTTP đang được xác minh thêm trên container QA riêng 8798, database tạm.
- Bản vá `INTEGRATION.patch` đã kiểm bằng `git apply --reverse --check` trên checkout hiện tại. Các tệp nền vẫn thuộc công việc chung chưa commit; không gom chúng vào commit Cua.

## Bản local cuối và hồi quy gián đoạn

- Đã sửa dọn hiệu ứng khi stop/resize/ẩn tab/xóa nhân vật/phát lại; chỉ dọn trạng thái do Cua sở hữu, giữ hiệu ứng của module khác. Bảy ca kiểm riêng và regression độc lập năm viewport đạt.
- Tên chiêu ở phía trên sân, z-index cao hơn Canvas, không bị Cua che. Mã cuối JS 20.403 byte, CSS 1.744 byte, WebP 298.234 byte đã phục vụ 200 và khớp SHA nguồn trên localhost8765.
- Đã rebuild/deploy lại image cuối và chạy lại hai build/SEO tám trang; backend giữ nguyên so với image đã đạt 77 tests. Container QA8798 dùng cùng image/database tạm để kiểm UI cuối.
- Owner đã release, trạng thái `pending_review`; artwork chưa tự duyệt. Chat nhận đọc bản ghi và dùng claim owner mới nếu sửa tiếp.

- UI HTTP và fixture HTTP của image cuối trên QA8798 đạt đủ luồng, năm viewport và dọn sau resize/stop; thời gian chiêu đến kết quả3,558s. Đã mở xem tên chiêu trước đòn/tại tác động, không bị Cua che; không lỗi JS/console/resource.
- Bản vá cuối dùng zero-context để giữ `git diff --check` sạch; kiểm bằng `git apply --unidiff-zero --reverse --check` từ gốc dự án. Không tự áp dụng lần nữa khi hook đã có.
