# Cơ sở dữ liệu 5BMath

Cập nhật ngày 12/11/2026. Cơ sở dữ liệu dùng SQLite tại localhost và Cloudflare D1 tại website. Lược đồ Python được quản lý trong `backend/migrations/`, gồm các phần tài khoản, RedUpdatev1, quản trị, mở rộng Lớp Zoom (`0013`–`0014`) và xác nhận hỗ trợ thưởng giới thiệu (`0015`). Việc bổ sung migration cục bộ không tự cập nhật D1 công khai. Xem [luồng localhost và API](LOCAL_API.md), [trang giáo viên và quản trị](STAFF_PORTAL.md); kiểm tra trạng thái triển khai thực tế trước khi áp dụng lên website.

Migration `0007_staff_management.sql` bổ sung `staff_users`, `staff_sessions`, `staff_audit_log`, `system_settings`; thêm revision cho dữ liệu lớp/học liệu và trạng thái nháp/phát hành bài giảng. Phiên nhân sự tách khỏi phiên học sinh. Giáo viên chỉ thao tác lớp được phân công, admin quản lý toàn hệ thống. Cập nhật câu hỏi tạo phiên bản mới và sao chép liên kết ảnh, giữ nguyên đề đã sinh.

## Các nhóm bảng

| Phạm vi | Bảng |
| --- | --- |
| Tài khoản, khối và lớp | accounts, students, grades, academic_years, student_grades, teachers, online_classes, class_enrollments, access_entitlements |
| Buổi học và bài tập Zoom | class_sessions, class_assignments, class_attendance, class_scores, class_session_comments, class_assignment_comments, class_submissions, class_notices, class_fees |
| VIP và giới thiệu | vip_purchases, account_referrals, referral_reward_confirmations, notifications |
| Học liệu và hình ảnh | topics, lessons, questions, question_versions, media_assets, question_assets, lesson_assets |
| Form và đề thi | schools, source_papers, source_paper_topics, exam_forms, exam_form_topics, exams, exam_items, exam_attempts, exam_answers |
| Đấu trí và linh vật | mascots, mascot_levels, mascot_variants, student_companions, bots, duels, duel_players, duel_rounds, duel_answers |
| Tiến độ và xếp hạng | lesson_progress, online_intervals, xp_events |

Một tài khoản gắn với tối đa một dòng học sinh qua khóa duy nhất `students.account_id`. Học sinh không tự đổi năm sinh; admin có thể sửa theo chỉ đạo ngày 12/11/2026, có quyền đổi được kiểm tra và nhật ký. Bản ghi học sinh demo cũ được giữ khi migration bổ sung cột liên kết tài khoản. Khối của từng năm lưu ở `student_grades`.

Quyền nội bộ lưu trong `access_entitlements`, có khoảng hiệu lực và liên kết ghi danh. Mốc VIP hiện tại lưu trong `accounts.vip_expires_at`, được cập nhật bởi sự kiện nâng cấp đã xác nhận hoặc thưởng giới thiệu.

## Cộng tháng và thông báo

`backend/membership.py` cung cấp `record_vip_purchase` để ghi nhận sự kiện mua VIP đã được máy chủ xác nhận. Sự kiện có mã duy nhất `payment_ref`. Truyền lại cùng mã với cùng tài khoản và gói trả kết quả đã ghi. Truyền lại mã cho tài khoản khác bị từ chối.

Trigger thực hiện trong cùng giao dịch với lần mua.

1. Gia hạn tài khoản mua từ mốc VIP hiện tại nếu còn hạn, hoặc từ thời điểm xác nhận nâng cấp.
2. Ghi mốc nâng cấp đầu tiên của tài khoản được mời.
3. Cộng một tháng lịch cho người mời nếu đủ điều kiện, hoặc ghi trạng thái `customer_service` cho người mời có quyền nội bộ đang hiệu lực.
4. Lưu mốc hết hạn ngay sau thưởng và một thông báo tới người mời.

