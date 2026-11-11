# Tích hợp Chim sẻ vào bản game đang phát triển

Yêu cầu ngày 11/11/2026 cho phép tích hợp game và commit cục bộ. Chim sẻ dùng mã `sparrow`, tên **Chim sẻ** và chiêu cuối **Lốc Xoáy Ríu Rít**. Runtime là `frontend/arena-sparrow-animation.js` + `.css`, ảnh tại `frontend/arena-art/chim-se/`; không dùng GIF/MP4 làm runtime.

## Phạm vi Git và điều kiện áp dụng

HEAD khi đóng gói là `a8221fa`. Bản game hiện có nhiều thay đổi từ các chat khác chưa được commit, gồm toàn bộ `frontend/learning.js`, `backend/platform_api.py`, Arena, database và các thành phần liên quan. Commit riêng Chim sẻ không thu gom các tệp đó. Cần phát hành nền game trong một đợt riêng trước khi có thể dựng đầy đủ ứng dụng từ một checkout sạch.

`integration.patch` lưu đúng các thay đổi Chim sẻ trên **nền phát triển cục bộ đã có**, gồm năm tệp chung. Đây không phải patch áp trực tiếp lên `a8221fa`, và không chứa toàn bộ snapshot của nền ứng dụng. `integration-baseline.json` lưu SHA-256 trước/sau khi bỏ/thêm riêng Chim sẻ; nền trước được dựng trong bộ nhớ từ các tệp tại thời điểm đóng gói bằng cách bỏ đúng phần Chim sẻ, không phải khẳng định đã khôi phục được mọi phiên bản lịch sử của các chat khác.

| Tệp chung | Thay đổi Chim sẻ |
|---|---|
| `backend/platform_api.py` | Thêm ánh xạ `sparrow` → Chim sẻ vào danh mục dùng chung của seed, lựa chọn và dữ liệu trả về. |
| `backend/server.py` | Cho phép phục vụ đúng JS/CSS cùng ba tài nguyên WebP/JSON đã đóng gói. |
| `frontend/index.html` | Tải JS/CSS của Chim sẻ. |
| `scripts/build-pages.cjs` | Sao chép JS/CSS vào bản dựng; ảnh được vòng sao chép `arena-art` đã có xử lý. |
| `frontend/learning.js` | Tên, lưu lựa chọn, thẻ chọn, hành động chọn và hook chiêu cuối. Giữ luật sát thương/kết quả trận. |

## Kiểm tra và áp dụng

Từ thư mục dự án, trước hết đối chiếu các tệp chung với `integration-baseline.json`. Hash `beforeSha256LF`/`afterSha256LF` dùng UTF-8 với CRLF đổi thành LF; `afterSha256Raw` dùng byte gốc tại thời điểm chụp. Cần đúng nền **before** để áp patch; nếu đúng **after** thì đã tích hợp, không áp lần nữa.

```powershell
git apply --check design/5bmath/linh-vat/animations/chim-se/v1/integration.patch
git apply design/5bmath/linh-vat/animations/chim-se/v1/integration.patch
```

Trong workspace đã tích hợp, kiểm tra ngược mà không thay tệp:

```powershell
git apply --check --reverse design/5bmath/linh-vat/animations/chim-se/v1/integration.patch
```

Lệnh kiểm tra không thay index hay working tree. Nếu hash không khớp hoặc kiểm tra báo xung đột, đọc diff và ghép đúng phần Chim sẻ vào nền mới; không ghi đè toàn bộ tệp chung hay hoàn nguyên thay đổi của chat khác. Việc nền vẫn đang được các chat khác cập nhật có thể làm hash thay đổi ngay sau khi đóng gói.

## Hành vi runtime

Tư thế lấy từ 16 alpha bounds trong `poses.json`, giữ tỷ lệ chung: idle 0; lấy đà 0–3; bay 4–7; tấn công 8–9; chịu đòn 10–11; ăn mừng 12–13; buồn khi thua 14–15. Observer theo `data-mood` tự gắn Canvas cho `.battle-pet.sparrow`; trạng thái kết thúc giữ hình cuối, không chạy vòng lặp vô hạn. Chiêu cuối dùng hook `ArenaSparrowAnimation.ultimate({source,victim})`; tên hiện ở 0,65 giây, đòn bắt đầu 0,95, tác động khoảng 1,75, kết thúc 3 giây. Giữ quy tắc Arena hiện có về 20 sát thương và điều kiện thắng/thua.

Ảnh được tải khi cần Chim sẻ. Ẩn tab, đổi màn hình hoặc xóa sân đấu sẽ hủy overlay và lịch vẽ; reduced motion hiển thị tư thế tĩnh. Chỉ tải WebP và JSON. Bộ kiểm Canvas riêng đã kiểm năm viewport, bốn tư thế khác nhau, dừng requestAnimationFrame, hidden/removal và reduced motion; báo cáo cục bộ ở `work/mascot-animation/chim-se/v1/runtime-qa.json`. Kết quả đầy đủ và trạng thái localhost/commit được ghi tại `HANDOFF.md` khi kết thúc phiên.

## Bàn giao

Giữ toàn bộ nền game đang phát triển trong workspace hiện tại. Khi nền đó được commit riêng, áp/ghép patch, chạy lại kiểm thử Python, cú pháp JavaScript, bản dựng và luồng chọn Chim sẻ → vào trận → đánh/chịu đòn → chiêu cuối/kết quả. Commit cục bộ Chim sẻ không tự push hoặc triển khai website công khai.
