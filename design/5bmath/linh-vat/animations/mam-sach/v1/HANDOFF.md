# Bàn giao Mầm Sách v1

Owner: mam-sach-01a1cb4e; thư mục F:\ChatGPT Math Project\design\5bmath\linh-vat\animations\mam-sach\v1.

Yêu cầu11/11/2026 đã cho phép tích hợp game/commit/chạy local,thay mặc định demo riêng của workshop đối với Mầm Sách. Không push/Internet.

Đã tạo16pose từ ảnh gốc thật bằng imagegen; lượt nền trắng bị chặn,lượt cắt nền giữ alpha thật. source/poses.png là bản dùng; poses-white-v1.png giữ truy vết; source/reference.png là ảnh gốc. WebP292.192byte/1254²/16ô.

Bốn hoạt cảnh: ultimate Đại Thụ Tri Thức,attack,hurt,defeat. Demo Canvas có chọn hoạt cảnh/replay/pause/seek/tốc độ; ultimateGIF90frame/3000ms vàMP4H26490sample/3s,1280×720. Đã xem contact sheet và hình pose sáng/tối; đúng hai lá,sách mở,cảm xúc. Renderer demo và game dùng cùng mã.

QA: exporter và demo smoke/renderer contract đạt; năm kích thước390×844,844×390,768×1024,1024×768,1440×900; timeline0.65/0.95/1.75/1.9s,phát một lần,reducedmotion,không lỗiJS. FullWindows74tests đạt; staticCloudflare/GitHub8trang SEOđạt. Kiểm game vàDocker được ghi tiếp trong bộ nhớ dự án khi kết thúc.

Docker đã dựng localhost8765; JS/CSS/WebP Mầm có hash trùng nguồn; HTML nạp module; learning.js có đúng hook,APIhealth200/chấmmẫu10/10. Không đòi toàn bộlearning.js hashtrùng vì đang có cập nhật đồng thời từ các chat khác.

Commit riêng cần lưu module3tệp,thư mụcjob và2WebPshared phụ thuộc; integration.patch chứa đúng27dòng nối vào4tệp nền đang chưacommit từ công việc khác. Không stage toàn bộlearning/server/index/build hoặc thay đổi chatkhác. Đây là checkpoint riêng MầmSách,chưa phải release độc lập của toàn bộgame.

Trạng thái giữpending_review,khôngapproved. Chưa đoFPS/CPUđiện thoại thật,chưa có âm thanh mới. Không đổiHP/điểm/deadline hayDB. Bước sau:người dùng xem demo và thửMầmSách trongĐấu trí; tinh chỉnh nếu cần; đồng bộGitHub/chínhthức chỉ khi được yêu cầu.

Đã kiểm game thực qua tài khoản DB thử trên cổng28794: năm viewport,đánh trừ20HP không đổi,chịu đòn,chiêu cuối hai hướng,giữ trang3giây rồi kết quả thắng/thua,posebuồn ởkếtquả,reducedmotion vàcleanup khôngRAF; zeroJSerrors/failedrequests. QAserver đã dừng. FullDocker77tests đạt sau cấp /work tmpfs cho fixture; bộWindows74tests đạt ở thời điểm chạy. Hai buildCloudflare/GitHub8trang đạt. Có phát hiện tán cây/đối thủ chạm mép trên ởtrậnđấu chéo; đang sửaheadroom và kiểm mục tiêu riêng trước bàn giao cuối.

Hoàn tất sửa headroom: tán cây scale theo khoảng trống,đối thủ nâng vừa đủ giữ mép trên8px. Kiểm lại desktop1440×900/mobile390×844/ngang844×390 đạt,zeroJSerrors;rootđãmởxemảnh mới và kếtquảbuồn. 91mốc demo tạo18.528lệnhCanvasgiốnghệthốngcũ nênGIF/MP4đãxuấtvẫnhợplệ,rendererjobđãđồngbộ. Dockerlocalhost8765đãdựnglạihealthy,3tàisảnJS/CSS/WebPkhớphashnguồn,hookđúng/API10/10. KhôngcònviệcđangghihoặclỗiQAđãbiếttrongphạmviMầmSách;chờngườidùngxemvàgópý,chưađophầncứngđiệnthoạithật.