Một tháng lịch tính theo giờ Việt Nam, giữ giờ trong ngày và dùng ngày cuối tháng nếu thiếu ngày tương ứng. Ví dụ 31/01/2027 cộng một tháng là 28/02/2027. Ngày giờ được lưu theo UTC.

Mỗi người được mời có một người mời. Cặp giới thiệu và sự kiện mua hợp lệ là duy nhất. Những lần gia hạn tiếp theo tiếp tục tăng VIP cho người mua. Phần thưởng giới thiệu gắn với lần nâng cấp đầu tiên.

Thông báo nằm trong database. Trên localhost, trang Tài khoản đã đọc thông báo, lịch sử giới thiệu và cho đánh dấu đã đọc theo phiên đăng nhập. Bản demo công khai vẫn hiển thị tài khoản mẫu. Cổng thanh toán và chính sách thu hồi thưởng khi hoàn tiền còn chờ. Bản duyệt localhost có sự kiện nâng cấp thử được bật bằng cờ riêng, không thu tiền.

## Năm ví dụ mẫu

Mốc thử cố định là 11/11/2026. Năm tài khoản có mã DEMO-01 đến DEMO-05. Các tình huống dùng chung một số tài khoản.

| Ví dụ | Kết quả cần thấy |
| --- | --- |
| Người mời đang VIP | DEMO-01 từ hạn 31/01/2027 được thưởng tới 28/02/2027 |
| Gửi lại cùng sự kiện | Sự kiện nâng cấp đầu của DEMO-02 gửi lại hai lần vẫn có một thưởng và một thông báo |
| Người được mời gia hạn | DEMO-02 có hai lần mua, DEMO-01 vẫn có một phần thưởng giới thiệu |
| Người mời đang Thường | DEMO-03 nhận thưởng tới 11/12/2026 khi DEMO-04 mua lần đầu |
| Người mời nội bộ | DEMO-05 nhận thông báo liên hệ chăm sóc khách hàng khi DEMO-03 mua lần đầu |

Sau đó DEMO-03 còn mua VIP cho chính mình. Hạn VIP hiện tại của tài khoản này là 11/01/2027, còn mốc ngay sau thưởng được giữ riêng là 11/12/2026.

Chạy `python -m backend.demo_seed` để khởi tạo và thêm mẫu vào database mặc định. Chạy lại seed giữ các bản ghi đã tạo. Có thể chọn database riêng bằng `--database`. Để xuất SQL cho D1, dùng `--export-sql work/demo-seed.sql`.

Bảng kiểm tra database đã bỏ khỏi Góc học tập theo RedUpdatev1. API đọc mẫu vẫn giữ để kiểm tra kỹ thuật và chỉ truy vấn các mã DEMO đã quy định.

## Công thức, hình ảnh và phiên bản

Câu hỏi, lời giải và gợi ý lưu thành mảng JSON gồm ba loại khối.

- `text` có nội dung văn bản.
- `math` có nguồn LaTeX và bản MathML để trình duyệt hiển thị.
- `image` tham chiếu `media_assets.id`.

`media_assets` lưu đường dẫn tệp, kiểu tệp, dung lượng, chiều rộng, chiều cao và mô tả. `question_assets` và `lesson_assets` nối ảnh với nội dung. Tệp ảnh được phục vụ riêng, có thể chuyển sang kho tệp khi mở rộng.

Năm bài mẫu gồm phân số, phần trăm, diện tích hình chữ nhật, hai lần thay đổi phần trăm và tổng số lẻ. Cả đề bài và lời giải có ví dụ công thức, hình minh họa. Bộ kiểm tra nội dung chỉ chấp nhận các phần tử MathML được quy định.

`question_versions` giữ nội dung đúng theo phiên bản. Khi phiên bản đã được đưa vào đề hoặc trận, hệ thống yêu cầu tạo phiên bản mới để sửa nội dung. Một đề đã bắt đầu giữ danh sách câu. `exam_attempts.exam_id` duy nhất để một đề đã sinh có một lần làm. Mỗi lần tạo đề tiếp theo cần một mã đề mới.

