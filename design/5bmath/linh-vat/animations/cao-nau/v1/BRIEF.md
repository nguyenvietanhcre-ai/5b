# Cáo Nâu — Lốc Đuôi Tinh Quái

Mã nhân vật: `cao-nau`. Đây là đầu bài cho **một demo animation để duyệt**, không phải lệnh tích hợp game.

## Phạm vi đã xác nhận

Người dùng đồng ý dùng Canvas + ảnh WebP cho game về sau, nhưng **chưa làm phần tích hợp bây giờ**. Tên chiêu và mô tả dưới đây là ý tưởng đã trao đổi; chưa coi choreography của từng con là đã được duyệt. Demo Chó hiện có cũng không phải phê duyệt toàn bộ 20 chiêu.

## Ảnh và phong cách cần giữ

- [Ảnh tham chiếu](../../mam-sach-cao-nau-goc.png): dùng đúng **hàng 1, cột 2 trong lưới 1×2 (tọa độ JSON là zero-based)**, chỉ nhân vật Cáo Nâu.
- Đường dẫn từ gốc dự án: `design/5bmath/linh-vat/mam-sach-cao-nau-goc.png`.
- [Phong cách gốc Cáo Nâu/Mầm Sách](../../STYLE.md).
- Tạo hình 3D đồ chơi đất sét mềm/vải nỉ mịn, bề mặt lì có vân nhẹ.
- Đầu/thân tròn, mắt nâu lớn có điểm sáng, má cam mơ, ánh sáng ấm mềm.
- Giữ nhận diện từ đúng ô ảnh tham chiếu; không thêm lá/sách của Mầm Sách cho các con khác.
- Hiệu ứng vui nhộn phù hợp trẻ em; giữ toàn thân, không cắt tai/cánh/đuôi/chi.

## Đặc điểm bắt buộc

- Giữ nguyên Cáo Nâu đã duyệt: lông cam nâu, mõm/bụng/đầu đuôi kem, mắt nâu, má cam.
- Hai tai nhọn, bốn chi, đúng một đuôi xù; khăn xanh lá từ ảnh gốc.
- Không tự thêm chín đuôi, bỏ khăn, thay mặt hoặc đổi chất liệu; bóng đuôi/lá là hiệu ứng riêng.

## Ý tưởng chiêu cuối

Ve vẩy đuôi đánh lạc hướng rồi lách nhanh ra sau đối thủ. Chiếc đuôi xù quét một vòng, cuốn lá cam thành cơn lốc hình đuôi cáo. Cú xoay đuôi cuối cuốn đối thủ lên rồi khiến cơn lốc bung thành pháo lá mùa thu.

## Timeline ba giây dùng chung

| Mốc | Yêu cầu |
|---|---|
| 0–0,65 giây | Lấy đà và dấu hiệu nhận diện chiêu. |
| 0,65 giây | Bắt đầu hiện tên **LỐC ĐUÔI TINH QUÁI**, trước khi ra đòn. |
| 0,65–0,95 giây | Tăng năng lượng/lấy đà, giữ tên đủ rõ để đọc. |
| 0,95–1,90 giây | Đòn quyết định; tác động chính ở khoảng 1,75 giây. |
| 1,90–3,00 giây | Hiệu ứng thắng trận và tư thế kết thúc rõ. |

Bản xuất chuẩn: **3,000 giây, 30 fps, 90 frame**. Đây là khung thời gian mẫu; chỉ điều chỉnh mốc chi tiết nếu người dùng yêu cầu, vẫn giữ tên trước đòn và tổng khoảng ba giây. Không tự đổi luật/sát thương/tính kết quả trận.

## Ba nhịp riêng của Cáo Nâu

1. **Lấy đà:** Ve vẩy đuôi và nghiêng người đánh lạc hướng; lá cam gom dần.
2. **Đòn quyết định:** Lách nhanh, quét đuôi tạo lốc; cú xoay đuôi khóa cơn lốc tại đối thủ.
3. **Chiến thắng:** Lốc bung thành pháo lá; Cáo Nâu giơ tay/đuôi tự hào, vẫn chỉ một đuôi thật.

## Tư thế và hiệu ứng

Tạo ảnh nhân vật bằng image_gen tích hợp với ảnh tham chiếu thực sự; giữ PNG nguồn có alpha thật và chuẩn bị WebP để chạy Canvas. Nếu dùng sheet 4×4 như demo Chó, có thể phân bốn hàng thành lấy đà / di chuyển hoặc tập trung năng lượng / đòn quyết định / chiến thắng. Tư thế phải hợp giải phẫu của Cáo Nâu; không ép côn trùng/chim/cá dùng bộ chạy bốn chân của Chó. Hiệu ứng ánh sáng, bóng ảo, nước, lá hoặc số được ghép riêng, không làm biến dạng hình gốc.

Mỗi chat tạo trong thư mục tác vụ riêng theo quy trình dùng chung. Không sửa catalog, brief của con khác, nguồn tham chiếu hay frontend/backend của website. Không tự ghi trạng thái "đã duyệt"; giữ kết quả ở trạng thái chờ người dùng xem.

## Kiểm tra trước khi gửi duyệt

- Đúng nhân vật/nhận diện, đủ chi/cánh/tay/đuôi theo mục đặc điểm bắt buộc; mỗi tư thế không crop.
- Nền trong suốt thật; không ô caro vẽ sẵn, không viền màu khi ghép nền.
- Tên chiêu đúng dấu Việt, hiện trước đòn; các hiệu ứng không che tên hoặc khuôn mặt.
- Đủ lấy đà → đòn quyết định → thắng; thắng giữ đủ lâu ở cuối.
- GIF/MP4 ba giây và bản HTML Canvas là các đầu ra riêng; GIF/MP4 dùng duyệt, không tải vào runtime game.
- Kiểm dung lượng WebP và chất lượng sau nén, xem trên màn dọc/ngang; chưa đo thiết bị thật thì ghi rõ, không suy diễn độ mượt từ video xuất sẵn.
