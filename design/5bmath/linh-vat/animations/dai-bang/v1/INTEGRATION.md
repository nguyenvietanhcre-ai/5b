# Tích hợp Đại bàng vào Đấu trí

Yêu cầu riêng của chat Đại bàng ngày 11/11/2026 đã cho phép tích hợp game và commit local. Quyền này chỉ áp dụng Đại bàng, không suy ra quyền phát hành các nhân vật hoặc thay đổi khác đang làm song song.

## Tệp chạy

- `frontend/eagle-animation.js`, `frontend/eagle-animation.css`.
- `frontend/arena-art/eagle/poses.webp`: 16 tư thế chiêu cuối, 4×4.
- `frontend/arena-art/eagle/states.webp`: hàng chờ, tấn công, chịu đòn, thua; mỗi hàng bốn tư thế.
- `integration.patch`: chỉ các móc nối Đại bàng trong năm tệp dùng chung. Bản vá không kèm mã ứng dụng hoặc animation của chat khác.

Hai ảnh WebP tải khi Đại bàng xuất hiện. Canvas phát hữu hạn, giữ khung cuối khi thắng/thua, dừng khi ẩn trang hoặc rời game. Chế độ giảm chuyển động hiển thị tư thế cuối. GIF/MP4 chỉ dùng để duyệt, không tải trong game.

Mã nhận diện lưu tài khoản là `eagle`, tên hiển thị `Đại bàng`. API giữ lựa chọn trong `student_companions`, trả đúng trong snapshot, bảng xếp hạng và hồ sơ phòng đấu qua bảng ánh xạ hiện có. Không thêm bảng hoặc thay đổi XP, sát thương, đáp án, thời hạn câu hỏi.

Đòn đánh thường dùng hàng tấn công; HP giảm thì chịu đòn. Khi đòn hiện có đưa HP đối thủ về 0, chiêu Sải Cánh Bão Táp phát ba giây: bay lên, vệt sáng chữ V, hãm cánh với hai luồng gió hợp bão lông vũ, đáp và thắng. Tác động ở 1,75 giây; tên hiện từ 0,65 giây. Màn kết quả dùng hàng buồn khi thua. Việc giữ màn hình trong 3,1 giây chỉ hoàn tất phần hình ảnh, không đổi kết quả máy chủ.

## Áp dụng lại bản vá

Các móc nối đã được áp dụng trong thư mục làm việc hiện tại. Vì nhiều chat đang sửa cùng mã chưa được commit, bản vá được lưu để phát hành riêng bộ Đại bàng mà không tự gom các công việc đó.

Trên bản ứng dụng có cùng nền Góc học tập/Đấu trí và bảng ánh xạ linh vật hiện tại, sao chép các tệp chạy ở trên, sau đó chạy từ gốc dự án:

```powershell
git apply --check design/5bmath/linh-vat/animations/dai-bang/v1/integration.patch
git apply design/5bmath/linh-vat/animations/dai-bang/v1/integration.patch
```

Để xác minh thư mục hiện tại đã có các móc nối:

```powershell
git apply --reverse --check design/5bmath/linh-vat/animations/dai-bang/v1/integration.patch
```

Không áp dụng bản vá hai lần. Nếu mã dùng chung đã thay đổi, đọc từng hunk và gộp lại; không ghi đè cả tệp. Bản vá dựa trên game hiện tại, không bổ sung toàn bộ ứng dụng Góc học tập còn thiếu ở commit gốc `a8221fa`.

## Kiểm tra

- `node --check frontend/eagle-animation.js` và `node --check frontend/learning.js`.
- Kiểm thử module: `node work/eagle-integration/browser-check.cjs`. Bộ kiểm dùng hai WebP thật, năm kích thước dọc/ngang, tấn công/chịu đòn/thua/chiêu cuối, giảm chuyển động và dọn Canvas. Báo cáo tại `work/eagle-integration/browser-report.json`.
- API chọn rồi đăng nhập lại với database QA riêng: `work/eagle-integration/api-check.py`; báo cáo `api-report.json`, không sửa database thật.
- Game dùng nguyên source qua tuyến HTTP giả lập HTTPS và hồ sơ trải nghiệm cục bộ: chọn Đại bàng bằng giao diện, năm kích thước dọc/ngang, đáp án gây đúng 20 máu/tấn công thường, đòn kết thúc và màn thắng, bot đánh và màn thua giữ tư thế buồn cuối, Đại bàng đấu Đại bàng chịu thua tại tác động, giảm chuyển động không tạo Canvas chiêu cuối. Không lỗi JavaScript, không tải GIF/MP4 hoặc gọi API. Báo cáo đã lược danh sách request, script và ảnh tại `qa/integration/game-source-report.json`, `qa/integration/offline-game-check.cjs` và các ảnh `game-*.png`.
- Máy chủ nguồn thử riêng ở 8794 không truy cập được từ tiến trình kiểm qua HTTP; đã dừng child của phép thử, giữ tiến trình không thuộc phép thử. Việc nghiệm thu game ở trên dùng source thật qua mock-route, không gọi đó là kiểm thử HTTP backend 8794. Bốn tài nguyên trên localhost8765 đã được kiểm HTTP200 và SHA256 khớp nguồn bằng phép thử riêng; bản chạy cuối do chat chính dựng/xác minh.
- Đã kiểm trình duyệt desktop giả lập kích thước màn hình. Chưa đo FPS/CPU trên điện thoại thật.