## Tốc độ truy xuất

Bản D1 có 43 chỉ mục khai báo riêng, ngoài các chỉ mục từ khóa chính và khóa duy nhất. Migration tài khoản localhost bổ sung chỉ mục tra phiên, bài học và khóa chống tạo đề trùng. Ba đường truy vấn đã kiểm tra bằng `EXPLAIN QUERY PLAN` sử dụng chỉ mục.

| Truy vấn | Chỉ mục |
| --- | --- |
| Danh sách câu theo khối và chuyên đề, phân trang theo mã | questions_pool |
| Hộp thông báo theo tài khoản và thời gian | notifications_inbox |
| Lịch sử đề theo học sinh và thời gian | exams_owner_history |

Phần dữ liệu để lọc ngân hàng câu hỏi nằm trong `questions` và các cột phân loại của `question_versions`. Truy vấn danh sách nên lấy mã, tiêu đề và thông tin phân loại, rồi tải JSON nội dung khi mở câu. Khi chọn câu ngẫu nhiên, có thể chọn trong danh sách mã đủ điều kiện và chỉ tải nội dung các câu đã chọn.

Danh sách lịch sử và thông báo dùng giới hạn số dòng cùng mốc thời gian/mã của trang trước. Ảnh có kích thước sẵn, tải trì hoãn, MathML dùng khả năng có sẵn của trình duyệt. SQLite cục bộ bật WAL để hỗ trợ truy cập đồng thời. Số liệu này xác nhận cấu trúc truy vấn và tính đúng của giao dịch. Cần đo tải thực tế khi các luồng tài khoản và học tập đầy đủ được đưa vào ứng dụng.

Phép đo SQLite cục bộ với 50.000 dòng câu hỏi giả, trang 20 dòng và 100 lần truy vấn cho P95 khoảng 0,02 ms. Kế hoạch sử dụng `questions_pool`. Phép đo này thực hiện trên database thử và bộ nhớ đệm tại máy phát triển. Tệp kết quả nằm ở `work/database-platform/query-performance.json`.

## Migration và kiểm tra

- Python áp dụng migration một lần khi khởi tạo, có bảng theo dõi `schema_migrations`.
- D1 dùng `wrangler d1 migrations apply 5bmath-demo --remote` và bảng theo dõi của Wrangler.
- Có bản xuất D1 trước đợt cập nhật trong `work/database-platform/d1-before-platform.sql`.
- Kiểm tra gồm ngày cuối tháng, năm nhuận, giờ Việt Nam, sự kiện gửi lại, nhiều giao dịch đồng thời, rollback nếu thông báo lỗi, năm sinh cố định, dữ liệu cũ, nội dung toán và chỉ mục.

## RedUpdatev1 — migration 0006 (11/11/2026)

Bảy bảng mới: `daily_usage`, `class_sessions`, `class_assignments`, `class_scores`, `class_attendance`, `class_fees`, `payment_orders`; thêm `online_classes.schedule/curriculum`. Migration giữ dữ liệu có sẵn. Database Python có 51 bảng nghiệp vụ và bảy migration; D1 công khai chưa áp dụng đợt này.

Lượt dùng có chỉ mục theo học sinh/ngày Việt Nam/loại và khóa chống ghi trùng; tạo đề/ghi lượt trong cùng giao dịch BEGIN IMMEDIATE. Lượt với người được ghi cho cả hai tài khoản khi chủ phòng chấp nhận; bot tính lúc bắt đầu. Quyền nội bộ đang hiệu lực được gọi SVip trên UI, vẫn dùng access_entitlements hiện có.

