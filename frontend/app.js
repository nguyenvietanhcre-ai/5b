'use strict';
const $=s=>document.querySelector(s), KEY='mamtoan-demo-v1';
const browser = typeof document !== 'undefined';
const offline = browser && location.protocol === 'file:';
const serverGrading = browser && !offline && document.documentElement.dataset.grading !== 'browser';
let data={name:'',completed:[],attempts:[],homework:null};
function loadProgress() {
    try {
        const saved = JSON.parse(localStorage.getItem(KEY));
        if (saved && typeof saved === 'object') data = { ...data, ...saved };
    } catch (_) {}
    if (!Array.isArray(data.completed)) data.completed = [];
    if (!Array.isArray(data.attempts)) data.attempts = [];
}
const esc=t=>String(t).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let clock=null, toastClock=null, remaining=900, submitted=false, gameStep=0,gameRound=0;
function save(){try{localStorage.setItem(KEY,JSON.stringify(data));}catch(_){toast('Trình duyệt chưa cho phép lưu tiến độ.');}}
function toast(t){$('#toast').textContent=t;$('#toast').classList.add('show');clearTimeout(toastClock);toastClock=setTimeout(()=>$('#toast').classList.remove('show'),4000);}
let modal;
function showModal(html){$('#modal-body').innerHTML=html;if(!modal.open)modal.showModal();}
function updateAccount(){$('#account').textContent=data.name?'Lớp của '+String(data.name).split(' ').slice(-1)[0]+' ↗':'Đăng nhập';}
function account(next){if(data.name){if(next)next();else location.assign(pageHref('dashboard'));return;}
showModal('<div class="modal-mark" aria-hidden="true">🌱</div><span class="eyebrow">GÓC HỌC TẬP CỦA EM</span><h2 class="modal-title">Chào em, nhà thám hiểm!</h2><p class="modal-copy">Đặt tên để trải nghiệm lớp học 5BMath.</p><form id="name-form"><label for="student-name">Tên em là gì?</label><input class="name-input" id="student-name" placeholder="Ví dụ: Minh Anh" maxlength="40" autocomplete="given-name" required><button class="btn dark" type="submit">Bắt đầu trải nghiệm ↗</button></form><p class="modal-note">TÀI KHOẢN MINH HỌA • Không có mật khẩu. Tên và tiến độ chỉ lưu trong trình duyệt này. Chưa có đăng nhập thật hoặc phân quyền bảo vệ tài liệu.</p>');
$('#name-form').onsubmit=e=>{e.preventDefault();const name=$('#student-name').value.trim();if(!name){$('#student-name').setCustomValidity('Em hãy nhập tên để tiếp tục.');$('#student-name').reportValidity();return;}data.name=name;save();updateAccount();modal.close();if(next)next();else location.assign(pageHref('dashboard'));};$('#student-name').oninput=e=>e.target.setCustomValidity('');
}
function setMenu(open) {
    const primaryNav = $('#primary-nav');
    const menuButton = $('#menu');
    primaryNav.classList.toggle('open', open);
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Đóng menu' : 'Mở menu');
}
const illustration=`<svg viewBox="20 24 540 428" role="img" aria-label="Linh vật mầm cây đọc sách trong Vườn Toán, cạnh dấu cộng và phân số một phần hai">
  <defs>
    <pattern id="garden-dots" width="23" height="23" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="1.4" fill="#809b58"/></pattern>
    <clipPath id="garden-edge"><path d="M59 105C109 38 250 16 366 44S541 111 548 219 463 445 319 439 64 404 35 313 20 162 59 105Z"/></clipPath>
  </defs>
  <g clip-path="url(#garden-edge)">
    <path d="M20 24H560V452H20Z" fill="#dcebbe"/>
    <path d="M65 116H540V313H65Z" fill="url(#garden-dots)" opacity=".3"/>
    <circle cx="452" cy="116" r="33" fill="#ffd68e"/>
    <path d="M18 337C112 269 183 294 254 315S461 277 558 301V455H18Z" fill="#bfd89e"/>
    <path d="M44 390C153 322 211 348 280 358S453 339 526 361V455H44Z" fill="#a8c682"/>
  </g>
  <ellipse cx="306" cy="378" rx="133" ry="17" fill="#89ab66"/>
  <path d="M145 111l4 12 12 4-12 4-4 12-4-12-12-4 12-4Zm248 46 5 14 14 5-14 5-5 14-5-14-14-5 14-5Zm115 45 3 9 9 3-9 3-3 9-3-9-9-3 9-3Z" fill="var(--paper)"/>
  <g transform="translate(111 221) rotate(-12)">
    <rect x="-37" y="-28" width="79" height="68" rx="15" fill="#96af93"/>
    <rect x="-41" y="-33" width="80" height="68" rx="15" fill="var(--paper)"/>
    <path d="M-10 1H10M0-9V11" stroke="var(--green)" stroke-width="4" stroke-linecap="round"/>
  </g>
  <g transform="translate(472 255) rotate(13)">
    <rect x="-37" y="-28" width="79" height="68" rx="15" fill="#96af93"/>
    <rect x="-41" y="-33" width="80" height="68" rx="15" fill="#ffda9d"/>
    <text y="13" text-anchor="middle" fill="var(--ink)" font-size="38" font-weight="800">½</text>
  </g>
  <path d="M177 369L174 344M174 353L164 343M175 351L185 337M436 375L432 352M433 361L421 350M433 359L444 345" stroke="#447a45" stroke-width="3" fill="none" stroke-linecap="round"/>
  <path d="M297 192C272 188 246 179 245 141 272 138 293 152 297 192Z" fill="#69a761"/>
  <path d="M297 193C299 155 318 131 353 132 350 164 329 188 297 193Z" fill="#317453"/>
  <path d="M190 289C187 224 242 177 302 180S404 226 401 287 358 375 297 373 192 338 190 289Z" fill="#296449"/>
  <path d="M197 277C203 221 249 186 304 189S393 229 394 279 351 362 296 363 197 326 197 277Z" fill="#458959"/>
  <path d="M204 267C210 228 246 201 291 196 253 208 235 232 226 266 218 278 207 277 204 267Z" fill="#5c9e68"/>
  <ellipse cx="262" cy="267" rx="15" ry="8" fill="var(--orange)"/><ellipse cx="331" cy="267" rx="15" ry="8" fill="var(--orange)"/>
  <ellipse cx="275" cy="254" rx="5" ry="9" fill="var(--ink)"/><ellipse cx="319" cy="254" rx="5" ry="9" fill="var(--ink)"/>
  <circle cx="274" cy="251" r="1.6" fill="#fff"/><circle cx="318" cy="251" r="1.6" fill="#fff"/>
  <path d="M288 268Q297 281 306 268" fill="none" stroke="var(--ink)" stroke-width="3" stroke-linecap="round"/>
  <path d="M216 291Q264 279 299 306 337 280 382 291L375 358Q332 359 299 373 265 359 223 358Z" fill="#e89554"/>
  <path d="M225 288Q269 281 299 305 329 281 373 288L367 348Q331 350 299 364 266 350 231 348Z" fill="#fffdf1"/>
  <path d="M299 308V360M242 305Q263 304 286 314M244 315Q264 314 286 324M312 314Q335 304 355 305M312 324Q334 314 354 315" stroke="#d78142" stroke-width="2" fill="none" stroke-linecap="round"/>
  <ellipse cx="222" cy="322" rx="15" ry="13" fill="#387750"/><ellipse cx="376" cy="322" rx="15" ry="13" fill="#387750"/>
</svg>`;
const courses=[
{id:'decimal',kind:'foundation',tag:'NỀN TẢNG',title:'Số thập phân, thật dễ hiểu!',description:'Cùng Thỏ và Sóc khám phá cách so sánh các số thập phân.',color:'green',number:'2,5',symbol:'<',meta:'20 phút · 4 câu luyện tập'},
{id:'percent',kind:'advanced',tag:'NÂNG CAO',title:'Giải mã tỉ số phần trăm',description:'Tăng 20% rồi giảm 20% — liệu có trở về như cũ?',color:'peach',number:'20%',symbol:'↗',meta:'30 phút · 2 bài vận dụng'},
{id:'exam',kind:'exam',tag:'LUYỆN THI',title:'Một bước gần hơn đến lớp 6',description:'Thử sức với số học, phần trăm và hình học qua 5 câu hỏi.',color:'mint',number:'5→6',symbol:'✦',meta:'15 phút · Thang điểm 10'}];
function cards(filter='all'){return courses.filter(c=>filter==='all'||c.kind===filter).map(c=>{const url=c.id==='exam'?'exam':'lesson-'+c.id;return '<article class="card"><a class="card-art art-'+c.color+'" href="'+pageHref(url)+'" aria-label="Mở '+c.title+'"><span class="number tile">'+c.number+'</span><span class="number number-symbol">'+esc(c.symbol)+'</span><span class="mini-label">'+(c.id==='exam'?'ĐỀ TỰ BIÊN SOẠN':'TOÁN LỚP 5')+'</span></a><div class="card-body"><div class="tag-row"><span class="tag '+(c.kind==='advanced'?'warm':'')+'">'+c.tag+'</span><span>'+(data.completed.includes(c.id)?'✓ Đã học':'Học liệu mẫu')+'</span></div><h3><a href="'+pageHref(url)+'">'+c.title+'</a></h3><p>'+c.description+'</p><div class="card-bottom"><span>'+c.meta+'</span><a class="round" href="'+pageHref(url)+'" aria-label="Học '+c.title+'">↗</a></div></div></article>';}).join('');}
const activities=[
    ['courses','Khám phá bài học','Hiểu số thập phân, phân số và hơn thế.','<path d="M12 6c-3-2-6-3-10-1v14c4-2 7-1 10 1 3-2 6-3 10-1V5c-4-2-7-1-10 1Zm0 0v14"/>'],
    ['exam','Góc luyện thi','Thử sức với đề luyện 15 phút.','<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>'],
    ['game','Chơi cùng toán','Xếp số và mở khóa thử thách mới.','<rect x="2" y="6" width="20" height="12" rx="5"/><path d="M6 12h5m-2.5-2.5v5m6.5-2.5h.01m3 0h.01"/>']
];
const learningSteps = [
    ['Khởi động', 'Làm một bài ngắn để tự xem mình đã nắm vững phần nào.'],
    ['Học theo chủ đề', 'Đọc ví dụ minh họa và thử giải lại theo cách của em.'],
    ['Luyện tập', 'Làm bài từ cơ bản đến vận dụng, xem lại những câu còn nhầm.'],
    ['Tự kiểm tra', 'Thử sức với đề bấm giờ và chọn phần cần ôn tiếp.']
];
function home(){
    return `<div class="wrap">
      <section class="hero home-anchor" id="home" aria-labelledby="home-heading" tabindex="-1">
        <div><span class="eyebrow pill"><span class="dot"></span>TOÁN LỚP 5 · KẾT NỐI TRI THỨC</span>
          <h1 id="home-heading">Học Toán lớp 5,<br><em>tự tin vào lớp 6.</em></h1>
          <p>Học chắc kiến thức, vui luyện tư duy và tự tin bước vào lớp 6.</p>
          <div class="actions">
            <a class="btn dark" href="${pageHref('courses')}">Khám phá bài học <span aria-hidden="true">→</span></a>
            <a class="btn outline" href="${pageHref('exam')}">Thử sức 15 phút <span aria-hidden="true">→</span></a>
          </div>
        </div>
        <div class="art">${illustration}</div>
      </section>
      <section class="section home-anchor" id="quy-trinh-hoc" aria-labelledby="process-heading" tabindex="-1">
        <div class="section-head"><div><span class="eyebrow">Quy trình học</span><h2 id="process-heading">Bốn bước học Toán mỗi ngày</h2><p>Gợi ý cách tự học với các bài mẫu của 5BMath.</p></div></div>
        <ol class="learning-steps">
          ${learningSteps.map(([title, description], index) => `<li class="panel"><span class="step-number" aria-hidden="true">0${index + 1}</span><h3>${title}</h3><p>${description}</p></li>`).join('')}
        </ol>
      </section>
      <section class="section home-anchor" id="chuong-trinh-hoc" aria-labelledby="program-heading" tabindex="-1">
        <div class="section-head">
          <div><span class="eyebrow">Chương trình học</span><h2 id="program-heading">Từ Toán lớp 5 đến luyện thi vào 6</h2><p>Khám phá bài nền tảng, chuyên đề nâng cao và đề luyện mẫu.</p></div>
          <a class="text-link" href="${pageHref('courses')}">Xem tất cả bài học ↗</a>
        </div>
        <div class="grid">${cards()}</div>
      </section>
      <section class="section home-anchor" id="tai-nguyen" aria-labelledby="resources-heading" tabindex="-1">
        <div class="section-head">
          <div><span class="eyebrow">Tài nguyên</span><h2 id="resources-heading">Góc học liệu và trò chơi</h2><p>Đọc bài mẫu, tải phiếu phần trăm hoặc luyện xếp số thập phân cùng Sóc.</p></div>
          <button class="text-link" type="button" data-download>Tải phiếu bài tập ↗</button>
        </div>
        <div class="activity-grid">${activities.map(([url,title,desc,icon])=>`<a class="activity" href="${pageHref(url)}">
          <span class="activity-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">${icon}</svg></span>
          <span class="activity-arrow" aria-hidden="true">→</span><span class="activity-copy"><strong>${title}</strong><span>${desc}</span></span>
        </a>`).join('')}</div>
      </section>
      <section class="banner section home-anchor" id="thi-thu" aria-labelledby="exam-heading" tabindex="-1">
        <div><span class="eyebrow">Thi Thử</span><h2 id="exam-heading">Thử sức với đề Toán vào lớp 6</h2><p>Đề mẫu tự biên soạn gồm 5 câu về số học, phần trăm và hình học. Xem điểm và lời giải sau khi nộp.</p><a class="btn orange small" href="${pageHref('exam')}">Bắt đầu thi thử →</a></div>
        <div class="steps">
          <div class="step"><i>5</i>Câu hỏi</div>
          <div class="step"><i>15</i>Phút</div>
          <div class="step"><i>10</i>Điểm tối đa</div>
        </div>
      </section>
      <section class="section home-anchor" id="tin-tuc" aria-labelledby="news-heading" tabindex="-1">
        <div class="section-head"><div><span class="eyebrow">Tin Tức</span><h2 id="news-heading">Có gì mới ở Vườn Toán?</h2></div></div>
        <article class="panel home-note">
          <span class="tag">Bài viết mẫu</span>
          <h3>Một mẹo nhỏ để so sánh số thập phân</h3>
          <p>So sánh phần nguyên trước. Nếu bằng nhau, nhìn từng chữ số sau dấu phẩy từ trái sang phải. Thử áp dụng với 1,08 và 1,8 nhé!</p>
          <a class="text-link" href="${pageHref('lesson-decimal')}">Đọc bài học ↗</a>
        </article>
      </section>
      <section class="section panel home-note home-anchor" id="tuyen-sinh" aria-labelledby="enrollment-heading" tabindex="-1">
        <span class="eyebrow">Tuyển sinh</span>
        <h2 id="enrollment-heading">Tìm hiểu lộ trình học cho con</h2>
        <p>Lịch khai giảng và thông tin đăng ký đang được cập nhật. Trong thời gian này, phụ huynh có thể xem chương trình mẫu hoặc hỏi thêm qua Zalo.</p>
        <a class="btn outline small" href="#chuong-trinh-hoc">Xem chương trình mẫu ↑</a>
      </section>
      <section class="section panel home-note home-anchor" id="tuyen-dung" aria-labelledby="careers-heading" tabindex="-1">
        <span class="eyebrow">Tuyển dụng</span>
        <h2 id="careers-heading">Đồng hành cùng 5BMath</h2>
        <p>Thông tin vị trí, tiêu chí và cách ứng tuyển sẽ được đăng tại đây khi có đợt tuyển dụng.</p>
      </section>
    </div>`;
}
function coursePage(){return '<div class="wrap"><div class="page-head"><span class="eyebrow"><span class="dot"></span>HỌC MỖI NGÀY, LỚN MỖI NGÀY</span><h1 class="title">Khu vườn kiến thức</h1><p>Bắt đầu từ nền tảng, khám phá chuyên đề nâng cao và thử sức với những bài toán thú vị.</p></div><div class="filters" role="group" aria-label="Lọc bài học"><button class="filter active" data-filter="all">Tất cả bài học</button><button class="filter" data-filter="foundation">Nền tảng lớp 5</button><button class="filter" data-filter="advanced">Chuyên đề nâng cao</button><button class="filter" data-filter="exam">Luyện thi vào 6</button></div><div class="grid mb" id="course-list">'+cards()+'</div><div class="notice mb">Bộ học liệu mẫu tự biên soạn để duyệt trải nghiệm. Nội dung sẽ được đối chiếu đầy đủ với sách Kết nối tri thức trước khi mở khóa học chính thức.</div></div>';}
function lessonPage(id){const percent=id==='percent';return '<div class="wrap"><div class="page-head"><div class="crumb"><a href="'+pageHref('courses')+'">Bài học</a> / '+(percent?'Chuyên đề nâng cao':'Nền tảng lớp 5')+'</div><span class="tag '+(percent?'warm':'')+'">'+(percent?'NÂNG CAO':'NỀN TẢNG')+'</span><h1 class="title">'+(percent?'Hai lần thay đổi phần trăm':'So sánh số thập phân')+'</h1><p>'+(percent?'Đừng để hai con số giống nhau đánh lừa em!':'Cùng Thỏ và Sóc tìm hiểu bí quyết so sánh thật chính xác.')+'</p></div><div class="split"><article class="panel lesson">'+(percent?
'<span class="eyebrow">CÂU HỎI KHỞI ĐỘNG</span><h2>Tăng 20% rồi giảm 20%,<br>giá có quay về như cũ?</h2><p>Một chiếc ba lô giá <b>200.000 đồng</b>. Cửa hàng tăng giá 20%, sau đó giảm 20% trên giá đã tăng.</p><div class="visual visual-prices"><b>200.000đ</b><span>→ +20% →</span><b>240.000đ</b><span>→ −20% →</span><b>192.000đ</b></div><h3>Cùng giải từng bước</h3><ol><li>Giá sau tăng: 200.000 × 120 : 100 = <b>240.000 đồng</b>.</li><li>Số tiền giảm: 240.000 × 20 : 100 = <b>48.000 đồng</b>.</li><li>Giá cuối: 240.000 − 48.000 = <b>192.000 đồng</b>.</li></ol><div class="example"><b>Điều quan trọng nhất</b><p>Hai lần “20%” được tính trên hai giá trị khác nhau. Giá cuối thấp hơn ban đầu 8.000 đồng, tương ứng 4% giá ban đầu.</p></div><h3>Đến lượt em suy nghĩ</h3><p>Một món đồ giá 100.000 đồng, giảm 20%. Muốn trở về giá cũ, cần tăng bao nhiêu phần trăm trên giá đã giảm?</p><details class="hint"><summary>Xem gợi ý và lời giải</summary><p>Giá sau giảm: 80.000 đồng. Cần tăng: 20.000 đồng. Tỉ lệ tăng: 20.000 : 80.000 × 100 = <b>25%</b>.</p></details>':
'<span class="eyebrow">CÂU HỎI KHỞI ĐỘNG</span><h2>Bạn nào nhảy xa hơn?</h2><p>Thỏ nhảy được <b>2,45 m</b>. Sóc nhảy được <b>2,5 m</b>. Em hãy đoán xem bạn nào nhảy xa hơn nhé!</p><div class="visual"><div class="jump"><span>🐇</span><b>Thỏ · 2,45 m</b></div><div class="math">&lt;</div><div class="jump"><span>🐿️</span><b>Sóc · 2,50 m</b></div></div><div class="example"><b>Sóc nhảy xa hơn!</b><p>Viết 2,5 = 2,50. Hai số có cùng phần nguyên là 2. Ở hàng phần mười, 5 lớn hơn 4 nên <b>2,50 &gt; 2,45</b>.</p></div><h3>Ba bước em cần nhớ</h3><ol><li>So sánh phần nguyên trước.</li><li>Nếu phần nguyên bằng nhau, so sánh lần lượt các hàng phần mười, phần trăm, phần nghìn… đến hàng đầu tiên khác nhau.</li><li>Có thể thêm chữ số 0 vào bên phải phần thập phân mà không đổi giá trị số.</li></ol><div class="math">4,8 = 4,80 &gt; 4,75</div><div class="hint"><b>Lỗi dễ mắc:</b> Không so sánh 8 và 75 rồi kết luận 4,8 bé hơn 4,75. Hãy so sánh các chữ số ở <b>cùng một hàng</b>.</div>')+
'<h3>Luyện tập ngay</h3><p>'+(percent?'Thử đề tổng hợp có câu vận dụng phần trăm.':'Làm 4 câu ngắn để chắc chắn em đã hiểu bài.')+'</p><a class="btn dark" href="'+pageHref(percent?'exam':'practice')+'">'+(percent?'Thử sức với đề mẫu':'Bắt đầu luyện tập')+' →</a></article><aside class="panel aside"><span class="aside-title">HÀNH TRÌNH BÀI HỌC</span><h3>'+(percent?'30':'20')+' phút khám phá</h3><div class="progress"><span style="width:'+(data.completed.includes(id)?100:30)+'%"></span></div><ul class="check-list"><li><b>01</b> · Khởi động bằng tình huống</li><li><b>02</b> · Hiểu cách giải</li><li><b>03</b> · Luyện tập và vận dụng</li></ul><button class="btn outline" data-video="'+id+'">▷ Kịch bản video mẫu</button><button class="btn dark" data-complete="'+id+'">'+(data.completed.includes(id)?'✓ Đã học xong':'Đánh dấu đã học')+'</button><p class="modal-note">Video chưa được quay. Em có thể đọc bài học đầy đủ trên trang.</p></aside></div></div>';}

