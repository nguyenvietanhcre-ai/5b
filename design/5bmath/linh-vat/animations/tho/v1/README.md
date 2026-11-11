# Thỏ — Cú Nhảy Trăng Rằm và bộ hành động

Yêu cầu ngày 11/11/2026 cho riêng Thỏ cho phép tạo **chiêu cuối, tấn công, chịu đòn, buồn khi thua**, tích hợp game, commit và triển khai **local**. Chỉ đạo này thay phạm vi demo trong BRIEF của job này; không mở rộng phê duyệt cho các nhân vật khác hoặc phát hành công khai.

- [Canvas + WebP](demo.html): chọn bốn hoạt cảnh, phát lại, kéo thời gian, xem chậm. Mỗi bản xem dài ba giây.
- [Chiêu cuối GIF](exports/demo.gif) · [MP4](exports/demo.mp4).
- [Tấn công](exports/attack.gif) · [Chịu đòn](exports/hit.gif) · [Buồn khi thua](exports/lose.gif).
- `source/poses.png`: 16 tư thế chiêu cuối; `source/actions.png`: 16 tư thế chờ/tấn công/chịu đòn/thua. Giữ PNG alpha gốc do imagegen tạo.
- `assets/poses.webp`, `assets/actions.webp`: ảnh dùng Canvas; `poses.js`, `assets/actions.js`: vùng ảnh từng tư thế.
- Tham chiếu thật: Thỏ ở hàng1/cột3 của `bo-nhan-vat-demo-2026-11-11/01-thu-tren-can.png`, vật liệu/nhận diện ở `mam-sach-cao-nau-goc.png`. Lông kem, hai tai lòng đào, bốn chi, đuôi bông, mắt nâu, má cam; không thêm lá/sách.

Chiêu cuối: lấy đà0–0,95s; tên xuất hiện0,65s; bật qua vầng trăng0,95–1,75s; đáp đệm trăng và sóng tròn1,75s; ăn mừng1,90–3,00s. Canvas ghép trăng, đệm, sao và sóng riêng, không sửa ảnh nguồn.

Trong game, tấn công/chịu đòn dài1,2s, chiêu cuối/thua/ăn mừng dài3s. Game không tải GIF/MP4 hoặc PNG nguồn. Bốn tệp `frontend/arena-art/tho-*` tổng1.011.896byte; chỉ tải sheet/metadata khi có Thỏ, dùng ảnh idle nhỏ cho thẻ chọn. Không đổi luật sát thương, XP hay thời gian câu hỏi.

QA và kết quả phát hành local được ghi ở `qa/`, HANDOFF và bản ghi dự án. Kiểm trình duyệt mô phỏng màn hình không phải chứng nhận FPS trên điện thoại thật. Tạo hình/choreography còn có thể được người dùng chỉnh sau khi xem; không tự đặt approved.
