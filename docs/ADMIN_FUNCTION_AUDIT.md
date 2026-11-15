# Rà soát quản trị 5BMath — 15/11/2026

Phạm vi: website Python localhost, kế thừa Nháp tài khoản/thiết bị, LAN, PDF và VIP+. Không phát hành website công khai trong đợt này.

| Chức năng học sinh/phụ huynh | Nơi quản lý | Khả năng và ranh giới |
|---|---|---|
| Tài khoản, Free/VIP/VIP+/SVip, linh vật, XP | Học sinh | Sửa hồ sơ, hạn gói, khóa/khôi phục theo revision; giữ lịch sử. |
| Nhân sự và lớp phụ trách | Nhân sự & quyền / Lớp Zoom | Admin/giáo viên, ít nhất một admin hoạt động; phân công lớp. |
| Học liệu kho chính | Học liệu | Chuyên đề, bài giảng, phiên bản câu hỏi; tạo/phát hành câu để dùng trong đề bán riêng và bộ VIP+. |
| Bài giảng lớp5 thực tế đang đọc | Bài giảng lớp5 | Biên tập tên và ba khung nội dung, lưu nháp, phát hành phiên bản mới, lưu trữ/khôi phục và nhật ký riêng. Giữ hình/SVG, câu tự kiểm tra/lời giải gốc và kết quả phiên bản cũ. Không gọi đây là editor đáp án fixed. |
| Kho câu luyện có ví / câu tự kiểm tra lớp5 | Trung tâm điều hành → phạm vi dữ liệu | Nguồn đã kiểm soát và pin phiên bản. Đợt này không thêm trình nhập/sửa ngân hàng thí điểm hoặc đổi cơ chế ví. Không dùng câu đã trả phí thay bài giảng miễn phí. |
| Video series | Series & video | Tạo/sửa/lưu trữ series, thêm URLHTTPS, nháp/phát hành/lưu trữ video, thứ tự và nút lên/xuống. Free mở ba video đang phát hành đầu của mỗi series. Chưa upload tệp video. |
| Đề bán riêng | Đề bán riêng | Mã, mô tả, giá, khối, thời gian, tìm/chọn/sắp câu đã phát hành, nháp/phát hành/lưu trữ. Mỗi đơn một đề/một bài làm; đơn đã tạo giữ snapshot. Chưa phải gói nhiều đề. |
| Ôn trường, siêu khó, phân loại, HSG | Nội dung VIP+ | Chọn đúng nhóm, trường/khối5 với đề trường; bộ câu được chọn rõ ràng. Không tự đặt câu ngẫu nhiên thành đề trường/HSG. |
| VIP/VIP+/đề/học phí và giới thiệu | Đối soát | Đơn, giao dịch, xác nhận đúng mã/số tiền, hỗ trợ thưởng; không sửa thẳng điểm hoặc đơn đã thanh toán. Giá thuê bao100k/200k giữ theo chỉ đạo đã chốt; không thêm editor đổi giá thuê bao. |
| Video/bán đề/cấp bài VIP+ | Vận hành | Ba công tắc riêng, revision và nhật ký. Dừng bán mới không hủy đơn cũ hoặc quyền đề đã mua. |
| Đăng ký/học/luyện/game/bảng hạng | Cấu hình | Các công tắc và hạn mức hiện hành; game chung cả ba trò. Kho kiến thức native tôn trọng trạng thái học. |
| Zoom, buổi học, bài tập, bài nộp, nhận xét, điểm danh, học phí | Lớp Zoom | Giữ toàn bộ luồng admin/giáo viên cũ, tệp thật và tính phí. |
| Khảo sát phụ huynh | Đăng ký đầu vào | Liên hệ, trạng thái tư vấn, ghi chú. |
| Thông báo | Gửi thông báo | Thêm đúng nhómVIP+, giữ nhómFree/VIP/SVip và lớp; xem số người nhận; idempotency. |
| Nháp/PDF/đáp án/bài làm | Tự động + quản lý đúng nghiệp vụ | Nháp theo tài khoản, thứ tự PDF, mã tra cứu và lịch sử không bị sửa trong đợt quản trị này. |
| Ảnh linh vật, animation, luật/engine game, website marketing | Nguồn và quy trình phát hành | Không có trình sửa mã/animation qua web. Công tắc vận hành có trong quản trị. Không bịa khả năng chỉnh mọi luật bằng form. |
| Ngân hàng/webhook/bí mật/backup/triển khai | Cấu hình vận hành riêng | UI chỉ hiện đã cấu hình/bật hay tắt. Không đưa token, khóa webhook hoặc thao tác restore/deploy vào form. |

Trung tâm điều hành tập hợp lối vào các nghiệp vụ và công khai những phần còn dùng nguồn/quy trình riêng, thay vì hiển thị nút quản lý không hoạt động. Sidebar có tìm mục, lối mở giữ trong URL hash; trang vận hành hiển thị số lượng và trạng thái thực tế.

Các thao tác mới chỉ admin được dùng; kiểm Origin/CSRF/session ở API. Biên tập catalogue dùng CASrevision; xung đột trả409. Lưu trữ thay xóa cứng. Câu/giá đã chốt vào đơn và bài làm không bị sửa khi biên tập sản phẩm. Bài giảng lớp5 có audit và draft/publish trong chính kho pilot, không ghi lại câu gốc hoặc đổi điểm/XP/ví.
