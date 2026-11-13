'use strict';
const $=s=>document.querySelector(s), KEY='mamtoan-demo-v1';
const browser = typeof document !== 'undefined';
const nicknamePolicy = browser ? NicknamePolicy : require('./nickname-policy.js');
const liveBackend = browser && typeof PlatformAPI !== 'undefined' && PlatformAPI.enabled;
let initialSession = Promise.resolve();
let learning = browser ? null : require('./learning.js');
let staff = browser ? null : require('./staff.js');
const learningRoutes = browser ? RuntimeAssets.manifest.routes.learning : learning.routes;
const staffRoutes = browser ? RuntimeAssets.manifest.routes.staff : staff.routes;
const offline = browser && location.protocol === 'file:';
const serverGrading = browser && !offline && document.documentElement.dataset.grading !== 'browser';
let data={name:'',completed:[],attempts:[],homework:null};
const publicLessonIds = {decimal:'public-decimal',percent:'public-percent'};
function applyAccount(snapshot) {
    data.name = snapshot.name ? nicknamePolicy.safe(snapshot.name) : '';
    data.completed = Object.entries(publicLessonIds).filter(([,key])=>snapshot.state?.completed?.[key]).map(([id])=>id);
    data.attempts = [];
}
function configureLearning() {
    learning?.configure({progress:data,saveProgress:save,toast,showModal,redraw:()=>render()});
}
async function ensureLearning() {
    if(!learning){await RuntimeAssets.ensureLearning();learning=LearningApp;configureLearning();}
    return learning;
}
async function ensureRoute(route) {
    await RuntimeAssets.ensureRoute(route);
    if(route==='dashboard'||route.startsWith('learn-')){learning=LearningApp;configureLearning();}
    if(route.startsWith('staff-'))staff=StaffApp;
}