const examQuestions=[
{text:'Điền dấu: 7,09 … 7,9',options:['<','=','>'],answer:'<',points:1,explanation:'7,9 = 7,90. So sánh hàng phần mười: 0 < 9.'},
{text:'Tính: 3/4 + 1/8 = ?',answer:0.875,points:1,explanation:'3/4 + 1/8 = 6/8 + 1/8 = 7/8.'},
{text:'Tìm 15% của 240.',answer:36,points:2,explanation:'240 × 15 : 100 = 36.'},
{text:'Hình chữ nhật có chu vi 54 cm, chiều dài gấp đôi chiều rộng. Diện tích bằng bao nhiêu cm²?',answer:162,points:3,explanation:'Nửa chu vi: 27 cm. Rộng: 27 : 3 = 9 cm. Dài: 18 cm. Diện tích: 18 × 9 = 162 cm².'},
{text:'Món đồ giá 250.000 đồng, tăng 10%, rồi giảm 10% trên giá đã tăng. Giá cuối bằng bao nhiêu đồng? (Nhập số không có dấu phân cách hàng nghìn.)',answer:247500,points:3,explanation:'Sau tăng: 250.000 × 110 : 100 = 275.000 đồng. Sau giảm: 275.000 × 90 : 100 = 247.500 đồng.'}
];
const practiceQuestions=[
{text:'Điền dấu: 6,07 … 6,7',options:['<','=','>'],answer:'<',points:1,explanation:'6,7 = 6,70. Vì 07 < 70 nên 6,07 < 6,7.'},
{text:'Điền dấu: 3,400 … 3,4',options:['<','=','>'],answer:'=',points:1,explanation:'Các chữ số 0 tận cùng phần thập phân không làm đổi giá trị.'},
{text:'Số nào lớn nhất trong ba số 5,09; 5,9; 5,19?',options:['5,09','5,9','5,19'],answer:'5,9',points:1,explanation:'Viết 5,9 = 5,90. So sánh: 5,09 < 5,19 < 5,90.'},
{text:'Viết một số thập phân nằm giữa 2,35 và 2,36.',answer:'interval',points:1,explanation:'Ví dụ 2,355, vì 2,350 < 2,355 < 2,360. Mọi số trong khoảng đều được chấp nhận.'}];
function quizPage(practice=false){submitted=false;remaining=900;const qs=practice?practiceQuestions:examQuestions;
return '<div class="wrap"><div class="page-head"><span class="eyebrow"><span class="dot"></span>'+(practice?'HIỂU BÀI, TỰ TIN LUYỆN TẬP':'MỘT THỬ THÁCH NHỎ CHO EM')+'</span><h1 class="title">'+(practice?'Luyện tập: Số thập phân':'Trạm thử sức vào lớp 6')+'</h1><p>'+(practice?'Không giới hạn thời gian. Em hãy đọc kỹ rồi trả lời nhé.':'5 câu hỏi · 15 phút · 10 điểm. Đề tự biên soạn, chưa mô phỏng riêng trường nào.')+'</p></div><div class="split"><section class="panel"><div class="quiz-top"><h2>'+(practice?'4 câu để hiểu thật chắc':'Bài kiểm tra mẫu số 01')+'</h2>'+(practice?'':'<div class="timer" id="timer" aria-label="Thời gian còn lại">15:00</div>')+'</div><div class="notice">'+(data.name?'Tiến độ được lưu trong trình duyệt của em.':'Em có thể xem đề. Khi nộp bài, hãy đặt tên để lưu kết quả minh họa.')+(practice?'':' Bản demo chấm đáp án cuối; chưa chấm từng bước tự luận.')+'</div><noscript><p class="notice">Bật JavaScript để làm bài và xem kết quả.</p></noscript><form id="quiz-form" method="post">'+qs.map((q,i)=>'<div class="question"><h3><b>Câu '+(i+1)+'.</b> '+esc(q.text)+' <small>('+q.points+' điểm)</small></h3>'+(q.options?'<div class="options">'+q.options.map(o=>'<label class="option"><input type="radio" name="q'+i+'" value="'+esc(o)+'">'+esc(o)+'</label>').join('')+'</div>':'<label for="q'+i+'">Đáp án của em</label><br><input id="q'+i+'" name="q'+i+'" type="text" maxlength="70" autocomplete="off" placeholder="'+(i===1&&!practice?'Ví dụ: 7/8 hoặc 0,875':'Nhập đáp án')+'">')+'<div id="feedback-'+i+'"></div></div>').join('')+'<div id="quiz-result" aria-live="polite"></div><div class="quiz-actions"><button class="btn dark" type="submit" id="submit-quiz" disabled>Nộp bài & xem kết quả →</button><button class="btn outline" type="button" id="retry" hidden>Làm lại</button></div></form></section><aside class="panel aside"><span class="aside-title">MẸO NHỎ CHO EM</span><h3>Bình tĩnh. Em làm được!</h3><ul class="check-list"><li>Đọc đề ít nhất hai lần.</li><li>Tính nháp trước khi nhập đáp án.</li><li>Kiểm tra lại đơn vị.</li><li>Dùng dấu phẩy hoặc dấu chấm cho phần thập phân.</li></ul><p class="modal-note">Bài thực hành mẫu, không phải đề thi chính thức. Không dùng một bài ngắn để kết luận năng lực tổng thể.</p></aside></div></div>';}
function numberValue(value){const text=String(value).trim().replace(/\s/g,'').replace(',','.');if(/^[-+]?\d+(?:\.\d+)?\/[-+]?\d+(?:\.\d+)?$/.test(text)){const [a,b]=text.split('/').map(Number);return b===0?NaN:a/b;}if(!/^[-+]?(?:\d+(?:\.\d*)?|\.\d+)$/.test(text))return NaN;return Number(text);}
async function submitQuiz(practice,force=false){if(submitted||!$('#quiz-form'))return;const form=$('#quiz-form'),qs=practice?practiceQuestions:examQuestions,values=new FormData(form);const missing=qs.filter((q,i)=>!String(values.get('q'+i)||'').trim()).length;
if(missing&&!force){showModal('<h2 class="modal-title">Em còn '+missing+' câu chưa trả lời</h2><p class="modal-copy">Em muốn làm tiếp hay nộp bài luôn? Câu để trống được tính 0 điểm.</p><button class="btn outline" id="back-quiz">Làm tiếp</button> <button class="btn dark" id="submit-anyway">Nộp bài</button>');$('#back-quiz').onclick=()=>modal.close();$('#submit-anyway').onclick=()=>{modal.close();account(()=>submitQuiz(practice,true));};return;}
if(!data.name&&!force){account(()=>submitQuiz(practice,true));return;}
submitted=true;let remote=null;if(serverGrading){try{const response=await fetch('/api/grade',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind:practice?'practice':'exam',answers:qs.map((q,i)=>String(values.get('q'+i)||''))}),signal:AbortSignal.timeout(10000)});if(!response.ok)throw Error('Grading failed');remote=await response.json();if(!Array.isArray(remote.results)||remote.results.length!==qs.length)throw Error('Invalid results');}catch(error){submitted=false;toast('Chưa kết nối được máy chủ chấm bài. Em hãy thử nộp lại.');return;}}if(!form.isConnected)return;clearInterval(clock);let score=0;const total=qs.reduce((s,q)=>s+q.points,0);
qs.forEach((q,i)=>{const raw=values.get('q'+i)||'',n=numberValue(raw);const right=remote?remote.results[i].correct:q.answer==='interval'?Number.isFinite(n)&&n>2.35&&n<2.36:typeof q.answer==='number'?Number.isFinite(n)&&Math.abs(n-q.answer)<1e-9:String(raw)===q.answer;if(right)score+=q.points;$('#feedback-'+i).innerHTML='<div class="feedback '+(right?'':'wrong')+'"><b>'+(right?'✓ Chính xác!':'Chưa đúng, cùng xem lại nhé.')+'</b> '+esc(remote?remote.results[i].explanation:q.explanation)+'</div>';});
form.querySelectorAll('input').forEach(el=>el.disabled=true);const out=remote?remote.score:Math.round(score/total*100)/10;
$('#quiz-result').innerHTML='<div class="score"><span class="eyebrow">EM ĐÃ HOÀN THÀNH</span><strong>'+out+'<small> / 10</small></strong><p>'+(out>=8?'Tuyệt lắm! Hãy đọc lời giải để hiểu thật sâu.':'Mỗi lần luyện tập là một lần tiến bộ. Cùng xem lại lời giải nhé!')+'</p>'+(!data.name?'<small>Chưa lưu kết quả vì chưa có tên học sinh.</small>':'')+'</div>';
$('#submit-quiz').hidden=true;$('#retry').hidden=false;if(data.name){data.attempts.push({type:practice?'Luyện số thập phân':'Đề thử sức 01',score:out,date:new Date().toISOString()});save();}$('#quiz-result').scrollIntoView({behavior:'smooth',block:'center'});}
const rounds=[['1,08','1,8','1,18','1,008'],['2,45','2,05','2,5','2,405'],['0,9','0,099','0,19','0,909']];
function gamePage(){gameStep=0;return '<div class="wrap"><div class="page-head"><span class="eyebrow"><span class="dot"></span>CHƠI MỘT CHÚT, HIỂU THÊM NHIỀU</span><h1 class="title">Giúp Sóc bắc cầu</h1><p>Chọn các phiến đá theo thứ tự <b>từ bé đến lớn</b> để giúp Sóc qua suối. Được thử lại, không giới hạn thời gian!</p></div><section class="panel mb"><div class="quiz-top"><span class="tag">SỐ THẬP PHÂN · VÒNG '+(gameRound+1)+'</span><b id="game-counter">0 / 4 phiến đá</b></div><div class="game-board"><div class="game-sky"><span>🐿️</span><span class="game-sun" aria-hidden="true">☀</span><span>🌳</span></div><div class="stones">'+rounds[gameRound].map(n=>'<button class="stone" data-stone="'+n+'" aria-label="Chọn số '+n+'">'+n+'</button>').join('')+'</div><div class="game-status" id="game-status" role="status">Phiến đá bé nhất là số nào nhỉ?</div></div><div class="game-bottom"><span>Mẹo: So sánh lần lượt từng hàng của số thập phân.</span><button class="btn outline small" id="game-reset">Chơi lại ↻</button></div></section></div>';}
function dashboard(){if(!data.name)return '<div class="wrap"><div class="page-head"><span class="eyebrow">LỚP HỌC CỦA EM</span><h1 class="title">Một góc nhỏ để lớn lên mỗi ngày.</h1><p>Đặt tên để trải nghiệm lưu tiến độ, làm bài tập và khám phá lịch học.</p></div><section class="panel mb"><h2>🌱 Sẵn sàng bắt đầu chưa?</h2><p>Đây là lớp học minh họa. Không cần tạo mật khẩu hoặc cung cấp thông tin liên hệ.</p><button class="btn dark" data-login>Vào lớp học mẫu →</button></section></div>';
const last=data.attempts.at(-1);
return '<div class="wrap"><div class="page-head"><span class="eyebrow"><span class="dot"></span>LỚP HỌC CỦA EM</span><h1 class="title">Chào '+esc(data.name)+', hôm nay học gì nhỉ?</h1><p>Mỗi bài học là một hạt mầm. Chăm chút một chút mỗi ngày nhé.</p><div class="notice">Tài khoản minh họa · Dữ liệu chỉ lưu trên trình duyệt này · Chưa kết nối giáo viên hoặc lớp thật. <button class="text-link" id="logout">Thoát tài khoản mẫu ↗</button></div></div><div class="stats"><div class="stat"><strong>'+data.completed.length+'<small> / 2</small></strong><span>Bài học đã hoàn thành</span></div><div class="stat"><strong>'+data.attempts.length+'</strong><span>Lượt luyện tập</span></div><div class="stat"><strong>'+(last?last.score:'—')+'<small>'+(last?' / 10':'')+'</small></strong><span>Điểm lần gần nhất</span></div></div><div class="dashboard-grid mb"><div><section class="panel panel-space"><span class="eyebrow">TIẾP TỤC HÀNH TRÌNH</span><div class="task"><div><b>So sánh số thập phân</b><small>Nền tảng · 20 phút '+(data.completed.includes('decimal')?'· Đã học':'')+'</small></div><a class="btn dark small" href="'+pageHref('lesson-decimal')+'">Vào học →</a></div><div class="task"><div><b>Hai lần thay đổi phần trăm</b><small>Nâng cao · 30 phút '+(data.completed.includes('percent')?'· Đã học':'')+'</small></div><a class="btn outline small" href="'+pageHref('lesson-percent')+'">Vào học →</a></div></section><section class="panel"><span class="eyebrow">BÀI TẬP VỀ NHÀ</span><h3>Phiếu 01 · Giải mã phần trăm</h3><p class="modal-copy">Giải 2 bài trong phiếu, ghi phép tính và kết luận. Chọn ảnh hoặc PDF để thử thao tác nộp bài.</p><button class="btn outline small" data-download>Tải phiếu bài tập ↓</button><div class="upload"><label for="homework-file">Chọn bài làm (ảnh hoặc PDF, tối đa 10 MB)</label><p><input type="file" id="homework-file" accept="image/jpeg,image/png,image/webp,application/pdf"></p><button class="btn dark small" id="submit-homework">Nộp bài minh họa →</button><p class="modal-note" id="homework-status" role="status">'+(data.homework?'Đã ghi nhận tên tệp: '+esc(data.homework.name)+'. Chưa gửi tới giáo viên.':'Tệp không được tải lên máy chủ. Demo chỉ ghi nhận tên tệp trong trình duyệt.')+'</p></div></section></div><div><section class="panel panel-space"><span class="eyebrow">LỚP TRỰC TIẾP</span><h3>Cùng giải bài với thầy cô</h3><p class="modal-copy">Chuyên đề: Hai lần thay đổi phần trăm</p><div class="notice">45 phút · Zoom / Google Meet<br>Lịch học và liên kết chưa được thiết lập.</div><button class="btn outline small" id="live-class">Xem buổi học mẫu ↗</button></section><section class="panel"><span class="eyebrow">NHẬT KÝ LUYỆN TẬP</span>'+(data.attempts.length?data.attempts.slice(-5).reverse().map(a=>'<div class="task"><div><b>'+esc(a.type)+'</b><small>'+new Date(a.date).toLocaleDateString('vi-VN')+'</small></div><b>'+a.score+'/10</b></div>').join(''):'<p class="muted">Chưa có kết quả. Thử làm một bài ngắn nhé!</p>')+'<a class="text-link" href="'+pageHref('exam')+'">Làm bài thử sức →</a></section></div></div></div>';}
const worksheet='5BMath — PHIẾU BÀI TẬP MẪU 01\nChuyên đề: Hai lần thay đổi phần trăm\n\nHọ và tên: ..................................\n\nBài 1. Một cuốn sách giá 150.000 đồng, giảm 20%, sau đó giảm tiếp 10% trên giá còn lại. Tính giá cuối và tỉ lệ giảm so với ban đầu.\n\nBài 2. Một món đồ giá 100.000 đồng, giảm 20%. Muốn trở về giá ban đầu thì phải tăng bao nhiêu phần trăm trên giá sau giảm?\n\nYêu cầu: Viết phép tính, đơn vị và câu trả lời.\n\nĐÁP ÁN ĐỐI CHIẾU\nBài 1: 120.000 đồng → 108.000 đồng; giảm 28%.\nBài 2: 80.000 đồng; tăng 20.000 đồng, tương ứng 25%.\n\nHọc liệu mẫu tự biên soạn, chưa phải tài liệu của trường tuyển sinh cụ thể.\n';
function download(){account(()=>{const blob=new Blob(['\ufeff'+worksheet],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='Mam-Toan-Phieu-01.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Đã tạo phiếu bài tập để tải về.');});}
function bind(route){
document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-filter]').forEach(x=>x.classList.remove('active'));b.classList.add('active');$('#course-list').innerHTML=cards(b.dataset.filter);});
document.querySelectorAll('[data-login]').forEach(b=>b.onclick=()=>account(()=>render()));
document.querySelectorAll('[data-complete]').forEach(b=>b.onclick=()=>account(()=>{const id=b.dataset.complete;if(!data.completed.includes(id)){data.completed.push(id);save();}b.textContent='✓ Đã học xong';$('.progress span').style.width='100%';toast('Đã ghi nhận bài học. Hẹn em ở thử thách tiếp theo!');}));
document.querySelectorAll('[data-video]').forEach(b=>b.onclick=()=>showModal('<span class="eyebrow">KỊCH BẢN VIDEO · CHƯA CÓ BẢN QUAY</span><h2 class="modal-title">'+(b.dataset.video==='decimal'?'So sánh số thập phân':'Hai lần thay đổi phần trăm')+'</h2><ol class="schedule"><li><b>0:00–0:40</b> — Câu hỏi khởi động từ bài học.</li><li><b>0:40–2:10</b> — Giải thích từng bước bằng hình minh họa.</li><li><b>2:10–3:20</b> — Ví dụ và lỗi thường gặp.</li><li><b>3:20–4:30</b> — Dừng để học sinh tự trả lời.</li><li><b>4:30–5:00</b> — Chốt kiến thức, chuyển sang luyện tập.</li></ol><p class="modal-copy">Bản demo đã có bài đọc. Video sẽ được bổ sung sau khi duyệt nội dung.</p>'));
if($('#quiz-form')){const practice=route==='practice';$('#submit-quiz').disabled=false;$('#quiz-form').onsubmit=e=>{e.preventDefault();submitQuiz(practice);};$('#retry').onclick=()=>render();if(!practice)clock=setInterval(()=>{if(!$('#timer')){clearInterval(clock);return;}remaining--;$('#timer').textContent=String(Math.floor(remaining/60)).padStart(2,'0')+':'+String(remaining%60).padStart(2,'0');if(remaining<=0)submitQuiz(false,true);},1000);}
if(route==='game'){document.querySelectorAll('[data-stone]').forEach(b=>b.onclick=()=>{const sorted=[...rounds[gameRound]].sort((a,b)=>numberValue(a)-numberValue(b));if(b.dataset.stone===sorted[gameStep]){b.classList.add('passed');b.disabled=true;gameStep++;$('#game-counter').textContent=gameStep+' / 4 phiến đá';$('#game-status').textContent=gameStep===4?'✦ Sóc đã qua suối! Em sắp xếp rất chính xác.':'Đúng rồi! Tiếp theo là số nào?';if(gameStep===4){$('#game-reset').textContent='Vòng tiếp theo →';toast('Em vừa hoàn thành một cây cầu!');}}else $('#game-status').textContent='Thử lại nhé. Hãy tìm số bé nhất trong các phiến đá còn lại.';});$('#game-reset').onclick=()=>{if(gameStep===4)gameRound=(gameRound+1)%rounds.length;render();};}
if($('#logout'))$('#logout').onclick=()=>{data.name='';save();updateAccount();render();};
document.querySelectorAll('[data-download]').forEach(b=>b.onclick=download);
if($('#live-class'))$('#live-class').onclick=()=>showModal('<span class="eyebrow">BUỔI HỌC TRỰC TIẾP MẪU</span><h2 class="modal-title">45 phút khám phá phần trăm</h2><ol class="schedule"><li><b>5 phút:</b> Khởi động: tăng rồi giảm cùng tỉ lệ.</li><li><b>10 phút:</b> Giáo viên giải thích bằng sơ đồ giá tiền.</li><li><b>15 phút:</b> Học sinh tự làm và trình bày.</li><li><b>10 phút:</b> Chữa lỗi chọn sai giá trị gốc.</li><li><b>5 phút:</b> Câu hỏi cuối buổi, giao bài về nhà.</li></ol><div class="notice">Chưa có phòng Zoom/Meet thật. Liên kết sẽ chỉ hiển thị cho học sinh được cấp quyền khi triển khai hệ thống chính thức.</div>');
if($('#submit-homework'))$('#submit-homework').onclick=()=>{const file=$('#homework-file').files[0];if(!file){toast('Em hãy chọn ảnh hoặc PDF trước nhé.');return;}if(!['image/jpeg','image/png','image/webp','application/pdf'].includes(file.type)){toast('Vui lòng chọn ảnh JPG, PNG, WebP hoặc PDF.');return;}if(file.size>10*1024*1024){toast('Tệp lớn hơn 10 MB. Em hãy chọn tệp nhỏ hơn.');return;}data.homework={name:file.name,date:new Date().toISOString()};save();$('#homework-status').textContent='Đã ghi nhận tên tệp: '+file.name+'. Chưa tải lên máy chủ hoặc gửi tới giáo viên.';toast('Đã ghi nhận bài nộp minh họa.');};
}
const pages = {
    home: {
        path: './',
        title: 'Toán lớp 5 và luyện thi vào lớp 6',
        description: 'Học Toán lớp 5 cùng 5BMath qua bài đọc, ví dụ có lời giải, trò chơi số thập phân và đề thi thử vào lớp 6.',
        render: home
    },
    courses: {
        path: 'bai-hoc-toan-lop-5/',
        title: 'Bài học Toán lớp 5',
        description: 'Khám phá bài học mẫu về số thập phân và phần trăm, kèm ví dụ từng bước và bài tập vận dụng.',
        render: coursePage
    },
    'lesson-decimal': {
        path: 'so-sanh-so-thap-phan/',
        title: 'Cách so sánh số thập phân lớp 5',
        description: 'Học ba bước so sánh số thập phân, hiểu vì sao 2,5 bằng 2,50 và thực hành với bốn bài tập ngắn.',
        render: () => lessonPage('decimal')
    },
    'lesson-percent': {
        path: 'hai-lan-thay-doi-phan-tram/',
        title: 'Hai lần thay đổi phần trăm',
        description: 'Tìm hiểu vì sao tăng 20% rồi giảm 20% cho kết quả khác giá ban đầu, với ví dụ và bài vận dụng có lời giải.',
        render: () => lessonPage('percent')
    },
    practice: {
        path: 'luyen-tap-so-thap-phan/',
        title: 'Bài tập so sánh số thập phân lớp 5',
        description: 'Luyện bốn câu so sánh và tìm số thập phân. Xem điểm và lời giải từng câu sau khi nộp bài.',
        render: () => quizPage(true)
    },
    exam: {
        path: 'de-thi-thu-toan-vao-lop-6/',
        title: 'Đề thi thử Toán vào lớp 6 trong 15 phút',
        description: 'Làm đề tự biên soạn gồm năm câu số học, phân số, phần trăm và hình học. Xem điểm và lời giải sau khi nộp.',
        render: quizPage
    },
    game: {
        path: 'tro-choi-xep-so-thap-phan/',
        title: 'Trò chơi xếp số thập phân',
        description: 'Giúp Sóc qua suối bằng cách xếp các số thập phân từ bé đến lớn qua ba vòng chơi.',
        render: gamePage
    },
    dashboard: {
        path: 'goc-hoc-tap/',
        title: 'Góc học tập',
        description: 'Góc học tập minh họa để xem tiến độ và thử nộp bài trên thiết bị này.',
        noindex: true,
        render: dashboard
    }
};

