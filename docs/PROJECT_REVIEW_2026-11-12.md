# Rà soát dự án 5BMath — 12/11/2026

Phạm vi: mã nguồn và tài liệu trong `F:\ChatGPT Math Project`, bản dựng Cloudflare/GitHub, dịch vụ localhost và các phép thử riêng. Đây là báo cáo và đề xuất; chưa áp dụng sửa mã ứng dụng, thay đổi database người dùng, commit, push hoặc triển khai. Thời điểm rà soát khoảng 08:44–08:55 Asia/Saigon. Nguồn có thay đổi đồng thời từ các chat khác; các số liệu là ảnh chụp tại lúc kiểm, không thay thế việc chốt phiên bản khi phát hành.

Kết luận: ưu tiên hoàn thiện luồng học liệu và tính nhất quán dữ liệu, sau đó giảm mã tải thừa và chốt một phiên bản Git có thể tái tạo. Việc dọn thư mục tạm có ích cho vận hành nhưng đứng sau các lỗi ảnh hưởng học sinh.

## 1. Các vấn đề cần xử lý

`P1`: sửa sớm hoặc chặn phát hành chức năng liên quan. `P2`: cải thiện có tác động rõ, triển khai sau các lỗi P1. `P3`: dọn kỹ thuật ít khẩn cấp. Những giới hạn đang có chủ ý của bản demo được ghi riêng, không coi là sự cố website công khai.

