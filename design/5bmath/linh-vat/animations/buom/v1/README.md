# Bướm · Vũ Điệu Ngàn Cánh

Mở [demo Canvas](demo.html) để xem bốn hoạt cảnh: chiêu cuối, tấn công, chịu đòn, buồn khi thua. Có tạm dừng, tua và tốc độ0,5×.

- [GIF chiêu cuối](exports/demo.gif) · [MP4 chiêu cuối](exports/demo.mp4) · [Ảnh cuối](exports/poster.png).
- [Bốn hoạt cảnh](qa/modes-contact.png) · [16pose trên nền sáng/tối](qa/alpha-light-dark.png).
- [QA xuất chuẩn](qa/qa-report.json) · [QA demo](qa/demo-controls.json) · [Bàn giao](HANDOFF.md).

Chiêu cuối dài3giây: lấy đà, hiện tên.65s, đàn bóng bướm tụ thành đôi cánh lớn rồi tung cầu vồng, tác động1.75s và ăn mừng từ1.90s. Tấn công/chịu đòn dài1.2s; bản xem giữ nghỉ tới3s. Thua giữ tư thế buồn cuối.

Runtime chỉ tải WebP/Canvas. Atlas16pose1254×1254, alpha,356.800byte; PNGnguồn và exact prompt được giữ trong`source/`. Bướm giữ tạo hình kem–đào, bốn cánh có hoa văn cam/xanh, hai râu và sáu chân nhỏ; style đất sét mềm/vải nỉ từ Cáo Nâu/Mầm Sách.

Yêu cầu chat này cho phép tích hợp game và triển khai local; mỹ thuật vẫn chờ người dùng xem. Không có phát hành công khai từ riêng tác vụ tạo hình này. Chưa đo FPS trên điện thoại thật.
