# Bạch tuộc — Tám Tay Ảo Thuật

**Cập nhật phạm vi 11/11/2026 trong chat Bạch tuộc:** người dùng đã yêu cầu thêm tấn công, chịu đòn, buồn khi thua, tích hợp game, commit và triển khai local. Các câu demo-only bên dưới là brief gốc được giữ để truy vết; yêu cầu mới áp dụng cho riêng job này. Không tự phát hành Internet hoặc đổi luật/sát thương. Xem README/HANDOFF để biết trạng thái thực tế.

Mã nhân vật: `bach-tuoc`. Đây là đầu bài cho **một demo animation để duyệt**, không phải lệnh tích hợp game.

## Phạm vi đã xác nhận

Người dùng đồng ý dùng Canvas + ảnh WebP cho game về sau, nhưng **chưa làm phần tích hợp bây giờ**. Tên chiêu và mô tả dưới đây là ý tưởng đã trao đổi; chưa coi choreography của từng con là đã được duyệt. Demo Chó hiện có cũng không phải phê duyệt toàn bộ 20 chiêu.

## Ảnh và phong cách cần giữ

- [Ảnh tham chiếu](../../bo-nhan-vat-demo-2026-11-11/03-bien-va-ong-v3.png): dùng đúng **hàng 2, cột 1 trong lưới 2×3 (tọa độ JSON là zero-based)**, chỉ nhân vật Bạch tuộc.
- Đường dẫn từ gốc dự án: `design/5bmath/linh-vat/bo-nhan-vat-demo-2026-11-11/03-bien-va-ong-v3.png`.
- [Phong cách gốc Cáo Nâu/Mầm Sách](../../STYLE.md).
- Tạo hình 3D đồ chơi đất sét mềm/vải nỉ mịn, bề mặt lì có vân nhẹ.
- Đầu/thân tròn, mắt nâu lớn có điểm sáng, má cam mơ, ánh sáng ấm mềm.
- Giữ nhận diện từ đúng ô ảnh tham chiếu; không thêm lá/sách của Mầm Sách cho các con khác.
- Hiệu ứng vui nhộn phù hợp trẻ em; giữ toàn thân, không cắt tai/cánh/đuôi/chi.

## Đặc điểm bắt buộc

- Bạch tuộc tím lavender, đầu/thân tròn với mắt nâu lớn, má cam.
- Đúng tám tay tách biệt, giác hút kem nhỏ phía dưới.
- Đếm rõ tám đầu tay, không sáu hoặc chín; tránh một tay giữa thừa, không ghép tay với đối thủ.

## Ý tưởng chiêu cuối

Phun một màn mực tím rồi biến mất. Tám tay bất ngờ xuất hiện quanh đối thủ, tung tám quả cầu nước vào giữa; màn mực tan ra giữa chùm sao lấp lánh.

## Timeline ba giây dùng chung

| Mốc | Yêu cầu |
|---|---|
| 0–0,65 giây | Lấy đà và dấu hiệu nhận diện chiêu. |
| 0,65 giây | Bắt đầu hiện tên **TÁM TAY ẢO THUẬT**, trước khi ra đòn. |
| 0,65–0,95 giây | Tăng năng lượng/lấy đà, giữ tên đủ rõ để đọc. |
| 0,95–1,90 giây | Đòn quyết định; tác động chính ở khoảng 1,75 giây. |
| 1,90–3,00 giây | Hiệu ứng thắng trận và tư thế kết thúc rõ. |

Bản xuất chuẩn: **3,000 giây, 30 fps, 90 frame**. Đây là khung thời gian mẫu; chỉ điều chỉnh mốc chi tiết nếu người dùng yêu cầu, vẫn giữ tên trước đòn và tổng khoảng ba giây. Không tự đổi luật/sát thương/tính kết quả trận.

## Ba nhịp riêng của Bạch tuộc

1. **Lấy đà:** Thu nhẹ tám tay, lấy đà phun màn mực tím.
2. **Đòn quyết định:** Ẩn trong mực; tám tay tạo/tung tám bóng nước đồng quy tại mục tiêu.
3. **Chiến thắng:** Mực tan giữa chùm sao; bạch tuộc hiện lại với tám tay xòe vui.

## Tư thế và hiệu ứng

Tạo ảnh nhân vật bằng image_gen tích hợp với ảnh tham chiếu thực sự; giữ PNG nguồn có alpha thật và chuẩn bị WebP để chạy Canvas. Nếu dùng sheet 4×4 như demo Chó, có thể phân bốn hàng thành lấy đà / di chuyển hoặc tập trung năng lượng / đòn quyết định / chiến thắng. Tư thế phải hợp giải phẫu của Bạch tuộc; không ép côn trùng/chim/cá dùng bộ chạy bốn chân của Chó. Hiệu ứng ánh sáng, bóng ảo, nước, lá hoặc số được ghép riêng, không làm biến dạng hình gốc.

Mỗi chat tạo trong thư mục tác vụ riêng theo quy trình dùng chung. Không sửa catalog, brief của con khác, nguồn tham chiếu hay frontend/backend của website. Không tự ghi trạng thái "đã duyệt"; giữ kết quả ở trạng thái chờ người dùng xem.

## Kiểm tra trước khi gửi duyệt

- Đúng nhân vật/nhận diện, đủ chi/cánh/tay/đuôi theo mục đặc điểm bắt buộc; mỗi tư thế không crop.
- Nền trong suốt thật; không ô caro vẽ sẵn, không viền màu khi ghép nền.
- Tên chiêu đúng dấu Việt, hiện trước đòn; các hiệu ứng không che tên hoặc khuôn mặt.
- Đủ lấy đà → đòn quyết định → thắng; thắng giữ đủ lâu ở cuối.
- GIF/MP4 ba giây và bản HTML Canvas là các đầu ra riêng; GIF/MP4 dùng duyệt, không tải vào runtime game.
- Kiểm dung lượng WebP và chất lượng sau nén, xem trên màn dọc/ngang; chưa đo thiết bị thật thì ghi rõ, không suy diễn độ mượt từ video xuất sẵn.
