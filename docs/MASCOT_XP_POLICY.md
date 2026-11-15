# Quy tắc kinh nghiệm linh vật

Từ 14/11/2026: **XP là số nguyên từ 0 đến 1.000.000.000**. Tài khoản mới bắt đầu ở 0. Không có quy tắc XP phải từ 1.000 trở lên.

| Vùng | Quy tắc hiện tại | Mã liên quan |
|---|---|---|
| Database đang dùng | `DEFAULT 0`, `CHECK (xp >= 0)` cho học sinh/bot; `min_xp >= 0` | `backend/migrations/0020_mascot_badge_ranks.sql` |
| Tạo tài khoản học sinh | Mặc định XP0; đổi linh vật giữ XP | `backend/platform_api.py` |
| Quản trị tạo/sửa tài khoản | Cho phép 0, 1, 20, 999; từ chối số âm, số lẻ, boolean và vượt trần | `backend/staff_api.py` |
| Giao diện quản trị | Input `min=0`; giá trị mặc định và dự phòng đều 0 | `frontend/staff.js` |
| Hiển thị, rank | XP0 là Đồng I; mỗi20XP lên bậc; sàn tính toán0 | `frontend/learning.js`, `backend/platform_api.py` |
| Thắng/thua/bỏ trận | Thưởng/phạt theo luật trận; kết quả XP không xuống dưới0, không kéo lên1000 | `backend/platform_api.py` |
| Offline cũ | Gỡ phần1000cấpsẵn mộtlần, đánh dấu `xpScale=2`; dữ liệu mới không bị trừ lại | `frontend/learning.js` |

## Dữ liệu lịch sử

`0001_learning_platform.sql` lưu cấu trúc **lịch sử** từng có sàn1.000. Không sửa ngược migration đã áp dụng. Khi dựng database mới hoặc nâng cấp database cũ, migration0020 thay cả ba bảng liên quan sang sàn0. Các giá trị1.000 trong phép chuyển đổi/fixture legacy là mức cấp sẵn cần loại một lần, không phải ràng buộc hiện hành.

Không chạy lại0020, không trừ1.000 vào dữ liệu đã chuyển và không reset XP đã kiếm được. Giữ `schema_migrations`, khóa ngoại, lịch sử trận/học tập/tài chính. Database đã có0020 chỉ cần kiểm schema hiện tại, không cần migration mới để đổi sàn.

## Kiểm tra

- `test_mascot_badges.py`: tài khoản mới0, ranh giới rank, legacy migration và tính lặp an toàn.
- `test_staff_accounts.py::test_xp_below_1000_can_be_saved_and_negative_values_are_rejected`: tạo/sửa từ0đến999 quaAPI quản trị và kiểmtrạngthái học sinh.
- `test_arena_penalties.py::test_xp_floor_and_preparation_cancellation_refund_both`: bỏ trận ở0XP không âm hoặc tự tăng lên1.000.

Tài liệu/bản ghi chat cũ có số1.000 là lịch sử, không được dùng làm nguồn quy tắc mới. Khi phát hành Cloudflare phải dựng và kiểm bản đang triển khai riêng; kết quả localhost không chứng minh website công khai đã cập nhật.