| Mức | Phát hiện đã xác nhận | Ảnh hưởng | Phương án xử lý |
| --- | --- | --- | --- |
| P1 | Bài học công khai báo đã hoàn thành nhưng không lưu vào tài khoản | Đăng nhập, bấm thành công rồi tải lại mất trạng thái | Thống nhất định danh bài công khai và bài trong tài khoản; lưu qua API, chỉ báo thành công sau khi server xác nhận; đọc lại tiến độ khi khởi tạo |
| P1 | Bài mới tạo trong quản trị thiếu `example` mà giao diện bắt buộc đọc | Bài đã phát hành có thể lỗi khi học sinh mở | Chuẩn hóa schema bài học; cho nhập ví dụ hoặc render an toàn khi chưa có; thử xuyên suốt admin tạo → học sinh học |
| P1 trước dùng điểm thật | Khôi phục được đáp án ngân hàng từ JavaScript công khai | Có thể làm đúng thi/Đấu trí mà không giải; ảnh hưởng XP và xếp hạng | Tách ngân hàng chấm thi/đấu khỏi bộ offline; giữ đáp án trên server; chỉ gửi câu cần thiết, dùng phiên bản câu hỏi |
| P1 | Git HEAD chưa chứa đủ nền ứng dụng hiện tại | Checkout sạch không chạy lại được phiên bản đã kiểm | Chốt WIP đã duyệt, lưu đủ dependency theo nhóm chức năng, kiểm trên checkout sạch rồi mới phát hành |
| P1 trước triển khai Python qua HTTPS | API học sinh chặn cả Origin HTTPS đúng | POST hồ sơ/luồng ghi bị 403 sau reverse proxy | Dùng cấu hình Origin chuẩn chung cho API; cookie Secure theo môi trường; kiểm HTTPS qua proxy tin cậy |
| P2 | Arena bỏ qua trạng thái ngân hàng do admin quản lý | Câu đã rút khỏi DB vẫn xuất hiện trong trận | Thi và Arena dùng chung kho câu hỏi published/versioned; chụp phiên bản khi tạo trận |
| P2 | URL video nhập trong admin không tới giao diện học sinh | Lưu thành công nhưng vẫn chỉ thấy kịch bản/chờ quay | Nối `video_ref` vào API và UI; kiểm URL an toàn; chỉ hiện chờ khi chưa có video |
| P2 | Hoạt động học được cộng theo ngày UTC | Biểu đồ lệch ngày Việt Nam, sai khi qua nửa đêm | Chia interval theo ngày Asia/Ho_Chi_Minh khi tổng hợp; giữ nguyên timestamp nguồn |
| P2 | GET vô danh cũng mở khóa ghi SQLite | Đọc session và các tác vụ khác phải chờ writer; giảm khả năng phục vụ đồng thời | Tách giao dịch đọc/ghi, đưa hash mật khẩu ra ngoài khóa ghi; giữ kiểm tra quyền/revision và tính nguyên tử khi ghi |
| P2 | Trang chủ tải cả quản trị và toàn bộ mã linh vật | Tốn tải/parse JavaScript, CSS và observer dù chưa chơi | Tách tải theo trang; tải renderer theo linh vật được chọn; một bộ quản lý mount/destroy thay observer rải rác |
| P2 | Độ khó và mức đa dạng ngân hàng còn yếu | Nhãn mức cao chưa phản ánh yêu cầu tư duy; học sinh đoán được quy luật đáp án | Biên tập theo kỹ năng và số bước lập luận, cân bằng đáp án, tránh câu trùng giữa mức; tách nhãn demo khỏi học liệu đã duyệt |
| P2 trước đưa Python làm web công khai | Python trả khung HTML, bản tĩnh trả nội dung đầy đủ | Trải nghiệm không JavaScript và SEO khác nhau giữa các cách chạy | Dùng chung HTML dựng sẵn cho trang công khai, bổ sung JavaScript để tương tác; metadata/canonical đúng từng trang |
| P1 trước phát hành | Pages deploy không chờ toàn bộ CI | Có thể xuất bản bản tĩnh dù kiểm thử Python/API thất bại | Đặt kiểm thử làm dependency của deploy và phát hành cùng SHA đã đạt |
| P2 | CI chưa bao phủ toàn bộ JS và bộ kiểm thử trong image | Lỗi staff/renderer hoặc khác biệt môi trường có thể lọt | Tự tìm JS để kiểm cú pháp; chạy suite trong image với scratch/DB riêng; thêm ít luồng trình duyệt có giá trị |
| P1 trước vận hành dữ liệu thật | Chưa có quy trình backup/restore thường xuyên trong repo | Volume giữ dữ liệu qua rebuild nhưng chưa đủ phục hồi khi hỏng/mất máy | Backup SQLite nhất quán, lưu nhiều mốc, kiểm integrity/FK và diễn tập restore trên DB độc lập |
| P2 | Tệp cục bộ và tệp được phép công khai chưa phân ranh đầy đủ | Dễ gom nhầm cache, học liệu nguồn và artefact khi commit | Ignore `.wrangler/`, xác định rõ Learn/Exams/outputs/req; commit bằng danh sách phạm vi |
| P2 | README và bộ nhớ lặp/trái trạng thái mới | Dễ triển khai theo chỉ dẫn cũ, mỗi phiên mất thời gian đọc | Một bảng trạng thái Python/Cloudflare/GitHub; bộ nhớ hiện hành ngắn, trỏ lịch sử; giữ nguyên nhật ký cũ |
| P2/P3 | Tệp tạm, đăng ký asset và lược đồ bị lặp | Tốn ổ đĩa, nhiều điểm cần sửa khi thêm nhân vật | Manifest asset dùng chung; dọn có chọn lọc artefact dựng lại được; migration làm nguồn lược đồ chuẩn |

## 2. Bằng chứng và vị trí mã

### A. Tiến độ bài học và học liệu quản trị