Điểm từ 0–10 theo bài/học sinh. Hoàn thành buổi khi có ít nhất một bài và tất cả bài đã có điểm, kể cả điểm 0. Trung bình tháng tính các bài đã chấm trong tháng địa phương; chu kỳ 14 ngày tính từ instruction_starts_on của năm học. Học phí theo tháng/học sinh/lớp, số buổi tính phí lấy điểm danh charged; free và absent hiển thị riêng. API không cho học sinh tự sửa điểm/điểm danh/học phí.

Đơn thanh toán chờ có mã duy nhất, một đơn chờ cho tài khoản/loại học phí; số tiền do máy chủ lấy từ giá VIP hoặc hóa đơn của mình. QR chưa được tạo khi thiếu cấu hình ngân hàng. Mở đơn không cấp quyền VIP. Chưa có webhook xác nhận hoặc chính sách đối soát/hoàn tiền.

Catalog giữ 20 bài gốc, thêm ba bài ôn tập tuần sau mỗi khối, id ổn định theo năm/tuần. Không dựng dữ liệu lớp thật; fixture lớp, điểm và học phí chỉ nằm ở work/red-update-v1/ui.sqlite3.

### Khảo sát kiểm tra đầu vào

Migration 0008 thêm `entrance_registrations`: mã đăng ký ngẫu nhiên, request_key/payload_hash chống gửi trùng, thông tin phụ huynh/học sinh và chi tiết khảo sát JSON, đồng ý liên hệ/phiên bản consent, trạng thái tư vấn, ghi chú nội bộ, revision và thời điểm. Không gắn quyền học hoặc tự tạo học sinh. Chỉ admin đọc/cập nhật qua API nhân sự; không có API đọc hồ sơ công khai. Xem LOCAL_API.md và STAFF_PORTAL.md.

### Quản lý tài khoản — migration 0009 (12/11/2026)

`accounts.revision` kiểm tra thay đổi đồng thời; `deleted_at` đánh dấu tài khoản đã xóa khỏi sử dụng, có chỉ mục cùng trạng thái và ID. Xóa giữ nguyên các khóa chính và lịch sử học tập/thanh toán, đặt tài khoản suspended/học sinh inactive, thu hồi phiên và mã đấu trí, kết thúc ghi danh/quyền lớp. Quyền lớp dự kiến chưa bắt đầu được hủy để không tự kích hoạt sau khôi phục. Khôi phục giữ suspended và không nối lại ghi danh cũ. Tên đăng nhập được giữ dành riêng. Các thao tác lưu/xóa/khôi phục và audit nằm trong cùng giao dịch. Giới hạn năm sinh của bản 0009 được mở riêng cho admin ở migration 0011 bên dưới.

### Admin sửa hồ sơ và quyền gói — migration 0011 (12/11/2026)

Thay trigger năm sinh cố định bằng cơ chế giấy phép sửa một lần `admin_birth_year_permits`: chỉ admin đang hoạt động, đúng tài khoản/năm cũ/năm mới, cùng giao dịch; trigger tiêu thụ giấy phép khi sửa. UPDATE năm sinh trực tiếp không có giấy phép vẫn bị chặn. API học sinh không nhận quyền này. Khi sửa, cập nhật `students.grade_level` và UPSERT `student_grades` của năm học hiện tại; không đổi khối lịch sử hoặc các đề đã sinh.

Gói thủ công dùng các trường/bảng hiện có: `accounts.vip_expires_at` cho VIP, `access_entitlements` loại internal không gắn enrollment cho SVip. Hạ/đổi gói kết thúc các quyền cũ, hủy quyền tương lai, giữ phân công lớp và lịch sử thanh toán/giới thiệu. Không tạo `vip_purchases`, đơn tiền hoặc thưởng. Cùng gói/hạn là thao tác không đổi quyền. Trigger tăng revision khi kinh nghiệm/linh vật, hạn VIP hoặc quyền nội bộ thay đổi, để form admin cũ không ghi đè dữ liệu vừa cập nhật.

### Thông báo nhân sự và hệ thống — migration 0012 (12/11/2026)