function loadProgress() {
    if (liveBackend) return;
    try {
        const saved = JSON.parse(localStorage.getItem(KEY));
        if (saved && typeof saved === 'object') data = { ...data, ...saved };
    } catch (_) {}
    if (!Array.isArray(data.completed)) data.completed = [];
    if (!Array.isArray(data.attempts)) data.attempts = [];
    if (data.name) data.name = nicknamePolicy.safe(data.name);
}
const esc=t=>String(t).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let clock=null, toastClock=null, remaining=900, submitted=false, gameStep=0,gameRound=0;
function save(){if(liveBackend)return;try{localStorage.setItem(KEY,JSON.stringify(data));}catch(_){toast('Trình duyệt chưa cho phép lưu tiến độ.');}}
function toast(t){$('#toast').textContent=t;$('#toast').classList.add('show');clearTimeout(toastClock);toastClock=setTimeout(()=>$('#toast').classList.remove('show'),4000);}
let modal, passwordFieldId=0;
function passwordFields(root) {
    root.querySelectorAll('input[type="password"]').forEach(input=>{
        if(input.closest('.password-control'))return;
        if(!input.id)input.id='password-field-'+(++passwordFieldId);
        const control=document.createElement('span');
        control.className='password-control';
        input.before(control);control.append(input);
        const toggle=document.createElement('button');
        toggle.type='button';toggle.className='password-toggle';
        toggle.setAttribute('aria-controls',input.id);
        toggle.setAttribute('aria-label','Hiện mật khẩu');
        toggle.setAttribute('aria-pressed','false');toggle.title='Hiện mật khẩu';
        toggle.innerHTML='<svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12Z"/><circle cx="12" cy="12" r="3"/><path class="password-slash" d="m3 3 18 18" hidden/></svg>';
        toggle.onclick=event=>{
            event.preventDefault();
            const visible=input.type==='password';
            input.type=visible?'text':'password';
            toggle.setAttribute('aria-pressed',String(visible));
            toggle.setAttribute('aria-label',visible?'Ẩn mật khẩu':'Hiện mật khẩu');
            toggle.title=visible?'Ẩn mật khẩu':'Hiện mật khẩu';
            toggle.querySelector('.password-slash').toggleAttribute('hidden',!visible);
        };
        control.append(toggle);
    });
}
function showModal(html){$('#modal-body').innerHTML=html;passwordFields($('#modal-body'));if(!modal.open)modal.showModal();}
function updateAccount(){$('#account').innerHTML=data.name?(learning?.avatar()||'<span class="avatar" aria-hidden="true">🌱</span>')+'<span>Góc học tập ↗</span>':'Đăng nhập';}
async function account(next){if(liveBackend){if(data.name){if(next)next();else location.assign(pageHref('dashboard'));}else realAccount(next);return;}try{await ensureLearning();}catch(error){toast(error.message);return;}if(data.name){if(next)next();else location.assign(pageHref('dashboard'));return;}
if(liveBackend){realAccount(next);return;}
showModal('<div class="modal-mark" aria-hidden="true">🌱</div><span class="eyebrow">GÓC HỌC TẬP CỦA EM</span><h2 class="modal-title">Chào em, nhà thám hiểm!</h2><p class="modal-copy">Đặt biệt danh để trải nghiệm lớp học 5BMath.</p><form id="name-form"><label for="student-name">Biệt danh của em</label><input class="name-input" id="student-name" placeholder="Ví dụ: Mầm Xanh" minlength="2" maxlength="40" autocomplete="nickname" aria-describedby="nickname-help" required><p class="modal-copy" id="nickname-help">'+esc(nicknamePolicy.help)+'</p><button class="btn dark" type="submit">Bắt đầu trải nghiệm ↗</button></form><p class="modal-note">TÀI KHOẢN MINH HỌA • Không có mật khẩu. Tên và tiến độ chỉ lưu trong trình duyệt này. Chưa có đăng nhập thật hoặc phân quyền bảo vệ tài liệu.</p>');
const year = document.createElement('label');
year.className = 'account-birth-year';
year.innerHTML = '<span>Năm sinh (cố định sau đăng ký)</span><input class="name-input" id="student-birth-year" type="number" inputmode="numeric" placeholder="Ví dụ 2016" required>';
$('#name-form button').before(year);
$('#name-form').onsubmit=e=>{e.preventDefault();const input=$('#student-name'),error=nicknamePolicy.error(input.value);if(error){input.setCustomValidity(error);input.reportValidity();return;}const name=nicknamePolicy.normalize(input.value);try{learning.setBirthYear($('#student-birth-year').value);}catch(error){toast(error.message);return;}data.name=name;save();updateAccount();modal.close();if(next)next();else location.assign(pageHref('dashboard'));};$('#student-name').oninput=e=>e.target.setCustomValidity('');
}
function realAccount(next, kind='login') {
    const register = kind === 'register';
    const invite = new URLSearchParams(location.search).get('invite') || '';
    showModal(`<div class="modal-mark" aria-hidden="true">🌱</div><h2 class="modal-title">${register?'Tạo tài khoản 5BMath':'Đăng nhập 5BMath'}</h2><p>Tiến độ và bài làm được lưu trong database của máy chủ.</p><form id="auth-form"><label class="field"><span>Tên đăng nhập</span><input class="name-input" name="login" autocomplete="username" minlength="3" maxlength="100" required></label><label class="field"><span>Mật khẩu${register?' (ít nhất 6 ký tự)':''}</span><input class="name-input" name="password" type="password" autocomplete="${register?'new-password':'current-password'}" minlength="${register?6:1}" maxlength="128" required></label>${register?`<label class="field"><span>Biệt danh của học sinh</span><input class="name-input" name="name" minlength="2" maxlength="40" autocomplete="nickname" aria-describedby="nickname-help auth-error" required></label><p class="modal-copy" id="nickname-help">${esc(nicknamePolicy.help)}</p><label class="field"><span>Năm sinh (cố định sau đăng ký)</span><input class="name-input" name="birthYear" type="number" required></label><label class="field"><span>Mã giới thiệu (nếu có)</span><input class="name-input" name="inviteCode" maxlength="30" value="${esc(invite)}"></label><p class="learning-notice">Một tài khoản dành cho một học sinh. Khối học được tính từ năm sinh.</p>`:''}<p id="auth-error" role="alert"></p><button class="btn dark" type="submit">${register?'Tạo tài khoản':'Đăng nhập'}</button></form><button class="btn outline" id="auth-switch" type="button">${register?'Đã có tài khoản? Đăng nhập':'Chưa có tài khoản? Đăng ký'}</button>`);
    $('#auth-form [name=name]')?.addEventListener('input',event=>{event.target.removeAttribute('aria-invalid');$('#auth-error').textContent='';});
    $('#auth-switch').onclick=()=>realAccount(next,register?'login':'register');
    $('#auth-form').onsubmit=async event=>{
        event.preventDefault();
        const form=event.currentTarget, button=form.querySelector('button[type=submit]');
        const values=Object.fromEntries(new FormData(form));
        if(register){const error=nicknamePolicy.error(values.name);if(error){$('#auth-error').textContent=error;const input=form.elements.name;input.setAttribute('aria-invalid','true');input.focus();return;}values.name=nicknamePolicy.normalize(values.name);values.birthYear=Number(values.birthYear);}
        if(button.disabled)return;
        button.disabled=true;button.textContent=register?'Đang tạo tài khoản…':'Đang đăng nhập…';
        form.setAttribute('aria-busy','true');
        try {
            await initialSession;
            const snapshot=await PlatformAPI.authenticate(kind,values,{compact:!next});
            if(snapshot.principal==='staff') {
                modal.close();
                location.assign(pageHref(snapshot.user.role==='admin'?'staff-admin':'staff-teacher'));
                return;
            }
            applyAccount(snapshot);
            configureLearning();
            updateAccount();modal.close();
            if(next)next();else location.assign(pageHref('dashboard'));
        } catch(error) { $('#auth-error').textContent=error.message; }
        finally { if(button.isConnected){button.disabled=false;button.textContent=register?'Tạo tài khoản':'Đăng nhập';form.removeAttribute('aria-busy');} }
    };
}
function setMenu(open) {
    const primaryNav = $('#primary-nav');
    const menuButton = $('#menu');
    primaryNav.classList.toggle('open', open);
    menuButton.setAttribute('aria-expanded', String(open));
    menuButton.setAttribute('aria-label', open ? 'Đóng menu' : 'Mở menu');
}
const illustration='<div class="home-mascot" role="img" aria-label="Mầm Sách đang đọc sách trong Vườn Toán"></div>';
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
      <a class="btn outline home-zoom-link" href="dang-ky-kiem-tra-dau-vao/">Đăng ký kiểm tra đầu vào · Học Zoom</a>
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
'<h3>Luyện tập ngay</h3><p>'+(percent?'Thử đề tổng hợp có câu vận dụng phần trăm.':'Làm 4 câu ngắn để chắc chắn em đã hiểu bài.')+'</p><a class="btn dark" href="'+pageHref(percent?'exam':'practice')+'">'+(percent?'Thử sức với đề mẫu':'Bắt đầu luyện tập')+' →</a></article><aside class="panel aside"><span class="aside-title">HÀNH TRÌNH BÀI HỌC</span><h3>'+(percent?'30':'20')+' phút khám phá</h3><div class="progress"><span style="width:'+(data.completed.includes(id)?100:30)+'%"></span></div><ul class="check-list"><li><b>01</b> · Khởi động bằng tình huống</li><li><b>02</b> · Hiểu cách giải</li><li><b>03</b> · Luyện tập và vận dụng</li></ul><button class="btn outline" data-video="'+id+'">▷ Kịch bản video mẫu</button><button class="btn dark" data-complete="'+id+'"'+(!browser?' disabled aria-busy="true"':'')+'>'+(data.completed.includes(id)?'✓ Đã học xong':'Đánh dấu đã học')+'</button><p class="modal-note">Video chưa được quay. Em có thể đọc bài học đầy đủ trên trang.</p></aside></div></div>';}

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
function appendRichContent(container, blocks, assets) {
    const mathNamespace = 'http://www.w3.org/1998/Math/MathML';
    const mathTags = new Set(['math', 'mrow', 'mfrac', 'mn', 'mo', 'mi', 'msup', 'msub', 'msqrt', 'mtext']);
    for (const block of blocks) {
        if (block.type === 'text') {
            const paragraph = document.createElement('p');
            paragraph.textContent = block.text;
            container.append(paragraph);
        } else if (block.type === 'math') {
            const wrapper = document.createElement('div');
            wrapper.className = 'sample-math';
            const parsed = new DOMParser().parseFromString(block.mathml, 'application/xml');
            const root = parsed.documentElement;
            const valid = root.localName === 'math' && [...parsed.getElementsByTagName('*')].every(element =>
                element.namespaceURI === mathNamespace && mathTags.has(element.localName) &&
                [...element.attributes].every(attribute => attribute.name === 'xmlns' ||
                    (attribute.name === 'display' && ['block', 'inline'].includes(attribute.value))));
            if (valid) wrapper.append(document.importNode(root, true));
            else wrapper.textContent = block.latex;
            container.append(wrapper);
        } else if (block.type === 'image') {
            const asset = assets.find(image => image.id === block.asset_id);
            if (!asset || new URL(asset.url, location.origin).origin !== location.origin) continue;
            const picture = document.createElement('img');
            picture.src = asset.url;
            picture.alt = asset.alt || asset.alt_text || '';
            picture.width = asset.width;
            picture.height = asset.height;
            picture.loading = 'lazy';
            picture.decoding = 'async';
            container.append(picture);
        }
    }
}

