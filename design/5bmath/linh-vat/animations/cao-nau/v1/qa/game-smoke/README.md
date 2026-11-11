# Kiểm tra runtime game Cáo Nâu

Playwright/Chrome headless; mọi request dùng tên miền thử fox.test được trả từ tệp local qua route.fulfill. Không truy cập HTTP backend thật trong phép thử này. Report passed=true,10 nhóm kiểm tra,không lỗi JavaScript. Đã kiểm lazy loading,pose hữu hạn,giữ tư thế cuối,tên trước tác động,cleanup ba giây,route removal,reduced motion và5viewport. HTTP local/Docker vàfullgame được xác minh riêng bởi phiên gốc. Không đo FPS trên điện thoại thật.