Mở rộng `notifications` với tiêu đề, tên/vai trò/người gửi, liên kết broadcast hoặc purchase. Giữ nguyên ID, account/referral, loại cũ, nội dung, created_at/read_at của thông báo có sẵn; bổ sung tiêu đề và người gửi hệ thống. Khi thay bảng, tạm gỡ rồi dựng lại `vip_purchase_apply` trong cùng migration để giữ liên kết trigger và toàn bộ quy tắc cộng tháng lịch/giới thiệu. Không gửi lại sự kiện thanh toán cũ.

`notification_broadcasts` lưu nội dung, phạm vi, người gửi, thời điểm, số người nhận và request_key duy nhất theo người gửi. `notification_broadcast_recipients` chốt tập tài khoản nhận tại lúc gửi, khóa chính theo broadcast/account. Một thông báo inbox mỗi broadcast/account và một thông báo thành công mỗi purchase được bảo vệ bằng UNIQUE. Thông báo thưởng giới thiệu tiếp tục dùng referral_id duy nhất.

Chỉ mục `notifications_priority` phục vụ tài khoản + chưa đọc trước + mới nhất; giữ cả chỉ mục inbox cũ và chỉ mục unread. API trả 5 dòng/trang, tổng unread đếm trên toàn inbox. Read kiểm tra chủ tài khoản và chỉ ghi read_at lần đầu. Gửi broadcast/delivery/notification/audit là một giao dịch. Trigger VIP tạo thông báo đăng ký lần đầu/gia hạn sau khi cộng hạn thành công, cùng giao dịch với thông báo thưởng giới thiệu, nên lỗi ghi thông báo cũng rollback xác nhận.

### Đơn giá lớp và tính học phí — migration 0014 (12/11/2026)

`online_classes.session_fee` là số nguyên đồng hoặc NULL khi lớp cũ chưa cấu hình; 0 là miễn phí. `class_fees` thêm source manual/calculated, đơn giá và số buổi từng trạng thái, lịch buổi học JSON, calculation_id và calculated_at. Các khoản cũ mặc định manual, không đổi tiền hoặc trạng thái thanh toán. Hóa đơn calculated dùng lịch/đơn giá đã lưu, manual tiếp tục tham chiếu điểm danh hiện tại.

`class_tuition_calculations` lưu lượt tính, người thực hiện, tháng, token nguồn, kết quả và request_key duy nhất theo nhân sự; `class_tuition_calculation_items` lưu hành động và snapshot mỗi học sinh. Preview không ghi dữ liệu. Save tính lại bằng dữ liệu máy chủ, đối chiếu token giá/điểm danh/hồ sơ/fee/payment để chặn dữ liệu cũ. Fee/audit/notification/class-unread ghi cùng giao dịch; paid/không đủ điều kiện giữ nguyên. Lưu lại cùng nội dung không gửi thêm, cùng request_key không tạo lượt mới.

Chỉ charged theo tháng Việt Nam được tính tiền; nhiều buổi cùng ngày vẫn riêng. Đổi tiền hủy payment_orders pending cũ, không sửa paid/history. Thông báo tài khoản loại staff_message mang người gửi thực tế. Marker class_notices của khoản thay đổi được thay bằng ID AUTOINCREMENT mới để readThrough cũ không tiêu thụ thông báo mới; toàn bộ hóa đơn và thông báo tài khoản cũ được giữ. Không chạy tính/gửi hóa đơn thật trong migration.

### Nhận xét, bài nộp và thông báo Lớp Zoom — migration 0013 (12/11/2026)

`0013_zoom_reviews_and_notices.sql` thêm bốn bảng, giữ nguyên dữ liệu điểm danh, điểm số và học phí đã có:

