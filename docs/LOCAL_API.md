# Luồng tài khoản và học tập trên localhost

Cập nhật 12/11/2026. Mở **http://localhost:8765/goc-hoc-tap/**, chọn **Đăng nhập / Đăng ký → Chưa có tài khoản? Đăng ký**. Dùng năm sinh tương ứng khối 1–5; ví dụ 2016 tương ứng khối 5 trong năm học 2026–2027. Tên đăng nhập dùng chữ không dấu, số và `. _ @ + -`, mật khẩu ít nhất 6 ký tự. Người dùng tự đặt mật khẩu; dự án không lưu mật khẩu vào hướng dẫn hoặc bản ghi chat.

## Biệt danh an toàn

- Khi đăng ký hoặc đổi tên, biệt danh cần 2–40 ký tự sau chuẩn hóa, có chữ cái tiếng Việt/Latin; cho phép chữ số, khoảng trắng, gạch ngang và gạch dưới. Chuẩn hóa Unicode, chữ số Unicode và khoảng trắng trước khi lưu; từ chối ký tự ẩn/điều khiển, email, đường dẫn hoặc ký hiệu khác.
- Không chấp nhận tên toàn số hoặc chứa từ bảy chữ số trở lên, kể cả số tách bằng dấu cách/dấu câu, gắn vào tên, đầu số quốc tế, chữ số Unicode. Chuỗi từ đọc chữ số tiếng Việt liên tiếp hoặc xen chữ số cũng bị chặn khi đạt bảy vị trí. Tên ngắn như “Sóc 5A” vẫn hợp lệ.
- Chặn danh sách từ và cụm từ không phù hợp cùng các biến thể viết hoa/thường, bỏ dấu, tách ký tự, ghép liền rõ nghĩa hoặc thay chữ bằng số thường gặp. Giữ tên hợp lệ như Đức, Dũng, Phúc Long, Bùi, Lồng Đèn và Đĩa Xinh. Đây là bộ lọc dựa trên quy tắc và danh sách có thể bổ sung; không khẳng định nhận diện mọi cách viết lách. Một số từ không dấu ngắn, đa nghĩa được giữ để tránh chặn nhầm tên lành.
- Backend kiểm tra trước khi ghi DB ở `auth/register`, `profile` và cổng Arena trực tiếp; quản trị tạo/đổi biệt danh dùng cùng helper. Frontend kiểm tra ngay trong biểu mẫu đăng ký/đổi biệt danh, cả chế độ offline. Gửi thẳng API vẫn bị từ chối nếu tên không hợp lệ.
- Tên cũ không hợp lệ hiển thị thành **Bạn học** ở hồ sơ/header, giới thiệu, bảng xếp hạng, lớp, phòng đấu/thách đấu/lịch sử và các danh sách học sinh, học phí, thanh toán của giáo viên/admin. Kiểm tra hiển thị không đổi dữ liệu cũ trong DB; người dùng có thể đổi lại biệt danh hợp lệ. Giữ thông tin liên hệ phụ huynh và tên nhân sự trong đúng phạm vi quản trị hiện có.

Nguồn quy tắc: `backend/nickname-policy.json`, hàm Python `backend/nickname_policy.py` và bản JavaScript `frontend/nickname-policy.js`. Kiểm tra dữ liệu hai bản giống nhau và 83 tình huống JavaScript bằng `node tests/test_nickname_policy.cjs`; bộ Python có kiểm thử ghi bị từ chối và che dữ liệu cũ. CI đã được bổ sung lệnh kiểm tra JavaScript này; việc sửa cấu hình CI không có nghĩa CI từ xa đã chạy.

## Cách duyệt sau RedUpdatev1

1. Vào **Học online**: bài theo tuần mới nhất ở trên, ba bài ôn tập tuần sau có nhãn **HỌC TRƯỚC**. Tìm chuyên đề giữ nguyên ô nhập và chỉ lọc thẻ sau 220 ms.
2. Vào **Luyện tập** (giữ URL `/thi-thu/`): Free có một lượt tạo đề theo nội dung và một lượt đề tổng hợp mỗi ngày Việt Nam. Lượt tính khi tạo thành công; làm tiếp/nộp lại cùng đề không tính thêm. **Luyện 3 câu** cũng thuộc lượt theo nội dung. VIP/SVip không giới hạn; bộ chống tạo quá nhanh 60 đề/giờ vẫn được giữ.
3. Chọn tuần/chuyên đề trong danh sách có tìm kiếm. Tuần chưa có ngân hàng được ghi “Đang biên soạn” và không chọn được. Đề tổng hợp có ba mức. VIP/SVip khối 5 mở đề theo trường; hiện vẫn là câu mẫu tự biên soạn, chưa có cấu trúc chuẩn đã kiểm duyệt từng trường. Tài liệu tải là phiếu mẫu TXT có đáp án.
4. **Nâng cấp gói** chỉ hiện với Free/VIP. Nâng cấp mở `/thanh-toan/`, tạo đơn chờ theo tài khoản, 100.000 đồng/một tháng. SePay có thể xác nhận tự động khi đã cấu hình HMAC và tài khoản nhận; giao diện chỉ đọc trạng thái từ server, không tự cấp quyền. Cấu hình và giới hạn ở [PAYMENTS.md](PAYMENTS.md). Nút kiểm tra VIP cũ đã bỏ khỏi giao diện.
5. Menu **Lớp Zoom** chỉ hiện cho SVip; khách/Free/VIP có **Đăng ký học Zoom** để xem tư vấn. Nội dung lớp yêu cầu quyền nội bộ đang hiệu lực và ghi danh đúng lớp. Lớp, giáo viên, lịch/chương trình, nhận xét riêng từng học sinh, video, bài tập/điểm/nhận xét bài làm, biểu đồ tháng, chu kỳ hai tuần, bảng điểm/xếp hạng và học phí/điểm danh đều đọc DB. Trong **Bài tập**, học sinh nộp ảnh JPG/PNG/WebP hoặc PDF tối đa 10 MB cho từng bài; tệp được lưu thật và nhân sự có quyền lớp tải để chấm. **Lớp Zoom**, **Bài tập**, **Học phí** có số thông báo chưa đọc; bấm Bài tập/Học phí để đánh dấu mục tương ứng. Chưa có dữ liệu thì hiện trạng thái trống, không tự tạo lớp/điểm/học phí thật.
6. **Đấu trí**: Free tối đa ba trận với người và năm lần bắt đầu bot/ngày. Lượt với người tính khi chủ phòng chấp nhận; hủy trước đó không trừ lượt. Tạo phòng chọn Bạn bè (private) hoặc Tất cả (public). Tìm nhanh ghép phòng public cùng khối/nội dung, hoặc tự mở phòng public. Có thể nhập mã/link, thu nhỏ phòng để học tiếp, phòng tự đóng sau năm phút.
7. Thách đấu có 30 giây chấp nhận/hủy, tiếp đến ba giây chuẩn bị, thời gian mỗi câu theo khối/độ khó trong bảng bên dưới, tự chuyển sau ba giây khi đúng/hết giờ/hai bên trả lời sai. Máu giảm có hoạt ảnh, đòn năng lượng kết thúc, mười biểu cảm (mỗi người gửi tối đa một lần trong 5 giây, tính liên tục qua các câu), kết quả và lời giải ẩn từng câu. Nhạc Web Audio tự sáng tác, mặc định âm lượng nhẹ, bật sau tương tác khi trình duyệt yêu cầu; tắt/ẩn tab hoặc rời phần game sẽ dừng. Nút nhạc giữ tùy chọn tắt trên thiết bị.
8. Xếp hạng mặc định **Tất cả** học sinh/thời gian. Có Linh vật và Chăm chỉ; Lớp Zoom chỉ dành cho SVip và theo lớp đang học. Ba hạng đầu có huy chương, dòng của em tô nền, không thêm badge “Em” cạnh tên. “Ham học” và bảng “Số đề đã làm” đã bỏ khỏi UI.

