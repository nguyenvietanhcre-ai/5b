# Đại bàng — Sải Cánh Bão Táp

Bộ animation riêng của Đại bàng theo `docs/ANIMATION_WORKSHOP.md`, phong cách Cáo Nâu/Mầm Sách. Yêu cầu ngày 11/11/2026 cho phép tạo chiêu cuối, tấn công, chịu đòn, buồn khi thua, tích hợp game và commit/chạy trên local. Phạm vi này chỉ áp dụng cho Đại bàng; không tự phê duyệt toàn bộ nhân vật. Bản tạo hình/choreography vẫn chờ người dùng xem.

Mở `demo.html` để xem Canvas, chọn hoạt cảnh, phát lại, tạm dừng, tua hoặc xem chậm. Canvas chỉ dùng WebP. GIF/MP4 là tệp duyệt riêng, không dùng để chạy trong trận.

## Tài sản và tham chiếu

- `source/poses.png`: 16 tư thế chiêu cuối, PNG alpha 1254 × 1254; lấy đà, bay lên, bổ nhào/hãm cánh, đáp và ăn mừng.
- `source/states.png`: 16 tư thế phụ, PNG alpha 1254 × 1254; bốn tư thế sẵn sàng, bốn tấn công vỗ cánh, bốn chịu đòn/phục hồi, bốn buồn khi thua.
- `assets/poses.webp`: 424.824 byte; `assets/states.webp`: 493.666 byte. Tổng hai sheet: **918.490 byte**. Có alpha thật, đã mở xem trên nền kem và xanh đậm.
- `poses.js`, `states.js`: vùng ảnh cho từng tư thế. Tổng cộng 32 tư thế; không có tay riêng, cánh thứ ba hoặc thay giải phẫu loài.
- Ảnh nhận diện: ô hàng 2, cột 1 của `design/5bmath/linh-vat/bo-nhan-vat-demo-2026-11-11/02-thu-va-canh.png` tính từ 1. Ảnh `mam-sach-cao-nau-goc.png` chỉ làm tham chiếu chất liệu/màu/phong cách.
- Đã dùng **built-in image_gen**. Prompt ban đầu ở `source/PROMPTS.json`; prompt sửa khoảng cách ở `source/REVISION.json`.
- `source/states-v1-spacing-rejected.png` được giữ để truy vết, **không dùng runtime**: cánh của tư thế tấn công cũ lấn sang ô kế. Bản `states.png` mới đã sửa bằng imagegen; vùng nét chính cách biên ô ít nhất 14 pixel theo QA.

## Hoạt cảnh

| Hoạt cảnh | Thời lượng | Chuyển động |
|---|---:|---|
| Chiêu cuối | 3,000 giây | Vút lên, bổ nhào theo vệt chữ V, xòe cánh hãm; hai luồng gió hợp bão lông vũ; đáp và ăn mừng. |
| Tấn công | 1,000 giây | Lấy đà ngắn, nhảy nhẹ và vỗ cánh tạo gió rồi trở lại tư thế sẵn sàng. |
| Chịu đòn | 1,100 giây | Giật mình, lùi/nghiêng nhẹ và lấy lại thăng bằng; không thương tích. |
| Buồn khi thua | 3,000 giây | Cánh rũ, hạ đầu, ngồi yên buồn nhưng không bị thương. |
| Sẵn sàng | 3,000 giây trong demo | Nhịp thở/chớp mắt nhẹ; game giữ tư thế nghỉ khi không có hành động. |

Chiêu cuối hiện tên **SẢI CÁNH BÃO TÁP** từ 0,65 giây, bắt đầu đòn lúc 0,95 giây, tác động khoảng 1,75 giây, ăn mừng từ 1,90 đến 3,00 giây. Banner nằm dưới vùng hành động trên sân để không che Đại bàng ở đỉnh đường bay; nhãn pha tạm ẩn trong thời gian hiện tên để tránh chồng chữ. Bản xuất chuẩn 30 fps, 90 khung; không có âm thanh riêng.

Ba GIF trạng thái riêng trong `exports/` đều 768 × 432, 30 fps: `attack.gif` 30 khung/1.000ms/591.424 byte, `hit.gif` 33 khung/1.100ms/608.833 byte, `defeat.gif` 90 khung/3.000ms/897.619 byte. GIF lặp để tiện duyệt, còn runtime Canvas trong trận phát hành động hữu hạn.

## Tích hợp và vòng đời

Runtime ở `frontend/eagle-animation.js` và CSS riêng, hai WebP dùng trong game ở `frontend/arena-art/eagle/`. Các hook lựa chọn linh vật, snapshot API, biểu diễn tấn công/chịu đòn/đòn kết thúc và kết quả trận đã được sửa hẹp trong cây làm việc. Không đổi sát thương hoặc quy tắc tính kết quả.

Tác vụ này chỉ commit tài sản/module Đại bàng và bản vá tích hợp theo phạm vi đã chốt; các tệp ứng dụng nền đang có thay đổi từ chat khác không được gom vào commit này. Đọc bản vá tích hợp và báo cáo bàn giao trước khi áp dụng vào checkout khác. Không tự push hoặc phát hành website công khai.

Animation hữu hạn: tấn công và chịu đòn trở về idle; thua/thắng giữ khung cuối. Dừng lịch vẽ khi ẩn trang, rời trang hoặc tháo nhân vật; hủy Canvas chiêu cuối sau ba giây. Có xử lý `prefers-reduced-motion`; không dùng vòng lặp liên tục cho nhân vật nghỉ. Canvas/game không tải GIF/MP4.

## QA và giới hạn

`qa/eagle-assets-report.json` lưu kích thước, alpha, byte và biên từng tư thế; `qa/eagle-runtime-report.json` lưu kiểm demo. Ảnh kiểm nền sáng/tối và banner cũng nằm trong `qa/`. Báo cáo `qa/qa-report.json` do exporter chiêu cuối quản lý riêng; `qa/eagle-state-gifs-report.json` ghi thời lượng/số khung/dung lượng GIF phụ sau khi xuất.

Đã kiểm demo bằng Chrome trên 390 × 844, 844 × 390, 768 × 1024, 1024 × 768, 1440 × 900: không tràn ngang, không lỗi JavaScript/tài nguyên; điều khiển cao ít nhất 44 pixel. Đạt tua/tạm dừng/xem chậm/phát một lần, reduced motion và handler ẩn trang được mô phỏng. Đã mở xem ảnh nguồn, WebP và các mốc hoạt cảnh. Kiểm thực tế game/API/Docker/localhost và commit do phiên chính ghi kết quả cuối vào HANDOFF/bộ nhớ; tài liệu này không khẳng định các kiểm thử đó đạt trước khi có báo cáo.

Chưa đo FPS/CPU trên điện thoại thật, mạng chậm hoặc Core Web Vitals. FPS của video xuất không chứng minh hiệu năng thiết bị thật. Cần người dùng duyệt chất lượng chuyển động; không tự đặt trạng thái `approved`.