const worksheet='5BMath — PHIẾU BÀI TẬP MẪU 01\nChuyên đề: Hai lần thay đổi phần trăm\n\nHọ và tên: ..................................\n\nBài 1. Một cuốn sách giá 150.000 đồng, giảm 20%, sau đó giảm tiếp 10% trên giá còn lại. Tính giá cuối và tỉ lệ giảm so với ban đầu.\n\nBài 2. Một món đồ giá 100.000 đồng, giảm 20%. Muốn trở về giá ban đầu thì phải tăng bao nhiêu phần trăm trên giá sau giảm?\n\nYêu cầu: Viết phép tính, đơn vị và câu trả lời.\n\nĐÁP ÁN ĐỐI CHIẾU\nBài 1: 120.000 đồng → 108.000 đồng; giảm 28%.\nBài 2: 80.000 đồng; tăng 20.000 đồng, tương ứng 25%.\n\nHọc liệu mẫu tự biên soạn, chưa phải tài liệu của trường tuyển sinh cụ thể.\n';
function download(){account(()=>{const blob=new Blob(['\ufeff'+worksheet],{type:'text/plain;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='Mam-Toan-Phieu-01.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Đã tạo phiếu bài tập để tải về.');});}
function bind(route){
document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-filter]').forEach(x=>x.classList.remove('active'));b.classList.add('active');$('#course-list').innerHTML=cards(b.dataset.filter);});
document.querySelectorAll('[data-login]').forEach(b=>b.onclick=()=>account(()=>render()));
document.querySelectorAll('[data-complete]').forEach(b=>b.onclick=()=>account(async()=>{
    const id=b.dataset.complete,owner=liveBackend?PlatformAPI.snapshot.account?.id:null,csrf=liveBackend?PlatformAPI.snapshot.csrf:null;
    if(b.disabled)return;b.disabled=true;
    try {
        if(liveBackend){
            const snapshot=await PlatformAPI.request('lessons/'+publicLessonIds[id]+'/complete',{}, {owner});
            if(PlatformAPI.snapshot.account?.id!==owner||PlatformAPI.snapshot.csrf!==csrf)return;
            applyAccount(snapshot);configureLearning();
            if(!data.completed.includes(id))throw new Error('Chưa xác nhận được tiến độ. Vui lòng thử lại.');
        } else if(!data.completed.includes(id)){data.completed.push(id);save();}
        if(!b.isConnected)return;
        b.textContent='✓ Đã học xong';const bar=document.querySelector('.progress span');if(bar)bar.style.width='100%';
        toast(liveBackend?'Đã lưu bài học vào tài khoản của em.':'Đã lưu tiến độ demo trong trình duyệt này.');
    } catch(error){if(error.name!=='AbortError'&&b.isConnected)toast(error.message||'Chưa lưu được bài học. Vui lòng thử lại.');}
    finally{if(b.isConnected)b.disabled=false;}
}));
document.querySelectorAll('[data-video]').forEach(b=>b.onclick=()=>showModal('<span class="eyebrow">KỊCH BẢN VIDEO · CHƯA CÓ BẢN QUAY</span><h2 class="modal-title">'+(b.dataset.video==='decimal'?'So sánh số thập phân':'Hai lần thay đổi phần trăm')+'</h2><ol class="schedule"><li><b>0:00–0:40</b> — Câu hỏi khởi động từ bài học.</li><li><b>0:40–2:10</b> — Giải thích từng bước bằng hình minh họa.</li><li><b>2:10–3:20</b> — Ví dụ và lỗi thường gặp.</li><li><b>3:20–4:30</b> — Dừng để học sinh tự trả lời.</li><li><b>4:30–5:00</b> — Chốt kiến thức, chuyển sang luyện tập.</li></ol><p class="modal-copy">Bản demo đã có bài đọc. Video sẽ được bổ sung sau khi duyệt nội dung.</p>'));
if($('#quiz-form')){const practice=route==='practice';$('#submit-quiz').disabled=false;$('#quiz-form').onsubmit=e=>{e.preventDefault();submitQuiz(practice);};$('#retry').onclick=()=>render();if(!practice)clock=setInterval(()=>{if(!$('#timer')){clearInterval(clock);return;}remaining--;$('#timer').textContent=String(Math.floor(remaining/60)).padStart(2,'0')+':'+String(remaining%60).padStart(2,'0');if(remaining<=0)submitQuiz(false,true);},1000);}
if(route==='game'){document.querySelectorAll('[data-stone]').forEach(b=>b.onclick=()=>{const sorted=[...rounds[gameRound]].sort((a,b)=>numberValue(a)-numberValue(b));if(b.dataset.stone===sorted[gameStep]){b.classList.add('passed');b.disabled=true;gameStep++;$('#game-counter').textContent=gameStep+' / 4 phiến đá';$('#game-status').textContent=gameStep===4?'✦ Sóc đã qua suối! Em sắp xếp rất chính xác.':'Đúng rồi! Tiếp theo là số nào?';if(gameStep===4){$('#game-reset').textContent='Vòng tiếp theo →';toast('Em vừa hoàn thành một cây cầu!');}}else $('#game-status').textContent='Thử lại nhé. Hãy tìm số bé nhất trong các phiến đá còn lại.';});$('#game-reset').onclick=()=>{if(gameStep===4)gameRound=(gameRound+1)%rounds.length;render();};}
if($('#logout'))$('#logout').onclick=()=>{data.name='';save();updateAccount();location.assign(pageHref('home'));};
document.querySelectorAll('[data-download]').forEach(b=>b.onclick=download);
if($('#live-class'))$('#live-class').onclick=()=>showModal('<span class="eyebrow">BUỔI HỌC TRỰC TIẾP MẪU</span><h2 class="modal-title">45 phút khám phá phần trăm</h2><ol class="schedule"><li><b>5 phút:</b> Khởi động: tăng rồi giảm cùng tỉ lệ.</li><li><b>10 phút:</b> Giáo viên giải thích bằng sơ đồ giá tiền.</li><li><b>15 phút:</b> Học sinh tự làm và trình bày.</li><li><b>10 phút:</b> Chữa lỗi chọn sai giá trị gốc.</li><li><b>5 phút:</b> Câu hỏi cuối buổi, giao bài về nhà.</li></ol><div class="notice">Chưa có phòng Zoom/Meet thật. Liên kết sẽ chỉ hiển thị cho học sinh được cấp quyền khi triển khai hệ thống chính thức.</div>');
if($('#submit-homework'))$('#submit-homework').onclick=()=>{const file=$('#homework-file').files[0];if(!file){toast('Em hãy chọn ảnh hoặc PDF trước nhé.');return;}if(!['image/jpeg','image/png','image/webp','application/pdf'].includes(file.type)){toast('Vui lòng chọn ảnh JPG, PNG, WebP hoặc PDF.');return;}if(file.size>10*1024*1024){toast('Tệp lớn hơn 10 MB. Em hãy chọn tệp nhỏ hơn.');return;}data.homework={name:file.name,date:new Date().toISOString()};save();$('#homework-status').textContent='Đã ghi nhận tên tệp: '+file.name+'. Chưa tải lên máy chủ hoặc gửi tới giáo viên.';toast('Đã ghi nhận bài nộp minh họa.');};
}
const pages = {
    home: {
        path: './',
        title: 'Ươm mầm tư duy - Khơi nguồn tri thức',
        description: 'Ôn thi vào trường cấp 2 chất lượng cao. Bồi dưỡng học sinh giỏi Toán. Học Toán đúng cách, hiểu bản chất. Phát triển tư duy cùng giáo viên tận tâm.',
        render: home
    },
    entrance: {
        path: 'dang-ky-kiem-tra-dau-vao/', title: 'Đăng Ký Kiểm Tra Đầu Vào',
        description: 'Đăng ký kiểm tra đầu vào Toán tại 5BMath để được tư vấn lộ trình và lớp Zoom phù hợp với học sinh tiểu học.',
        render: () => browser ? '' : require('node:fs').readFileSync(require('node:path').join(__dirname,'admissions.html'),'utf8').match(/<main id="app">([\s\S]*?)<\/main>/)[1]
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
        render: () => learning.render('dashboard')
    },
    ...Object.fromEntries(Object.entries(learningRoutes).map(([id,[path,title]]) => [
        id === 'dashboard' ? 'dashboard' : 'learn-' + id,
        {path,title,description:'Khu học tập 5BMath · ' + title + '.',noindex:true,
            render:()=>learning.render(id)}
    ])),
    ...Object.fromEntries(Object.entries(staffRoutes).map(([id,[path,title]])=>[
        'staff-'+id,{path,title,description:title+' của 5BMath.',noindex:true,render:()=>staff.render(id)}
    ]))
};

function pageHref(route) {
    return offline ? '#' + route : pages[route].path;
}

let renderedRoute, renderRevision=0;

async function render(route = renderedRoute) {
    const revision=++renderRevision;
    try {await ensureRoute(route);}catch(error){toast(error.message);return;}
    if(revision!==renderRevision)return;
    // A new battle question redraws this route without navigating away.
    const battleScroll = route === renderedRoute && route === 'learn-battle'
        ? {left:window.scrollX,top:window.scrollY,behavior:'instant'} : null;
    RuntimeAssets.unmountMascots();
    staff?.unmount();
    learning?.unmount();
    clearInterval(clock);
    document.body.classList.toggle('learning-mode', route === 'dashboard' || route.startsWith('learn-'));
    document.body.classList.toggle('staff-mode',route.startsWith('staff-'));
    $('#app').innerHTML = pages[route].render();
    document.title = route==='home' ? pages[route].title : pages[route].title + ' | 5BMath';
    document.querySelector('meta[name="description"]')?.setAttribute('content',pages[route].description);
    const robots=document.querySelector('meta[name="robots"]');
    if(pages[route].noindex){const meta=robots||document.head.appendChild(document.createElement('meta'));meta.name='robots';meta.content='noindex,nofollow';}
    else robots?.remove();
    const canonical=document.querySelector('link[rel="canonical"]');
    if(pages[route].noindex)canonical?.remove();
    else {const link=canonical||document.head.appendChild(document.createElement('link'));link.rel='canonical';link.href=new URL(pages[route].path,'https://5bmath.vn/').href;}
    if (route === renderedRoute && !battleScroll) window.scrollTo({ top: 0, behavior: 'instant' });
    renderedRoute = route;
    updateAccount();
    bind(route);
    if (route === 'dashboard' || route.startsWith('learn-')) learning.mount(route === 'dashboard' ? 'dashboard' : route.slice(6));
    if (route.startsWith('staff-')) staff.mount(route.slice(6),{showModal,toast,passwordFields});
    await RuntimeAssets.syncMascots($('#app')).catch(error=>toast(error.message));
    if (revision===renderRevision && battleScroll) window.scrollTo(battleScroll);
}

async function navigate(focusAnchor = false) {
    const fragment = location.hash.slice(1).split('?')[0] || 'home';
    const entry = document.documentElement.dataset.page || 'home';
    const legacyRoute = Object.hasOwn(pages, fragment) ? fragment : 'home';
    if (!offline && entry === 'home' && legacyRoute !== 'home') {
        const url = new URL(pageHref(legacyRoute), document.baseURI);
        url.search = location.search;
        location.replace(url);
        return;
    }
    const route = offline ? legacyRoute : entry;
    if (route !== renderedRoute) await render(route);
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

async function start() {
    const entry=document.documentElement.dataset.page||'home';
    const privateRoute=entry==='dashboard'||entry.startsWith('learn-')||entry.startsWith('staff-');
    if(liveBackend)initialSession=PlatformAPI.refresh({compact:!privateRoute}).then(snapshot=>{applyAccount(snapshot);}).catch(error=>{if(error.name!=='AbortError')toast('Chưa thể kiểm tra phiên. Em có thể thử đăng nhập lại.');});
    loadProgress();
    configureLearning();
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
    $('#account').disabled = false;
    $('#account').removeAttribute('aria-busy');
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
    window.addEventListener('pageshow', async event => {
        if (!event.persisted) return;
        if(liveBackend){try{applyAccount(await PlatformAPI.refresh());}catch{data.name='';data.completed=[];}}
        loadProgress();
        configureLearning();
        if(data.name)await ensureLearning();
        configureLearning();updateAccount();
        if(['lesson-decimal','lesson-percent'].includes(renderedRoute))await render();
        else await RuntimeAssets.syncMascots($('#app')).catch(error=>toast(error.message));
    });
    bindContact();
    // Public controls/rendering never wait for the session network request.
    if(!privateRoute){await navigate();window.PageLoading?.finish();}
    await initialSession;
    if(data.name)await ensureLearning();
    configureLearning();updateAccount();
    if(privateRoute)await navigate();
    else if(['lesson-decimal','lesson-percent'].includes(renderedRoute))await render();
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

if (browser) start().catch(error=>toast(error.message)).finally(()=>window.PageLoading?.finish());
else module.exports = { pages, esc };
