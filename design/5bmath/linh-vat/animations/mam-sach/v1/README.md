# Mầm Sách — Đại Thụ Tri Thức

Bộ bốn animation theo yêu cầu ngày 11/11/2026: chiêu cuối, tấn công thường, chịu đòn và buồn khi thua. Người dùng đã yêu cầu tích hợp game, commit và chạy local trong chính chat này; đây là ngoại lệ riêng Mầm Sách so với phạm vi demo mặc định của workshop. Không tự phê duyệt tạo hình và không phát hành Internet.

Mở [demo Canvas](demo.html), chọn hoạt cảnh và dùng Phát lại/Tạm dừng/thanh thời gian/0,5×. Chiêu cuối [GIF](exports/demo.gif) và [MP4](exports/demo.mp4) dài đúng 3,000 giây,90khung ở30fps. Canvas chỉ dùng WebP; GIF/MP4 dành xem duyệt. WebP1254×1254,16pose,alpha thật,292.192byte.

Tên hiện0,65giây; số và phép toán bay ra0,95giây; cây sáng nâng đối thủ/tác động1,75giây; sao và trang sách/ăn mừng1,90–3giây. Tấn công thường đẩy sách phát ký hiệu; chịu đòn co/recoil rồi hồi phục; thua ngồi buồn với sách mở và hai lá rũ. Cây là phép tách riêng, nhân vật luôn đúng hai lá và cuốn sách.

Nguồn PNG và bản tham chiếu gốc được giữ trong source/; PROMPTS.json lưu hai lượt imagegen. Bản đầu còn nền trắng bị prepare chặn, bản sau tách nền bằng imagegen. Đã xem WebP trên nền sáng/tối. Không dùng mã để cắt nền.

Runtime game: frontend/mam-sach-animation.js,frontend/mam-sach-animation.css,frontend/arena-art/mam-sach/poses.webp. Tải ảnh khi cần,phát một lần,dừng khi ẩn trang/thay màn,hỗ trợ giảm chuyển động. Không thay luật,tính máu,deadline hay điểm; chờ3,1giây trước kết quả để chiêu cuối phát hết.

## Commit local trong checkout đang phát triển

Nền game và nhiều thay đổi của các chat khác chưa được commit ở thời điểm làm. Commit riêng của chat này lưu module,tài sản,Demo và integration.patch mô tả chính xác các điểm nối vào index/server/build/learning. Các điểm nối đã áp dụng trong cây làm việc và Docker local; không gom toàn bộ nền game/chức năng khác vào commit. Đây là checkpoint riêng Mầm Sách,không phải một release độc lập từ HEAD cũ.

QA xuất tại qa/qa-report.json và qa/contact-sheet.png; QA tương tác/renderer/game/HTTP tại work/mam-sach-animation/. Chưa đo FPS/CPU trên điện thoại thật. Job giữ pending_review,không tự approved.