- `frontend/app.js:23` bỏ lưu khi dùng backend; handler `data-complete` tại dòng 353 chỉ sửa `data.completed` trong bộ nhớ và báo thành công. Khởi tạo tại dòng 482–487 không khôi phục phần tiến độ này từ snapshot như luồng học online. Chrome fixture dùng đúng source hiện tại xác nhận: nút đổi thành **✓ Đã học xong**, có toast thành công, **không có API POST**, tải lại về **Đánh dấu đã học**. API được giả lập, không ghi DB thật. Bằng chứng: `work/project-review-20261112/frontend/report.json` và `public-lesson-390.png`.
- `backend/staff_api.py:714` tạo presentation bài mới không có `example`; `backend/platform_api.py:401` đưa payload đó tới học sinh. `frontend/learning.js:285` lấy `lesson.example`, dòng 288 đọc `example.text`/`steps`. Probe tạo bài trong DB QA xác nhận payload thiếu; Chrome dùng payload này phát sinh **Cannot read properties of undefined (reading 'text')**. Bằng chứng: `backend/admin-created-lesson-api.json`, `frontend/report.json.adminCreatedLesson` và `frontend/admin-lesson-crash-390.png` trong thư mục QA. Không dùng trường ví dụ giả để âm thầm che học liệu còn thiếu.
- `backend/staff_api.py:709` có nhận/lưu `video_ref`, nhưng SELECT bài học tại `backend/platform_api.py:401` không đưa trường đó vào API; `frontend/learning.js:288`/`:1402` vẫn xử lý kịch bản demo. Probe xác nhận URL có trong DB QA nhưng không có trong dữ liệu học sinh.

### B. Ngân hàng câu hỏi, độ khó và công bằng

- `scripts/export-learning-catalog.cjs:5` tạo catalog server trực tiếp từ `frontend/learning-content.js`, trong khi `frontend/index.html:28` công khai mô-đun đó. Đã khôi phục đủ **960/960 bản ghi câu hỏi** chỉ từ JavaScript frontend. Dùng dữ liệu khôi phục để gọi API ở DB QA đạt **10/10** và thắng Arena sau năm câu, được **+2 XP**. Bằng chứng: `work/project-review-20261112/backend/answer-recovery-evidence.json`. Đây là kiểm chứng giới hạn bản demo, không phải cáo buộc có người đã gian lận.
- `backend/arena.py:206` đọc `learning-catalog.json`; đề luyện lấy câu published từ DB tại `backend/platform_api.py:362`. Sau khi ngừng phát hành toàn bộ câu trong DB QA, DB có **0 câu published**, Arena vẫn tạo **20 câu**. Cần thống nhất nguồn vận hành trước khi admin bắt đầu biên tập thật.
- Catalog có **20 bài/960 ID câu**, nhưng chỉ **784 cặp khối + đề bài khác nhau**; **80 đề bài xuất hiện ở nhiều mức độ**. Riêng khối 5 so sánh thập phân có 48 ID, chỉ 12 đề và toàn bộ đáp án **`>`**. Các chủ đề `4-fraction`, `5-fraction`, `5-percent`, `5-decimal` giữ nguyên câu khi đổi cả bốn mức. Nguồn: `frontend/learning-content.js:126`–`:145`. Số ID không nên dùng để khẳng định số câu độc lập hoặc độ phủ chương trình.
- Hướng biên tập: xác định kỹ năng, điều kiện tiên quyết, yêu cầu giải thích và ví dụ đủ dữ kiện; áp dụng `docs/PHUONG_PHAP_GIAI_TOAN_TIEU_HOC.md`, đối chiếu trang nguồn khi dùng Learn. Giữ đề/sách gốc; không tự nhập hàng loạt bộ Exams chưa duyệt vào ngân hàng đang chạy.

### C. Database, ngày giờ và HTTPS