- `class_session_comments`: khóa chính `(session_id,student_id)`, nhận xét cá nhân sau buổi học. Tách khỏi `class_attendance` để lưu được nhận xét khi chưa chọn điểm danh; nhận xét chung của buổi trong `class_sessions.teacher_comment` vẫn giữ riêng.
- `class_assignment_comments`: khóa chính `(assignment_id,student_id)`, nhận xét bài làm. Tách khỏi `class_scores` để lưu khi chưa có điểm, không đưa điểm rỗng vào trung bình/xếp hạng. Điểm 0 vẫn là một điểm đã chấm.
- `class_submissions`: mã nộp tự tăng, bài tập/học sinh, tên/MIME/dung lượng, nội dung BLOB, SHA-256 và thời điểm nộp. Chỉ JPG/PNG/WebP/PDF, dung lượng 1–10.485.760 byte. API chỉ thêm bản nộp mới, giữ các bản cũ; cùng tên/nội dung với bản mới nhất trả lại bản đã có. Chỉ mục `class_submissions_latest` lấy bản mới nhất theo bài/học sinh. Nộp lại không xóa điểm hoặc nhận xét, nhưng tăng revision buổi học để nhân sự tải dữ liệu mới trước khi lưu.
- `class_notices`: lớp/học sinh, mục `assignments` hoặc `fees`, mã nguồn sự kiện, thời điểm tạo/đã đọc. Khóa duy nhất `(student_id,section,source_id)` chống nhân đôi sự kiện cùng loại; chỉ mục lọc `class_notices_unread` hỗ trợ số chưa đọc theo học sinh/lớp/mục.

Tạo bài tập mới ghi notice cho học sinh đang ghi danh trong lớp đang hoạt động; tạo khoản phí mới chỉ ghi cho học sinh được lập phí. Các tài khoản đã xóa/học sinh không hoạt động bị loại. Sửa bài tập hoặc học phí không phát lại notice, không tạo bù cho dữ liệu có trước migration hoặc học sinh ghi danh về sau. Ghi notice cùng giao dịch với bài tập/học phí; thao tác lớp và nhân sự giữ kiểm tra quyền hiện có. Giáo viên xem học phí, admin lập phí và đối soát.

`account.classroomUnread`/`GET classes/unread` tổng hợp theo quyền SVip, lớp đang hoạt động và ghi danh hiện tại. API chi tiết lớp trả `unread` cùng `readThrough` là mã notice lớn nhất theo mục của chính học sinh/lớp. Khi bấm Bài tập/Học phí, client gửi mục và mốc đã tải; UPDATE chỉ ghi `read_at` cho notice chưa đọc có ID không vượt mốc đó. Notice đến sau vẫn chưa đọc; tải lớp hoặc làm mới số đếm không tự đánh dấu. Bộ đếm lớp không dùng chung bảng inbox `notifications`.

Metadata lớp chỉ trả bản nộp mới nhất và đường dẫn API riêng, không trả BLOB. Tải tệp yêu cầu học sinh sở hữu vẫn có quyền SVip/ghi danh lớp, hoặc nhân sự có quyền lớp. Không đưa bài nộp vào danh sách tài nguyên công khai; phản hồi tải dùng `no-store` và `Content-Disposition: attachment`. Nội dung BLOB làm tăng dung lượng SQLite và bản sao lưu; chưa có kho tệp ngoài hoặc chính sách dọn các bản nộp cũ trong luồng này.

### Xác nhận hỗ trợ thưởng giới thiệu SVip — migration 0015 (12/11/2026)

`0015_referral_reward_confirmations.sql` thêm ledger `referral_reward_confirmations`: `referral_id` là khóa chính/khóa ngoại tới `account_referrals`, `confirmed_by` tham chiếu `staff_users`, `confirmed_at` lưu thời điểm xác nhận. Trigger chặn UPDATE/DELETE để giữ lịch sử. Migration không tạo xác nhận cho các quan hệ cũ và không đổi trạng thái thưởng, hạn VIP, quyền gói hoặc thanh toán.