Bot vẫn chạy ở trình duyệt, không ghi XP. Kết quả bot mới nhất được giữ trong sessionStorage để xem sau điều hướng; lịch sử bot đa thiết bị chưa được triển khai. Biểu mẫu nộp tệp minh họa cũ ở chế độ tĩnh/offline chỉ ghi tên; luồng Lớp Zoom trên Python dùng API tệp riêng bên dưới. Phòng người thật vẫn dùng RAM; kết quả/XP hoàn tất lưu DB. Khởi động lại máy chủ sẽ kết thúc phòng đang chờ/đang đấu.

### Cấu hình ngân hàng sau

Đặt ba biến môi trường `MAM_TOAN_BANK_ID`, `MAM_TOAN_BANK_ACCOUNT`, `MAM_TOAN_BANK_NAME` rồi dựng lại Compose. Chưa đặt thì đơn vẫn có số tiền/mã tham chiếu, không sinh QR. Khi đủ cấu hình, QR dùng [VietQR Quick Link](https://www.vietqr.io/qr-dong) với số tiền và mã đơn theo tài khoản. QR chỉ hướng dẫn chuyển khoản; cấp quyền sau khi webhook đã xác thực hoặc admin đối soát. Đơn lưu snapshot ngân hàng, không tự đổi tài khoản nhận của đơn cũ khi thay cấu hình.

API thử `dev/upgrade` còn phục vụ kiểm thử tự động khi cờ `MAM_TOAN_REVIEW_UPGRADES=1`; container bản RedUpdatev1 chạy cờ `0`, giao diện không có nút này.

## Hợp đồng API

API cùng nguồn tại `/api/v1/`, JSON UTF-8 (riêng tải bài nộp trả dữ liệu nhị phân), `Cache-Control: no-store`. Đăng ký/đăng nhập trả cookie phiên HttpOnly, SameSite=Strict và `csrf` trong JSON. Client gửi `X-CSRF-Token` cho thao tác ghi sau đăng nhập. Cookie phiên và mật khẩu không được đặt trong localStorage. Mật khẩu băm PBKDF2-HMAC-SHA256, 600.000 vòng, salt ngẫu nhiên; database chỉ lưu mã băm token phiên. Phiên có hạn bảy ngày, đăng xuất thu hồi phiên hiện tại. Cấu hình hiện dành cho HTTP loopback; phát hành HTTPS cần cookie Secure và cấu hình kiểm tra Origin tương ứng.

| API | Dữ liệu / hành vi |
| --- | --- |
| `POST auth/register` | `login, password, name, birthYear, inviteCode?`; tạo một tài khoản/một học sinh, cố định người mời và năm sinh |
| `POST auth/login` | `login, password`; tạo phiên và trả trạng thái tài khoản |
| `POST auth/logout` | `{}`; thu hồi phiên hiện tại |
| `GET session`, `GET state` | `authenticated, csrf, name, account, lessons, state`; tài khoản chưa đăng nhập chỉ nhận `authenticated:false` ở session |
| `POST profile` | Chỉ `name`; từ chối trường năm sinh và các trường khác |
| `POST preferences` | Chỉ `{theme}` thuộc danh sách năm giao diện; đăng nhập/CSRF/Origin, lưu theo học sinh và trả snapshot có `state.theme`; không đổi bài đang học hoặc tiến độ |
| `POST mascot` | `mascot: sprout hoặc fox`; lựa chọn được lưu theo học sinh |
| `POST lessons/{client_key}/open` | Lưu bài đang xem, kiểm tra đúng khối |
| `POST lessons/{client_key}/complete` | Đánh dấu hoàn thành một lần, kiểm tra đúng khối |
| `POST exams` | `requestKey, topic?, count:3/10, difficulty:0..3, maxWeek?`; khối/tuần hiện tại do server xác định. Có maxWeek nghĩa là giới hạn đến tuần hiện tại |
| `GET exams/{id}` | Đề của học sinh hiện tại; chưa nộp không trả đáp án, lời giải hoặc gợi ý chấm |
| `POST exams/{id}/answers` | `position, answer`; lưu từng câu, kiểm tra lựa chọn và hạn làm bài |
| `POST exams/{id}/submit` | `{}`; chấm bằng phiên bản câu hỏi đã lưu; gửi lại trả cùng kết quả |
| `GET leaderboard` | Bộ lọc `kind=battle/lessons/activity/exams`, `period=day/week/month/all`, `scope=grade/class`; tối đa 50 dòng |
| `POST heartbeat` | `{}`; máy chủ ghi khoảng hoạt động, ngắt khoảng khi quá 75 giây không có heartbeat |
| `POST notifications/{id}/read` | `{}`; chỉ đánh dấu thông báo của tài khoản hiện tại |
| `POST arena` | Giao thức phòng hiện có; lấy tên/khối từ phiên đăng nhập, ràng buộc token phòng với học sinh, lưu kết quả và XP một lần |
| `POST dev/upgrade` | `requestKey`; chỉ khi bật cờ duyệt. Ghi sự kiện mua thử và chạy trigger VIP/giới thiệu/thông báo |

Đường dẫn trong bảng có tiền tố `/api/v1/`. Response đăng nhập và thao tác hồ sơ trả snapshot; thao tác đề trả `{exam:...}`. `state.exams` chứa tối đa 100 đề gần nhất, lịch sử đã nộp chỉ có tóm tắt để tải nhanh; client lấy chi tiết khi mở trang làm bài/kết quả theo id. Thông báo và quan hệ mời hiển thị 50 dòng gần nhất. Bài cũ vẫn mở được qua API chi tiết theo id. Giao diện cũ/offline dùng luồng trải nghiệm riêng; dữ liệu localStorage không được nhập vào tài khoản thật.

## Dữ liệu và phạm vi hiện tại

- SQLite WAL trong volume Docker `demo-db`, tệp `/data/5bmath-demo.sqlite3`. Migration bổ sung không xóa dữ liệu cũ. `0004` thêm phiên, đáp án nháp, cấu hình học và liên kết phòng; `0005` thêm kết quả phòng; `0006` thêm dữ liệu RedUpdatev1; `0007` thêm quản trị; `0013` thêm nhận xét từng học sinh, bài nộp và thông báo Lớp Zoom. Danh mục migration trong `backend/migrations/` là nguồn đối chiếu lược đồ hiện tại.
- `backend/learning-catalog.json` giữ 20 bài và 960 câu mẫu tự biên soạn cho khối 1–5. Xuất lại từ học liệu đã duyệt bằng `node scripts/export-learning-catalog.cjs`. Seed idempotent; không ghi đè phiên bản câu đã dùng. Nội dung mới cần mã/phiên bản mới.
- Nội dung JSON hỗ trợ text, LaTeX/MathML và ảnh tham chiếu. Bài diện tích khối 5 có công thức và ảnh kiểm tra thực tế. Ảnh có kích thước, mô tả và tải trì hoãn. Thông tin đáp án chấm không được gửi trong đề chưa nộp.
- Đề chọn ngẫu nhiên trên danh sách id phù hợp rồi chỉ tải câu đã chọn. Tránh dùng lại câu của đề ngay trước nếu ngân hàng đủ câu. Nội dung/đáp án/thứ tự lựa chọn được lưu theo đề; không chấm theo dữ liệu do client tự khai.
- Kết quả đấu hai người và XP lưu trong DB. Phòng đang chờ/đang đấu vẫn ở bộ nhớ Python và hết khi restart; bot luyện tập vẫn chạy trong trình duyệt, không ghi XP. Nộp ảnh/PDF của Lớp Zoom lưu BLOB trong SQLite; biểu mẫu minh họa tĩnh/offline cũ chỉ ghi tên. Video thực, đề theo trường, cổng thanh toán, quên mật khẩu/xác minh email và phân trang giao diện cho dữ liệu cũ hơn giới hạn trên là các bước tiếp theo.
- Cờ `data-backend="database"` chỉ được Python thêm vào HTML. Static Cloudflare/GitHub/offline không bật luồng này; D1 và website công khai chưa được nâng cấp theo đợt localhost.

## Xác minh ngày 11/11/2026

32 bài thử Python đạt trên Windows và image Docker. Chrome xác minh đăng ký, cookie HttpOnly, lưu bài, đọc lại ở trình duyệt thứ hai, chấm/lời giải, mời bạn/nâng cấp thử/thưởng/thông báo và bảng xếp hạng. Các trang khu học tập kiểm tra ở 390×844, 844×390, 768×1024, 1024×768 và 1440×900; không lỗi JavaScript hoặc tràn ngang. Đã restart container và đọc lại phiên, tiến độ, câu trả lời từ cùng database. 40 lần đọc state tuần tự của một tài khoản thử cho P50 7 ms, P95 8 ms trên máy này; đây không phải kiểm thử tải đồng thời. Nguồn/báo cáo/ảnh chỉ lưu cục bộ tại `work/backend-integration/`.

## API bổ sung RedUpdatev1

| API | Hành vi |
| --- | --- |
| `GET session` | `account.membership = Free / VIP / SVip`, `account.usage` gồm content/combined/human/bot; `limit:null` là không giới hạn |
| `POST exams` | Thêm category content/combined/school, week?, school?; kiểm tra quyền, khối, phạm vi và lượt trong giao dịch. Giữ requestKey để tạo lại cùng đề an toàn |
| `GET classes/:id?from=&to=` | Chỉ SVip đang ghi danh lớp đó; trả thông tin, buổi học/bài tập/điểm của mình, điểm TB tháng/chu kỳ và học phí/điểm danh của mình |
| `GET classes/:id/ranking?assignment=:id` hoặc `cycle=:index` | Bảng điểm/xếp hạng các học sinh đang ở cùng lớp; chu kỳ 14 ngày tính từ ngày bắt đầu giảng dạy của năm học |
| `POST payments` | `{}` tạo/reuse đơn VIP 100.000đ; `{feeId}` tạo/reuse đơn học phí của chính mình chưa nộp. Client không được gửi số tiền hoặc trạng thái đã thanh toán |
| `GET materials` | Phiếu TXT mẫu; chặn Free trên máy chủ |
| `POST bot/start` | requestKey, ghi lượt bắt đầu theo ngày Việt Nam, gửi lại cùng key không trừ thêm |
| `POST arena` | Thêm list, accept, emote; create có public; danh tính/chỉ số từ DB; trạng thái waiting/challenged/preparing/playing/finished/cancelled. Đồng hồ/auto chuyển câu phía server, danh sách phòng không trả token |

Học phí/điểm/nhận xét được nhập qua [trang giáo viên và quản trị](STAFF_PORTAL.md). Thông tin lớp thực do admin và giáo viên nhập. Các fixture lớp trong `work/red-update-v1/ui.sqlite3` và `work/staff-pages/qa.sqlite3` chỉ dùng kiểm thử riêng.

### Nhận xét, bài nộp và số chưa đọc Lớp Zoom — 12/11/2026

| API | Dữ liệu / hành vi |
| --- | --- |
| `GET /api/v1/classes/unread` | Trả `{classroomUnread:{total,assignments,fees,classes:{"classId":{total,assignments,fees}}}}`; chỉ tính lớp đang hoạt động, đang ghi danh và quyền SVip hiệu lực; nhóm khác nhận số 0 |
| `GET /api/v1/classes/:id?from=&to=` | Bổ sung `sessions[].personal_comment`, `attendance_status`, `assignments[].comment`, `assignments[].submission` mới nhất hoặc `null`; trả `unread:{total,assignments,fees}` và `readThrough:{assignments,fees}` cho lớp; GET không đánh dấu đã đọc |
| `POST /api/v1/classes/:id/read` | `{section:"assignments" hoặc "fees",through:mốc_ID_đã_tải}`; đánh dấu riêng thông báo của học sinh/lớp/mục có ID không quá mốc; trả `classroomUnread`, `unread`, `readThrough` mới |
| `POST /api/v1/classes/:classId/assignments/:assignmentId/submissions` | `{filename,mimeType,data}`; `data` là base64 thuần của một tệp; trả `{submission:{id,assignment_id,student_id,filename,mime_type,size,submitted_at,url}}` |
| `GET /api/v1/class-submissions/:id/file` | Tải tệp nhị phân của chính học sinh sau kiểm tra phiên, SVip và ghi danh lớp; `Content-Disposition: attachment`, không có URL tải công khai |
| `GET /api/staff/submissions/:id/file` | Tải tệp nhị phân sau kiểm tra phiên nhân sự và quyền lớp; giáo viên chỉ tải lớp đang được phân công |
| `POST /api/staff/sessions/:id/records` | `{revision,attendance:[{studentId,status,comment}]}` để lưu điểm danh/nhận xét buổi, hoặc `{revision,scores:[{studentId,assignmentId,score,comment}]}` để chấm bài; trả chi tiết lớp và revision mới |

Snapshot tài khoản có `account.classroomUnread` cùng cấu trúc tổng hợp như `GET classes/unread`. Metadata `submission` không chứa dữ liệu BLOB/base64. Tệp nhận JPG/PNG/WebP/PDF tối đa 10 MB, kiểm tra tên/đuôi tệp, MIME và dấu nhận dạng nội dung. Cùng nội dung và tên với bản nộp mới nhất trả lại bản đó; nộp lại khác tạo bản ghi mới, giữ bản trước và giữ điểm/nhận xét đã chấm. Bảng nhân sự dùng `sessions[].submissions` là bản mới nhất theo bài/học sinh, `attendance[].comment` và `scores[].comment`; có thể có hàng nhận xét với `status:null` hoặc `score:null`.

`status` nhận `charged`, `free`, `absent` hoặc `null`; `score` nhận số 0–10 hoặc `null`. Nhận xét tối đa 10.000 ký tự, lưu được khi chưa điểm danh/chưa có điểm. Các mảng và trường không gửi được giữ nguyên; gửi `status:null` hoặc `score:null` xóa riêng giá trị đó, không xóa nhận xét nếu không gửi `comment`. Điểm danh và chấm điểm đều yêu cầu revision buổi hiện tại; nộp tệp mới tăng revision để form cũ không ghi đè kết quả trên dữ liệu đã thay đổi. Giáo viên và admin có luồng **Điểm danh & Nhận Xét** riêng với **Chấm điểm → Buổi học → Bài tập → Học sinh/Bài nộp/Điểm/Nhận xét**. Giáo viên được tính và lưu học phí tự động cho lớp phụ trách; admin đặt đơn giá, giữ cách lập thủ công và đối soát.

Tạo bài tập mới ghi thông báo cho học sinh hiện đang ghi danh lớp; tạo khoản phí mới chỉ ghi cho học sinh có khoản phí đó. Sửa bài tập hoặc phí thủ công không tạo lại thông báo, không tạo bù sự kiện cũ hoặc học sinh ghi danh sau. Riêng tính học phí tự động, khoản mới/thay đổi tạo thông báo tài khoản và mốc unread mới của mục Học phí; khoản không đổi không gửi thêm. Bộ đếm lớp riêng với inbox `notifications` của tài khoản. UI ẩn số 0, gộp tổng ở menu Lớp Zoom, hiện riêng Bài tập/Học phí theo lớp đang chọn và làm mới khoảng 30 giây khi trang hiển thị/có mạng hoặc khi trở lại trang. Bấm mục tương ứng mới gửi xác nhận tới `readThrough` đã tải; thông báo mới tới sau mốc đó không bị đọc nhầm, cập nhật nền không tự xác nhận.

## API giáo viên và quản trị (11/11/2026)

Popup trang chủ dùng `POST /api/v1/auth/login` cho cả học sinh và nhân sự. API ưu tiên xác thực tài khoản học sinh như cũ; nếu không khớp, kiểm tra nhân sự đang hoạt động. Thành công với nhân sự trả `principal: "staff"`, `user`, `csrf`, cookie `5bmath_staff`; client chuyển admin tới `/quan-tri/`, giáo viên tới `/giao-vien/`. Response nhân sự không có snapshot học sinh. Các phiên và quyền của hai nhóm vẫn tách biệt; API `/api/staff/login` trực tiếp giữ nguyên.

Hai trang `/giao-vien/` và `/quan-tri/` dùng `/api/staff/`, cookie nhân sự riêng, CSRF và kiểm tra vai trò/lớp ở server. Admin cấp tài khoản giáo viên, phân công lớp, ghi danh, quản lý học liệu và tài khoản, xác nhận thanh toán thủ công, cấu hình chức năng/hạn mức và xem nhật ký. Giáo viên tạo buổi/bài tập, nhập video/tài liệu bằng URL, điểm danh, điểm và nhận xét cho lớp được phân công. Học sinh đọc lại qua API lớp hiện có. Cấu hình mở/đóng chức năng và hạn mức được API học sinh thực thi; bài đang làm vẫn được hoàn thành. Chi tiết khởi tạo admin và vận hành ở [STAFF_PORTAL.md](STAFF_PORTAL.md).

Quản lý tài khoản học sinh (12/11/2026):

- `GET /api/staff/accounts?q=&grade=0&page=1&status=all` tìm kiếm và phân trang 25 tài khoản, trả `revision`, `deleted_at`, `membership`, `membership_expires_at`, `mascot`, `points`, cùng danh mục `mascots:[{code,name}]` cho biểu mẫu. `status=all` gồm tài khoản chưa xóa; `active`, `suspended`, `deleted` lọc trạng thái tương ứng.
- `POST /api/staff/accounts` tạo `{login,name,birthYear,password,status,membership,membershipExpiresAt,mascot,points}`. Các trường gói/linh vật/kinh nghiệm tùy chọn, mặc định Free/Mầm Sách/1.000. Một tài khoản/một học sinh, có khối và tùy chọn học ban đầu; không cấp cookie học sinh cho admin.
- `POST /api/staff/accounts/:id` sửa `{revision,login,name,birthYear,password,status,membership,membershipExpiresAt,mascot,points}`; có thể gửi riêng `{revision,status}` để khóa/mở. Mật khẩu trống giữ nguyên. **Admin được sửa năm sinh** theo chỉ đạo mới ngày 12/11/2026; học sinh không được tự sửa. Khối và student_grades của năm học hiện tại được tính lại; giữ lịch sử năm học cũ/bài làm. Những thay đổi cần làm mới hồ sơ/quyền thu hồi phiên và token phòng cũ.
- `membership` nhận `Free`, `VIP`, `SVip`; VIP cần `membershipExpiresAt` ISO có múi giờ và trong tương lai; SVip nhận hạn tương lai hoặc `null` để không thời hạn. Free dừng quyền gói cũ. Gán gói trực tiếp cập nhật quyền học, giữ phân công lớp, không tạo purchase/payment/referral reward. Lưu lại cùng gói và cùng hạn không tạo thêm quyền. `mascot` lấy từ danh mục server; `points` là số nguyên 1.000–1.000.000.000.
- `POST /api/staff/accounts/:id/delete` nhận `{revision,confirmLogin}`; đánh dấu xóa, khóa đăng nhập, kết thúc ghi danh/quyền lớp và thu hồi phiên. Giữ lịch sử và tên đăng nhập. `POST /api/staff/accounts/:id/restore` nhận `{revision}`, khôi phục ở trạng thái tạm khóa, không tự ghi danh lại.
- Các thao tác ghi trả `{saved:true,account:{...}}`, không trả mật khẩu hoặc hash. Revision cũ trả 409. Tất cả chỉ dành cho admin và yêu cầu CSRF; xem [hướng dẫn xóa/khôi phục](STAFF_PORTAL.md#xóa-và-khôi-phục-tài-khoản-học-sinh).

## Đối soát và người giới thiệu (12/11/2026)

- `GET /api/staff/payments?q=&referrer=&page=1` chỉ dành cho admin, trả `{rows,total,page,pageSize:25}`, đơn mới nhất trước. `q` tìm theo mã đơn, tên đăng nhập/biệt danh học sinh hoặc người giới thiệu; `referrer` lọc riêng tên đăng nhập/biệt danh người giới thiệu. Hai bộ lọc kết hợp bằng AND, áp dụng cả tổng số và các trang kết quả.
- Mỗi dòng giữ các trường đơn thanh toán, `login_identifier` và `full_name` của học sinh; thêm `referrer:{referralId,accountId,login,name,membership,rewardStatus,rewardGrantedAt,rewardVipExpiresAt,supportConfirmedAt,supportConfirmedBy,canConfirmSupport}` hoặc `null` khi không có người giới thiệu. `membership` là gói đang hiệu lực `Free`, `VIP`, `SVip` tại lúc đọc, không phải gói tại lúc đăng ký hay nhận thưởng; UI ghi `VIP` thành **Vip**. `rewardStatus` lấy nguyên hồ sơ giới thiệu (`pending`, `granted`, `customer_service`), các mốc thưởng/hỗ trợ có thể `null`. `supportConfirmedBy` là ID nhân sự xác nhận; `canConfirmSupport` điều khiển nút confirm khi chưa xác nhận.
- `POST /api/staff/referrals/:id/confirm-support` nhận `{referrerAccountId}`, chỉ admin có phiên và CSRF hợp lệ. Server đối chiếu đúng người giới thiệu; lần đầu chỉ nhận quan hệ có `reward_status=customer_service`, lần nâng cấp VIP đầu/qualifying purchase hợp lệ, người giới thiệu hiện SVip và chưa bị xóa. Trả `{saved:true,referralId,supportConfirmedAt,supportConfirmedBy,replayed}`. Gửi lại lượt đã xác nhận trả ngày/người xác nhận cũ, `replayed:true`, không tạo thêm ledger/audit kể cả gói hiện tại đã thay đổi; sai người giới thiệu hoặc chưa đủ điều kiện trả 409.
- Bảng/popup giữ tên đăng nhập học sinh trước biệt danh. Nút **confirm** mở popup kiểm tra người giới thiệu và học sinh; **OK** mới gửi xác nhận. Sau xác nhận hiện **Đã được hỗ trợ nhận thưởng** và ẩn nút. Migration `0015_referral_reward_confirmations.sql` chỉ thêm ledger xác nhận bất biến; thao tác này không cộng tháng VIP, không đổi `account_referrals.reward_status`, ngày/hạn thưởng cũ, quyền gói hoặc thanh toán. Cơ chế cộng một tháng VIP hiện có không đổi.
- `GET /api/v1/referrals?page=1` và snapshot giới thiệu của tài khoản thêm `support_confirmed_at` (ISO hoặc `null`). Lịch sử của chính người giới thiệu hiển thị đã nhận thưởng, **Đã được hỗ trợ nhận thưởng** và ngày xác nhận khi có mốc này; lượt `granted` vẫn có ngày cộng thưởng/hạn VIP theo luồng cũ. Trang Tài khoản làm mới trang lịch sử đang xem khoảng 30 giây/khi trở lại trang khi có mạng và đang hiển thị, có kiểm tra chủ tài khoản/trang/yêu cầu để không ghi đè kết quả mới; tải lại trang cũng đọc được xác nhận đã lưu.

## Trung tâm thông báo (12/11/2026)

- `GET /api/staff/notifications?page=1`: metadata nhóm nhận (admin), danh sách lớp đang hoạt động theo quyền và lịch sử gửi. Giáo viên chỉ xem lịch sử gửi của mình; admin xem toàn bộ. `POST /api/staff/notifications/preview` nhận `{audience,classId?}`, trả `{recipientCount,audienceLabel}`.
- `POST /api/staff/notifications` nhận `{title,body,audience,classId?,requestKey}`; `audience` là `all`, `Free`, `VIP`, `SVip`, `class`. Tiêu đề 1–160 ký tự, nội dung 1–10.000, requestKey 8–80. Giáo viên chỉ được chọn class thuộc quyền hiện tại. Server chốt người nhận, lưu broadcast/delivery/inbox/audit cùng giao dịch. Gửi lại cùng requestKey/payload trả kết quả cũ; đổi payload với key cũ trả 409. Không có người nhận trả lỗi, không tạo bản gửi rỗng.
- `GET /api/v1/notifications?page=1` trả `{rows,total,page,pageSize:5,unreadCount}` cho chính tài khoản; thứ tự `(chưa đọc, created_at DESC, id DESC)`. Mỗi hàng có `id,title,sender_name,sender_role,kind,body,created_at,read_at`. `unreadCount` đếm toàn bộ inbox.
- `POST /api/v1/notifications/:id/read` đánh dấu đã đọc một lần và trả snapshot tài khoản cùng `notification` là chi tiết mục vừa mở; không thuộc tài khoản hoặc không tồn tại trả 404. Yêu cầu phiên học sinh và CSRF như các thao tác ghi khác.
- `GET /api/v1/referrals?page=1` trả `{rows,total,page,pageSize:5}`, mới nhất trước theo `registered_at DESC,id DESC`. Snapshot account có 5 thông báo/giới thiệu đầu tiên, `notificationUnreadCount`, `notificationTotal`, `referralTotal`.
- Thành công mua VIP lần đầu/gia hạn và thưởng giới thiệu tạo thông báo hệ thống ngay trong trigger xác nhận, không tạo trùng khi gửi lại thanh toán. Admin cấp quyền gói thủ công không phải sự kiện thanh toán. Trình duyệt cập nhật badge bằng API inbox nhẹ khi có mạng/trang hiển thị, không vẽ lại trận đấu.

## Ảnh Đấu trí v2 và Zoom tư vấn (11/11/2026)

Khung đấu vuông, hai nhân vật chéo nhau; desktop đặt câu hỏi bên cạnh, mobile đặt bên dưới. 10 cảnh ảnh chọn theo mã trận và giữ ổn định trong trận. Hai mascot có bốn hành động bằng sprite ảnh; mỗi đòn gây sát thương được chọn ngẫu nhiên một hiệu ứng đá rơi/dây leo/sấm sét và máy chủ gửi cùng kết quả cho hai phía. Chiêu cuối vẫn thêm luồng năng lượng cũ. Không đổi luật/XP/quota. PNG gốc/prompt ở design/5bmath/dau-tri-v2, bản WebP website ở frontend/arena-art; server chỉ phục vụ các WebP trong danh sách. prefers-reduced-motion dùng tư thế/chiêu tĩnh.

Quy tắc menu hiện tại thay bản mở Zoom cho mọi người ở đợt này: Lớp Zoom chỉ hiện với SVip, khách/Free/VIP dùng Đăng ký học Zoom. Mở trực tiếp `/lop-zoom/` bằng tài khoản không đủ quyền chỉ dẫn tới hướng dẫn đăng ký; không cấp quyền GET classes/:id, bảng điểm hay học phí. Các kiểm tra entitlement/enrollment giữ nguyên.

## Điều khiển Đấu trí v3 và menu điện thoại (11/11/2026)

Đấu trí có ba tab Đấu nhanh / Với bạn / Với máy; ba mức bot truyền level 0/1/2. Không có điều kiện thắng ba trận để mở bot Khó theo ảnh tham khảo. Chỉ đạo tiếp ngày 12/11/2026 đổi từ PA2 sang PA3: bấm tìm đối thủ/tạo phòng/chọn mức máy mở bước chọn nội dung trong dialog trên máy tính hoặc bottom sheet trên điện thoại. Nhãn trường là **Chọn nội dung thi đấu**; hai lựa chọn là Chương trình trên lớp / Kiến Thức Tổng Hợp (`weekly` / `all`). Mỗi lần mở đều chọn sẵn Chương trình trên lớp, kể cả trước đó đã chọn Kiến Thức Tổng Hợp. Chỉ xác nhận mới tạo/tìm trận hoặc dùng lượt bot; hủy/Escape/quay lại không dùng lượt. Tạo phòng vẫn chọn được Bạn bè/Tất cả; khi vào phòng bằng mã hoặc thách đấu, nội dung do chủ phòng quyết định. Hình phạt hiện có tiếp tục được kiểm khi mở và xác nhận bắt đầu. Luật mở sẵn chỉ còn bốn thẻ luật và ba ô kinh nghiệm; không có đoạn chú thích cuối. Không hiện thông báo nhắc nhở chung khi không bị nghỉ đấu; lúc đang nghỉ vẫn hiện thời gian còn lại. Điện thoại/màn ngang hẹp dùng hamburger trên header sticky, đủ các link học tập, đóng bằng X/nền/Escape và khi chuyển trang; desktop giữ sidebar.

Zoom khách/Free/VIP chỉ còn phần tư vấn/điều hướng và thẻ SVip vàng dùng chung với Nâng cấp gói. Ba thẻ giới thiệu nhỏ cũ đã bỏ. Xếp hạng còn Linh vật/Chăm chỉ, bỏ badge Em và giữ nền dòng mình. Các API/data học tập/nhân sự, quyền lớp và quota không thay đổi do đợt UI này.

## Thời gian mỗi câu Đấu trí (11/11/2026)

| Khối | Thời gian mỗi câu |
| --- | --- |
| 1–2 | 60 giây |
| 3–4 | 120 giây |
| 5, câu mức Khó | 240 giây |
| 5, các mức còn lại | 180 giây |

Áp dụng đấu người và đấu bot. Độ khó tính theo từng câu thực tế, mức Khó có chỉ số 2 trong dữ liệu Arena/LearningContent (tương ứng nhãn Khó, số 3 trong trình quản trị). Thời gian bắt đầu sau chuẩn bị ba giây ở câu đầu trận người (bot giữ năm giây); mỗi câu tiếp theo tính lại, chuyển câu vẫn nghỉ ba giây. Bot chờ 70% đầu và trả lời trong 30% cuối nếu đủ trình độ; hết giờ không ghi nhận đòn trả lời muộn. Deadline trận người do server quyết định và gửi chung cho hai phía. Thời hạn lưu phòng tính đủ tổng thời gian 20 câu cùng chờ/thách đấu/chuẩn bị/chuyển câu, thay giới hạn 30 phút cũ; vẫn hủy phòng chờ sau năm phút. Để chịu được việc điện thoại tạm ngừng poll khi đọc đề, ngưỡng mất kết nối là thời lượng câu dài nhất trong trận cộng 60 giây (120–300 giây); yêu cầu hợp lệ của người quay lại được cập nhật hiện diện trước khi dọn phòng. Rời trận chủ động vẫn kết thúc ngay và phòng vẫn có hạn lưu hữu hạn.

## Đăng ký Zoom và khảo sát đầu vào (11/11/2026 — cập nhật mới nhất)

Quy tắc mới thay các đoạn mở Zoom cho tất cả ở trên: menu **Lớp Zoom chỉ dành cho SVip**. Tab **Đăng ký học Zoom** ở `/dang-ky-hoc-zoom/` chỉ hiện trong menu khách/Free/VIP; tài khoản **SVip ẩn tab đăng ký và giữ Lớp Zoom**. URL đăng ký vẫn được giữ. Thẻ vàng dùng chung helper với Nâng cấp gói, riêng tab mới có tiêu đề Học Zoom online, Học phí: 100k/buổi và ba CTA khảo sát/Zalo/Facebook. Free/VIP mở sâu `/lop-zoom/` chỉ thấy thông báo quyền và link đăng ký; API lớp vẫn kiểm tra entitlement/ghi danh.

Khảo sát công khai `/dang-ky-kiem-tra-dau-vao/` có HTML đầy đủ ngay khi tắt JavaScript. GET `/api/v1/admissions/token` cấp cookie HttpOnly/SameSite và token biểu mẫu ngắn hạn; POST `/api/v1/admissions` nhận thông tin phụ huynh/học sinh, khối, tỉnh/thành, mục tiêu, mức hiện tại, khung giờ, kênh liên hệ, ghi chú và đồng ý liên hệ. Tên trường tùy chọn: email/trường/ghi chú. Không yêu cầu tài khoản. Có kiểm tra Origin/token, định dạng/độ dài, honeypot, tối đa năm đăng ký/IP/giờ trong RAM và khóa yêu cầu chống gửi trùng; không lưu IP vào hồ sơ. Gửi lại cùng nội dung/mã giữ cùng reference; không có API công khai đọc hồ sơ. Access log bỏ query để tránh ghi nội dung tìm kiếm liên hệ.

Migration `0008_entrance_registrations.sql` thêm bảng `entrance_registrations`, tổng localhost 56 bảng nghiệp vụ + schema_migrations/9 migration. Hồ sơ lưu consent version và mã DV ngẫu nhiên. Admin GET `/api/staff/admissions?q=...&page=1`, POST `/api/staff/admissions/:id` với status/note/revision; giữ CSRF staff, kiểm tra quyền admin, phát hiện sửa đồng thời và audit chỉ mã/trạng thái. Giáo viên và khách không xem/sửa hồ sơ.

Khảo sát mới chỉ nhận dữ liệu khi có backend Python. Bản tĩnh Cloudflare/GitHub khóa nút gửi, hướng sang Zalo/Facebook; không hiển thị xác nhận lưu giả. Chưa gửi tin nhắn/email tự động, chưa có giao diện xóa hồ sơ hoặc form builder. Phụ huynh có thể yêu cầu sửa/xóa qua kênh liên hệ, admin xử lý theo vận hành hiện tại. Ngân hàng vẫn chờ cấu hình.


## Bảng kết quả và tự chuyển câu Đấu trí (12/11/2026)

`battle.roundOutcome` gồm `waiting`, `correct`, `wrong`, `opponent`, `timeout`; `roundReason` là `null` khi chưa kết thúc hoặc `correct`, `both_wrong`, `timeout`. Dữ liệu này không lộ đáp án/steps trước kết quả trận. Người đã trả lời sai giữ trạng thái `wrong` dù đối thủ trả lời đúng sau đó. Khi cả hai bỏ trống, server chốt `timeout`, giữ máu, đặt `nextAt` sau ba giây và tự đổi câu qua poll; không cần thao tác trả lời/next từ một trong hai người.

Khung câu hỏi chuyển thành bảng kết quả có “Hãy chuẩn bị cho câu X” và số đếm 3–2–1. Trả lời sai khi câu chưa chốt thì hiện đang chờ và thời gian còn lại, chưa đếm ngược câu tiếp theo. Câu cuối/đòn kết thúc trận chuyển sang lời nhắc xem kết quả, không có câu 21. Giữ chiều cao khung và vị trí cuộn; biểu cảm/Rời trận tiếp tục dùng được. Khi tab trở lại/focus, poll/tick được đồng bộ ngay sau khi hồ sơ đăng nhập sẵn sàng. Lỗi mạng tạm giữ phiên để thử lại; lỗi phòng thực sự hết hạn/không hợp lệ xóa phiên và về Đấu trí thay vì để màn chiến đấu đứng 00:00.


## Giới hạn cổ vũ (12/11/2026)

Mỗi người có thể gửi một lời cổ vũ mỗi 5 giây, độc lập với người còn lại. `battle.emoteAvailableAt` là thời điểm epoch ms được gửi tiếp (0 khi chưa gửi); `emoteUsed` tương thích cũ nay nghĩa là đang trong thời gian chờ. Đổi câu không đặt lại mốc này. Gửi sớm hoặc giá trị không hợp lệ không làm tăng thời gian chờ. Bong bóng giữ 4 giây, kể cả khi sang câu mới. Giao diện bot/phòng thật làm mờ cả dàn icon và khóa các nút ngay khi gửi, tự mở lại sau 5 giây; không có dòng thông báo dưới icon.


## Phong cách thông báo trận đấu (12/11/2026)

Bảng kết quả phân biệt cả nền, viền, biểu tượng, tiêu đề và màu số đếm: trả lời đúng dùng xanh lá, trả lời sai dùng đỏ hồng dịu, bạn trả lời nhanh hơn dùng cam ấm, hết giờ dùng màu trung tính. Số đếm câu tiếp theo chỉ hiện 3–2–1, bỏ đơn vị “giây”. Nội dung và biểu tượng vẫn phân biệt trạng thái để không phụ thuộc riêng màu sắc.


## Hiệu ứng ngẫu nhiên cho mỗi đòn đánh (12/11/2026)

Mỗi đòn gây sát thương chọn một trong `rock`, `vine`, `lightning` với khả năng như nhau; được phép lặp lại cùng hiệu ứng ở hai đòn liên tiếp. Đấu người: server chỉ bốc một lần trong nhánh trả lời đúng có giảm HP, lưu `lastAttack={id,spell,index,attacker}`; `attacker` là `me` hoặc `opponent` theo người đang xem. ID/phép/index giống nhau cho hai phía, không công khai token. Trả lời sai/hết giờ/cổ vũ/poll lại không bốc phép. Đổi câu và kết quả cuối vẫn gửi đòn mới nhất để hỗ trợ bỏ lỡ một lượt poll; đây không phải lịch sử để phát lại mọi đòn bỏ lỡ.

Bot lưu cùng metadata trong session ngay khi gây sát thương. Lớp hiệu ứng riêng dùng ba WebP có sẵn, hiển thị trên sân cho cả linh vật dùng hoạt cảnh riêng và linh vật dùng sprite chung, không bị các module ghi đè. Chặn hiệu ứng chung cũ để tránh hai phép chồng nhau, giữ hoạt cảnh đánh/chịu đòn/chiêu cuối hiện có; âm thanh đòn thường theo phép được chọn. Đòn thường hiện1,5s; đòn kết thúc thêm tác động ở1,75s trong1s, nằm trong hoạt cảnh cuối3s hiện có. Lớp được giới hạn trong sân, không chặn chạm, giảm chuyển động dùng ảnh tĩnh, dọn khi đổi trang/khung. Không đổi HP/XP/deadline/cooldown/luật.

## Bỏ trận, thống kê và thời gian nghỉ (12/11/2026)

- Chủ động rời sau khi câu đầu bắt đầu: thua và −1 kinh nghiệm, sàn 1.000. Người ở lại thắng do đối thủ rời nhưng nhận 0 kinh nghiệm và được hoàn lượt `human` đã dùng cho trận đó. Trận không hoàn thành ghi `duels.status='abandoned'`; **không cộng số thắng/thua của cả hai**, kể cả phòng bạn bè. Phòng bạn bè hoàn thành bình thường vẫn tính kinh nghiệm và thống kê như trước. Bot không tính XP hoặc vi phạm đấu với người.
- Lần vi phạm đầu trong cửa sổ 24 giờ được nhắc nhở; lần 2/3/từ lần 4 có thời gian nghỉ đấu với người 300/900/3.600 giây. Hạn chế áp dụng cả Free/VIP/SVip và mọi đường tạo/tìm/vào/chấp nhận phòng; học và bot vẫn dùng được. Tải lại trang, phiên đăng nhập mới hoặc restart server không xóa thời gian nghỉ đã lưu.
- Hủy khi waiting/challenged/preparing không phạt; nếu đã ghi lượt khi accept thì hoàn lượt cho cả hai khi hủy trước câu đầu. Kết quả đã chốt do HP 0 hoặc câu 20 không bị đổi thành bỏ trận khi rời màn hình, kể cả lúc đang chờ hiệu ứng cuối.
- Giữ khoảng chờ kết nối lại hiện có (câu dài nhất +60 giây). Lần ngắt kéo dài đầu tiên trong 24 giờ có sự kiện `disconnect` nhưng không tạo strike hoặc trừ XP; lần lặp lại tạo strike và điểm phạt. Đóng tab và mất mạng thật không thể phân biệt chắc chắn; có thời gian quay lại trước khi ghi vi phạm. Khi cả hai hết thời gian nối lại, xử mỗi người theo lịch sử riêng, không có người nhận XP/hoàn lượt vì ở lại.
- Sự kiện được lưu ở migration `0010_arena_discipline.sql`, duy nhất theo trận/học sinh. Máy chủ chốt kết quả, XP, hoàn lượt và vi phạm một lần, kể cả khi gửi lại yêu cầu hoặc bên kia chưa poll. Chốt các trận cũ trước khi kiểm tra điều kiện vào trận mới, nên đổi luồng không tránh được hình phạt. Phòng hoạt động vẫn trong RAM: restart server không được coi là hành vi bỏ trận của người dùng.

API phiên và phản hồi arena có `arenaDiscipline={availableAt,remainingSeconds,recentAbandons,recentStrikes,warning,freeDisconnectAvailable}`. `availableAt` dùng epoch ms; 0 khi không có thời gian nghỉ. HTTP 429 do thời gian nghỉ cũng gửi trường này để giao diện đồng bộ ngay. `recentAbandons` gồm cả lần mạng được miễn; `recentStrikes` chỉ đếm vi phạm có hình phạt.

Kết quả có `completed`, `reason`, `quotaRefunded`, `penalty={kind,strike,cooldownSeconds,xpDelta,disconnectForgiven}`; `points` là XP thực tế sau áp dụng sàn. Giao diện nói rõ trận bỏ dở không tính thống kê, đối thủ rời không nhận XP, lượt được hoàn và thời gian được đấu tiếp. Trước khi chủ động rời trận đang chơi có xác nhận; hủy trước câu đầu không hiển thị cảnh báo điểm phạt.

### Nội dung thông báo và tương thích HTTP LAN

Các thông báo học sinh không giải thích sàn kinh nghiệm; giữ quy tắc tính và giá trị XP thực tế. Lobby không có thẻ nhắc Tùy chọn trận đấu hoặc banner nhắc nhở chung. Luật không có các đoạn chú thích nhỏ phía cuối; banner thời gian nghỉ vẫn hiện khi thực sự bị hạn chế và ẩn khi hết hạn.

Trình duyệt mở địa chỉ LAN qua HTTP có thể không cung cấp `crypto.randomUUID()`, dù cùng trình duyệt vẫn có hàm này tại localhost. Helper tạo ID của khu học tập dùng native `randomUUID` nếu có, còn lại tạo UUID v4 bằng `crypto.getRandomValues()`; không dùng Math.random cho ID. Cách này sửa lỗi xác nhận đấu bot dừng trước POST `bot/start` trên điện thoại dùng HTTP LAN; API, hạn mức và điểm bot không thay đổi.

## Tính học phí mỗi buổi — 12/11/2026

- `POST /api/staff/classes` nhận thêm `sessionFee` là số nguyên đồng 0–1.000.000.000. Chỉ admin đổi được đơn giá. Không gửi trường này trên client cũ thì giữ giá cũ/NULL. Class response có `session_fee`; NULL là chưa cấu hình, 0 là miễn phí.
- `POST /api/staff/classes/:id/fees/preview` nhận `{month:"YYYY-MM"}`, trả `{classId,className,month,sessionFee,previewToken,rows,totals}`. Chỉ đọc dữ liệu, không lập phí. Theo tháng Việt Nam; charged được nhân giá, free/absent/null không tính. Nhiều buổi cùng ngày vẫn đếm riêng. Roster gồm hiện tại, điểm danh tháng và fee cũ; tài khoản không đủ điều kiện và khoản đã trả bị khóa.
- Mỗi row có studentId/fullName/accountId/historical/eligible, số buổi chargedCount/freeCount/absentCount/pendingCount, amount/existingAmount/calculatedAmount, feeId/paidAt/source/locked/lockedReason, changed và sessions với id/title/startsAt/date/status. `amount` của hàng khóa là khoản đã lưu, không phải số dự kiến thay thế. `previewToken` ràng buộc dữ liệu giá/lớp/học sinh/điểm danh/fee/orders tại lúc xem.
- `POST /api/staff/classes/:id/fees/calculate` nhận `{month,previewToken,requestKey}`. Server tính lại; nguồn thay đổi trả409, không tin số tiền do client gửi. Thành công trả class_detail và `calculation:{id,month,created,updated,unchanged,paidLocked,notificationsSent,totalAmount,replayed}`. Cùng key/payload trả kết quả cũ; key cũ với bảng khác409. Teacher chỉ lớp được phân công; CSRF như các thao tác staff khác.
- `GET /api/staff/classes/:id/fees/:feeId` trả `{fee,sessions}` cho lớp thuộc quyền. Fee tính tự động có source=calculated, session_fee, charged_count/free_count/absent_count/pending_count, sessions_json, calculation_id/calculated_at; lịch đã lưu là nguồn hiển thị. API lớp của học sinh cũng dùng snapshot này và trả count/sessions, chỉ dữ liệu của chính mình. Khoản manual tiếp tục dùng điểm danh hiện tại.
- Lưu khoản mới/thay đổi ghi fee/snapshot/audit/notice trong cùng giao dịch; paid/inactive giữ nguyên, nội dung không đổi không spam. Đổi amount hủy payment_orders pending cũ; paid/history không sửa. Marker Học phí được thay bằng ID mới để readThrough cũ không đánh dấu nhầm cập nhật. Thông báo tài khoản giữ đầy đủ lịch sử, người gửi là nhân sự thực hiện.
- `POST .../fees` thủ công vẫn chỉ admin, giữ schema body cũ. Nếu sửa khoản đã tính tự động thành thủ công, xóa metadata tính/snapshot để không hiện công thức cũ; đổi tiền cũng hủy pending order cũ. Không có thanh toán cho khoản0đ và không tự đánh dấu0đ là đã trả tiền.

## Thanh toán SePay — 12/11/2026

Xem [PAYMENTS.md](PAYMENTS.md) và [.env.example](../.env.example) để cấu hình. API tài khoản và webhook dùng cùng SQLite. Tự động mặc định tắt; thiếu khóa HMAC tối thiểu32ký tự/thông tin ngân hàng thì fail closed.

- POST /api/webhooks/sepay: application/json rawbytes, tối đa16.384byte, Content-Length duy nhất, không Transfer-Encoding; HMAC-SHA256(timestamp.raw_body), cửa sổ300giây. Không dùng cookie/CSRF học sinh, không nhận accountId của client làm đích cấp quyền. Thành công201 {success:true} sau commit; mockid0 không ghi tiền; sai xác thực401/nội dung400/415/413, database503.
- GET /api/v1/payments/:id: session đúng chủ, đơn khác404, đọc không tạo đơn. order giữ schema cũ và thêm kind,vip_months,vip_unit_price,fee_student_id/fee_class_id/fee_month,bank_id/bank_account/bank_name,paid_at,confirmed_source,receipt_id,automationEnabled. Không trả secret hoặc payload ngân hàng gốc.
- POST payments: {} VIP hoặc {feeId} học phí. BM+20hex cho đơn mới; pending có tiền đổi bị hủy và tạo đơn mới, không sửa QR cũ. Ngân hàng chỉ chụp khi cấu hình hợp lệ; đơn cũ trống ngân hàng chỉ gắn lại khi chủ mở POST thông tin thanh toán.
- GET /api/staff/payment-receipts?page=1&status=all&q=: chỉadmin,25dòng/trang. Trả rows,total,page,pageSize,automationEnabled; mỗi dòng có id,provider,transaction_id,order_id,status,reason,reasonLabel,amount,reference,bank,bank_account,bank_reference,transaction_at,received_at. status processed/review/ignored; tìm mã thanh toán/tham chiếu/mãgiao dịch. Không có hành động tự gán khoản không khớp tài khoản.
- Staffconfirm dùng cùngsettlement với webhook: kiểm tài khoản/học sinh active, snapshot sản phẩm/phí, khóa cấp trùng. Paid replay không ghi lặp audit/thông báo. Tiền tuition tạo thông báo hoàn tất đúngchủ;VIP dùng trigger thánglịch/referral lần đầu,SVip giữcustomer_service.
- MAM_TOAN_PUBLIC_ORIGIN trống choHTTPcục bộ; đặt đúngHTTPSorigin trênmáychủchínhthức đểkiểmyêucầughi vàSecurecookie student/staff. Không tin X-Forwarded-* từclient. Luồng chính thức dùng cùngorigin, chưa mởCORSliênmiền.

### Giao diện học sinh — 12/11/2026

`state.theme` có trong snapshot tài khoản/session. `POST /api/v1/preferences` chỉ nhận `{theme}` với một trong: `garden-adventure` (04, mặc định), `morning-garden` (01), `crayon-workshop` (02), `clay-sprout` (03), `garden-notebook` (05). ID lạ, sai kiểu, thiếu/trường thừa bị từ chối. Thao tác dùng phiên học sinh hiện tại, CSRF và kiểm Origin; client không được chỉ định student/account khác. Lưu theme giữ nguyên last_lesson và tiến độ.

Bộ chọn trong Tài khoản xem trước chỉ đổi thuộc tính giao diện trên document, không ghi server hoặc tải lại trang. Áp dụng mới lưu; Hủy hoặc rời trang trả về lựa chọn đã lưu. Client cache riêng guest/tài khoản để hiển thị sớm; server là nguồn chính cho tài khoản. Đăng xuất xóa cache tài khoản, không nhập lựa chọn guest vào tài khoản. Bộ đếm phiên phía client chặn response cũ sau đăng nhập/đăng xuất ghi đè hồ sơ/giao diện mới.