- `backend/platform_api.py:70`–`:75`, `:736` và `backend/staff_api.py:845` mở `BEGIN IMMEDIATE` cho mỗi request, gồm GET session vô danh. Khi writer QA giữ khóa 0,35 giây, GET session chờ khoảng **0,44 giây**. Đây là probe cơ chế khóa, chưa phải benchmark tải thực tế. SQLite chỉ có một writer đồng thời theo [tài liệu SQLite](https://sqlite.org/lang_transaction.html).
- `backend/platform_api.py:731`–`:734` chỉ cho Origin scheme `http`. Probe với Host/Origin đúng `https://5bmath.vn`, phiên/CSRF hợp lệ vẫn trả **403**. Cookie học sinh tại `:196` có chú thích local HTTP và chưa bật Secure. Localhost HTTP hiện không mắc lỗi HTTPS này; chưa kết luận website công khai đang lỗi.
- `backend/platform_api.py:420` lấy ngày bằng `substr(started_at,1,10)` từ timestamp UTC. Phiên **00:05–00:15 ngày 12/11 Việt Nam** được trả dưới khóa **2026-11-11**, 600 giây. Cần thử thêm phiên qua ranh giới ngày và chia đúng phần thời gian của mỗi ngày.
- `backend/server.py` dùng `http.server` thư viện chuẩn; giữ phù hợp cho demo hiện tại. Khi triển khai dịch vụ thật, chọn máy chủ Python phù hợp cùng proxy HTTPS, giới hạn request, quan sát và phục hồi. [Tài liệu Python](https://docs.python.org/3/library/http.server.html) không khuyến nghị dùng `http.server` cho production. Chưa cần đổi database chỉ vì thấy một điểm nghẽn khóa có thể sửa.

### D. Tải trang, cấu trúc frontend và SEO

- `frontend/index.html:12`–`:57` khai báo **30 JavaScript + 18 CSS**, tổng **749.050 byte chưa nén**, gồm staff và renderer các linh vật. Chrome fixture ở trang chủ thấy **12 MutationObserver** được đăng ký, phần lớn theo dõi toàn body/subtree. Đây là lượng mã và observer đã đo, chưa phải kết luận FPS/Core Web Vitals trên điện thoại thật.
- Tệp lớn hiện tại: `learning.js` khoảng 164 KB/1.706 dòng; `learning.css` khoảng 76 KB/812 dòng; `staff.js` khoảng 62 KB; `app.js` khoảng 60 KB. Tách theo nghiệp vụ học, đề, phòng đấu, lớp và hồ sơ; gom lifecycle animation; thống nhất manifest cho template, server allowlist và script build. Giữ allowlist tài nguyên thay vì phục vụ tùy ý thư mục nội bộ.
- Phần dư cụ thể có thể dọn: `frontend/app.js:341` còn hàm `dashboardContent()` khoảng **3.983 byte**, chỉ có định nghĩa và không còn được tuyến gọi; tuyến dashboard đã dùng LearningApp. Tham số diagnostic database cũ còn truyền qua build/render nhưng renderer hiện không sử dụng. Xác nhận lại dependency trước khi bỏ; một số handler cũ vẫn được luồng mới dùng nên không xóa cả khối theo tuổi mã.
- Hướng tải theo nhu cầu có thể dùng [dynamic import](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/import). Mục tiêu nghiệm thu là trang công khai không tải staff/game chưa dùng, một renderer hoạt động cho mỗi nhân vật hiển thị và không phát sinh observer sau khi rời trang. Đo lại trước/sau trên điện thoại dọc/ngang.
- `backend/server.py:144`–`:158` trả `index.html` với `<main id="app"></main>`, bỏ canonical trang con và không chèn nội dung học. Bản dựng tĩnh có HTML đầy đủ và check_pages đạt. Giới hạn này cần xử lý nếu đưa Python phục vụ trang công khai; các trang tài khoản noindex vẫn có thể chạy bằng JavaScript.
- `backend/server.py:111` đặt `Cache-Control: no-store` cho cả JS/CSS/ảnh. Có thể tách cache API riêng, dùng ETag/revalidation hoặc asset có hash cho tài nguyên tĩnh; đo trên bản Python/LAN, không suy rộng thành Cloudflare đang có cùng header.

### E. Git, CI, vận hành và phần dư thừa

- Tại lúc kiểm: `main/343d33061d7fc9994928eab19198465e11aa39e2`; **95 tệp backend/frontend/tests chưa track**. Main hơn local remote-tracking `origin/main` **16 commit**; đây không phải kết quả fetch mới. Xuất đúng backend/tests từ HEAD vào QA rồi import test Cua thất bại vì thiếu `test_platform_api`, vốn chưa có trong commit. Bằng chứng: `work/project-review-20261112/ops/clean-head-import.txt`. Các commit riêng linh vật có ích nhưng chưa thay thế checkpoint toàn app.
- `.github/workflows/pages.yml:37` chỉ chờ job build trong chính workflow; không chờ `ci.yml`. `ci.yml:20` chỉ kiểm cú pháp ba JS; Docker ở dòng 38–47 kiểm ba endpoint, chưa full suite trong image. Đề xuất gắn deploy với cùng SHA đã qua các bước kiểm; thêm test hợp đồng admin → học sinh và hoàn thành bài → tải lại, thay vì chỉ tăng số test đơn vị.
- `compose.yaml:20` giữ volume; không tìm thấy quy trình backup/retention/restore định kỳ trong code, script hoặc hướng dẫn vận hành được rà. Các bản backup thủ công trong work có giá trị và phải giữ. Khi chuẩn bị dùng dữ liệu thật, cần công cụ backup nhất quán và diễn tập restore độc lập.
- `.gitignore` đã che chat chi tiết, `.env` và `work/`, nhưng chưa che `.wrangler/`; Learn/Exams/outputs/req đang hiện untracked. **Chưa phát hiện bằng chứng lộ secret**. Cần chốt danh sách được công khai trước khi gom commit vào repo public.
- `work/` khoảng **5.909 MiB/25.657 tệp**, trong đó mascot-animation khoảng **3.830 MiB**. Chỉ dọn frame/render, bản build và snapshot có thể dựng lại sau khi xác nhận release; giữ PNG nguồn, prompt, bản đã duyệt, QA quan trọng và DB backup. Không xóa theo tên giống nhau: SHA-256 **73 PDF Exams khác nhau hoàn toàn**, không có tệp byte-identical trong tập đã kiểm.
- `README.md:99` còn nói đăng nhập là bước tiếp theo, trái phần đang hoạt động ở dòng 136; dòng 160 nói chưa có quản trị giáo viên/lớp, trái dòng 150 và STAFF_PORTAL. PROJECT_MEMORY khoảng 180 KB, SESSION_LOG khoảng 162 KB, chat index khoảng 31 KB và có nhiều mô tả lịch sử dễ nhầm là hiện tại. Rút gọn bộ nhớ hiện hành về quyết định/trạng thái/chờ, chuyển người đọc tới bản ghi; **giữ lịch sử nhật ký theo AGENTS**.
- `backend/schema.sql` và `backend/migrations/0000_demo_base.sql` trùng chính xác **936 byte**; `database.py:24` chạy cả hai. Đây là dư thừa nhỏ, chưa gây lỗi dữ liệu. Migration nên là nguồn chuẩn; schema snapshot có thể sinh tự động. Thống nhất hướng dẫn bootstrap D1 đang có hai cách khác nhau.
- Các launcher ngắn START-DEMO/START-DOCKER/START-PYTHON/START-PHONE phục vụ mục đích khác nhau hoặc tương thích; không cần xóa chỉ để giảm số tệp. Giữ nguyên style Vườn Toán và các tài sản đã duyệt; việc tải thừa renderer không đồng nghĩa các nhân vật là thừa về sản phẩm.

## 3. Thứ tự triển khai đề xuất

1. **Chốt nền có thể phục hồi:** xác định các WIP được duyệt, manifest nguồn và tài sản cần giữ; checkpoint Git đầy đủ, backup/restore QA. Đơn vị nghiệm thu là checkout sạch chạy được, không chỉ workspace hiện tại chạy được.
2. **Sửa đúng luồng học:** hoàn thành bài và đọc lại tiến độ; admin tạo bài có ví dụ/video; lịch hoạt động theo Việt Nam; Arena và đề dùng chung nguồn câu hỏi. Thêm ít kiểm thử xuyên suốt các luồng vừa tái hiện.
3. **Chuẩn bị dùng điểm và phát hành thật:** ngân hàng server riêng, biên tập lại mức độ/đáp án; Origin/cookie HTTPS; deploy chờ CI; phân biệt rõ Python, Cloudflare và GitHub static.
4. **Tối ưu rồi dọn:** tải module theo trang/nhân vật, giảm observer, tách giao dịch đọc/ghi và cache asset; đo lại kết quả. Sau đó dọn work có manifest, gom đăng ký asset và sửa tài liệu lỗi thời.

Mỗi đợt nên là một nhóm thay đổi có thể kiểm và hoàn tác; giữ đầy đủ chức năng trên điện thoại, máy tính bảng và máy tính. Chưa đề xuất đổi framework/database hoặc thay toàn bộ giao diện khi các điểm trên còn giải quyết được theo phạm vi nhỏ.

## 4. Kiểm tra thực tế và giới hạn

- Toàn bộ JS trực tiếp dưới `frontend/`, `build-pages.cjs` và `pages-worker.mjs`: kiểm cú pháp đạt; nickname JavaScript **83 trường hợp đạt**.
- Bản Cloudflare và GitHub: dựng thành công, **check_pages đạt tám trang công khai/URL canonical/404** cho đúng từng target. Lượt gọi checker GitHub đầu dùng sai target, đã gọi lại đúng và đạt; không tính lỗi lệnh công cụ là lỗi sản phẩm.
- Compose config hợp lệ. Đầu audit container dùng `mam-toan:password-min6-20261112`; chat khác cập nhật PA3 trong lúc audit. Đọc lại khoảng **08:53 Asia/Saigon**: container `5c1684a1e4cb`, alias image **mam-toan:local**, trạng thái **healthy**, localhost và LAN **192.168.1.14:8765** vẫn hiện. Health/trang chủ/Đấu trí trả 200, URL lạ/README trả 404. Audit chỉ đọc trạng thái, không build/recreate container; không quy lần triển khai đồng thời cho phiên rà soát này.
- HTTP localhost: health, trang chủ, bài học, Đấu trí, giáo viên/quản trị và ba JS trả **200**; URL lạ và README nội bộ trả **404**. Không đăng nhập hoặc tạo QA vào DB thật.
- Các probe backend dùng SQLite mới hoàn toàn trong work; Chrome fixture dùng source thật nhưng API giả lập. Không gọi fixture là E2E backend thật. Không đo thiết bị vật lý, tải thực tế hoặc Core Web Vitals.
- Python Windows 3.12.14: **127/127 đạt, 199,798 giây**, log `python-tests-elevated.log`. Lượt đầu chạy sandbox vướng WinError 10013 tại HTTP tests (**127 chạy, tám lỗi**, 202,404 giây), không được tính là lỗi ứng dụng đã xác nhận; đã chạy lại với quyền loopback và đạt. Các lỗi hợp đồng được probe riêng ở trên vẫn tồn tại dù suite hiện có đạt.
- Chưa chạy full suite trong Docker, chưa kiểm CI từ xa và chưa xác minh website công khai; công cụ đọc `5bmath.vn` không truy cập được trong lượt này. Không suy ra website công khai đang lỗi hoặc trùng localhost.
- Bằng chứng cục bộ: `work/project-review-20261112/`; danh sách SHA-256 nguồn: `source-hashes.json`. Các DB/probe/chi tiết kỹ thuật thử nghiệm giữ cục bộ, không đưa vào repo public.
