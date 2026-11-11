# Mầm Sách — Đại Thụ Tri Thức

Mã nhân vật: `mam-sach`. Đây là đầu bài cho **một demo animation để duyệt**, không phải lệnh tích hợp game.

## Phạm vi đã xác nhận

Người dùng đồng ý dùng Canvas + ảnh WebP cho game về sau, nhưng **chưa làm phần tích hợp bây giờ**. Tên chiêu và mô tả dưới đây là ý tưởng đã trao đổi; chưa coi choreography của từng con là đã được duyệt. Demo Chó hiện có cũng không phải phê duyệt toàn bộ 20 chiêu.

## Ảnh và phong cách cần giữ

- [Ảnh tham chiếu](../../mam-sach-cao-nau-goc.png): dùng đúng **hàng 1, cột 1 trong lưới 1×2 (tọa độ JSON là zero-based)**, chỉ nhân vật Mầm Sách.
- Đường dẫn từ gốc dự án: `design/5bmath/linh-vat/mam-sach-cao-nau-goc.png`.
- [Phong cách gốc Cáo Nâu/Mầm Sách](../../STYLE.md).
- Tạo hình 3D đồ chơi đất sét mềm/vải nỉ mịn, bề mặt lì có vân nhẹ.
- Đầu/thân tròn, mắt nâu lớn có điểm sáng, má cam mơ, ánh sáng ấm mềm.
- Giữ nhận diện từ đúng ô ảnh tham chiếu; không thêm lá/sách của Mầm Sách cho các con khác.
- Hiệu ứng vui nhộn phù hợp trẻ em; giữ toàn thân, không cắt tai/cánh/đuôi/chi.

## Đặc điểm bắt buộc

- Giữ nguyên mầm xanh bơ tròn, hai lá xanh trên đầu, mắt sẫm lớn, má cam và bốn chi ngắn.
- Luôn giữ cuốn sách mở màu kem đúng tỷ lệ và phong cách đất sét/nỉ mềm.
- Đúng hai lá thật trên đầu; đại thụ và trang sách bay là phép tách riêng, không biến nhân vật thành cây hoặc thêm chi.

## Ý tưởng chiêu cuối

Mở sách, hai lá trên đầu bừng sáng. Những con số và dấu + − × ÷ bay ra, gieo thành hạt mầm dưới chân đối thủ. Một đại thụ ánh sáng vươn lên, nâng đối thủ vào tán lá rồi bung thành mưa sao và những trang sách màu kem.

## Timeline ba giây dùng chung

| Mốc | Yêu cầu |
|---|---|
| 0–0,65 giây | Lấy đà và dấu hiệu nhận diện chiêu. |
| 0,65 giây | Bắt đầu hiện tên **ĐẠI THỤ TRI THỨC**, trước khi ra đòn. |
| 0,65–0,95 giây | Tăng năng lượng/lấy đà, giữ tên đủ rõ để đọc. |
| 0,95–1,90 giây | Đòn quyết định; tác động chính ở khoảng 1,75 giây. |
| 1,90–3,00 giây | Hiệu ứng thắng trận và tư thế kết thúc rõ. |

Bản xuất chuẩn: **3,000 giây, 30 fps, 90 frame**. Đây là khung thời gian mẫu; chỉ điều chỉnh mốc chi tiết nếu người dùng yêu cầu, vẫn giữ tên trước đòn và tổng khoảng ba giây. Không tự đổi luật/sát thương/tính kết quả trận.

## Ba nhịp riêng của Mầm Sách

1. **Lấy đà:** Mở sách, hai lá bừng sáng; số và dấu phép toán nổi lên.
2. **Đòn quyết định:** Số gieo thành hạt mầm; đại thụ ánh sáng vươn dưới mục tiêu, nâng đối thủ vào tán lá.
3. **Chiến thắng:** Tán cây bung thành mưa sao/trang sách; Mầm Sách mỉm cười với sách, hai lá giữ đúng.

## Tư thế và hiệu ứng

Tạo ảnh nhân vật bằng image_gen tích hợp với ảnh tham chiếu thực sự; giữ PNG nguồn có alpha thật và chuẩn bị WebP để chạy Canvas. Nếu dùng sheet 4×4 như demo Chó, có thể phân bốn hàng thành lấy đà / di chuyển hoặc tập trung năng lượng / đòn quyết định / chiến thắng. Tư thế phải hợp giải phẫu của Mầm Sách; không ép côn trùng/chim/cá dùng bộ chạy bốn chân của Chó. Hiệu ứng ánh sáng, bóng ảo, nước, lá hoặc số được ghép riêng, không làm biến dạng hình gốc.

Mỗi chat tạo trong thư mục tác vụ riêng theo quy trình dùng chung. Không sửa catalog, brief của con khác, nguồn tham chiếu hay frontend/backend của website. Không tự ghi trạng thái "đã duyệt"; giữ kết quả ở trạng thái chờ người dùng xem.

## Kiểm tra trước khi gửi duyệt

- Đúng nhân vật/nhận diện, đủ chi/cánh/tay/đuôi theo mục đặc điểm bắt buộc; mỗi tư thế không crop.
- Nền trong suốt thật; không ô caro vẽ sẵn, không viền màu khi ghép nền.
- Tên chiêu đúng dấu Việt, hiện trước đòn; các hiệu ứng không che tên hoặc khuôn mặt.
- Đủ lấy đà → đòn quyết định → thắng; thắng giữ đủ lâu ở cuối.
- GIF/MP4 ba giây và bản HTML Canvas là các đầu ra riêng; GIF/MP4 dùng duyệt, không tải vào runtime game.
- Kiểm dung lượng WebP và chất lượng sau nén, xem trên màn dọc/ngang; chưa đo thiết bị thật thì ghi rõ, không suy diễn độ mượt từ video xuất sẵn.
