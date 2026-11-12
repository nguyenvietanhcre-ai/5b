# Mầm Toán — Python / GitHub / Docker

Website tiếng Việt của 5BMath, có bài đọc công khai và khu vực học sinh lớp 1–5. Học liệu và ngân hàng mẫu được gắn nhãn, chưa thay cho chương trình/đề chính thức đã duyệt.
Tất cả tệp dự án đặt tại F:\ChatGPT Math Project.

## Trạng thái và nguồn dữ liệu

| Thành phần | Cách chạy và dữ liệu |
|---|---|
| Python/Docker cục bộ | API tài khoản, học tập, Zoom và VIP dùng SQLite riêng; volume Docker giữ dữ liệu qua các lần dựng lại image. |
| Cloudflare Pages | HTML công khai dựng sẵn, CSS/JS/ảnh; bản `cloudflare-live` gọi binding `BACKEND` cùng Origin. |
| Python Workers + Durable Object | API tài khoản, học tập, Zoom và VIP trên `5bmath.vn`; SQLite bền vững tách theo trường. Đã chuyển dữ liệu và đối chiếu bản xuất độc lập ngày 12/11/2026. |
| D1 `5bmath-demo` | Chỉ API mẫu `/api/database-demo`; tách khỏi database tài khoản |
| GitHub Pages và bản mở tệp | Trải nghiệm offline/trình duyệt, không tạo tài khoản thật hoặc xác nhận thanh toán |

Trạng thái phát hành và bằng chứng của đợt hiện tại: [triển khai rà soát](docs/REVIEW_IMPLEMENTATION_2026-11-12.md). Không suy ra backend đã chạy chỉ từ việc upload giao diện. [Thanh toán](docs/PAYMENTS.md), [sao lưu và phục hồi](docs/BACKUPS.md), [API](docs/LOCAL_API.md).

## Chạy bằng Python
Cần Python 3.12 trở lên. Bản hiện tại không cần cài thư viện ngoài.

    python -m backend --host 127.0.0.1 --port 8765

Mở http://127.0.0.1:8765. Trên Windows có thể chạy START-PYTHON.cmd. Launcher kiểm tra Python 3.12 trở lên trong môi trường ảo, runtime Codex hoặc PATH, kể cả Python cài từ Microsoft Store. Đã chạy thử với Python 3.13.14 trên Windows ngày 08/11/2026.
Nếu Docker đang dùng cổng 8765, dừng Docker bằng STOP-DOCKER.cmd trước khi chạy START-PYTHON.cmd, hoặc chạy PowerShell với lệnh dưới đây để dùng cổng riêng. Dừng Python bằng Ctrl+C.

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start-demo.ps1 -Port 8766
Có thể xem giao diện offline bằng frontend/index.html; khi đó việc chấm điểm chạy tại trình duyệt.

## Chạy bằng Docker (mặc định trên máy này)
Docker Desktop cần đang mở và Linux containers đang chạy.
Ngày 08/11/2026 đã dựng lại và kiểm tra bản demo sau khi cài lại Windows 11 Pro. Máy dùng Docker Engine 29.9.2 và Compose v5.6.1.

- Nhấp đôi **START-DEMO.cmd** hoặc **START-DOCKER.cmd** để build/cập nhật image và chạy nền.
- Dùng **START-PHONE.cmd** để bật thử trên điện thoại cùng mạng LAN. Sau khi bật, các lần chạy START-DEMO/START-DOCKER tiếp tục giữ địa chỉ LAN.
- Mở **http://localhost:8765/**.
- Nhấp đôi **STOP-DOCKER.cmd** để dừng website. Docker Desktop vẫn hoạt động.
- Docker Desktop hiển thị nhóm **mam-toan**, dịch vụ **web**.
- Đóng cửa sổ chạy không dừng container.