function pageHref(route) {
    return offline ? '#' + route : pages[route].path;
}

let renderedRoute;

function render(route = renderedRoute) {
    clearInterval(clock);
    $('#app').innerHTML = pages[route].render();
    document.title = pages[route].title + ' | 5BMath';
    if (route === renderedRoute) window.scrollTo({ top: 0, behavior: 'instant' });
    renderedRoute = route;
    updateAccount();
    bind(route);
}

function navigate(focusAnchor = false) {
    const fragment = location.hash.slice(1) || 'home';
    const entry = document.documentElement.dataset.page || 'home';
    const legacyRoute = Object.hasOwn(pages, fragment) ? fragment : 'home';
    if (!offline && entry === 'home' && legacyRoute !== 'home') {
        const url = new URL(pageHref(legacyRoute), document.baseURI);
        url.search = location.search;
        location.replace(url);
        return;
    }
    const route = offline ? legacyRoute : entry;
    if (route !== renderedRoute) render(route);
    setMenu(false);
    const section = route === 'home' && document.getElementById(fragment);
    const anchor = section && section.classList.contains('home-anchor') ? section : null;
    document.querySelectorAll('#primary-nav a').forEach(link => {
        if (anchor && link.hash === '#' + anchor.id) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
    });
    if (anchor && focusAnchor) anchor.focus({ preventScroll: true });
    if (anchor && anchor.id !== 'home') anchor.scrollIntoView({ block: 'start' });
    else window.scrollTo({ top: 0, behavior: route === 'home' ? 'auto' : 'instant' });
}

