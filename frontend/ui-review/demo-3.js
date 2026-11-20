'use strict';

(() => {
  const tile = (number, title, description, route, symbol, extra = '') => `
    <a class="l3-tile ${extra}" href="#${route}">
      <span class="l3-tile-top"><span class="l3-index">${number}</span><span class="l3-tile-icon">${UI.icon(symbol)}</span></span>
      <span class="l3-tile-title">${title}</span>
      <span class="l3-tile-copy">${description}</span>
      <span class="l3-tile-end">Khám phá <span aria-hidden="true">↗</span></span>
    </a>`;
  const row = (title, description, route) => `<a class="l3-row" href="#${route}"><span><strong>${title}</strong><small>${description}</small></span><span class="l3-row-arrow" aria-hidden="true">→</span></a>`;
  const shelf = (number, title, description, rows) => `<section class="l3-shelf" aria-labelledby="l3-shelf-${number}"><div class="l3-shelf-heading"><span class="l3-index">${number}</span><div><h3 id="l3-shelf-${number}">${title}</h3><p>${description}</p></div></div><div class="l3-shelf-links">${rows}</div></section>`;

  window.Demo = {
    id: '3',
    name: 'Thư viện thông minh',
    tagline: 'Tìm nhanh, chọn đúng, học theo cách của em.',
    nav: [['home', 'Khám phá', 'search'], ['learn', 'Bài giảng', 'book'], ['practice', 'Luyện tập', 'pen'], ['play', 'Trò chơi', 'game'], ['account', 'Cá nhân', 'user']],
    home: () => `
      <div class="l3-home">
        <section class="l3-intro" aria-labelledby="l3-title">
          <div class="l3-intro-copy">
            <p class="l3-eyebrow"><span class="l3-dot" aria-hidden="true"></span> GÓC HỌC TẬP · KHỐI ${UI.state.grade}</p>
            <h1 id="l3-title">Em muốn học gì<br><span>hôm nay?</span></h1>
            <p class="l3-intro-description">Bài giảng, luyện tập và trò chơi.<br>Mọi thứ đều có một chỗ dễ tìm.</p>
          </div>
          <div class="l3-library-mark" aria-hidden="true"><span>5B</span><small>HỌC MỖI NGÀY<br>THÊM MỘT CHÚT</small><i>+</i></div>
        </section>

        <section class="l3-search-section" aria-labelledby="l3-search-title">
          <label id="l3-search-title" for="l3-search">Tìm trong Góc Học Tập</label>
          <div class="l3-search-box">${UI.icon('search')}<input id="l3-search" data-demo-search type="search" placeholder="Bài giảng, nháp, PDF, Đấu trí…" autocomplete="off" aria-describedby="l3-search-help"></div>
          <p id="l3-search-help">Gõ tên chức năng, có dấu hoặc không dấu.</p>
          <div id="search-results" aria-live="polite"></div>
        </section>

        <nav class="l3-quick-links" aria-label="Truy cập nhanh">
          <span>Đến nhanh</span>
          <a href="#lookup">Tra mã câu <span aria-hidden="true">↗</span></a>
          <a href="#history">Lịch sử <span aria-hidden="true">↗</span></a>
          <a href="#pdf">Xuất PDF <span aria-hidden="true">↗</span></a>
          <a href="#notifications">Thông báo <span aria-hidden="true">↗</span></a>
        </nav>

        <section class="l3-main-catalogue" aria-labelledby="l3-catalogue-title">
          <div class="l3-section-heading"><div><p class="l3-eyebrow">CHỌN KHÔNG GIAN</p><h2 id="l3-catalogue-title">Một chạm đến đúng việc</h2></div><a class="l3-text-link" href="#all">Tất cả chức năng <span aria-hidden="true">→</span></a></div>
          <div class="l3-tiles">
            ${tile('01', 'Học kiến thức', 'Theo tuần, chuyên đề<br>và bài giảng video.', 'learn', 'book', 'l3-tile-green')}
            ${tile('02', 'Luyện &amp; thi', 'Luyện tập, thi thử,<br>nháp và xem lời giải.', 'practice', 'pen', 'l3-tile-peach')}
            ${tile('03', 'Chơi cùng bạn', 'Đấu trí, Cướp Cờ,<br>Đua Thú và xếp hạng.', 'play', 'game', 'l3-tile-cream')}
            ${tile('04', 'Không gian của em', 'Linh vật, tài khoản<br>và thông báo học tập.', 'account', 'user', 'l3-tile-white')}
          </div>
        </section>

        <section class="l3-directory" aria-labelledby="l3-directory-title">
          <div class="l3-section-heading"><div><p class="l3-eyebrow">DANH MỤC CHỨC NĂNG</p><h2 id="l3-directory-title">Tìm theo nhu cầu</h2></div><span class="l3-directory-note">Cùng một thư viện, nhiều lối vào.</span></div>
          <div class="l3-shelves">
            ${shelf('01', 'Học và luyện', 'Từ hiểu bài đến tự làm bài.',
              row('Bài giảng', 'Theo tuần · Chuyên đề · Video', 'learn') +
              row('Luyện tập', 'Chọn nội dung · Tra cứu mã câu', 'practice') +
              row('Thi thử', 'Làm đề · Xem kết quả và lời giải', 'exams') +
              row('Bảng nháp', 'Viết, vẽ và xem nháp theo câu', 'scratch'))}
            ${shelf('02', 'Chơi và phát triển', 'Học Toán cùng những người bạn.',
              row('Phòng trò chơi', 'Đấu trí · Cướp Cờ · Đua Thú', 'play') +
              row('Bảng xếp hạng', 'Theo dõi thành tích học tập', 'rank') +
              row('Linh vật', 'Bạn đồng hành và huy hiệu', 'mascot') +
              row('Lịch sử hoạt động', 'Mở lại bài đã làm và kết quả', 'history'))}
            ${shelf('03', 'Tài khoản của em', 'Thông tin và quyền lợi ở cùng chỗ.',
              row('Hồ sơ cá nhân', 'Thông tin · Gói học · Tài khoản', 'account') +
              row('Thông báo', 'Xem nội dung và đánh dấu đã đọc', 'notifications') +
              row('Mời bạn học cùng', 'Mã giới thiệu và lịch sử', 'referral') +
              row('Nâng cấp gói', 'Xem quyền lợi các gói học', 'upgrade'))}
            ${shelf('04', 'Học cùng gia đình', 'Phụ huynh dễ tìm việc cần làm.',
              row('Lớp Zoom', 'Đăng ký hoặc xem lớp của em', 'zoom') +
              row('Kho đề', 'Xem đề bán riêng và đề đã mua', 'buy') +
              row('Xuất PDF', 'Đề bài, đáp án và lời giải', 'pdf') +
              row('Kết quả học tập', 'Xem lại kết quả và bài đã làm', 'results'))}
          </div>
        </section>

        <aside class="l3-tip"><span class="l3-tip-icon">${UI.icon('search')}</span><div><strong>Không cần nhớ chức năng nằm ở đâu.</strong><p>Dùng ô tìm kiếm ở đầu trang hoặc mở “Tất cả chức năng”. Mọi mục đều có nhãn rõ ràng.</p></div><a href="#all" aria-label="Mở tất cả chức năng">${UI.icon('grid')}</a></aside>
      </div>`,
  };

  UI.boot(window.Demo);
})();
