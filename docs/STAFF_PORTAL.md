# Trang giáo viên và quản trị 5BMath

Mở [Không gian giáo viên](http://localhost:8765/giao-vien/) và [Quản trị hệ thống](http://localhost:8765/quan-tri/). Hai trang dùng giao diện Vườn Toán, hoạt động trên Python/Docker cục bộ và có noindex.

## Đăng nhập và phân quyền

Tài khoản nhân sự có phiên đăng nhập riêng với tài khoản học sinh. Admin cấp tài khoản ở **Nhân sự & quyền**, chọn Giáo viên hoặc Quản trị viên. Có thể gắn với hồ sơ giáo viên đã có, tạo hồ sơ mới, đổi mật khẩu hoặc khóa truy cập.

Có thể đăng nhập nhân sự ngay trong popup **Đăng nhập** trên trang chủ localhost: admin được đưa tới trang quản trị, giáo viên tới không gian giáo viên. Hai URL riêng vẫn dùng được. Popup dùng cùng tên đăng nhập/mật khẩu nhưng server cấp cookie nhân sự riêng; quyền học sinh không được cấp theo tài khoản nhân sự.

Nhấn icon mắt trong ô mật khẩu để hiện/ẩn nội dung đang nhập. Mật khẩu mặc định được che mỗi khi mở lại form. Khi đăng xuất, hệ thống kết thúc phiên và đưa về trang chủ; quy tắc này cũng áp dụng với tài khoản học sinh.

Giáo viên chỉ đọc và sửa các lớp được phân công. Admin quản lý toàn hệ thống. Kiểm tra quyền và CSRF được thực hiện trên server cho mỗi yêu cầu. Các thay đổi được lưu trong nhật ký với người thực hiện và thời điểm, mật khẩu được lưu dưới dạng PBKDF2 theo cơ chế của dự án.

Khi một nơi triển khai mới chưa có admin, người vận hành có thể khởi tạo bằng lệnh dưới đây. Lệnh hỏi mật khẩu trực tiếp, chỉ cho khởi tạo admin đầu tiên.

    docker compose exec web python -m backend.staff_admin --database /data/5bmath-demo.sqlite3

Nếu chạy Python trực tiếp, dùng lệnh dưới đây tại thư mục dự án.

    python -m backend.staff_admin --database work/database/5bmath-demo.sqlite3

## Dành cho giáo viên

1. Chọn lớp được phân công.
2. Thêm buổi học với ngày giờ Việt Nam, tiêu đề, liên kết video xem lại và nhận xét.
3. Thêm bài tập, loại bài và liên kết tài liệu theo từng buổi.
4. Mở **Điểm danh & Nhận Xét**, chọn buổi học, ghi nhận có học tính phí, có học miễn phí hoặc vắng; lưu nhận xét riêng cho từng học sinh sau buổi học. Có thể ghi nhận xét trước khi chọn trạng thái điểm danh.
5. Mở **Chấm điểm**, bấm buổi học, bấm bài tập cần chấm rồi xem bảng **Học sinh / Bài nộp / Điểm / Nhận xét**. Mở tệp bài nộp mới nhất, nhập điểm 0–10 và nhận xét bài làm. Để trống điểm nếu chưa chấm; nhận xét vẫn lưu được. Điểm/nhận xét bài tập và điểm danh/nhận xét buổi học được lưu riêng.
6. Xem danh sách học sinh và học phí theo tháng. Giáo viên được **Tính học phí** và lưu cho lớp mình phụ trách. Admin cấu hình **Học phí mỗi buổi**, giữ cách lập thủ công, ghi danh và đối soát.
7. Mở **Gửi thông báo**, chọn một lớp đang được phân công, nhập tiêu đề/nội dung, kiểm tra số tài khoản nhận rồi gửi. Giáo viên không có lựa chọn gửi theo nhóm Free/VIP/SVip hoặc tới lớp của giáo viên khác.

Điểm, nhận xét, bài tập, video và điểm danh ghi vào các bảng lớp Zoom đang dùng. Học sinh nội bộ đang ghi danh đọc lại đúng dữ liệu trong trang Lớp Zoom. Liên kết phòng Zoom được nhập ở thông tin lớp. Video và tài liệu hiện được nhập bằng URL, phù hợp các trường dữ liệu đã có.

Trong tab **Bài tập**, học sinh SVip nộp một ảnh JPG/PNG/WebP hoặc PDF tối đa 10 MB cho mỗi bài tập. Tệp thật lưu trong SQLite, tải qua API có kiểm tra phiên và quyền: học sinh chỉ tải bài của mình; giáo viên chỉ tải bài của lớp được phân công; admin tải bài thuộc các lớp quản lý. Mỗi lần nộp lại khác nội dung hoặc tên tạo bản ghi mới; bảng chấm điểm hiển thị bản mới nhất. Nộp lại giữ điểm và nhận xét đã có để nhân sự xem lại, không tự xóa kết quả chấm.

### Số chưa đọc của Lớp Zoom

Giao bài tập mới tự tạo một thông báo cho từng học sinh đang ghi danh trong lớp. Lập khoản học phí mới chỉ tạo thông báo cho học sinh có khoản phí đó. Sửa bài tập hoặc sửa số tiền không tạo thông báo trùng; không tạo bù thông báo cho bài tập/học phí đã có trước tính năng này. Học sinh ghi danh về sau vẫn xem được nội dung lớp nhưng không nhận lại sự kiện giao bài cũ.

Tài khoản SVip thấy vòng tròn đỏ tổng chưa đọc ở menu **Lớp Zoom**, số riêng tại **Bài tập** và **Học phí** của lớp đang chọn. Số bằng 0 thì ẩn. Mở Lớp Zoom không đánh dấu toàn bộ; học sinh bấm mục tương ứng để lưu đã đọc tới mốc thông báo vừa tải. Thông báo đến sau mốc đó vẫn chưa đọc. Số đếm cập nhật khoảng 30 giây khi trang đang hiển thị/có mạng và khi quay lại trang; tự làm mới số đếm không tự đánh dấu thông báo mới. Đây là bộ đếm riêng với **Thông báo tài khoản**.

## Dành cho admin

- **Tổng quan** hiển thị số học sinh, lớp, bài giảng, bài toán và đơn chờ đối soát.
- **Lớp Zoom** tạo/sửa lớp, phân công giáo viên, nhập lịch/chương trình/link phòng và **Học phí mỗi buổi**, ghi danh hoặc cho rời lớp, lập/tính học phí theo tháng. Ghi danh cấp quyền nội bộ gắn với ghi danh, rời hoặc kết thúc lớp chấm dứt quyền đó. Lịch sử điểm và học phí được giữ.
- **Học liệu** quản lý chuyên đề, bài giảng và ngân hàng câu hỏi. Bài giảng có nháp/phát hành. Câu hỏi có đáp án, hai đến bốn lựa chọn, độ khó, tuần kiến thức, lời giải và hướng dẫn tư duy. Sửa phần chữ giữ các khối MathML/ảnh đang có. Sửa câu hỏi tạo phiên bản mới, giữ nguyên nội dung các đề đã sinh.
- **Học sinh** thêm tài khoản, tìm theo tên/tài khoản/khối/trạng thái, sửa biệt danh, tên đăng nhập, năm sinh, gói Free/VIP/SVip và hạn gói, linh vật, kinh nghiệm; đặt lại mật khẩu, tạm khóa/mở lại hoặc xóa tài khoản. Khối được tính tự động từ năm sinh. Mật khẩu ban đầu/mật khẩu mới cần 6–128 ký tự, để trống khi sửa để giữ mật khẩu hiện tại. Những thay đổi cần làm mới quyền/hồ sơ sẽ kết thúc phiên đăng nhập học sinh; các điều chỉnh đều có nhật ký.
- **Nhân sự & quyền** cấp tài khoản, chọn vai trò và hồ sơ giáo viên, thay đổi trạng thái hoặc mật khẩu. Hệ thống giữ ít nhất một admin đang hoạt động.
- **Đối soát** tra cứu đơn và xác nhận khoản tiền thực nhận bằng đúng mã đơn và số tiền. Đơn VIP kích hoạt cơ chế một tháng lịch/giới thiệu/thông báo hiện có; học phí ghi ngày đã nộp. Gửi lại cùng xác nhận giữ nguyên kết quả.
- **Cấu hình** tạm dừng/mở đăng ký, học online, tạo đề, tạo/ghép trận và bảng xếp hạng; cập nhật bốn hạn mức Free theo ngày Việt Nam. Việc tạo đề/trận mới và hạn mức được kiểm tra ở API. Đề/trận đang làm có thể hoàn thành.
- **Nhật ký** xem người cập nhật, đối tượng, nội dung và thời điểm.
- **Gửi thông báo** chọn Tất cả, Free, VIP, SVip hoặc một Lớp Zoom; nhập tiêu đề và nội dung chữ, xem số người nhận rồi gửi. Nhóm tính theo quyền đang hiệu lực, không chỉ theo nhãn tài khoản lưu trước đó. Lịch sử gửi ghi người gửi, nhóm/lớp, thời gian và số người nhận.

Hạn mức mặc định giữ nguyên 1 lượt nội dung, 1 đề tổng hợp, 3 trận người và 5 lượt bot mỗi ngày. Cấu hình ngân hàng vẫn theo lựa chọn chờ bổ sung, các biến môi trường hiện hành ở LOCAL_API.md. Xác nhận tiền là thao tác thủ công của admin; đối soát ngân hàng tự động/webhook còn chờ tích hợp.

### Đối soát và người giới thiệu

Chỉ admin mở **Đối soát**. Dòng học sinh hiển thị tên đăng nhập trước biệt danh. Cột **Người giới thiệu** hiển thị tên đăng nhập, biệt danh và gói **Free / Vip / SVip** đang hiệu lực; không có quan hệ giới thiệu thì ghi rõ. Ô **Mã đơn / học sinh** tìm theo mã đơn, tên đăng nhập hoặc biệt danh của học sinh/người giới thiệu. Ô **Người giới thiệu** lọc riêng theo tên đăng nhập hoặc biệt danh người giới thiệu; điền cả hai ô thì kết quả phải thỏa cả hai điều kiện. Danh sách có 25 đơn mỗi trang.

Gói hiện tại khác với trạng thái phần thưởng đã lưu trong hồ sơ giới thiệu: **Chờ đủ điều kiện nhận thưởng**, **Đã thưởng VIP** hoặc **Cần đối chiếu phần thưởng**. Popup đối soát hiển thị thêm ngày nhận thưởng/hạn VIP sau nhận thưởng nếu đã có. Quan hệ giới thiệu dùng dữ liệu đã lưu; thao tác xác nhận tiền và cơ chế cộng tháng VIP hiện có được giữ nguyên.

Với người giới thiệu hiện là **SVip**, có lượt giới thiệu đã đủ điều kiện nâng cấp VIP lần đầu và đang cần hỗ trợ, bảng hiện nút **confirm** cạnh tên đăng nhập. Sau khi đã hỗ trợ nhận thưởng, admin bấm nút, kiểm tra người giới thiệu/học sinh trong popup rồi bấm **OK** để ghi nhận. Gửi lại không tạo lần xác nhận hoặc nhật ký thứ hai. Đã xác nhận thì ẩn nút và hiện **Đã được hỗ trợ nhận thưởng**, cùng ngày xác nhận trong popup. Đây là ghi nhận hỗ trợ thủ công, không cộng thêm tháng VIP, không xác nhận thanh toán và không sửa trạng thái thưởng gốc. Lịch sử xác nhận được giữ, không có thao tác sửa/xóa trong luồng này.

Người giới thiệu xem **Tài khoản → Lịch sử giới thiệu**: mục đã được hỗ trợ có trạng thái đã nhận thưởng, nội dung **Đã được hỗ trợ nhận thưởng** và ngày xác nhận. Trang cập nhật khoảng 30 giây khi đang hiển thị/có mạng hoặc khi quay lại; có thể tải lại trang để đọc ngay trạng thái mới. Ngày và hạn VIP của các lượt được cộng tháng tự động vẫn hiển thị theo luồng cũ.

### Sửa năm sinh, gói và hồ sơ học sinh

Admin vào **Học sinh → Chỉnh sửa**. Năm sinh có thể chỉnh để tính lại khối hiện tại; học sinh vẫn không tự đổi được. Lịch sử năm học cũ, học liệu đã hoàn thành, bài làm, điểm và thanh toán được giữ. Các mã định danh hệ thống và quan hệ giới thiệu được giữ để không làm đứt liên kết lịch sử.

Chọn **Free**, **VIP** hoặc **SVip**. VIP cần hạn gói trong tương lai, hiển thị theo giờ Việt Nam; SVip có thể chọn hạn hoặc để trống để cấp không thời hạn. Free dùng hạn mức thông thường. Hạ gói dừng quyền gói cũ và hủy quyền dự kiến chưa bắt đầu; không thay danh sách lớp đã phân công. SVip có quyền nội bộ, còn nội dung lớp chỉ đọc được khi đã ghi danh đúng lớp. Chỉnh gói trực tiếp không tạo đơn thanh toán, không xác nhận tiền và không kích hoạt thưởng giới thiệu.

Linh vật chọn từ danh mục của máy chủ; kinh nghiệm tối thiểu 1.000, cấp linh vật tự tính từ kinh nghiệm. Nếu học sinh vừa đổi linh vật, nhận kinh nghiệm hoặc thay đổi quyền gói ở nơi khác, bản chỉnh sửa cũ bị từ chối để admin tải lại trước khi lưu.

### Xóa và khôi phục tài khoản học sinh

Bấm **Xóa**, nhập lại đúng tên đăng nhập rồi xác nhận. Tài khoản chuyển sang **Đã xóa**, mất quyền đăng nhập và không còn trong danh sách mặc định. Các phiên đăng nhập/phiên đấu trí bị thu hồi; ghi danh và quyền lớp hiện hành kết thúc. Lịch sử bài làm, học tập, điểm, thanh toán và nhật ký được giữ để tránh mất dữ liệu liên quan. Tên đăng nhập vẫn được dành cho tài khoản này.

Chọn bộ lọc **Đã xóa** để tìm và **Khôi phục**. Tài khoản khôi phục ở trạng thái **Tạm khóa**; admin cần **Mở lại** để cho đăng nhập. Khôi phục không tự ghi danh lại hoặc cấp lại quyền lớp đã kết thúc. Thời hạn VIP đã có tiếp tục trôi theo lịch, không được cộng thêm khi khôi phục. Đây là xóa khỏi sử dụng, có thể khôi phục; chưa có chức năng xóa vĩnh viễn toàn bộ lịch sử.

Mỗi lần sửa, khóa/mở, xóa hoặc khôi phục có kiểm tra phiên bản dữ liệu. Nếu một nơi khác vừa cập nhật, tải lại danh sách để xem bản mới trước khi lưu tiếp.

## Dữ liệu và vận hành

Migration 0007_staff_management.sql bổ sung bốn bảng staff_users, staff_sessions, staff_audit_log, system_settings, cùng revision cho các dữ liệu được sửa và trạng thái phát hành bài giảng. Migration `0013_zoom_reviews_and_notices.sql` bổ sung nhận xét từng học sinh, tệp bài nộp và thông báo chưa đọc của lớp. Các lần lưu điểm danh/chấm điểm có kiểm tra revision để phát hiện dữ liệu vừa được sửa ở nơi khác; lượt nộp bài mới cũng làm đổi revision buổi học.

API nhân sự nằm dưới /api/staff/. Trang tĩnh Cloudflare/GitHub có màn hình đăng nhập và noindex, các thao tác nhân sự cần backend Python. Các trang hiện chưa cung cấp tải tệp video/ảnh lên server, trình biên tập trực quan công thức hoặc cập nhật mã nguồn ứng dụng từ trình duyệt.

## Tính học phí theo điểm danh

Admin nhập **Học phí mỗi buổi** khi tạo hoặc sửa lớp, theo số nguyên đồng. **0** là miễn phí; lớp cũ chưa cấu hình giá cần được admin cập nhật trước khi tính, hệ thống không tự lấy mức giá quảng cáo để lập hóa đơn.

Trong lớp → **Học phí → Tính học phí**, chọn tháng theo giờ Việt Nam. Mỗi học sinh được tính **số buổi “Có học · tính phí” × đơn giá mỗi buổi**; buổi miễn phí, vắng hoặc chưa điểm danh không tính. Nhiều buổi cùng ngày vẫn đếm riêng. Bảng gồm học sinh hiện tại, học sinh có điểm danh trong tháng và khoản phí đã lập. Học sinh cũ hoặc khoản đã thanh toán được ghi nhãn rõ; khoản đã thanh toán hoặc hồ sơ không còn đủ điều kiện được khóa, giữ nguyên.

Bấm tên học sinh để xem lịch, các ngày có điểm danh và danh sách buổi học với trạng thái. Lịch chỉ để kiểm tra; sửa điểm danh tại mục Điểm danh & Nhận Xét, rồi tính lại. Quay về bảng tính và bấm **Lưu toàn bộ** để lưu khoản mới/cập nhật và gửi thông báo tài khoản cho từng học sinh có thay đổi. Giáo viên chỉ thực hiện được lớp mình quản lý. Cách **Lập học phí** thủ công của admin vẫn có sẵn; bảng xem trước chỉ rõ khoản thủ công chưa thanh toán sẽ được thay bằng kết quả tính nếu tiếp tục lưu.

Lưu đơn giá, số buổi và lịch từng buổi vào hóa đơn tính tự động. Đổi giá hoặc sửa điểm danh về sau không đổi khoản đã lưu cho tới khi tính/lưu lại. Khoản thủ công vẫn giữ hành vi tham chiếu điểm danh hiện tại. Hóa đơn 0 đồng hiển thị **Không phát sinh học phí**, không yêu cầu thanh toán.

Nếu điểm danh, giá, hóa đơn hoặc thanh toán vừa đổi sau khi xem trước, máy chủ yêu cầu tính lại trước khi lưu. Gửi lại cùng lượt lưu không tạo trùng khoản phí/thông báo; lưu lại nội dung không đổi không gửi thêm thông báo. Các khoản phí, lịch tính, nhật ký và thông báo được lưu cùng giao dịch. Khi số tiền thay đổi, đơn chờ thanh toán cũ được hủy để lần mở thanh toán tiếp theo dùng đúng số tiền; các khoản đã thanh toán và lịch sử được giữ.

## Thông báo và quyền người nhận

Tiêu đề tối đa 160 ký tự, nội dung tối đa 10.000 ký tự, hỗ trợ xuống dòng. Người gửi và vai trò được lấy từ phiên nhân sự trên máy chủ. Gửi cho lớp chỉ nhận các tài khoản học sinh đang ghi danh; lớp phải đang hoạt động và giáo viên phải đang phụ trách. Tài khoản đã xóa/học sinh không hoạt động bị loại; tài khoản tạm khóa vẫn lưu thông báo để đọc khi mở lại. Nhóm không có người nhận không tạo lượt gửi.

Mỗi lượt gửi có mã chống trùng. Nếu mất mạng sau khi máy chủ đã lưu, gửi lại cùng nội dung của lượt đó trả lại kết quả cũ, không gửi thêm. Đổi nội dung hoặc nhóm nhận tạo lượt gửi mới. Bản nháp giữ khi lỗi hoặc chuyển tab của cùng người gửi; không chuyển sang tài khoản nhân sự khác. Nội dung chỉ phát trong tài khoản học sinh, không tự gửi email, SMS hoặc ứng dụng khác.

Học sinh thấy số thông báo chưa đọc trong vòng tròn đỏ ở mục **Tài khoản**. Bảng **Thông báo tài khoản** có tiêu đề, người gửi và nút **Xem**, tối đa 5 dòng mỗi trang; chưa đọc lên trước, mới nhất trước trong từng nhóm. Bấm Xem lưu trạng thái đã đọc và mở nội dung chi tiết. Số đếm tính tất cả trang, cập nhật khi xem, khi trở lại trang và khoảng 30 giây khi trang đang hiển thị/có mạng. Bảng **Lịch sử giới thiệu** có 5 dòng mỗi trang, mới nhất trước, tách tên, trạng thái, các mốc thời gian và hạn VIP nhận được.

Sau xác nhận một khoản VIP mới, hệ thống gửi thông báo **Đăng ký VIP thành công** cho lần đầu hoặc **Gia hạn VIP thành công** cho lần sau; người giới thiệu nhận thông báo thưởng theo cơ chế một lần hiện có. Thông báo ghi thời hạn đã cộng theo giờ Việt Nam. Cấp gói thủ công trong hồ sơ admin không tạo thông báo thanh toán thành công. Thông báo cũ được giữ khi nâng cấp; không tự gửi lại các sự kiện thanh toán cũ.

## Đăng ký kiểm tra đầu vào — 11/11/2026

Admin có mục **Đăng ký đầu vào**, tìm theo mã DV, tên phụ huynh/học sinh hoặc số điện thoại. Bấm **Xem / cập nhật** để đọc thông tin khảo sát và ghi chú; chọn Mới đăng ký / Đã liên hệ / Đã hẹn kiểm tra / Đã kiểm tra / Đã đóng. Lưu có revision chống ghi đè và nhật ký, giáo viên không có quyền truy cập. Đây là quản lý hồ sơ tư vấn, chưa tự tạo tài khoản, lịch kiểm tra, ghi danh hay gửi tin nhắn.

Hồ sơ đến từ `/dang-ky-kiem-tra-dau-vao/`, lưu bằng migration 0008 trong SQLite hiện có. Không tạo dữ liệu khảo sát giả trong DB localhost khi kiểm thử; các ca gửi thật và quản trị chạy trên DB QA riêng trong work/zoom-admissions/.

## Xác nhận tiền tự động và sổ ngân hàng — 12/11/2026

Đối soát admin giữ bảng **Đơn thanh toán** và thêm **Giao dịch ngân hàng** có tìm mã, lọc kết quả, phân trang25 và nút Cập nhật. Chỉ admin đọc; giáo viên/học sinh không thấy sổ. Đã xác nhận là khoản khớp và đã cập nhật quyền; **Cần đối soát** là khoản chưa tự cấp quyền; **Không dùng thanh toán** gồm tiền ra. Trạng thái học phí đã thanh toán hiện **Đã hoàn thành**;0đ vẫn Không phát sinh học phí.

Webhook và xác nhận thủ công dùng cùng hàm kiểm tra và chống trùng. VIP lần đầu/gia hạn/thưởng giới thiệu giữ quy tắc trước;SVip vẫn confirm hỗ trợ riêng; học phí chỉ hoàn tất đúnghóađơn và gửi thôngbáo chochủ. Với sai mã/số tiền/ngân hàng/đơn đãhủy hoặc chuyểnthêm, kiểm tra sổ và ngân hàng rồi xác nhận đúngđơn bằng luồngthủcông hiệncó. Không xóa/sửa sổ nhận để thử lại; replay không tự sửa một giao dịch cầnđốisoát.

Cần cấu hình biến môi trường/HMAC/HTTPS và liên kết ngân hàng theo [PAYMENTS.md](PAYMENTS.md). Có QR không chứng minh đã bật tự động. Giao dịch ngân hàng thật chỉ thử sau khi chủ ngân hàng cấu hình xong, không dùng dữ liệu học sinh thật cho QA.
