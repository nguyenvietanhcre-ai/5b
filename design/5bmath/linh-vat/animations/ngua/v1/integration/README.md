# Tích hợp ngoại hình Ngựa

`frontend/horse-animation.js` và CSS đi kèm thêm lựa chọn **Ngựa · ngoại hình trận đấu** ở sảnh Đấu trí và trang Linh vật. Lựa chọn lưu riêng trong trình duyệt (`5bmath:arena-appearance`); không thay hồ sơ máy chủ, HP, điểm, câu hỏi hay kết quả.

Tài nguyên cần đóng gói: `frontend/arena-art/horse/v1/{poses,reactions}.{webp,json}`. Tải hai WebP và hai metadata khi cần. Trang chủ không tải sheet. Thêm JS/CSS vào HTML, allowlist Python và bản dựng tĩnh; chỉ công khai bốn tài nguyên đã nêu.

API trình duyệt: `HorseAnimation.create(canvas,{direction:1})` trả controller có `ready`, `play(state)`, `stop()`, `dispose()`; state gồm `idle`, `attack`, `hit`, `ultimate`, `win`, `defeat`. `HorseAnimation.preload()`, `setEnabled(bool)`, `enabled`, `activeCount`, `hit({source,victim,final})`, `notifyVictim(targetSelector,attackerSelector,final)` phục vụ game và QA.

`learning-hook.patch` chỉ ghi hai đoạn bổ sung Ngựa của checkout làm việc hiện tại. Kiểm tra `git apply --check` trước khi dùng ở checkout khác vì các chat khác có thể thay ngữ cảnh. Phần `hit` gọi ở đầu luồng hoạt cảnh; chỉ trả `true` khi bên tấn công đang dùng ngoại hình Ngựa. Khi kết liễu, giữ trang trận đủ 3,1 giây qua bộ đếm kết thúc có sẵn. Checkout hiện tại dùng `catFinaleUntil`; bản triển khai local tách riêng dùng `horseFinaleUntil` và cơ chế trì hoãn do bộ phát hành thêm. Không thêm biến trì hoãn mà thiếu chỗ sử dụng nó.

Nếu game có `dispatchBattleHit`, gọi `HorseAnimation.notifyVictim(...)` tại đó trước các handler nguồn để nhân vật Ngựa vẫn chịu đòn/thua khi một con vật khác xử lý chiêu rồi trả về sớm. Ở game cũ chỉ có một `animateHit`, đặt hook Ngựa đầu hàm là đủ. Module vẫn quan sát mood/HP để hỗ trợ game cũ.

Ngựa tạm nhận quyền hiển thị avatar bên mình bằng cách lưu rồi bỏ các class loài trên DOM, ẩn Canvas cũ sau khi sheet đã sẵn sàng. Tắt Ngựa khôi phục các class và nhãn. Đối thủ, tài khoản và luật đấu không đổi. Runtime hỗ trợ vẽ đảo hướng qua `direction:-1`; lựa chọn local chỉ áp dụng avatar của người chơi trên trình duyệt đó.

Chiêu cuối ba giây: tên 0,65 giây; phi 0,95; tác động/lốc đối thủ 1,75; thắng từ 1,90. Phát một lần; reduced motion giữ tư thế tĩnh; ẩn trang/rời trang dừng lịch vẽ. Không phát GIF/MP4 trong game. Chưa đo FPS trên thiết bị di động thật.