Sau khi khởi động lại Windows, đăng nhập và đợi Docker Desktop khởi động xong rồi mở [localhost:8765](http://localhost:8765/). Máy này đã bật **Start Docker Desktop when you sign in** trong Docker Desktop và **Docker Desktop Launcher** trong **Settings → Apps → Startup**. Docker tự khởi động lại container đã chạy trước đó theo cấu hình Compose. Nếu đã chủ động dừng bằng `STOP-DOCKER.cmd`, chạy `START-DEMO.cmd` để mở lại.

Lệnh tương đương:

    docker compose up --build --wait --wait-timeout 120
    docker compose ps
    docker compose logs --tail 100 web
    docker compose stop web

PowerShell hỗ trợ đổi cổng hoặc xem trạng thái:

    .\docker-demo.ps1 -Port 8767
    .\docker-demo.ps1 -Action Status
    .\docker-demo.ps1 -Action Logs

Lệnh dừng bằng script:

    .\docker-demo.ps1 -Action Stop

Mặc định map 127.0.0.1:8765 vào cổng 8000 trong container. Có thể dùng biến MAM_TOAN_PORT khi chạy Compose trực tiếp.
Nếu cổng bị chiếm bởi bản Python, dừng đúng máy chủ Python hoặc chọn cổng khác. Script không tự dừng tiến trình lạ.
Image chạy với UID 65532, filesystem chỉ đọc, chứa mã ứng dụng và script vận hành; nhật ký container được giới hạn dung lượng.
Khi sửa mã nguồn, chạy START-DOCKER.cmd lại để build/cập nhật. Docker không tự đồng bộ sửa mã vào container.
Tại localhost, tài khoản và tiến độ học/thi được lưu trong SQLite ở volume `demo-db`. Mở Góc học tập để đăng ký/đăng nhập. Bản static/offline vẫn dùng hồ sơ trải nghiệm trong trình duyệt. Xem [hướng dẫn duyệt và hợp đồng API](docs/LOCAL_API.md).

### Thử trên điện thoại qua mạng nội bộ

Điện thoại kết nối Wi-Fi cùng mạng LAN với máy tính; máy tính có thể dùng dây mạng. Bật Docker Desktop rồi nhấp đôi **START-PHONE.cmd**, hoặc chạy PowerShell trong thư mục dự án:

    .\docker-demo.ps1 -Lan

Launcher tự tìm IPv4 LAN hiện tại, giữ `http://localhost:8765/` và in địa chỉ để mở trên điện thoại. Ngày 12/11/2026, máy này dùng **http://192.168.1.14:8765/goc-hoc-tap/**. Trên điện thoại, `localhost` chỉ chính điện thoại; hãy dùng địa chỉ IP máy tính được launcher in ra. Bản LAN và localhost dùng cùng container, cùng volume database; điện thoại cần đăng nhập lại vì cookie theo địa chỉ truy cập. Giữ máy tính bật trong lúc thử.

Cấu hình được lưu trong `compose.override.yaml` riêng của máy và loại khỏi Git. START-DEMO/START-DOCKER tự cập nhật IP trong tệp do launcher quản lý khi DHCP đổi địa chỉ; `docker compose up` mặc định cũng đọc tệp này nhưng không tự dò IP mới. Nếu có nhiều adapter LAN, chọn bằng `.\docker-demo.ps1 -Lan -LanIP 192.168.1.14`. Launcher giữ nguyên tệp override tự viết của người dùng. Khi dùng lệnh có `-f` tường minh để cập nhật image, thêm `-f compose.override.yaml` để giữ LAN.

Firewall Windows cần cho phép TCP 8765 tới đúng IPv4, chỉ từ subnet LAN và trên đúng adapter. Nếu IP thay đổi hoặc firewall chưa được bật, mở PowerShell bằng **Run as administrator** và chạy (thay IP bằng địa chỉ launcher vừa in):

    .\scripts\enable-phone-firewall.ps1 -LanIP 192.168.1.14 -Port 8765

Script chỉ tạo/cập nhật luật `5BMath-LAN-8765`, không tắt firewall hay đổi mạng Windows. Nếu Wi-Fi khách bật cách ly thiết bị, dùng Wi-Fi chính. Không cần mở cổng router. Muốn trở về chỉ phục vụ localhost lâu dài, đổi tên `compose.override.yaml` thành `work/compose.override.disabled.yaml`, rồi chạy `docker compose -f compose.yaml up --wait --wait-timeout 120`. Để bật lại, dùng START-PHONE.cmd. `compose.lan.yaml` vẫn dành cho cấu hình LAN thủ công qua biến `MAM_TOAN_LAN_IP`.

Kiểm thử trong đúng image (chạy tại thư mục gốc dự án trên Windows):

    docker compose -f compose.yaml -f compose.test.yaml run --rm --no-deps -T web python -m unittest discover -s tests -v

Ngày 08/11/2026, container healthy, trang chủ/JS/CSS/health trả về HTTP 200, đề mẫu đạt 10/10 và 10 kiểm thử Python đều đạt trong image lẫn trên Windows. Kiểm tra cú pháp JavaScript cũng đạt.
Nguồn cách dùng Compose: https://docs.docker.com/reference/cli/docker/compose/up/

## Kiểm tra

    python -m unittest discover -s tests -v
    npm ci --ignore-scripts --no-audit --no-fund
    npm run check:js
    node tests/test_nickname_policy.cjs
    node tests/test_themes.cjs
    node tests/test_bank_boundary.cjs
    node scripts/check-prerender.cjs

Python phục vụ giao diện và chấm bài qua POST /api/grade; GET /api/health báo backend đang chạy.
Chỉ các tệp giao diện trong danh sách cho phép được phục vụ. README, .git và tài liệu nội bộ không công khai.

## Demo cơ sở dữ liệu

Mở **Góc học tập → Kiểm tra kết nối**, rồi chọn **Xem 5 ví dụ mẫu**. Hai API `GET /api/database-demo` và `GET /api/database-demo/samples` đọc số đề đã phát hành và dữ liệu giả dùng để kiểm thử. Bản mẫu có năm tài khoản, các tình huống thưởng VIP và năm bài toán có công thức, hình ảnh, lời giải.

- Python trực tiếp dùng `work/database/5bmath-demo.sqlite3`. Có thể chỉ định tệp khác bằng `--database`.
- Docker giữ tệp trong volume `demo-db` qua các lần dựng lại container.
- Cloudflare Pages dùng D1 cho API. GitHub Pages và bản mở trực tiếp từ tệp giữ chế độ tĩnh.

Python tự áp dụng migration trong `backend/migrations/` khi khởi động. Có thể tạo database và dữ liệu giả cục bộ bằng lệnh dưới đây.

    python -m backend.demo_seed

Trong Docker dùng `docker compose exec -T web python -m backend.demo_seed --database /data/5bmath-demo.sqlite3`.
Để đưa lược đồ lên D1, dùng `wrangler d1 migrations apply 5bmath-demo --remote`. Xuất seed bằng `python -m backend.demo_seed --export-sql work/demo-seed.sql` rồi dùng `wrangler d1 execute 5bmath-demo --remote --file work/demo-seed.sql`. Dữ liệu mẫu có mã `DEMO-` và được gắn nhãn rõ trên giao diện.

Các bảng dùng cho tài khoản, học liệu, đề, đấu trí, tiến độ, thưởng và thông báo nằm trong các migration. `backend/membership.py` ghi sự kiện nâng cấp VIP đã xác nhận; `backend/payments.py` xử lý đơn và webhook SePay có chữ ký. Database cộng tháng lịch theo giờ Việt Nam, chặn thưởng trùng và ghi thông báo trong cùng giao dịch. Đăng ký/đăng nhập và thanh toán dùng backend Python; xem [cấu hình thanh toán](docs/PAYMENTS.md).

Nội dung dạng khối lưu LaTeX, MathML và tham chiếu ảnh. `media_assets` chứa đường dẫn, kích thước và mô tả ảnh. Màn hình mẫu dùng MathML của trình duyệt, ảnh có kích thước sẵn và tải trì hoãn. Các chỉ mục hỗ trợ lọc câu theo khối/chuyên đề, lịch sử đề, hộp thông báo và các số liệu xếp hạng.

## GitHub
[Mở 5BMath](https://5bmath.vn/) trên điện thoại, máy tính bảng hoặc máy tính. Tên miền chính dùng Cloudflare Pages Free. [Bản GitHub Pages](https://nguyenvietanhcre-ai.github.io/5b/) là bản thử.
`.github/workflows/pages.yml` tạo và kiểm tra bản tĩnh từ `frontend/`. Bản Pages chấm bài bằng JavaScript và lưu hồ sơ mẫu trong trình duyệt. Khi chạy bằng Python hoặc Docker, giao diện dùng API Python.
`.github/workflows/ci.yml` được Pages gọi cho cùng SHA: kiểm Python 3.12/3.13, toàn bộ JavaScript, ranh giới ngân hàng offline, HTML/SEO của hai bản dựng, toàn bộ kiểm thử trong image và các luồng Chrome với database dùng một lần. `pages.yml` chỉ dựng và triển khai sau khi checks đạt.

Trước khi phát hành lên Cloudflare production, chạy `node scripts/verify-release.cjs --sha SHA_DA_PUSH` để kiểm HEAD, `origin/main`, thay đổi mã nguồn chưa commit và Actions cùng SHA. Script sẽ chặn khi có lỗi hoặc CI còn đang chạy.
Kho đích đã xác nhận: https://github.com/nguyenvietanhcre-ai/5b (public).
Lịch sử phát hành cũ nằm trong SESSION_LOG; chỉ dùng kết quả CI và deployment gắn đúng SHA của đợt đang phát hành để nghiệm thu.
Trong GitHub Desktop, mở kho cục bộ ở F:\ChatGPT Math Project. Nếu ứng dụng đang hiển thị bản sao 5b ở Documents\GitHub\5b, dùng File → Add local repository để thêm đúng thư mục trên ổ F. Xem thay đổi, commit các tệp cần thiết, rồi push lên origin khi có yêu cầu.

## SEO và phát hành tên miền chính

1. Khi thêm học liệu công khai, viết nội dung phục vụ học sinh hoặc phụ huynh. Dùng URL riêng, liên kết mô tả rõ đích đến, tiêu đề trang và mô tả riêng, tiêu đề chính phản ánh nội dung. Kiểm tra nội dung chính và liên kết trên điện thoại lẫn máy tính. [Google Search Essentials](https://developers.google.com/search/docs/essentials)
2. Khai báo trang mới trong danh mục `pages` của `frontend/app.js` và đường dẫn tương ứng trong `backend/server.py`. HTML của bản tĩnh và Python được dựng từ cùng `pages.render` của ứng dụng. Bản Python đã dựng nằm tại `frontend/public-pages/`; Docker tự dựng lại trong stage Node. Khi sửa nội dung công khai, dựng target `python` vào thư mục mới, thay đúng phần HTML được tạo và chạy `node scripts/check-prerender.cjs` để tránh mã nguồn/HTML lệch nhau. Mỗi trang công khai khai báo canonical trên `https://5bmath.vn/`. Giữ URL cũ hoạt động khi đổi đường dẫn và loại màn hình tài khoản, trang lỗi khỏi sitemap. [Hướng dẫn JavaScript SEO](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
3. Dựng bản Cloudflare vào thư mục mới hoặc trống trong `work/`, sau đó kiểm tra URL, HTML, sitemap và liên kết.

       node scripts/build-pages.cjs work/pages-release
       python -m scripts.check_pages work/pages-release

4. Bản Cloudflare chứa `_worker.js` và `_routes.json` cho API thử. `wrangler.toml` liên kết dự án Pages `5bmath` với D1 `5bmath-demo` qua binding `DB`. Khi khởi tạo D1 mới, áp dụng lược đồ bằng `wrangler d1 migrations apply 5bmath-demo --remote`. Sau khi kiểm tra bản xem trước, dùng `wrangler pages deploy work/pages-release --project-name 5bmath --branch main` cho production. Kiểm tra API, các trang công khai trả 200, URL sai trả 404, `robots.txt`, sitemap, giao diện di động và luồng chấm bài. [Hướng dẫn Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/), [Binding D1](https://developers.cloudflare.com/pages/functions/bindings/#d1-databases)
5. Sau khi bản mới đã chạy, xác minh quyền sở hữu `5bmath.vn` trong Google Search Console, gửi `https://5bmath.vn/sitemap.xml` và dùng Kiểm tra URL cho trang chủ cùng bài học đại diện. Theo dõi lỗi lập chỉ mục và Core Web Vitals khi có dữ liệu. [Hướng dẫn gửi sitemap](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)

## Bộ nhớ cho phiên sau
AGENTS.md bắt buộc mọi phiên đọc docs/PROJECT_MEMORY.md, docs/SESSION_LOG.md và docs/chat/README.md lúc bắt đầu.
Trước khi kết thúc mỗi đợt công việc phải cập nhật bộ nhớ hiện hành, nhật ký và bản ghi phiên tương ứng, không chờ nhắc.
Bản ghi đầy đủ cuộc chat khởi tạo: docs/chat/2026-11-06-initial-project.md và JSON đồng hành, lưu cục bộ trong dự án. Bản ghi chi tiết không tự đưa lên GitHub công khai.
Skill [mam-toan-release](.agents/skills/mam-toan-release/SKILL.md) dùng để kiểm tra bản mới, khôi phục localhost và chuẩn bị cập nhật GitHub. Gọi `$mam-toan-release` trong chat Codex mở tại thư mục dự án. Xem [trạng thái các skill](docs/SKILL_CANDIDATES.md).

## Chức năng demo
Giao diện Vườn Toán dùng xuyên suốt trang chủ, bài học, luyện tập, luyện thi, trò chơi và lớp học mẫu. Nền kem, nút xanh lá, điểm nhấn cam mơ và thẻ bo góc dùng chung kiểu trong `frontend/styles.css`. Trang chủ có linh vật mầm cây tự vẽ và lối vào Bài học, Luyện thi, Trò chơi.

Bản demo có bộ lọc bài học, hai bài đọc, bài luyện bốn câu, đề năm câu/15 phút, trò chơi ba vòng, tiến độ lưu trong trình duyệt, tải phiếu TXT, nộp bài minh họa, kịch bản video và buổi Zoom/Meet mẫu.

## Góc học tập hiện tại

### Giao diện theo sở thích

Các mẫu01/02/03/05 cũng đã được hiệu chỉnh theo ảnh tham chiếu: Sương Mai thoáng/mint, Bút Sáp giấy/viền sáp, Mầm Sách 3D khung mềm và icon đất sét, Sổ Tay ô ly/marker/thẻ đánh số. Ảnh chạy thật và biên bản kiểm tra tại work/theme-four-fidelity-20261112/; mẫu04 tiếp tục là mặc định.

Mẫu04 đã được chỉnh bám ảnh duyệt: khung xanh đậm và lá góc, icon sách/bút/mầm minh họa, đường nối thẻ, nút xanh–cam, nền vườn và khung Mẹo học tốt. Trên điện thoại, hai nút banner xếp dọc rộng toàn khung; giữ tiến độ thật và đầy đủ chức năng.

Mặc định dùng **04 — Vườn Khám Phá**. Vào **Tài khoản → Giao diện của em** để chọn Vườn Sương Mai, Xưởng Bút Sáp, Mầm Sách 3D, Vườn Khám Phá hoặc Sổ Tay Vườn Toán. Chạm một thẻ để xem trước, **Áp dụng** để lưu hoặc **Hủy xem trước** để trở lại lựa chọn đã lưu. Nút **Mặc định: Vườn Khám Phá** cho xem trước mẫu 04; bấm Áp dụng để lưu lại mẫu mặc định.

Lựa chọn lưu theo học sinh trên máy chủ và có lại khi đăng nhập trên thiết bị khác. Bản static/offline lưu riêng trong trình duyệt. Đổi giao diện không tải lại trang hoặc thay đổi bài làm, tiến độ và chức năng. Các phong cách dùng chung nền tảng Vườn Toán, phông Be Vietnam Pro và logo chính thức; mẫu nhỏ trong bộ chọn được dựng bằng CSS, không tải ảnh demo nặng.

Mở [Góc học tập localhost](http://localhost:8765/goc-hoc-tap/) để đăng ký/đăng nhập. Python dùng SQLite bền vững trong volume Docker; static/offline giữ chế độ trải nghiệm riêng. Một tài khoản/một học sinh; học sinh không tự đổi năm sinh, admin được sửa thông tin hồ sơ, năm sinh và gói Free/VIP/SVip. Khối tính theo mốc 01/07, tuần học từ 05/09 theo giờ Việt Nam. Hướng dẫn và hợp đồng API ở [LOCAL_API.md](docs/LOCAL_API.md).

RedUpdatev1 bổ sung Free/VIP/SVip, Nâng cấp gói/thanh toán chờ, Lớp Zoom cho SVip (buổi học, bài tập, tổng kết, học phí), giới hạn luyện tập và game theo ngày Việt Nam. Khách/Free/VIP có tab Đăng ký học Zoom để xem tư vấn. Nhãn Thi thử đổi thành Luyện tập, giữ liên kết `/thi-thu/`. Bài tuần mới nhất ở trên, ba bài ôn tuần sau có nhãn HỌC TRƯỚC; tìm chuyên đề lọc tại chỗ để không thay ô nhập khi đang gõ.

Free có một lượt theo nội dung và một đề tổng hợp/ngày, ba trận với người và năm lần bắt đầu bot/ngày. VIP/SVip không giới hạn lượt; đề theo trường chỉ mở cho khối 5 có quyền trả phí. Ngân hàng hiện là học liệu mẫu tự biên soạn, chưa thay cho đề chính thức/cấu trúc trường đã kiểm duyệt. Câu hỏi, đáp án nháp và kết quả được lưu theo tài khoản; đề chấm trên máy chủ và nộp một lần cho mỗi mã.

Phòng private/public, danh sách thách đấu, chấp nhận trong 30 giây, chuẩn bị ba giây sau khi chấp nhận và tự chuyển câu sau ba giây hoạt động qua API Python. Bảng kết quả từng câu thay phần câu hỏi, hiện đúng/sai/bạn nhanh hơn/hết giờ và số đếm lớn trước câu tiếp theo. Kết quả/XP người thật lưu DB một lần. Phòng đang hoạt động của bản Python cục bộ dùng RAM và mất sau restart; chờ quá năm phút tự hủy. Bot không ghi XP. Đấu trí có 10 ảnh nền thiên nhiên, khung vuông/hai nhân vật chéo, dải ảnh hành động và ba chiêu đá rơi/dây leo/sét. [Ảnh gốc và prompt](design/5bmath/dau-tri-v2/README.md), bản WebP trong frontend/arena-art/. Nhạc và hiệu ứng tự tạo bằng Web Audio, có nút tắt và dừng khi ẩn tab/rời game; trình duyệt có thể yêu cầu một lần chạm để phát âm thanh.

Tab Lớp Zoom chỉ hiện trong menu tài khoản SVip. Khách/Free/VIP có tab Đăng ký học Zoom với liên kết kiểm tra đầu vào và tư vấn fanpage/Zalo; SVip ẩn tab đăng ký. Dữ liệu lớp chỉ đọc khi đang ghi danh và có quyền nội bộ hiệu lực. Chưa có lớp/lịch/điểm/video/học phí thật thì hiện trạng thái chờ cập nhật. Dữ liệu lớp dùng kiểm thử không nhập vào volume người dùng. QR thanh toán gắn đúng tài khoản và đơn; webhook SePay xác thực HMAC có thể tự cộng VIP/thưởng giới thiệu hoặc đổi đúng học phí sang **Đã hoàn thành**. Chức năng tự động mặc định tắt, cần cấu hình ngân hàng/khóa webhook/backend HTTPS theo [PAYMENTS.md](docs/PAYMENTS.md); xác nhận thủ công vẫn có. Đã bỏ nút VIP thử và bảng kiểm tra database khỏi giao diện Góc học tập.

SVip nộp ảnh JPG/PNG/WebP hoặc PDF tối đa 10 MB cho từng bài tập trong buổi học. Tệp được lưu vào SQLite, chỉ học sinh sở hữu và nhân sự có quyền lớp được tải. Nộp lại giữ bản cũ và giữ điểm/nhận xét hiện tại để giáo viên xem lại. Menu **Lớp Zoom** có vòng tròn đỏ đếm tổng chưa đọc; **Bài tập** và **Học phí** có số riêng, ẩn khi bằng 0. Bài tập mới gửi thông báo tới học sinh đang trong lớp; học phí mới chỉ gửi tới học sinh có khoản phí đó. Bấm mục tương ứng để đánh dấu các thông báo đã tải là đã đọc; mở trang Lớp Zoom đơn thuần không xóa số đếm. Sửa bài tập/học phí không tạo thông báo trùng, không bổ sung thông báo cho dữ liệu cũ.

Mầm Sách 3D là hình ảnh đã duyệt cho website và truyền thông. Ảnh gốc và mô tả ở [STYLE.md](design/5bmath/linh-vat/STYLE.md).

## Giáo viên và quản trị

Mở [Trang giáo viên](http://localhost:8765/giao-vien/) hoặc [Trang quản trị](http://localhost:8765/quan-tri/). Giáo viên quản lý buổi học, bài tập và xem học phí của lớp được phân công. **Điểm danh & Nhận Xét** lưu điểm danh cùng nhận xét riêng từng học sinh sau mỗi buổi. **Chấm điểm** mở theo Buổi học → Bài tập → danh sách Học sinh/Bài nộp/Điểm/Nhận xét; điểm dùng thang 0–10, có thể lưu nhận xét khi chưa chấm điểm. Admin có cùng luồng lớp học và quản lý học liệu, lớp, nhân sự, tài khoản, lập học phí, đối soát và cấu hình chức năng/hạn mức. Dữ liệu lưu vào SQLite đang dùng và có kiểm tra quyền trên server.

Hướng dẫn cấp tài khoản, khởi tạo admin, nhập học liệu và vận hành ở [docs/STAFF_PORTAL.md](docs/STAFF_PORTAL.md). Mật khẩu nhân sự không lưu trong tài liệu.

Admin đặt **Học phí mỗi buổi** khi tạo/sửa lớp. Trong lớp → **Học phí**, admin hoặc giáo viên phụ trách bấm **Tính học phí**, chọn tháng, xem số buổi tính phí và lịch từng học sinh, rồi **Lưu toàn bộ** để lập/cập nhật phí và gửi thông báo. Chỉ buổi điểm danh tính phí được nhân tiền; giữ khoản đã thanh toán, lưu đơn giá/lịch của hóa đơn để không đổi theo giá lớp về sau. Cách lập thủ công của admin vẫn có sẵn. Lớp cũ chưa có đơn giá cần được cấu hình trước; 0 đồng là miễn phí.

Admin và giáo viên có tab **Gửi thông báo**. Admin gửi theo nhóm Tất cả/Free/VIP/SVip hoặc lớp; giáo viên chỉ gửi tới lớp đang phụ trách. Tài khoản học sinh hiện badge đỏ đếm chưa đọc, bảng thông báo có Tiêu đề/Người gửi/Xem và popup chi tiết; chưa đọc trước, mới nhất trước, 5 dòng mỗi trang. Thông báo hệ thống gồm đăng ký/gia hạn VIP đã xác nhận và thưởng giới thiệu. Lịch sử giới thiệu cũng có 5 dòng mỗi trang, mới nhất trước và tách rõ trạng thái/các mốc thời gian. Nội dung gửi nằm trong tài khoản trên website; hướng dẫn quyền và chống gửi trùng ở STAFF_PORTAL.

Điện thoại dùng hamburger trên header luôn ở trên khi cuộn; desktop giữ sidebar. Lobby Đấu trí chia ba chế độ Đấu nhanh/Với bạn/Với máy với nút lớn. Từ 12/11/2026 áp dụng PA3: bấm tìm đối thủ, tạo phòng hoặc chọn mức máy sẽ mở bước **Chọn nội dung thi đấu**, mặc định **Chương trình trên lớp** mỗi lần mở; có thể đổi sang **Kiến Thức Tổng Hợp** trước khi xác nhận bắt đầu. Máy tính dùng hộp thoại, điện thoại dùng bảng trượt từ dưới lên; hủy bước chọn không tạo trận hoặc dùng lượt. Luật chỉ còn các thẻ chính và bảng kinh nghiệm; thông báo thời gian nghỉ chỉ hiện khi đang bị hạn chế đấu người. Bảng xếp hạng còn Linh vật/Chăm chỉ, dòng mình tô nền không có badge “Em”. Zoom cho khách/Free/VIP giữ liên kết tư vấn và thẻ SVip vàng dùng chung với Nâng cấp gói.

Chủ động bỏ trận người thật sau khi bắt đầu tính thua và trừ một kinh nghiệm (sàn 1.000); người ở lại không nhận kinh nghiệm và được hoàn lượt đấu. Trận chưa hoàn thành không tăng thống kê thắng/thua của cả hai. Vi phạm lần đầu nhắc nhở, lần 2/3/từ lần 4 trong 24 giờ nghỉ đấu với người 5/15/60 phút; vẫn được học và luyện với máy. Mất mạng có thời gian nối lại, lần ngắt kéo dài đầu tiên trong 24 giờ được miễn điểm phạt; lặp lại ghi nhận vi phạm. Bộ đếm/thời gian nghỉ lưu DB, giữ qua tải lại và khởi động lại server. Phòng đang đấu vẫn dùng RAM; restart server không tự phạt người chơi. Chi tiết tại [hợp đồng API cục bộ](docs/LOCAL_API.md).

## Giới hạn

Chưa có video quay, lịch Zoom thực hoặc khôi phục mật khẩu. Tích hợp nhận tiền SePay cần được bật/cấu hình và nối backend chính thức trước khi thu tiền thật; chưa có tự trích tiền định kỳ hoặc hoàn tiền tự động. Phiếu tải là mẫu tự biên soạn; biểu mẫu nộp minh họa cũ ở chế độ tĩnh/offline chỉ ghi tên tệp. Luồng bài tập Lớp Zoom trên Python lưu tệp thật như mô tả trên. Tài khoản thật mới chạy trên Python cục bộ; bản D1 công khai chưa có API đăng nhập này. Không có bảo đảm cùng dữ liệu/tính năng giữa localhost và website công khai trước khi phát hành backend tương ứng.

Chấm đáp án cuối, chưa chấm từng bước tự luận. Chưa gắn số bài/trang SGK. Không dùng đề Ams cũ để khẳng định tuyển sinh hiện tại. Phông Be Vietnam Pro có phông hệ thống dự phòng.
Không lấy logo, ảnh hoặc mã nguồn Bigtree Land.
Máy chủ Python thư viện chuẩn phục vụ bản demo; trước khi mở dịch vụ thật cần hoàn thiện vận hành HTTPS, khôi phục tài khoản, quản trị và kiểm tra chuyên môn.

## Đăng ký học Zoom và khảo sát đầu vào

- `/dang-ky-hoc-zoom/`: tab đăng ký cho khách/Free/VIP, ẩn trong menu SVip; thẻ Học Zoom online, Học phí: 100k/buổi, link kiểm tra đầu vào và tư vấn Zalo/Facebook. `/lop-zoom/` chỉ hiện trong menu tài khoản SVip.
- `/dang-ky-kiem-tra-dau-vao/`: khảo sát công khai, không cần tài khoản; phụ huynh cung cấp thông tin liên hệ, học sinh và nhu cầu học. Bản Python lưu SQLite; admin xem tại **Quản trị → Đăng ký đầu vào**. Bản tĩnh chưa nhận biểu mẫu, hướng phụ huynh liên hệ trực tiếp.
- Trang chủ dùng meta title **Ươm mầm tư duy - Khơi nguồn tri thức**. Meta description 146 ký tự, giữ nguyên ba câu đầu người dùng cung cấp và rút gọn câu cuối. Các trang con giữ title/description riêng; khảo sát có canonical HTTPS và nằm trong tám trang công khai của sitemap. HTML khảo sát dùng chung giữa Python và bản dựng tĩnh ở `frontend/admissions.html`.

## Tạo animation linh vật từ các chat khác

Đã có [quy trình và câu lệnh mở việc](docs/ANIMATION_WORKSHOP.md), [20 đầu bài](design/5bmath/linh-vat/animations/README.md) và bộ công cụ `tools/mascot-animation/`. Mỗi nhân vật/biến thể có thư mục và owner riêng, tạo WebP cho Canvas cùng GIF/MP4 ba giây để duyệt. Người dùng đồng ý hướng kỹ thuật nhưng **chưa tích hợp vào game bây giờ**; không tự phát hành khi tạo xong demo.

## Ranh giới học liệu và dữ liệu vận hành

`backend/migrations/*.sql` là nguồn lược đồ duy nhất. Migration 0000 khởi tạo schema cũ, thay cho việc duy trì thêm một bản `schema.sql` trùng lặp. Migration 0018 lưu bài nộp thành các chunk 1 MB, giữ hạn mức 10 MB và khả năng đọc tệp inline cũ. Sao lưu và diễn tập khôi phục trước migration theo [BACKUPS.md](docs/BACKUPS.md).

`backend/learning-catalog.json` chỉ chứa 20 bài/ví dụ công khai. Kho chấm thi/Đấu trí được tạo ngẫu nhiên riêng một lần trong database với mã `BANK2` không thể suy ra từ bộ offline. 960 là số câu mẫu tự biên soạn, chưa phải ngân hàng đã duyệt toàn chương trình.

Các phiên bản `BANK` cũ đã lộ bị rút phát hành; nội dung, đáp án và lịch sử bài đã làm vẫn được giữ, cùng các bản sửa riêng của giáo viên. Khi admin rút câu, thay đổi có hiệu lực với đề/trận mới; phiên bản đã chọn cho bài đang làm giữ nguyên. Bộ offline chỉ có 22 ví dụ độc lập, luôn có nhãn mẫu và không xuất đáp án của kho chấm thật.

`scripts/cloudflare-data.py` dùng giao thức chuyển dữ liệu v1, tạo snapshot nhất quán trước khi xuất và chỉ ghi dữ liệu riêng dưới `work/`. Kiểm thử cục bộ 8/8 đã đạt; nhập/xuất remote và bản sao ngoài máy cần được nghiệm thu riêng. Xem [quy trình sao lưu và chuyển dữ liệu](docs/BACKUPS.md).

`.env`, `.wrangler/`, database/bản sao lưu, `work/`, `Learn/`, `Exams/`, `outputs/`, `req/` và chat chi tiết giữ cục bộ. Khi còn thay đổi thiết kế đang làm, chọn đúng tệp thuộc phạm vi thay vì dùng `git add .`. Giữ PNG nguồn, brief và QA không thể dựng lại; chỉ dọn artefact tạo lại được sau khi xác định chủ sở hữu.