function start() {
    loadProgress();
    modal = $('#modal');
    $('#close-modal').onclick = () => modal.close();
    modal.addEventListener('click', event => {
        if (event.target !== modal) return;
        const rect = modal.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right ||
            event.clientY < rect.top || event.clientY > rect.bottom) modal.close();
    });
    const primaryNav = $('#primary-nav');
    const menuButton = $('#menu');
    menuButton.onclick = () => setMenu(!primaryNav.classList.contains('open'));
    $('#account').onclick = () => {
        setMenu(false);
        account();
    };
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && primaryNav.classList.contains('open')) {
            setMenu(false);
            if (menuButton.offsetWidth) menuButton.focus();
        }
    });
    document.addEventListener('click', event => {
        if (!event.target.closest('.site-header')) setMenu(false);
    });
    $('.site-header').addEventListener('click', event => {
        const link = event.target.closest('a');
        if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
        setMenu(false);
        if (link.href === location.href || link.href === location.href + '#home') {
            event.preventDefault();
            navigate(true);
        }
    });
    window.addEventListener('hashchange', () => navigate(true));
    window.addEventListener('pageshow', event => {
        if (!event.persisted) return;
        loadProgress();
        updateAccount();
    });
    bindContact();
    navigate();
}

function bindContact() {
    const contactPanel = $('#contact-panel');
    const chatButton = $('#chat-toggle');
    const messengerButton = $('#messenger-toggle');
    const closeContactButton = $('#contact-close');
    let contactTrigger = null;

    function closeContact(restoreFocus = true) {
        if (!contactTrigger) return;
        contactPanel.hidden = true;
        contactTrigger.setAttribute('aria-expanded', 'false');
        if (restoreFocus) contactTrigger.focus();
        contactTrigger = null;
    }

    function toggleContact(button) {
        if (contactTrigger === button) {
            closeContact();
            return;
        }
        closeContact(false);
        contactTrigger = button;
        const chat = button === chatButton;
        $('#contact-title').textContent = chat ? 'Chat với 5BMath' : 'Messenger 5BMath';
        $('#web-chat').hidden = !chat;
        $('#messenger-info').hidden = chat;
        contactPanel.hidden = false;
        button.setAttribute('aria-expanded', 'true');
        closeContactButton.focus({ preventScroll: true });
    }

    chatButton.onclick = () => toggleContact(chatButton);
    messengerButton.onclick = () => toggleContact(messengerButton);
    closeContactButton.onclick = () => closeContact();
    document.addEventListener('keydown', event => {
        if (event.key === 'Escape' && event.target.closest('.contact-dock')) closeContact();
    });
    document.addEventListener('click', event => {
        if (!event.target.closest('.contact-dock')) closeContact(false);
    });

    const chatAnswers = {
        learning: ['5BMath có bài mẫu về số thập phân và phần trăm, cùng các bài vận dụng chuẩn bị lên lớp 6.', '#chuong-trinh-hoc', 'Xem chương trình học'],
        exam: ['Bạn có thể làm đề mẫu 5 câu trong 15 phút. Trang sẽ hiện điểm và lời giải sau khi nộp bài.', '#thi-thu', 'Xem mục Thi Thử'],
        enrollment: ['Thông tin khai giảng đang được cập nhật. Phụ huynh có thể hỏi thêm qua nút Zalo bên dưới.', '#tuyen-sinh', 'Xem mục Tuyển sinh']
    };
    const chatLink = $('#chat-link');
    const topicButtons = [...document.querySelectorAll('[data-chat-topic]')];
    topicButtons.forEach(button => {
        button.onclick = () => {
            const [answer, href, label] = chatAnswers[button.dataset.chatTopic];
            topicButtons.forEach(topic => topic.setAttribute('aria-pressed', String(topic === button)));
            $('#chat-answer').textContent = answer;
            chatLink.href = href;
            chatLink.textContent = label + ' ↗';
            chatLink.hidden = false;
        };
    });
    chatLink.onclick = () => {
        closeContact();
        if (chatLink.href === location.href) navigate(true);
    };
}

if (browser) start();
else module.exports = { pages, esc };
