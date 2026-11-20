/* Review prototype 02: a guided, expandable learning journey. */
window.Demo = {
  id: '2',
  name: 'Hành trình kiến thức',
  tagline: 'Mỗi ngày một bước nhỏ',
  nav: [['home', 'Hành trình', 'home'], ['learn', 'Bài giảng', 'book'], ['practice', 'Luyện tập', 'pen'], ['play', 'Trò chơi', 'game'], ['all', 'Tất cả', 'grid']],
  home: () => `
    <div class="j2-home">
      <header class="j2-intro">
        <div><p class="j2-eyebrow">HÀNH TRÌNH HỌC TOÁN · KHỐI ${UI.state.grade}</p><h1>Mỗi ngày,<br>tiến thêm một chút.</h1><p class="j2-lead">Học hiểu, luyện chắc, rồi thử sức. Mầm Sách đồng hành cùng em qua từng chặng.</p></div>
        <div class="j2-intro-art"><span class="j2-art-ring"></span><img src="assets/mascot.webp" width="180" height="180" alt="Mầm Sách đọc sách đồng hành cùng em"><span class="j2-art-caption">Cùng em lớn lên</span></div>
      </header>
      <div class="j2-layout">
        <section class="j2-journey" aria-labelledby="j2-journey-title">
          <div class="j2-section-head"><div><p class="j2-eyebrow">LỘ TRÌNH GỢI Ý</p><h2 id="j2-journey-title">Tuần học của em</h2></div><a class="j2-text-link" href="#learn">Chọn tuần ${UI.icon('arrow')}</a></div>
          <nav class="j2-week-switch" aria-label="Xem tuần học"><a href="#learn">Tuần 15</a><a href="#learn" class="is-current" aria-label="Tuần 16, tuần minh họa hiện tại">Tuần 16 <span>Đang học</span></a><a href="#learn">Tuần 17</a></nav>
          <p class="j2-example-note">Tuần và tiến độ chỉ minh họa lộ trình; chưa đối chiếu tuần SGK. Ví dụ dùng nội dung lớp 5, không phải kế hoạch riêng của khối đang chọn.</p>
          <div class="j2-timeline">
            <details class="j2-stop j2-complete">
              <summary><span class="j2-node" aria-hidden="true">${UI.icon('check')}</span><span class="j2-stop-copy"><small>CHẶNG 01 · LÀM QUEN</small><strong>Nhắc lại điều đã biết</strong><span>Ôn kiến thức trước khi học bài mới</span></span><span class="j2-summary-arrow" aria-hidden="true">${UI.icon('down')}</span></summary>
              <div class="j2-stop-body"><a class="j2-lesson-row" href="#lesson"><span class="j2-small-icon">${UI.icon('book')}</span><span><strong>Ôn tập số thập phân</strong><small>Xem lại phần ghi nhớ</small></span>${UI.icon('arrow')}</a><a class="j2-text-link" href="#history">Xem hoạt động đã làm ${UI.icon('arrow')}</a></div>
            </details>
            <details class="j2-stop j2-current" open>
              <summary><span class="j2-node" aria-hidden="true">2</span><span class="j2-stop-copy"><small>CHẶNG 02 · HIỂU VÀ VẬN DỤNG</small><strong>Gieo một mầm kiến thức</strong><span>Bắt đầu bằng bài giảng, tiếp nối bằng bài luyện</span></span><span class="j2-summary-arrow" aria-hidden="true">${UI.icon('down')}</span></summary>
              <div class="j2-stop-body">
                <article class="j2-focus-lesson"><div class="j2-focus-label">${UI.icon('book')} BÀI HỌC ĐANG DỞ · MINH HỌA</div><h3>Ôn tập phép tính<br>với số thập phân</h3><p>Đọc hướng dẫn tư duy, nắm điểm mấu chốt và theo dõi lời giải từng bước.</p><div class="j2-focus-progress"><div><span>Tiến độ bài học</span><strong>2 / 3 phần</strong></div><span class="j2-progress-track"><span></span></span></div><a href="#lesson" class="j2-button j2-button-peach">Học tiếp bài này ${UI.icon('arrow')}</a></article>
                <div class="j2-next-steps"><a href="#practice"><span class="j2-small-icon">${UI.icon('pen')}</span><span><strong>Luyện để hiểu chắc</strong><small>Chọn bài, dùng nháp và xem lời giải</small></span>${UI.icon('arrow')}</a><a href="#exams"><span class="j2-small-icon">${UI.icon('file')}</span><span><strong>Thử sức với một đề</strong><small>Làm bài, xem kết quả, tải PDF</small></span>${UI.icon('arrow')}</a></div>
              </div>
            </details>
            <details class="j2-stop j2-future">
              <summary><span class="j2-node" aria-hidden="true">3</span><span class="j2-stop-copy"><small>CHẶNG 03 · THỬ THÁCH</small><strong>Cho kiến thức nở hoa</strong><span>Luyện tư duy qua trò chơi và thử thách</span></span><span class="j2-summary-arrow" aria-hidden="true">${UI.icon('down')}</span></summary>
              <div class="j2-stop-body"><a class="j2-lesson-row" href="#play"><span class="j2-small-icon">${UI.icon('game')}</span><span><strong>Vào sân chơi Toán</strong><small>Đấu trí, Cướp Cờ và Đua Thú</small></span>${UI.icon('arrow')}</a><a class="j2-text-link" href="#rank">Xem bảng xếp hạng ${UI.icon('arrow')}</a></div>
            </details>
          </div>
          <div class="j2-path-footer">${UI.icon('grid')} <p>Em muốn tự chọn nội dung?<br><a href="#all">Mở toàn bộ Góc Học Tập</a></p></div>
        </section>
        <aside class="j2-support" aria-label="Công cụ và hoạt động bên cạnh hành trình">
          <section class="j2-rhythm"><div class="j2-section-head"><h2>Một nhịp học nhẹ nhàng</h2><span class="j2-sun" aria-hidden="true">${UI.icon('spark')}</span></div><p>Ba việc nhỏ, giúp em nhớ lâu hơn.</p><ol><li><span>01</span><div><strong>Đọc một bài giảng</strong><small>Hiểu vì sao trước khi tính</small></div><a href="#learn" aria-label="Mở bài giảng">${UI.icon('arrow')}</a></li><li><span>02</span><div><strong>Tự giải một bài toán</strong><small>Có bảng nháp ngay cạnh câu hỏi</small></div><a href="#practice" aria-label="Mở luyện tập">${UI.icon('arrow')}</a></li><li><span>03</span><div><strong>Xem lại cách làm</strong><small>Nhận ra chỗ mình có thể làm tốt hơn</small></div><a href="#results" aria-label="Xem kết quả và lời giải">${UI.icon('arrow')}</a></li></ol></section>
          <a href="#mascot" class="j2-companion"><span class="j2-companion-icon">${UI.icon('leaf')}</span><div><small>BẠN ĐỒNG HÀNH</small><h2>Mầm nhỏ, niềm vui lớn</h2><p>Ghé thăm linh vật và xem các huy hiệu của em.</p><strong>Đến vườn linh vật ${UI.icon('arrow')}</strong></div></a>
          <section class="j2-quick"><h2>Khi em cần</h2><a href="#scratch">${UI.icon('pen')}<span>Bảng nháp</span>${UI.icon('arrow')}</a><a href="#history">${UI.icon('clock')}<span>Lịch sử học và thi</span>${UI.icon('arrow')}</a><a href="#zoom">${UI.icon('video')}<span>Học cùng thầy cô</span>${UI.icon('arrow')}</a><a href="#notifications">${UI.icon('bell')}<span>Thông báo</span>${UI.icon('arrow')}</a></section>
        </aside>
      </div>
    </div>`
};
UI.boot(window.Demo);
