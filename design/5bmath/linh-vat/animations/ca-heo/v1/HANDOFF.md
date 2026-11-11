# Bàn giao Cá heo / v1

- Chủ phiên: ca-heo-01a1cb4d
- Trạng thái: pending_review về hình ảnh; đã tích hợp và dựng Docker local theo yêu cầu mới của người dùng.
- Đã có: hai PNG nguồn imagegen, prompt/tham chiếu thật, hai WebP alpha, demo Canvas bốn mode; GIF/MP4 chiêu cuối và ba animated WebP tấn công/chịu đòn/thua.
- Chiêu Sóng Âm Cầu Vồng: quẫy đuôi → bật nhảy/lộn vòng → cầu nước → bọt cầu vồng; ba giây, tên0,65/đòn0,95/impact1,75/thắng1,90. Không dùng choreography Chó.
- QA: 77 test Docker đạt; 2 test Cá heo; Chrome năm viewport/bốn mode/reduced motion/cleanup, luồng chọn+đánh+thua+ultimate/thắng qua Python fixture đạt; review1câu/1vòng. Hai build/SEO đạt; HTTP trong container200/404,grade10/10,DB integrityok/FK0.
- HTTP trình duyệt trực tiếp bị sandbox hạn chế; QA app dùng source+Python dispatch qua stdin với database thử riêng. Không đo FPS điện thoại thật. Nguồn kiểm tra/chụp tại work/mascot-animation/ca-heo/v1; fixture8793 đã dừng.
- Mã game: frontend/arena-dolphin.js/.css và arena-art/ca-heo-v1. Hai sheet954.992byte; WebP phụ trong exports chỉ dùng xem, không tải vào game.
- Baseline chung chưa commit và được nhiều chat sửa: các hook đã áp dụng thực tế, commit riêng giữ integration.patch/manifest, không gom thay đổi khác. Xem INTEGRATION.md. Test snapshot sửa chọn đúng mã có patch riêng trong qa/.
- Không tự approved; không push, CI hoặc phát hành công khai. Giữ nguyên nguồn/job của các con khác.
- Kết thúc không còn tiến trình ghi. Release lease sau khi lưu hồ sơ; chat sau đọc HANDOFF rồi claim owner mới nếu cần sửa. Bước tiếp là người dùng xem demo/chọn Cá heo ở localhost; thay đổi hình ảnh tiếp phải giữ PNG nguồn và tạo phiên bản mới.
