# Bàn giao Ngựa / v1

- Owner phiên: `ngua-01a1cb49`; thư mục `F:\ChatGPT Math Project\design\5bmath\linh-vat\animations\ngua\v1`.
- Đã xong bốn trạng thái: chiêu cuối Vó Ngựa Cuồng Phong, tấn công, chịu đòn, buồn khi thua. PNG nguồn, prompt, hai WebP/metadata, Canvas, tám bản GIF/MP4 và QA đều lưu trong job.
- Người dùng đã yêu cầu tích hợp game, commit và triển khai local trong phiên này. Không có yêu cầu push hoặc phát hành công khai. Hình ảnh vẫn `pending_review`, approval null; chờ người dùng xem và chỉnh nếu cần.
- Runtime: `frontend/horse-animation.js`, `horse-animation.css`, `arena-art/horse/v1/`. Lựa chọn Ngựa lưu trên trình duyệt, không đổi DB, linh vật hồ sơ, HP, XP hay luật. `integration/install.cjs` và patch/README ghi các thay đổi vào game nền.
- Đã kiểm: demo năm viewport × bốn trạng thái, media 3,000 giây/90 frame, WebP sáng/tối, runtime 30 ca/no JS errors; bot thắng/thua và lifecycle/reduced motion/fallback trên cả snapshot scoped và bundle local thực tế đều đạt. Xem qa/game-flow.json, qa/live-game-flow.json và qa/runtime-integration.json.
- Source baseline 57 kiểm thử Windows đạt. Image Ngựa riêng đạt 54 kiểm thử core Docker; không gộp bài thử companion mới của các chat khác vào kết luận backend snapshot.
- Image scoped `mam-toan:horse-local-01a1cb49` đã dựng và triển khai healthy, giữ volume `mam-toan_demo-db` và localhost/LAN. Sau đó chat khác redeploy bundle tổng hợp; đã kiểm lại Ngựa trên bundle thật `sha256:4fd47218ec3402e8b35a5e74ebbd1b38b5d55c23726eb39301430c419cceb3a4`, đủ bốn trạng thái/no JS error. HTTP module/CSS/4asset khớp SHA, MIME đúng, grade 10/10 và private 404.
- Runtime WebP tổng 666.150 byte, hai JSON tổng 3.680 byte. GIF/MP4 là bản xem, không tải vào game.
- Chưa đo FPS/CPU trên điện thoại thật. Native tab hiding chưa xác nhận trong Chrome headless; hidden/dispose kiểm bằng trạng thái giả lập và lifecycle. Demo không có âm thanh riêng; game giữ âm thanh hiện có.
- Commit chỉ tài sản/runtime Ngựa và bộ cài/hook; không gom mã game nền hoặc staged files của chat khác. Demo tự đầy đủ; addon cần game nền hiện có. Bản ghi chi tiết chỉ lưu cục bộ ở `docs/chat/2026-11-11-animation-ngua.md`.
- Không còn tiến trình ghi job. Khi làm tiếp: đọc README/QA và bộ nhớ, claim bằng owner mới nếu lease đã release. Không tự chuyển approved; nếu thay tạo hình đã được duyệt về sau thì tạo variant mới.
