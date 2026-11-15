# Linh vật theo huy hiệu và animation trong game

Đã được người dùng giao tích hợp ngày14/11/2026; các demo trước vẫn giữ riêng để đối chiếu. Không sửa nguồnPNG/job đã bàn giao.

## Hình và chuyển động

- `frontend/arena-art/badge-mascots/data.js`:20nhân vật,atlas16tưthế từngcon,tênchiêu và hiệu ứng riêng; nguồn từ demo3huy hiệu đãduyệt.
- `runtime.js`:Canvas chờ/rađòn/trúng/chiêucuối/phòngthủ, lớpFX sân; tải WebP nhân vật đang dùng, ngừng vẽ khiẩn tab và hỗtrợ giảmchuyểnđộng.
- Hình ngoài trận dùng tư thế chờ có alpha thật trong bộ WebP đã duyệt ở `arena-art/badge-mascots/`, theo đúng huy hiệu; không còn cắt từ bảng duyệt có nền kem. Avatar, thẻ, popup tiến hóa/thăng hạng/thách đấu dùng chung hàm `portrait()`. Không lật ảnh theo vị trí ngoài trận. Chỉ Canvas và ảnh dự phòng **trong trận** mới hướng cả mặt/thân về đối thủ; bên phải lật toàn bộ nhân vật.
- Từ0XP dùng Đồng,100XP dùng Bạc,200XP dùng Vàng; các bậcI–V trong cùng huy hiệu dùng chung tạo hình. Rank20XP/bậc và sànXP0 giữ nguyên.
- Thẻ chọn,avatar,thanhbên,phòng công khai,lời thách đấu,xếphạng,trận/kếtquả đều lấy hình theo XP của đúng đối tượng. Bot luyện tập không cóXP, dùng hình Đồng.
- `dispatchBattleHit()` ưu tiên renderer mới cho đủ20con. Ba hiệu ứng ngẫu nhiên cũ không còn được dùng để vẽ đòn thường của các Canvas mới; trường spell cũ trong lịch sử/giao thức vẫn có thể tồn tại để tương thích.
- Bản vá nền trắng/chiêu cuối ngày 14/11: `portrait()` tái sử dụng khung chờ alpha thật, không sửa ảnh nguồn. Chiêu cuối phía chịu đòn: 0–1,75 giây chờ, 1,75–2,45 giây chịu đòn, từ 2,45 giây thua cuộc; sau 3 giây giữ tư thế kết quả. Bên đánh chỉ ăn mừng từ 2,45 giây. Có timer chuyển trạng thái cho chế độ giảm chuyển động và hủy timer khi rời trận. Bằng chứng mới: `work/mascot-fix-20261114/` (265 kiểm thử, 60 dạng alpha, 120 timeline, 6 viewport trên QA và localhost).
- Khiên chỉ xuất hiện cho người trả lời sau khi máy chủ đã chốt đáp án đúng trong cửa sổ 3 giây (`resolved`, `damage=10`, `lastAttack.defended=true`). `defenseUntil` chỉ là thời hạn còn cơ hội đỡ đòn, không tự kích hoạt tư thế/khiên. Trả lời sai, không trả lời hoặc đến hạn trở đi không đỡ đòn; bot dùng cùng điều kiện hiển thị. Luật máy chủ giữ nguyên: nhận đáp án trước hạn mới hợp lệ. Bằng chứng bản vá: `work/mascot-guard-rule-20261114/`.

## Thăng hạng sau trận

Server chốt `xpBefore`/`xpAfter` cùng thưởng/phạt và lưu trong `arena_members.result_json`; đọc lại kết quả trả cùng giá trị, không cộng XP lần nữa. Frontend dùng các mốc này để hiện “Chúc mừng thăng hạng!” sau khi hiệu ứng kết thúc trận hoàn tất.

Chỉ hiện khi thắng trận tínhXP và tăng bậc; không hiện khi bot/thua/hòa/bỏ trận/không tăng bậc/đãVàngV. Sessionpending gắn tài khoản vàIDtrận, đánh dấu đãhiện để reload không lặp; sai tài khoản không được hiển thị. Lên I–V trong cùng huy hiệu có hiệu ứng chúc mừng và nhãn bậc mới; vượt Đồng→Bạc/Bạc→Vàng có chuyển mờ/phóng hình cũ sang hình mới. Không tạo thêm dạng hình chưa được duyệt.

## Lời thách đấu

`opponentStats` chỉ gồm mascot,xp,level,wins,losses doAPI lấy từ dữliệu máy chủ;`opponentGrade` từkhối của phòng. UIhiện hình đúng huy hiệu,tênlinhvật,rank,XP,khối,100HPkhởitrận và thắng/thua. Không tự đặt chỉsố tấn công/phòng thủ hoặc thay luật sát thương. Giữ nút chấp nhận/hủy và bộ đếm; màn ngang dùng bố cục hai cột.

## Nghiệm thu14/11/2026

- Full265testbackendPASS, gồm chống giả thông số và idempotent98→100XP.
- QA hình60dạng;120cảnhđònthường,120chiêucuối,120phòngthủ (20con×3dạng×2phía),0JSerror.
- Trận hai người QA: CáHeoVàng200XP ở lời thách đấu; MầmSách98→100XP, popup ĐồngV→BạcI đổi hình; reload không lặp. Thử thêm tăng bậc cùnghuyhiệu,đúngtài khoản,reducedmotion.
- 6viewport dọc/ngang,ảnh và mã từ localhost khớpSHA; mainAPI riêng tư bị chặn trong lượt kiểmtra giao diện primary,0ghiDBthật.
- Backup/fingerprint70bảng mọi hàng trước/sau cập nhật khớp;giữXP/tài khoản/lịch sử/tài chính. Không đổi schema/luật trận/thanh toán.

Đây là Canvas2D với bộ tư thế đã duyệt và hiệu ứng rời, chưa phải rig3D/từngkhớp/cánh/đuôi/vải, chưa đoFPSđiệnthoại vật lý. Dữliệu và bằngchứng chi tiết riêng tư ở `work/mascot-integration-20261114/`; chỉ cập nhậtlocalhost, không đồng nghĩa Git/CI/website đã phát hành.
