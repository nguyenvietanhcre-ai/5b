# Tích hợp Thỏ vào game cục bộ

Người dùng yêu cầu rõ trong chat Thỏ ngày 11/11/2026: tạo chiêu cuối, tấn công, chịu đòn, thua cuộc; tích hợp game, commit và triển khai local. Chỉ đạo này thay phạm vi demo cũ đối với riêng Thỏ.

Runtime: `frontend/rabbit-animation.js`. Asset runtime: `frontend/arena-art/tho-poses.webp`, `tho-actions.webp`, `tho-idle.webp`, `tho-frames.json`. Chỉ tải hai sheet WebP và metadata khi trận/kết quả có Thỏ; không tải GIF/MP4. Art tĩnh dùng ảnh idle riêng.

- `RabbitAnimation.mount(root)`: khởi tạo Canvas trong `.battle-pet.rabbit`.
- `RabbitAnimation.play(node, action)`: idle/attack/hit/lose/win/ultimate; ultimate, lose, win ba giây; attack/hit 1,2 giây. Phát một lần, dừng khi ẩn tab, hỗ trợ reduced motion, không khởi động lại cùng action đang phát.
- `RabbitAnimation.notifyVictim(target, attacker, final)`: hook chung trước mọi renderer đặc biệt; tác động ultimate ở 1,75 giây, nhận thua khi hết máu.
- `RabbitAnimation.destroy()`: hủy requestAnimationFrame, timer và Canvas phủ stage khi rời trang.

Metadata có hai khóa `ultimate` và `actions`; mỗi khóa chứa kích thước sheet/cell và 16 frame bounds thật. Ultimate: bốn hàng lấy đà/bật nhảy/đáp xuống/ăn mừng. Actions: idle/tấn công/chịu đòn/thua. Runtime giữ kích thước nhân vật giữa pose, chừa khoảng trống cho tai khi bật trước trăng, ghép đệm trăng/sóng/sao bằng Canvas. Tên hiện từ 0,65 giây, trước cú bật 0,95; tác động 1,75; tổng ba giây.

Không đổi luật/sát thương, XP hoặc schema. API danh sách linh vật thêm mã `rabbit` ↔ `Thỏ`; lưu bằng bảng companions có sẵn. Hook game dùng thời gian giữ cảnh cuối hiện có để không cắt chiêu khi nhận kết quả PvP.

`game-integration.patch` lưu riêng delta của Thỏ trên nền app đang được nhiều chat sửa đồng thời. Đây **không phải diff từ HEAD**: trước phiên, nhiều tệp nền game vẫn chưa được Git theo dõi. Không dùng patch để thay thế toàn bộ các tệp chung hay tự kéo thay đổi của nhân vật khác. Trước khi áp dụng vào checkout khác phải có nền app tương ứng và kiểm tra `git apply --check`; không áp dụng lại vào bản làm việc đã có hook Thỏ.

QA game và database thử riêng ở `work/rabbit-game-integration/`; QA chuyên biệt không dùng tài khoản hoặc dữ liệu học sinh thật. Tình trạng/kết quả cuối được ghi trong HANDOFF và báo cáo QA của job.