Admin chỉ ghi xác nhận lần đầu cho quan hệ `customer_service` đã có lần nâng cấp VIP đầu và qualifying purchase đúng học sinh được mời, người giới thiệu hiện là SVip và chưa bị xóa. Xác nhận và audit cùng giao dịch; mỗi referral có tối đa một bản ghi. Gửi lại trả người/ngày xác nhận cũ, không tạo audit lần hai; replay vẫn đọc lại được sau khi gói của người giới thiệu thay đổi. Khớp `referrerAccountId` với quan hệ đã lưu trước khi xác nhận hoặc replay.

Ledger ghi nhận admin đã hỗ trợ nhận thưởng ngoài luồng cộng tháng, không cộng thêm tháng VIP và không ghi đè `account_referrals.reward_status`, `reward_granted_at` hoặc `reward_vip_expires_at`. Danh sách đối soát nối ledger để trả `supportConfirmedAt/supportConfirmedBy`; lịch sử của chính người giới thiệu nối cùng bản ghi để trả `support_confirmed_at` và hiển thị **Đã được hỗ trợ nhận thưởng**. Luồng thưởng VIP tự động hiện có tiếp tục dùng dữ liệu và quy tắc cũ.

### Thanh toán SePay — migration 0016 (12/11/2026)

payment_orders giữ nguyên ID/reference/amount/status và thêm snapshot kind/vip_months/vip_unit_price, fee_student_id/fee_class_id/fee_month, ngân hàng nhận bank_id/bank_account/bank_name, paid_at/confirmed_source/receipt_id. Backfill loại đơn và thông tin phí từ dữ liệu cũ; ngân hàng lịch sử và mốc thanh toán chưa biết giữNULL, không tự tạo purchase/notice/receipt hoặc đoán thời điểm paid cũ. Đơn mới BM+20hex; ngân hàng có thể gắn lần đầu khi chủ yêu cầu thông tin QR, sau đó giữ nguyên.

payment_receipts lưu provider sepay, transaction_id duy nhất theo provider, payload_hash chuẩn hóa, order_id nếu khớp, status processed/review/ignored, reason, số tiền/mã thanh toán/ngân hàng nhận/tham chiếu ngân hàng/thời gian. Không lưu sender, số dư hoặc rawpayload. Unique partial processed order bảo vệ một đơn chỉ cấp quyền một lần; trigger chặn sửa/xóa receipt để giữ lịch sử. Mã giao dịch cũ có payload khác trả409, không đổi quyền. Hai mã giao dịch khác nhau cho cùng đơn chỉ một processed; khoản sau review.

BEGIN IMMEDIATE bao receipt, kiểm lại account↔student↔fee/snapshot tiền/trạng thái, ghi vip_purchase hoặc fee.paid_at/notice và order.paid. Bất kỳ lỗi database rollback toàn bộ và cho provider retry. Cùng khóa purchase STAFF-ORDER-id cho webhook và admin giúp không cộng trùng giữa hai đường xác nhận. Học phí không phát referral. Sai tiền/tài khoản nhận/mã/đơn hủy/paid/khóa chủ/hóa đơn đổi lưu review; tiền ra ignored; mockid0 không lưureceipt. Chi tiết vận hành ở [PAYMENTS.md](PAYMENTS.md).

### Giao diện học sinh — migration 0017 (12/11/2026)

`learning_preferences.theme` là TEXT NOT NULL, mặc định `garden-adventure` (04 — Vườn Khám Phá), CHECK chỉ cho năm ID: garden-adventure / morning-garden / crayon-workshop / clay-sprout / garden-notebook. Khóa student_id có sẵn gắn một sở thích với đúng học sinh. Migration thêm cột/default vào hàng cũ, không thay last_lesson, bài làm, linh vật, XP, tài khoản, gói hoặc các bảng thanh toán. Tài khoản mới/hàng thiếu dùng mặc định04; API upsert chỉ theme. Không lưu CSS, HTML hoặc URL tùy ý trong database.