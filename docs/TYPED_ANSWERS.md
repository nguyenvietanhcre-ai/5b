# Hình thức trả lời và phòng thủ Đấu trí

Quy tắc được người dùng phê duyệt trong chat ngày 13/11/2026; triển khai và QA tiếp sang 14/11/2026. Trạng thái phát hành xem PROJECT_MEMORY, không suy ra từ tài liệu thiết kế này.

## Bài luyện và ngân hàng

Quy tắc mới nhất ngày 14/11/2026: câu một đáp số dùng tự nhập; câu nhiều ý (a, b), nhiều đối tượng cần đáp số hoặc nhiều kết quả dùng trắc nghiệm. Mỗi phương án chứa đủ mọi kết quả, ghi rõ nhãn và đơn vị, chỉ chọn một phương án đúng hoàn toàn. Không bắt học sinh gõ một chuỗi dài khi thi đấu.

Ngân hàng ghi `responseType=typed|choice`, `answerShape=single|parts|objects|solutions`, `answerTargets` trong grading rule của phiên bản câu hỏi. Quản trị chọn cấu trúc và hình thức; máy chủ bắt buộc choice nếu có nhiều nhãn/ý/kết quả. Cần khai báo cấu trúc chính xác, không dựa hoàn toàn vào việc máy đọc hiểu đề văn. Metadata/đánh dấu a), b) giúp phát hiện trường hợp rõ ràng; không phải bộ phân tích Toán tự động.

Trắc nghiệm có đúng bốn phương án không trùng, một đáp án chuẩn và giải thích cho cả bốn. Ba phương án sai phải từ lỗi giải cụ thể: nhầm nửa chu vi với chu vi, đổi chỗ đại lượng, lấy phần trăm trên sai lượng gốc, sai bước quy đồng… Giữ cùng thứ tự nhãn, đơn vị và cách trình bày; tránh lộ đáp án qua độ dài hoặc một phương án vô lý. Hàm `backend.answers.propose_choices` ghép bộ đáp số từ ba lỗi có lý do do người soạn cung cấp, từ chối bộ giá trị tương đương; không bù số ngẫu nhiên. Gợi ý luôn là nháp, người soạn phải kiểm lại toàn bộ điều kiện và tính duy nhất. Chưa có dữ liệu thực nghiệm để khẳng định độ phân biệt của từng câu; chất lượng nhiễu cần rà soát và theo dõi sau sử dụng.

Ví dụ hình chữ nhật có chu vi 40 cm, dài/rộng = 3/2: phương án đúng `Dài: 12 cm; Rộng: 8 cm`; nhiễu `Dài: 8 cm; Rộng: 12 cm` (đảo đối tượng), `Dài: 24 cm; Rộng: 16 cm` (dùng chu vi thay nửa chu vi), `Dài: 16 cm; Rộng: 4 cm` (nhầm tổng–tỉ thành tổng–hiệu). Mỗi phương án đều chứa hai kết quả.

Đề mới có thể trộn hình thức: `question.responseMode` quyết định từng câu; `exams.response_mode` còn là fallback tương thích đề cũ. Đề typed không trả options; câu choice chỉ trả lựa chọn, không trả đáp án hay giải thích trước nộp. Máy chủ kiểm lựa chọn thuộc snapshot bất biến rồi chấm đúng phương án; không chấm theo đáp án chuẩn client tự khai. Sửa câu hỏi tạo phiên bản mới, không chấm lại điểm đã nộp hoặc sửa bài đang làm.

Câu tự nhập lưu nháp tối đa 500 ký tự. Bộ chấm `backend/answers.py` dùng số học chính xác cho dấu phẩy/chấm thập phân và phân số tương đương; không eval, AI hay dịch vụ trả phí. Không tự xóa đơn vị/đoán dấu hàng nghìn. `auto`, `number`, `text` tiếp tục dùng cho một đáp số; `ordered`, `unordered` chỉ giữ cho lịch sử tương thích, câu mới nhiều kết quả chuyển choice. Chứng minh/lời giải dài vẫn cần giáo viên chấm lập luận.

Native Free/VIP cục bộ: giữ nguyên 60 câu trắc nghiệm và các gói nguồn đã niêm phong; 30 câu một đáp số còn cho tạo lượt typed, 19 câu phức hợp trong bộ 49 typed chuyển sang lựa chọn MCQ có sẵn cho lượt mới. Chặn yêu cầu typed không phù hợp trước trừ ví; bài/lượt cũ và requestKey retry của chính chủ giữ hình thức và chi phí ban đầu. Không sửa nội dung nguồn, database hoặc quyền/quota để chuyển hình thức.

## Đấu trí

1. Mỗi người nộp một lần/câu. Nộp sai không tạo đòn tấn công.
2. Đáp án **đúng đầu tiên**, tới máy chủ trước hạn câu, mở cửa sổ phòng thủ đủ **3 giây**. Cửa sổ này thay thời gian câu còn lại, kể cả khi câu gốc sắp hết giờ.
3. Người còn lại chưa nộp: giữ đề, chữ đang gõ hoặc lựa chọn đang chọn, focus và bàn phím. Với câu trắc nghiệm, chọn phương án rồi bấm “Gửi đáp án”; chỉ chọn chưa tiêu thụ lượt trả lời. Bên tấn công hiện “Em trả lời đúng! Chờ đối thủ phòng thủ: 3…2…1”; bên phòng thủ được nhắc trả lời đúng để giảm sát thương. Không lộ đáp án đúng.
4. Đáp án đúng của người sau phải tới máy chủ **trước** `defenseUntil`: đỡ đòn, mất **10 máu**. Tới đúng mốc hết hạn hoặc muộn hơn, sai hoặc bỏ trống: mất **20 máu**. Đã nộp sai trước đó không có lần nộp thứ hai.
5. Chỉ trừ máu một lần sau khi chốt phòng thủ. Không báo KO trước đó, không trừ20 rồi hồi10. Người phòng thủ đúng vẫn được ghi nhận trả lời đúng. Không đổi cách thưởng XP trận.
6. Sau kết quả mới bắt đầu **3 giây chuyển câu** riêng. Hai bên sai/hết giờ không có đáp án đúng thì giữ máu. Phòng thủ và chuyển câu là hai giai đoạn khác nhau.

Máy chủ quyết định thời hạn, thứ tự request, điểm và sát thương của trận người thật; đồng hồ trình duyệt chỉ hiển thị. Bot vẫn là demo không XP chạy trong trình duyệt như trước, nhưng dùng cùng cửa sổ3giây/10–20máu. Bot chỉ phòng thủ nếu tới thời điểm trả lời đã lên lịch của nó và khả năng mức bot đáp ứng câu; không tự trả lời đúng ngay vì người chơi vừa tấn công.

## QA Free/VIP riêng

Worktree `work/free-vip-round1-20261113/nen-tang/src` cũng tạo đề mới typed. Bộ nhập đọc được legacy `single-choice` và mới `short-answer`; kiểu mới dùng `correctAnswer`, `answerKind`, không yêu cầu `choices`, `correctChoiceId`, `choiceRationales`. Giữ wrapper schema `mcq-draft-v1` tương thích gói cũ, các ràng buộc nguồn/quyền/revision/draft/QA-only và transaction không đổi. Chưa nối importer này vào dữ liệu học sinh thật. Không sửa nguyên gói10câu/60tựluận hoặc biến chúng thành học liệu đã duyệt.
