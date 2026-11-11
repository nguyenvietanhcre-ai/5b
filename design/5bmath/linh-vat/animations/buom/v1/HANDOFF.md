# Bàn giao Bướm / v1

- Chủ phiên: buom-01a1cb4c-root
- Trạng thái tác vụ hình ảnh: `pending_review`; chưa tự ghi phê duyệt mỹ thuật.
- Yêu cầu mới trong chat này đã cho phép tích hợp game, commit và triển khai **local**. Giới hạn demo trong BRIEF là lịch sử; không suy ra quyền push/phát hành công khai.
- Nguồn `source/poses.png`: sheet 4×4 / 1254×1254 / alpha thật, image_gen từ Bướm ở hàng2 cột3 của `02-thu-va-canh.png`, style Cáo Nâu/Mầm Sách. Exact prompt và tham chiếu ở `source/PROMPTS.json`.
- Runtime `assets/poses.webp`: 356.800 byte, 16pose, alpha. PNG gốc giữ nguyên. Đã xem16pose trên nền kem và xanh đậm; không nền ôcaro/viền màu; hai râu/bốn cánh/sáu chân nhỏ cách điệu, không cắt hình trong cell.
- `butterfly-renderer.js` là bản sao cùng nội dung của `frontend/butterfly-renderer.js`. Pure API: `pose(ctx,image,index,x,y,size,rotation=0,flip=false)`, `effects(ctx,t,source,target,options)`, `state(t)`; x/y tâm và size là chiều vuôngcell. Helpers `butterfly/star`. Options `title:false`, `lowQuality:true` (48 thay128 bóng), `reducedMotion:true`.
- `animation.js`/`demo.html` đã dựng riêng chuyển động bay/vỗ cánh, 128bóng bướm tụ thành đôi cánh lớn/bốn thùy rồi sóng cầu vồng. Tên .65s trước đòn .95s, tác động1.75s, thắng1.90–3.00s. Không còn choreography Chó.
- Demo có bốn mode `ultimate/attack/hit/lose`, replay/pause/seek/.5×. Tấn công/chịu đòn1.2s rồi giữ nghỉ trong cửa sổ xem3s; thua giữ tư thế buồn cuối. Reduced motion ban đầu dừng; ẩn trang dừng RAF.
- QA `qa/demo-controls.json`: bốn mode,5viewport390×844/844×390/768×1024/1024×768/1440×900, nút/select46px, không tràn ngang/JSerror, seek/pause/replay/mode/speed, reduced motion và WebP-only đạt. Xem `qa/modes-contact.png`, `qa/alpha-light-dark.png`.
- QA xuất chuẩn `qa/qa-report.json`: GIF90frame/3.000ms, MP4H.264 1280×720/90sample/3.000s và giải mã frameđầu; không tải PNG/GIF/MP4 trong Canvas. Báo cáo và file output hiện hành cần đối chiếu cùng thời giancheckedAt nếu xuất lại.
- Bản xuất cuối `checkedAt=2026-11-11T16:14:02.185Z`: GIF2.413.941byte, MP4 2.033.526byte. `qa/video-playback.json` xác minh giải mã bốn mốc .2/1.5/1.8/2.8s và phát MP4 đến kết thúc, không lỗi. Đã mở contactsheet timeline/bốnmode/alpha sáng-tối và khung MP4 giải mã.
- Chưa đo FPS/CPU trên điện thoại thật, chưa có âm thanh mới. Video/GIF là bản xem, runtime game chỉ dùng Canvas/WebP.
- Root đang quản lý tích hợp game/kiểm thử API/commit/local và bốn tệp bộ nhớ; bản ghi kỹ thuật này không xác nhận các bước đó đã hoàn tất.
- Lệnh xuất lại đúng owner: `node tools/mascot-animation/export.cjs buom --owner buom-01a1cb4c-root --variant v1 --replace`. Lệnh kiểm demo: `node work/mascot-animation/buom/v1/check-demo.cjs`.
- Trước khi đổi người: root ghi trạng thái tích hợp cuối rồi release; chat nhận tạo owner mới và claim theo workshop. Không tự xóa lease/lock của tác vụ đang chạy.

## Nghiệm thu tích hợp local — root, 11/11/2026

- Source game đã tích hợp đầy đủ lựa chọn/lưu Bướm, avatar, bốn trạng thái và finale; `install-butterfly.cjs --check` đạt20 điểm. Commit riêng bộ Bướm và installer tái lập các điểm nối, giữ các file dùng chung đang sửa đồng thời ngoài commit; xem INTEGRATION.md.
- Windows full74tests đạt; Docker2API Bướm +13HTTP/chấm bài đạt. Hai static build và SEO Cloudflare/GitHub đạt. Cú pháp JS/runtime/installer và diff-check đạt.
- QA game dùng Playwright phục vụ source qua route fulfillment và hồ sơ demo: 5viewport dọc/ngang không tràn; attack/hit/lose cả hai phía; ultimate đối thủ tên/impact/cleanup; đáp án đúng khi bot còn20HP kích hoạt finale và chờ đủ>=2,9s mới kết quả; reduced motion0job/overlay; rời trang0job, không JSerror/404 hoặc video/GIF runtime. Báo cáo/two screenshots đã lưu qa/game-integration.json và game-*-ultimate.png. Đã chọn Bướm qua UI/API backend thử riêng lần đầu; TCPQA sau đó không ổn định nên không gọi routedQA là end-to-end backend.
- Docker local đã triển khai và healthy trên127.0.0.1:8765, không mở LAN. Trang chủ/health/linh-vật/trận-đấu và4assetBướm200; hash4asset khớp source, đề mẫu10/10. DB trước/sau integrityok/FK0/accounts27/students27; catalog Bướm đúng1. Không tạo tài khoản QA vào database thật.
- Auto-review từ chối sao lưu fullDB vì có thể chứa dữ liệu tài khoản; không tạo bản sao. Cấu hình giữLAN cũng bị từ chối vì phạm vi local; đã dùng compose mặc định loopback, không lách các quyết định này.
- Chưa push/CI hoặc public deploy, chưa có đoFPS/CPU điện thoại thật. Duyệt mỹ thuật vẫn pending_review. Job được release sau khi tác vụ xuất và chỉnh hình hoàn tất; phiên sau claim owner mới trước sửa.
