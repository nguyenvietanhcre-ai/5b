'use strict';

const StaffApp = (() => {
    const browser = typeof document !== 'undefined';
    const routes = {teacher:['giao-vien/','Không gian giáo viên'],admin:['quan-tri/','Quản trị hệ thống']};
    const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const money = value => new Intl.NumberFormat('vi-VN').format(value || 0) + ' đ';
    const date = value => value ? new Date(value).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',dateStyle:'short',timeStyle:'short'}) : '—';
    const localTime = value => value ? new Date(new Date(value).getTime()+7*3600000).toISOString().slice(0,16) : '';
    const statusLabel = value => ({
        active:'Đang hoạt động',closed:'Đã kết thúc',disabled:'Đã khóa',suspended:'Tạm khóa',deleted:'Đã xóa',
        published:'Đã phát hành',draft:'Bản nháp',retired:'Ngừng phát hành',pending:'Chờ đối soát',
        paid:'Đã thanh toán',cancelled:'Đã hủy',teacher:'Giáo viên',admin:'Quản trị viên',
    }[value] || value);
    const badge = value => `<span class="staff-badge ${['closed','disabled','suspended','deleted','retired','cancelled'].includes(value) ? 'muted' : ['draft','pending'].includes(value) ? 'warm' : ''}">${esc(statusLabel(value))}</span>`;
    const input = (label,name,value='',type='text',extra='') => `<label class="staff-field"><span>${label}</span><input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
    const text = (label,name,value='',extra='') => `<label class="staff-field"><span>${label}</span><textarea name="${name}" rows="4" ${extra}>${esc(value)}</textarea></label>`;
    const select = (label,name,options,value='',accessibleLabel='') => `<label class="staff-field"><span>${label}</span><select name="${name}" ${accessibleLabel?'aria-label="'+esc(accessibleLabel)+'"':''}>${options.map(([key,title]) => `<option value="${esc(key)}" ${String(value)===String(key)?'selected':''}>${esc(title)}</option>`).join('')}</select></label>`;
    const button = (label,action,extra='',kind='outline') => `<button class="btn ${kind}" type="button" data-staff="${action}" ${extra}>${label}</button>`;
    const submit = label => `<button class="btn dark" type="submit">${label}</button>`;
    const panel = (title,body,extra='') => `<section class="staff-panel ${extra}"><h2>${title}</h2>${body}</section>`;
    const empty = (title,copy='') => `<div class="staff-empty"><span aria-hidden="true">◇</span><h3>${title}</h3>${copy ? '<p>'+copy+'</p>' : ''}</div>`;
    const table = (heads,rows) => `<div class="staff-table-wrap"><table class="staff-table"><thead><tr>${heads.map(head=>'<th scope="col">'+head+'</th>').join('')}</tr></thead><tbody>${rows.join('')}</tbody></table></div>`;
    const gradeOptions = Array.from({length:5},(_,index)=>[index+1,'Khối '+(index+1)]);
    const adminTabs = [
        ['overview','Tổng quan','▦'],['classes','Lớp Zoom','◷'],['content','Học liệu','▤'],
        ['accounts','Học sinh','♙'],['users','Nhân sự & quyền','♧'],
        ['admissions','Đăng ký đầu vào','✎'],['notifications','Gửi thông báo','✉'],['payments','Đối soát','₫'],['settings','Cấu hình','⚙'],['audit','Nhật ký','≡'],
    ];
    let mode = 'teacher';
    let user = null;
    let csrf = '';
    let tab = 'overview';
    let payload = {};
    let classList = [];
    let teachers = [];
    let detail = null;
    let classId = null;
    let classTab = 'sessions';
    let sessionId = null;
    let gradingSessionId = null;
    let gradingAssignmentId = null;
    let topicKind = 'lessons';
    let filter = {q:'',grade:'0',page:1};
    let host = {};
    let setupNeeded = false;
    let loading = false;
    let generation = 0;
    let modalContext = null;
    let loadError = '';
    let notificationOwner = '';
    let notificationDraft = {title:'',body:'',audience:'',classId:'',requestKey:'',signature:''};
    let notificationPreview = {target:'',count:null,label:'',pending:false,error:'',ticket:0};
    let notificationSending = false;
    let notificationError = '';
    let notificationResult = '';
    let notificationGeneration = 0;
    let tuition = {owner:null,classId:null,month:'',preview:null,selected:null,invoice:null,busy:false,stale:false,error:'',requestKey:'',signature:'',ticket:0};
    let receipts={owner:null,page:1,status:'all',q:'',rows:null,total:0,pageSize:25,automationEnabled:false,error:'',loading:false,ticket:0};

    async function request(path,body) {
        const response = await fetch('/api/staff/'+path,{
            method:body===undefined?'GET':'POST',credentials:'same-origin',
            headers:body===undefined?{}:{'Content-Type':'application/json','X-CSRF-Token':csrf},
            body:body===undefined?undefined:JSON.stringify(body),signal:AbortSignal.timeout(20000),
        });
        const result = await response.json().catch(()=>({error:'Mở trang bằng máy chủ Python để sử dụng quản trị.'}));
        if (!response.ok) {
            if(response.status===401) {user=null;csrf='';resetNotificationDraft();}
            const error=new Error(result.error || 'Chưa thể kết nối. Vui lòng thử lại.');error.status=response.status;throw error;
        }
        return result;
    }

    function header(title,copy,actions='') {
        return `<div class="staff-page-head"><div><h1>${title}</h1><p>${copy}</p></div><div class="staff-actions">${actions}</div></div>`;
    }

    function loginView() {
        return `<div class="staff-login"><div class="staff-login-intro"><span class="staff-kicker">5BMath · Vườn Toán</span><h1>${mode==='admin'?'Quản trị hệ thống':'Không gian giáo viên'}</h1><p>${mode==='admin'?'Theo dõi hoạt động, quản lý học liệu và cập nhật hệ thống.':'Chuẩn bị buổi học, theo dõi học sinh và đồng hành cùng từng lớp Zoom.'}</p><div class="staff-mascot" role="img" aria-label="Mầm Sách đang đọc sách"></div></div><section class="staff-login-card"><img src="5bmath-logo.svg" alt="5BMath Gieo Mầm Toán" width="628" height="168"><h2>Đăng nhập làm việc</h2><form id="staff-login-form">${input('Tên đăng nhập','login','','text','required autocomplete="username" maxlength="100"')}${input('Mật khẩu','password','','password','required autocomplete="current-password" maxlength="128"')}${submit('Vào '+(mode==='admin'?'trang quản trị':'trang giáo viên'))}<p id="staff-login-error" class="staff-error" role="alert"></p></form><p>Tài khoản nhân sự do quản trị viên cấp.</p>${setupNeeded ? '<details class="staff-setup"><summary>Khởi tạo quản trị viên đầu tiên</summary><p>Chạy lệnh sau trong thư mục dự án. Lệnh hỏi mật khẩu trực tiếp trên máy.</p><code>docker compose exec web python -m backend.staff_admin --database /data/5bmath-demo.sqlite3</code></details>' : ''}<div class="staff-login-links"><a href="${mode==='admin'?'giao-vien/':'quan-tri/'}">${mode==='admin'?'Trang giáo viên':'Trang quản trị'}</a><a href="./">Về trang chủ</a></div></section></div>`;
    }

    function shell(body) {
        if (!user) return loginView();
        if(mode==='admin' && user.role!=='admin') {
            return header('Quyền truy cập','Tài khoản này được cấp vai trò giáo viên.')+
                panel('Về không gian làm việc','<a class="btn dark" href="giao-vien/">Mở trang giáo viên</a>');
        }
        const nav = mode==='admin' ? adminTabs.map(([key,label,symbol]) => `<button type="button" data-tab="${key}" ${tab===key?'aria-current="page"':''}><span aria-hidden="true">${symbol}</span>${label}</button>`).join('') :
            `<button type="button" data-tab="overview" ${tab!=='notifications'?'aria-current="page"':''}><span aria-hidden="true">▦</span>Lớp của tôi</button><button type="button" data-tab="notifications" ${tab==='notifications'?'aria-current="page"':''}><span aria-hidden="true">✉</span>Gửi thông báo</button><a href="./"><span aria-hidden="true">⌂</span>Trang chủ 5BMath</a>`;
        return `<div class="staff-shell"><aside class="staff-sidebar"><a class="staff-brand" href="./"><img src="5bmath-logo.svg" alt="5BMath Gieo Mầm Toán" width="628" height="168"></a><span class="staff-role">${mode==='admin'?'Quản trị hệ thống':'Không gian giáo viên'}</span><nav aria-label="Điều hướng nhân sự">${nav}</nav><div class="staff-side-footer">${user.role==='admin'?'<a href="'+(mode==='admin'?'giao-vien/':'quan-tri/')+'">'+(mode==='admin'?'Mở trang giáo viên':'Mở trang quản trị')+' ↗</a>':''}<span>5BMath · Gieo Mầm Toán</span></div></aside>
        <div class="staff-main"><header class="staff-topbar"><a class="staff-mobile-brand" href="./"><img src="5bmath-logo.svg" alt="5BMath" width="628" height="168"></a><span class="staff-date">${new Intl.DateTimeFormat('vi-VN',{dateStyle:'full',timeZone:'Asia/Ho_Chi_Minh'}).format(new Date())}</span><div class="staff-identity"><span class="staff-avatar">${esc(user.full_name.trim().split(/\s+/).slice(-2).map(part=>part[0]).join(''))}</span><div><b>${esc(user.full_name)}</b><small>${statusLabel(user.role)}</small></div>${button('Đổi mật khẩu','password')}${button('Thoát','logout')}</div></header>
        <div class="staff-content">${body}</div></div></div>`;
    }

    function stats(items) {
        return `<div class="staff-stats">${items.map(([label,value,detail])=>`<article><span>${label}</span><strong>${esc(value)}</strong>${detail?'<small>'+detail+'</small>':''}</article>`).join('')}</div>`;
    }

    function overview() {
        if(mode==='teacher') {
            const active=classList.filter(item=>item.status==='active');
            return header('Lớp của tôi','Theo dõi lớp được phân công và chuẩn bị buổi học.',button('Tải lại','reload'))+
                stats([['Lớp đang dạy',active.length],['Học sinh đang học',active.reduce((sum,item)=>sum+item.student_count,0)],['Lớp có buổi sắp tới',active.filter(item=>item.next_session).length]])+
                classCards(classList);
        }
        const count=payload.counts || {};
        return header('Quản trị hệ thống','Theo dõi dữ liệu hiện có và điều phối công việc của 5BMath.',button('Tải lại','reload'))+
            stats([['Học sinh',count.students||0],['Lớp Zoom',count.classes||0],['Bài học',count.lessons||0],['Bài toán',count.questions||0]])+
            `<div class="staff-grid-two">${panel('Công việc quản trị',`<div class="staff-task-list"><button type="button" data-tab="payments"><span><b>Đối soát thanh toán</b><small>Đơn chờ xác nhận tiền đã nhận</small></span><strong>${count.pendingPayments||0} →</strong></button><button type="button" data-tab="classes"><span><b>Quản lý lớp Zoom</b><small>Phân công giáo viên và ghi danh học sinh</small></span>→</button><button type="button" data-tab="content"><span><b>Cập nhật học liệu</b><small>Bài giảng, chuyên đề và câu hỏi theo phiên bản</small></span>→</button></div>`)}${panel('Điều hành hệ thống',`<p>Điều chỉnh trạng thái chức năng và hạn mức tài khoản Free.</p><div class="staff-actions">${button('Mở cấu hình','settings','', 'dark')}${button('Xem nhật ký','audit')}</div><div class="staff-small-mascot" aria-hidden="true"></div>`)}</div>`;
    }

    function classCards(items) {
        if(!items.length) return panel('Danh sách lớp',empty('Chưa có lớp được phân công',mode==='admin'?'Tạo lớp sau khi đã cấp tài khoản giáo viên.':'Các lớp do admin phân công sẽ xuất hiện tại đây.'));
        return `<div class="staff-class-grid">${items.map(item=>`<article class="staff-panel staff-class-card"><div class="staff-split">${badge(item.status)}<span>Khối ${item.grade_id}</span></div><h2>${esc(item.name)}</h2><p>${esc(item.teacher)} · ${item.student_count} học sinh</p><div class="staff-class-meta"><span>${esc(item.schedule || 'Chưa có lịch định kỳ')}</span><span>Buổi tiếp theo · ${date(item.next_session)}</span><span>Năm học ${esc(item.academic_year)}</span></div><div class="staff-actions">${button('Mở lớp','open-class','data-id="'+item.id+'"','dark')}${mode==='admin'?button('Sửa lớp','edit-class','data-id="'+item.id+'"'):''}</div></article>`).join('')}</div>`;
    }

    function classView() {
        if(!detail) return header('Lớp Zoom','Quản lý phân công, lịch học và ghi danh.',mode==='admin'?button('Tạo lớp mới','new-class','','dark'):'')+classCards(classList);
        const info=detail.class;
        const tabs=[['sessions','Buổi học'],['students','Học sinh'],['records','Điểm danh & Nhận Xét'],['grading','Chấm điểm'],['fees','Học phí']];
        return header(esc(info.name),'Khối '+info.grade_id+' · '+esc(info.teacher),button('Danh sách lớp','back-classes')+
            (info.meeting_ref?`<a class="btn dark" href="${esc(info.meeting_ref)}" target="_blank" rel="noopener noreferrer">Vào Zoom ↗</a>`:''))+
            `<div class="staff-class-summary"><span>${esc(info.schedule || 'Chưa có lịch định kỳ')}</span>${badge(info.status)}<span>${detail.students.length} học sinh</span></div><nav class="staff-tabs" aria-label="Quản lý lớp">${tabs.map(([id,title])=>`<button type="button" data-class-tab="${id}" aria-current="${classTab===id?'page':'false'}">${title}</button>`).join('')}</nav>`+
            (classTab==='sessions'?sessionList():classTab==='students'?rosterView():classTab==='records'?recordsView():classTab==='grading'?gradingView():feesView());
    }

    function sessionList() {
        return panel('Buổi học',`<div class="staff-panel-tools">${button('Thêm buổi học','new-session','','dark')}</div>`+
            (detail.sessions.length?table(['Buổi học','Thời gian','Bài tập','Video','Thao tác'],detail.sessions.map(item=>`<tr><td><b>${esc(item.title)}</b><small>${esc(item.teacher_comment.slice(0,110))}</small></td><td>${date(item.starts_at)}</td><td>${item.assignments.length}</td><td>${item.video_url?'<a href="'+esc(item.video_url)+'" target="_blank" rel="noopener noreferrer">Mở video ↗</a>':'Chưa có'}</td><td><div class="staff-actions">${button('Sửa','edit-session','data-id="'+item.id+'"')}${button('Bài tập','assignments','data-id="'+item.id+'"')}${button('Điểm danh','open-records','data-id="'+item.id+'"')}</div></td></tr>`)):empty('Chưa có buổi học','Thêm thời gian, nội dung và nhận xét cho buổi học đầu tiên.')));
    }

    function rosterView() {
        return panel('Học sinh trong lớp',`${mode==='admin'?'<div class="staff-panel-tools">'+button('Ghi danh học sinh','enroll','','dark')+'</div>':''}`+
            (detail.students.length?table(['Học sinh','Tài khoản','Thao tác'],detail.students.map(student=>`<tr><td><b>${esc(student.full_name)}</b><small>Mã học sinh ${student.id}</small></td><td>${esc(student.login_identifier||'—')}</td><td>${mode==='admin'?button('Cho rời lớp','leave-student','data-id="'+student.id+'"'):'Đang theo học'}</td></tr>`)):empty('Chưa có học sinh','Admin ghi danh học sinh để giáo viên điểm danh và nhập điểm.')));
    }

    function selectedSession() {
        return detail?.sessions.find(item=>item.id===Number(sessionId)) || detail?.sessions[0];
    }

    function recordsView() {
        const item=selectedSession();
        if(!item) return panel('Điểm danh & Nhận Xét',empty('Chưa có buổi học','Tạo buổi học trước khi điểm danh và lưu nhận xét.'));
        return panel('Điểm danh & Nhận Xét',`<div class="staff-toolbar">${select('Buổi học','record-session',detail.sessions.map(session=>[session.id,session.title+' · '+date(session.starts_at)]),item.id)}</div>
        <form id="staff-records-form" class="staff-student-records"><div class="staff-table-wrap"><table class="staff-table"><thead><tr><th scope="col">Học sinh</th><th scope="col">Điểm danh</th><th scope="col">Nhận xét sau buổi học</th></tr></thead><tbody>${detail.students.map(student=>{
            const attendance=item.attendance.find(value=>value.student_id===student.id);
            return `<tr><td><b>${esc(student.full_name)}</b></td><td data-label="Điểm danh">${select('','attendance-'+student.id,[['','Chưa điểm danh'],['charged','Có học · tính phí'],['free','Có học · miễn phí'],['absent','Vắng']],attendance?.status||'','Điểm danh '+student.full_name)}</td><td data-label="Nhận xét sau buổi học">${text('','session-comment-'+student.id,attendance?.comment||'','maxlength="10000" aria-label="Nhận xét sau buổi học của '+esc(student.full_name)+'"')}</td></tr>`;
        }).join('')}</tbody></table></div>${detail.students.length?'<div class="staff-form-footer">'+submit('Lưu điểm danh và nhận xét')+'</div>':empty('Lớp chưa có học sinh')}</form><p class="staff-note">Nhận xét được lưu riêng cho từng học sinh trong buổi học đang chọn.</p>`);
    }

    function submissionLink(submission) {
        const value=submission.url || '';
        const safe=/^\/api\/staff\/submissions\/\d+\/file$/.test(value);
        return safe?`<a class="staff-submission-link" href="${esc(value)}" target="_blank" rel="noopener noreferrer">${esc(submission.filename || 'Mở bài nộp')} ↗</a><small>${date(submission.submitted_at)}</small>`:'<span>Chưa có tệp bài nộp</span>';
    }

    function drawGrading() {
        draw();
        const title=document.querySelector('.staff-content > .staff-panel > h2');
        if(title) {title.tabIndex=-1;title.focus();}
    }

    function gradingView() {
        const item=detail.sessions.find(value=>value.id===Number(gradingSessionId));
        if(!item) return panel('Chấm điểm',detail.sessions.length?
            '<p class="staff-grading-copy">Chọn buổi học để xem các bài tập cần nộp.</p>'+table(['Buổi học','Thời gian','Bài tập'],detail.sessions.map(session=>`<tr><td>${button(esc(session.title),'grade-session','data-id="'+session.id+'"','outline staff-grading-title')}</td><td>${date(session.starts_at)}</td><td>${session.assignments.length}</td></tr>`)):
            empty('Chưa có buổi học','Tạo buổi học và giao bài tập để bắt đầu chấm điểm.'));
        const assignment=item.assignments.find(value=>value.id===Number(gradingAssignmentId));
        const navigation=`<nav class="staff-grading-path" aria-label="Vị trí chấm điểm">${button('Các buổi học','grade-sessions')}<span aria-hidden="true">›</span>${assignment?button(esc(item.title),'grade-session','data-id="'+item.id+'"'):'<strong>'+esc(item.title)+'</strong>'}${assignment?'<span aria-hidden="true">›</span><strong>'+esc(assignment.title)+'</strong>':''}</nav>`;
        if(!assignment) return panel('Chấm điểm',navigation+'<p class="staff-grading-copy">'+date(item.starts_at)+' · Chọn bài tập để xem bài nộp và nhập điểm.</p>'+
            (item.assignments.length?table(['Bài tập','Loại bài tập','Bài nộp'],item.assignments.map(row=>{
                const count=new Set((item.submissions||[]).filter(value=>value.assignment_id===row.id).map(value=>value.student_id)).size;
                return `<tr><td>${button(esc(row.title),'grade-assignment','data-id="'+row.id+'"','outline staff-grading-title')}</td><td>${esc(row.kind)}</td><td>${count} / ${detail.students.length} học sinh</td></tr>`;
            })):empty('Chưa có bài tập','Thêm bài tập cho buổi học này trong mục Buổi học.')));
        return panel('Chấm điểm',navigation+`<p class="staff-grading-copy">${esc(assignment.kind)} · ${date(item.starts_at)}</p><form id="staff-grading-form" class="staff-student-records"><div class="staff-table-wrap"><table class="staff-table"><thead><tr><th scope="col">Học sinh</th><th scope="col">Bài nộp</th><th scope="col">Điểm · 0–10</th><th scope="col">Nhận xét</th></tr></thead><tbody>${detail.students.map(student=>{
            const score=item.scores.find(value=>value.student_id===student.id && value.assignment_id===assignment.id);
            const submissions=(item.submissions||[]).filter(value=>value.student_id===student.id && value.assignment_id===assignment.id);
            return `<tr><td><b>${esc(student.full_name)}</b></td><td data-label="Bài nộp"><div class="staff-submissions">${submissions.length?submissions.map(submissionLink).join(''):'<span class="staff-note">Chưa nộp bài</span>'}</div></td><td data-label="Điểm · 0–10">${input('','score-'+student.id,score?.score??'','number','min="0" max="10" step="0.01" aria-label="Điểm của '+esc(student.full_name)+'"')}</td><td data-label="Nhận xét">${text('','score-comment-'+student.id,score?.comment||'','maxlength="10000" aria-label="Nhận xét bài tập của '+esc(student.full_name)+'"')}</td></tr>`;
        }).join('')}</tbody></table></div>${detail.students.length?'<div class="staff-form-footer">'+submit('Lưu điểm và nhận xét')+'</div>':empty('Lớp chưa có học sinh')}</form><p class="staff-note">Để trống điểm nếu chưa chấm. Điểm và nhận xét được lưu riêng cho bài tập này.</p>`);
    }

    function feesView() {
        const rate=detail.class.session_fee;
        return panel('Học phí theo tháng',`<div class="staff-split staff-fee-tools"><p>Học phí mỗi buổi: <b>${rate===null||rate===undefined?'Chưa thiết lập':rate===0?'Miễn phí · 0 đ':money(rate)}</b></p><div class="staff-actions">${button('Tính học phí','calculate-fees','','dark')}${mode==='admin'?button('Lập học phí','new-fee'):''}</div></div>`+
            (detail.fees.length?`<div class="staff-saved-fees">${table(['Tháng','Học sinh','Số tiền','Trạng thái','Chi tiết'],detail.fees.map(fee=>`<tr><td>${esc(fee.month)}</td><td>${esc(fee.full_name)}</td><td><b>${money(fee.amount)}</b></td><td>${fee.paid_at?'<span class="staff-badge">Đã hoàn thành</span>':fee.amount===0?'<span class="staff-badge muted">Không phát sinh học phí</span>':badge('pending')}</td><td>${button('Xem học phí','open-fee','data-id="'+fee.id+'"')}</td></tr>`))}</div>`:empty('Chưa lập học phí','Chọn Tính học phí để xem trước số buổi theo điểm danh.')));
    }

    function pagination() {
        const total=payload.total || 0, pages=Math.max(1,Math.ceil(total/(payload.pageSize||25)));
        return `<div class="staff-pagination"><span>${total} bản ghi · Trang ${filter.page} / ${pages}</span><div class="staff-actions">${button('Trang trước','previous',filter.page<=1?'disabled':'')}${button('Trang sau','next',filter.page>=pages?'disabled':'')}</div></div>`;
    }

    function searchForm(grades=false,accountStatus=false) {
        return `<form class="staff-toolbar" id="staff-filter-form">${input('Tìm kiếm','q',filter.q,'search','placeholder="Nhập tên hoặc mã…" maxlength="100"')}${grades?select('Khối','grade',[['0','Tất cả khối'],...gradeOptions],filter.grade):''}${accountStatus?select('Trạng thái','status',[['all','Tất cả chưa xóa'],['active','Đang hoạt động'],['suspended','Tạm khóa'],['deleted','Đã xóa']],filter.status||'all'):''}${submit('Tìm kiếm')}</form>`;
    }

    function contentView() {
        const kind=topicKind;
        const titles={lessons:'Bài giảng',topics:'Chuyên đề',questions:'Ngân hàng câu hỏi'};
        let rows;
        if(kind==='lessons') rows=table(['Bài giảng','Khối / tuần','Trạng thái',''],(payload.rows||[]).map(row=>`<tr><td><b>${esc(row.title)}</b><small>${row.kind==='topic'?'Theo chuyên đề':'Theo tuần'}</small></td><td>Khối ${row.grade_id} · Tuần ${row.week_no}</td><td>${badge(row.publication_status)}</td><td>${button('Chỉnh sửa','edit-content','data-id="'+row.id+'"')}</td></tr>`));
        else if(kind==='topics') rows=table(['Chuyên đề','Khối',''],(payload.rows||[]).map(row=>`<tr><td><b>${esc(row.title)}</b><small>${esc(row.intro.slice(0,100))}</small></td><td>Khối ${row.grade_id}</td><td>${button('Chỉnh sửa','edit-content','data-id="'+row.id+'"')}</td></tr>`));
        else rows=table(['Bài toán','Khối / mức độ','Phiên bản',''],(payload.rows||[]).map(row=>`<tr><td><b>${esc(row.prompt)}</b><small>${esc(row.question_code)}</small></td><td>Khối ${row.grade_id} · ${['Cơ bản','Nâng cao','Khó','Tư duy'][row.difficulty-1]}</td><td>v${row.revision} ${badge(row.status)}</td><td>${button('Sửa nội dung','edit-content','data-id="'+row.id+'"')}</td></tr>`));
        return header('Học liệu','Quản lý nội dung theo khối và chuyên đề.',button('Thêm '+(kind==='questions'?'câu hỏi':kind==='topics'?'chuyên đề':'bài giảng'),'new-content','','dark'))+
            `<nav class="staff-tabs" aria-label="Loại học liệu">${Object.entries(titles).map(([id,title])=>`<button type="button" data-content-kind="${id}" aria-current="${kind===id?'page':'false'}">${title}</button>`).join('')}</nav>`+
            panel(titles[kind],searchForm(true)+(payload.rows?.length?rows:empty('Chưa có học liệu phù hợp'))+pagination());
    }

    function accountsView() {
        return header('Học sinh & tài khoản','Thêm, sửa thông tin, quản lý truy cập và xóa tài khoản học sinh.',button('Thêm tài khoản','new-account','','dark'))+
            panel('Danh sách tài khoản',searchForm(true,true)+(payload.rows?.length?`<div class="staff-account-list">${table(['Học sinh','Khối','Quyền học','Trạng thái','Thao tác'],payload.rows.map(row=>{
                const id='data-id="'+row.id+'"';
                const actions=row.deleted_at?button('Khôi phục','restore-account',id):button('Chỉnh sửa','edit-account',id)+button(row.status==='active'?'Tạm khóa':'Mở lại','account-status',id)+button('Xóa','delete-account',id,'outline staff-danger');
                const mascot=(payload.mascots||[]).find(item=>item.code===row.mascot)?.name;
                return `<tr><td><b>${esc(row.full_name)}</b><small>${esc(row.login_identifier)}${row.is_demo?' · Dữ liệu thử':''}</small>${mascot?'<small>'+esc(mascot)+' · '+new Intl.NumberFormat('vi-VN').format(row.points??1000)+' kinh nghiệm</small>':''}</td><td data-label="Khối">Khối ${row.grade_level}<small>Sinh năm ${esc(row.birth_year)}</small></td><td data-label="Quyền học">${badge(row.membership)}${row.class_name?'<small>'+esc(row.class_name)+'</small>':''}${row.membership!=='Free'?'<small>'+(row.membership_expires_at?'Đến '+date(row.membership_expires_at):'Không giới hạn thời hạn')+'</small>':''}</td><td data-label="Trạng thái">${badge(row.deleted_at?'deleted':row.status)}${row.deleted_at?'<small>'+date(row.deleted_at)+'</small>':''}</td><td data-label="Thao tác"><div class="staff-actions">${actions}</div></td></tr>`;
            }))}</div>`:empty('Không tìm thấy tài khoản','Thử đổi từ khóa hoặc bộ lọc trạng thái.'))+pagination()+
            '<p class="staff-note">Tạm khóa giữ tài khoản trong danh sách. Xóa chuyển tài khoản sang mục Đã xóa và ngừng truy cập; lịch sử học tập, điểm và thanh toán vẫn được giữ.</p>');
    }

    function usersView() {
        return header('Nhân sự & phân quyền','Cấp tài khoản giáo viên, phân quyền quản trị và quản lý truy cập.',button('Thêm nhân sự','new-user','','dark'))+
            panel('Tài khoản nhân sự',table(['Nhân sự','Vai trò','Trạng thái',''],(payload.users||[]).map(row=>`<tr><td><b>${esc(row.full_name)}</b><small>${esc(row.login)}</small></td><td>${badge(row.role)}</td><td>${badge(row.status)}</td><td>${button('Chỉnh sửa','edit-user','data-id="'+row.id+'"')}</td></tr>`)));
    }

    function resetNotificationDraft() {
        notificationGeneration++;
        notificationOwner='';notificationDraft={title:'',body:'',audience:'',classId:'',requestKey:'',signature:''};
        notificationPreview={target:'',count:null,label:'',pending:false,error:'',ticket:notificationPreview.ticket+1};
        notificationSending=false;notificationError='';notificationResult='';
        const form=browser?document.querySelector('#staff-notification-form'):null;
        if(form) {
            form.elements.title.value='';form.elements.body.value='';
            document.querySelector('#staff-notification-preview-title').textContent='Tiêu đề thông báo';
            document.querySelector('#staff-notification-preview-body').textContent='Nội dung sẽ hiển thị trong tài khoản học sinh.';
            document.querySelector('#staff-notification-send').disabled=true;
        }
    }

    function syncNotificationDraft() {
        if(notificationOwner!==String(user.id)) {
            resetNotificationDraft();
            notificationOwner=String(user.id);
        }
        const groups=user.role==='admin'?(payload.groups||[]):[];
        if(user.role!=='admin') notificationDraft.audience='class';
        else if(![...groups.map(item=>item.value),'class'].includes(notificationDraft.audience)) notificationDraft.audience=groups[0]?.value||'class';
        if(!(payload.classes||[]).some(item=>String(item.id)===String(notificationDraft.classId))) notificationDraft.classId=String(payload.classes?.[0]?.id||'');
    }

    function notificationTarget() {
        const audience=user.role==='admin'?notificationDraft.audience:'class';
        return {audience,...(audience==='class'?{classId:Number(notificationDraft.classId)}:{})};
    }

    function notificationTargetValid() {
        const target=notificationTarget();
        return target.audience==='class'?(payload.classes||[]).some(item=>item.id===target.classId):user.role==='admin'&&(payload.groups||[]).some(item=>item.value===target.audience);
    }

    function notificationsView() {
        const groups=user.role==='admin'?(payload.groups||[]):[];
        const classOptions=(payload.classes||[]).map(item=>[item.id,item.name]);
        const rows=payload.rows||[];
        return header('Gửi thông báo',user.role==='admin'?'Gửi thông báo trong tài khoản học sinh theo nhóm quyền học hoặc lớp.':'Gửi thông báo trong tài khoản học sinh của lớp được phân công.',button('Tải lại','reload'))+
            panel('Soạn thông báo',`<form id="staff-notification-form"><div class="staff-form-grid">
            ${user.role==='admin'?select('Người nhận','audience',[...groups.map(item=>[item.value,item.label]),['class','Học sinh theo lớp']],notificationDraft.audience):'<input type="hidden" name="audience" value="class">'}
            <div id="staff-notification-class" ${notificationDraft.audience==='class'?'':'hidden'}>${select('Lớp nhận thông báo','classId',classOptions.length?classOptions:[['','Chưa có lớp được phân công']],notificationDraft.classId)}</div></div>
            <div class="staff-notification-target"><p id="staff-notification-count" role="status" aria-live="polite"></p>${button('Kiểm tra người nhận','notification-preview')}</div>
            ${input('Tiêu đề','title',notificationDraft.title,'text','required maxlength="160" autocomplete="off"')}
            ${text('Nội dung thông báo','body',notificationDraft.body,'required maxlength="10000"')}
            <details class="staff-notification-preview"><summary>Xem trước thông báo</summary><strong id="staff-notification-preview-title">${esc(notificationDraft.title||'Tiêu đề thông báo')}</strong><p id="staff-notification-preview-body">${esc(notificationDraft.body||'Nội dung sẽ hiển thị trong tài khoản học sinh.')}</p></details>
            <p id="staff-notification-error" class="staff-error" role="alert">${esc(notificationError)}</p><p id="staff-notification-result" class="staff-notification-result" role="status">${esc(notificationResult)}</p>
            <div class="staff-form-footer"><button id="staff-notification-send" class="btn dark" type="submit" disabled>Chọn người nhận</button></div></form>`)+
            panel('Thông báo đã gửi',rows.length?`<div class="staff-notification-outbox">${rows.map(row=>`<details><summary><strong>${esc(row.title)}</strong><small>${date(row.created_at)} · ${esc(row.audience_label)} · ${row.recipient_count} học sinh${row.sender_name?' · '+esc(row.sender_name):''}</small></summary><p>${esc(row.body)}</p></details>`).join('')}</div>`+pagination():empty('Chưa gửi thông báo','Thông báo đã gửi sẽ xuất hiện tại đây.'));
    }

    function updateNotificationComposer() {
        const form=document.querySelector('#staff-notification-form');
        if(!form) return;
        const isClass=notificationDraft.audience==='class',valid=notificationTargetValid();
        const group=document.querySelector('#staff-notification-class');group.hidden=!isClass;
        form.elements.classId.disabled=notificationSending||!isClass||!payload.classes?.length;
        if(form.elements.audience.type!=='hidden') form.elements.audience.disabled=notificationSending;
        form.elements.title.readOnly=notificationSending;form.elements.body.readOnly=notificationSending;
        document.querySelector('#staff-notification-count').textContent=notificationPreview.pending?'Đang kiểm tra người nhận…':!valid?'Chưa có lớp đang hoạt động để gửi thông báo.':notificationPreview.error||notificationPreview.count===null?'Chưa kiểm tra được người nhận.':notificationPreview.label+' · '+notificationPreview.count+' tài khoản nhận thông báo';
        const control=document.querySelector('#staff-notification-send');
        control.disabled=notificationSending||notificationPreview.pending||!valid||!(notificationPreview.count>0)||notificationPreview.target!==JSON.stringify(notificationTarget());
        control.textContent=notificationSending?'Đang gửi…':notificationPreview.count>0?'Gửi tới '+notificationPreview.count+' học sinh':'Chưa có người nhận';
        form.querySelector('[data-staff=notification-preview]').disabled=notificationSending||notificationPreview.pending||!valid;
        document.querySelector('#staff-notification-error').textContent=notificationError||notificationPreview.error;
        document.querySelector('#staff-notification-result').textContent=notificationResult;
        document.querySelector('#staff-notification-preview-title').textContent=notificationDraft.title||'Tiêu đề thông báo';
        document.querySelector('#staff-notification-preview-body').textContent=notificationDraft.body||'Nội dung sẽ hiển thị trong tài khoản học sinh.';
    }

    async function previewNotifications(force=false) {
        if(!user || tab!=='notifications') return;
        const owner=user.id,target=notificationTarget(),signature=JSON.stringify(target);
        if(!force && notificationPreview.target===signature && (notificationPreview.pending||notificationPreview.count!==null)) {updateNotificationComposer();return;}
        const ticket=notificationPreview.ticket+1;
        notificationPreview={target:signature,count:null,label:'',pending:notificationTargetValid(),error:'',ticket};
        updateNotificationComposer();
        if(!notificationPreview.pending) return;
        try {
            const result=await request('notifications/preview',target);
            if(user?.id!==owner||notificationPreview.ticket!==ticket) return;
            notificationPreview.count=result.recipientCount;notificationPreview.label=result.audienceLabel;
        } catch(error) {
            if(user?.id!==owner||notificationPreview.ticket!==ticket) return;
            notificationPreview.error=error.message;
        } finally {
            if(user?.id===owner&&notificationPreview.ticket===ticket) {notificationPreview.pending=false;updateNotificationComposer();}
        }
    }

    function notificationRequestKey() {
        const bytes=new Uint8Array(16);
        if(!globalThis.crypto?.getRandomValues) throw new Error('Trình duyệt chưa hỗ trợ tạo mã gửi an toàn. Vui lòng cập nhật trình duyệt.');
        globalThis.crypto.getRandomValues(bytes);
        return 'notice-'+Array.from(bytes,value=>value.toString(16).padStart(2,'0')).join('');
    }

    function bindNotificationComposer() {
        const form=document.querySelector('#staff-notification-form');
        if(!form) return;
        form.oninput=event=>{
            if(['title','body'].includes(event.target.name)) {notificationDraft[event.target.name]=event.target.value;notificationError='';notificationResult='';updateNotificationComposer();}
        };
        form.onchange=event=>{
            if(!['audience','classId'].includes(event.target.name)) return;
            notificationDraft[event.target.name]=event.target.value;notificationError='';notificationResult='';previewNotifications(true);
        };
        form.onsubmit=async event=>{
            event.preventDefault();
            if(notificationSending||notificationPreview.pending||!(notificationPreview.count>0)||!notificationTargetValid()||notificationPreview.target!==JSON.stringify(notificationTarget())) return;
            const owner=user.id,ownerGeneration=notificationGeneration,body={...notificationTarget(),title:notificationDraft.title.trim(),body:notificationDraft.body.trim()};
            const signature=JSON.stringify(body);
            try {
                if(notificationDraft.signature!==signature||!notificationDraft.requestKey) {notificationDraft.signature=signature;notificationDraft.requestKey=notificationRequestKey();}
                notificationSending=true;notificationError='';notificationResult='';updateNotificationComposer();
                const result=await request('notifications',{...body,requestKey:notificationDraft.requestKey});
                if(user?.id!==owner||notificationGeneration!==ownerGeneration) return;
                notificationDraft={...notificationDraft,title:'',body:'',requestKey:'',signature:''};
                notificationResult='Đã gửi tới '+result.recipientCount+' học sinh · '+result.audienceLabel+'.';
                try {payload=await request('notifications?page='+filter.page);} catch(error) {notificationError='Đã gửi thành công; chưa tải lại được danh sách: '+error.message;}
                notificationSending=false;draw();await previewNotifications(true);
            } catch(error) {
                if(user?.id!==owner||notificationGeneration!==ownerGeneration) return;
                notificationError=error.message;
            } finally {
                if(user?.id===owner&&notificationGeneration===ownerGeneration) {notificationSending=false;updateNotificationComposer();}
            }
        };
        previewNotifications();
    }

    function paymentReferrerMarkup(referrer,expanded=false) {
        if(!referrer) return '<span class="staff-note">Không có người giới thiệu</span>';
        const membership=referrer.membership==='VIP'?'Vip':referrer.membership;
        const status=referrer.supportConfirmedAt?'Đã được hỗ trợ nhận thưởng':{pending:'Chờ đủ điều kiện nhận thưởng',granted:'Đã thưởng VIP',customer_service:'Cần đối chiếu phần thưởng'}[referrer.rewardStatus]||'Chưa có trạng thái thưởng';
        const confirm=!expanded&&referrer.canConfirmSupport&&!referrer.supportConfirmedAt?button('confirm','confirm-referral-support','data-id="'+Number(referrer.referralId)+'" aria-label="Xác nhận hỗ trợ nhận thưởng cho '+esc(referrer.login)+'"','outline staff-referral-confirm'):'';
        return `<div class="staff-referrer-info"><div class="staff-referrer-heading"><b class="staff-referrer-login">${esc(referrer.login)}</b>${confirm}${badge(membership)}</div>${referrer.name?'<small>'+esc(referrer.name)+'</small>':''}<small class="staff-referral-state">${status}</small>${expanded&&referrer.supportConfirmedAt?'<small>Ngày xác nhận hỗ trợ: '+date(referrer.supportConfirmedAt)+'</small>':''}${expanded&&referrer.rewardGrantedAt?'<small>Ngày nhận thưởng: '+date(referrer.rewardGrantedAt)+'</small>':''}${expanded&&referrer.rewardVipExpiresAt?'<small>VIP sau nhận thưởng đến: '+date(referrer.rewardVipExpiresAt)+'</small>':''}</div>`;
    }

    function paymentsView() {
        const search=`<form class="staff-toolbar" id="staff-filter-form">${input('Mã đơn / học sinh','q',filter.q,'search','placeholder="Mã đơn, tên đăng nhập hoặc biệt danh…" maxlength="100"')}${input('Người giới thiệu','referrer',filter.referrer||'','search','placeholder="Tên đăng nhập hoặc biệt danh người giới thiệu…" maxlength="100"')}${submit('Tìm kiếm')}</form>`;
        return header('Đối soát thanh toán','Theo dõi thanh toán tự động và kiểm tra các khoản tiền cần đối soát.')+
            panel('Đơn thanh toán',search+'<p class="staff-note staff-payment-note">Loại tài khoản người giới thiệu là gói đang hiệu lực. Trạng thái thưởng được lấy từ hồ sơ giới thiệu.</p>'+(payload.rows?.length?table(['Mã đơn / học sinh','Người giới thiệu','Nội dung','Số tiền','Trạng thái','Thao tác'],payload.rows.map(row=>`<tr><td data-label="Mã đơn / học sinh"><b>${esc(row.reference)}</b><small><span class="staff-payer-login">${esc(row.login_identifier)}</span> · ${esc(row.full_name)}</small><small>${date(row.created_at)}</small></td><td data-label="Người giới thiệu">${paymentReferrerMarkup(row.referrer)}</td><td data-label="Nội dung">${row.fee_id?esc(row.class_name)+' · '+esc(row.month):'VIP một tháng'}</td><td data-label="Số tiền"><b>${money(row.amount)}</b></td><td data-label="Trạng thái">${row.fee_id&&row.status==='paid'?'<span class="staff-badge">Đã hoàn thành</span>':badge(row.status)}${row.paid_at?'<small>'+date(row.paid_at)+'</small>':''}</td><td data-label="Thao tác">${row.status==='pending'?button('Đối soát','confirm-payment','data-id="'+row.id+'"'):'Đã xử lý'}</td></tr>`)):empty('Không có đơn thanh toán phù hợp','Thử đổi mã đơn, tên học sinh hoặc người giới thiệu.'))+pagination(),'staff-payment-list')+panel('Giao dịch ngân hàng','<div id="staff-bank-receipts">'+receiptsMarkup()+'</div>','staff-receipt-list');
    }
    function receiptReason(row){
        const reasons={paid:'Đã xác nhận thanh toán',settled:'Đã xác nhận thanh toán',processed:'Đã xác nhận thanh toán',amount_mismatch:'Số tiền chưa khớp đơn',unknown_reference:'Chưa tìm thấy đơn theo mã',missing_reference:'Chưa nhận diện được mã thanh toán',ambiguous_reference:'Nội dung có nhiều mã thanh toán',order_cancelled:'Đơn đã hủy',cancelled_order:'Đơn đã hủy',order_paid:'Đơn đã được thanh toán trước đó',already_paid:'Đơn đã được thanh toán trước đó',duplicate_payment:'Có khoản chuyển khác cho đơn đã hoàn tất',wrong_account:'Tài khoản nhận chưa khớp',account_mismatch:'Tài khoản nhận chưa khớp',bank_mismatch:'Ngân hàng nhận chưa khớp',outgoing:'Giao dịch tiền ra',not_incoming:'Giao dịch tiền ra',fee_changed:'Học phí đã thay đổi',fee_paid:'Học phí đã được thanh toán',account_inactive:'Tài khoản học sinh không hoạt động',invalid_owner:'Chủ tài khoản và học phí chưa khớp',legacy_unconfigured:'Đơn cũ chưa đủ thông tin ngân hàng để tự xác nhận'};
        return row.reasonLabel||reasons[row.reason]||(row.status==='processed'?'Đã xác nhận thanh toán':row.status==='ignored'?'Không dùng để xác nhận thanh toán':'Cần kiểm tra thông tin giao dịch và đơn thanh toán');
    }
    function receiptsMarkup(){
        const pages=Math.max(1,Math.ceil(receipts.total/receipts.pageSize));
        const toolbar=`<form class="staff-toolbar" id="staff-receipts-filter">${input('Mã thanh toán / giao dịch','q',receipts.q,'search','maxlength="100" placeholder="Tìm mã thanh toán hoặc mã giao dịch…"')}${select('Trạng thái','status',[['all','Tất cả'],['review','Cần đối soát'],['processed','Đã xác nhận'],['ignored','Không dùng thanh toán']],receipts.status)}${submit('Lọc giao dịch')}${button('Cập nhật','receipts-reload',receipts.loading?'disabled':'')}</form>`;
        const rows=receipts.rows||[];
        const list=rows.length?table(['Giao dịch / thời điểm','Mã thanh toán','Số tiền / tài khoản nhận','Kết quả'],rows.map(row=>`<tr><td data-label="Giao dịch / thời điểm"><b>${esc(row.transaction_id)}</b><small>${date(row.transaction_at||row.received_at)}</small>${row.bank_reference?'<small>Tham chiếu ngân hàng: '+esc(row.bank_reference)+'</small>':''}</td><td data-label="Mã thanh toán"><b>${esc(row.reference||'Chưa có mã')}</b>${row.order_id?'<small>Đơn #'+Number(row.order_id)+'</small>':''}</td><td data-label="Số tiền / tài khoản nhận"><b>${money(row.amount)}</b><small>${esc(row.bank)} · ${esc(row.bank_account)}</small></td><td data-label="Kết quả"><span class="staff-badge ${row.status==='review'?'warm':row.status==='ignored'?'muted':''}">${{processed:'Đã xác nhận',review:'Cần đối soát',ignored:'Không dùng thanh toán'}[row.status]||'Cần kiểm tra'}</span><p class="staff-receipt-reason">${esc(receiptReason(row))}</p></td></tr>`)):empty(receipts.loading?'Đang tải giao dịch…':'Chưa có giao dịch phù hợp','Các giao dịch nhận được sẽ xuất hiện ở đây.');
        return `<p class="staff-note">${receipts.automationEnabled?'Đang bật xác nhận thanh toán tự động.':'Xác nhận tự động đang chờ cấu hình hoặc chưa bật.'} Các khoản cần đối soát chưa được dùng để cộng quyền học tự động.</p>${toolbar}<p class="staff-error" role="alert" ${receipts.error?'':'hidden'}>${esc(receipts.error)}</p>${receipts.loading?'<p role="status">Đang cập nhật…</p>':''}${list}<nav class="staff-receipt-pagination" aria-label="Trang giao dịch ngân hàng"><span>${receipts.total} giao dịch · Trang ${receipts.page} / ${pages}</span><div class="staff-actions">${button('Trang trước','receipts-previous',receipts.page<=1||receipts.loading?'disabled':'')}${button('Trang sau','receipts-next',receipts.page>=pages||receipts.loading?'disabled':'')}</div></nav>`;
    }
    function updateReceipts(){
        const target=document.querySelector('#staff-bank-receipts');if(!target)return;
        const position={x:scrollX,y:scrollY},focused=target.contains(document.activeElement)?document.activeElement:null;
        const action=focused?.dataset.staff;
        target.innerHTML=receiptsMarkup();bindReceipts();
        if(action)target.querySelector('[data-staff="'+action+'"]')?.focus({preventScroll:true});
        window.scrollTo({left:position.x,top:position.y,behavior:'instant'});
    }
    async function loadReceipts({render=true}={}){
        if(!user||user.role!=='admin'||tab!=='payments')return;
        if(receipts.owner!==user.id)receipts={owner:user.id,page:1,status:'all',q:'',rows:null,total:0,pageSize:25,automationEnabled:false,error:'',loading:false,ticket:receipts.ticket+1};
        const owner=user.id,session=csrf,ticket=++receipts.ticket,view=generation;
        receipts.loading=true;receipts.error='';if(render)updateReceipts();
        try{
            const result=await request('payment-receipts?'+new URLSearchParams({page:receipts.page,status:receipts.status,q:receipts.q}));
            if(owner!==user?.id||session!==csrf||ticket!==receipts.ticket||view!==generation||tab!=='payments')return;
            Object.assign(receipts,{rows:result.rows,total:result.total,page:result.page,pageSize:result.pageSize||25,automationEnabled:Boolean(result.automationEnabled)});
        }catch(error){if(owner===user?.id&&session===csrf&&ticket===receipts.ticket&&view===generation)receipts.error='Chưa tải được giao dịch ngân hàng. '+error.message;}
        finally{if(owner===user?.id&&session===csrf&&ticket===receipts.ticket&&view===generation){receipts.loading=false;if(render)updateReceipts();}}
    }
    function bindReceipts(){
        const form=document.querySelector('#staff-receipts-filter');if(!form)return;
        form.onsubmit=async event=>{event.preventDefault();if(receipts.loading)return;const data=new FormData(form);receipts.q=String(data.get('q')||'');receipts.status=String(data.get('status')||'all');receipts.page=1;await loadReceipts();};
    }

    const admissionStates=[['new','Mới đăng ký'],['contacted','Đã liên hệ'],['scheduled','Đã hẹn kiểm tra'],['completed','Đã kiểm tra'],['closed','Đã đóng']];
    function admissionsView() {
        return header('Đăng ký đầu vào','Thông tin phụ huynh gửi từ khảo sát kiểm tra đầu vào. Chỉ quản trị viên được xem.')+
            panel('Danh sách đăng ký',searchForm()+(payload.rows?.length?table(['Mã / thời điểm','Học sinh','Phụ huynh / liên hệ','Trạng thái',''],payload.rows.map(row=>`<tr><td><b>${esc(row.reference)}</b><small>${date(row.created_at)}</small></td><td><b>${esc(row.student_name)}</b><small>Lớp ${row.grade} · ${esc(row.details.city)}</small></td><td>${esc(row.parent_name)}<small>${esc(row.phone)} · ${esc(row.details.contact)}</small></td><td>${esc(admissionStates.find(([key])=>key===row.status)?.[1]||row.status)}</td><td>${button('Xem / cập nhật','open-admission','data-id="'+row.id+'"')}</td></tr>`)):empty('Chưa có đăng ký phù hợp'))+pagination());
    }
    function admissionForm(row) {
        const fields=[['parentName','Phụ huynh'],['phone','Điện thoại'],['email','Email'],['contact','Liên hệ qua'],['studentName','Học sinh'],['grade','Khối lớp'],['school','Trường'],['city','Tỉnh/thành'],['goal','Mục tiêu'],['level','Khả năng hiện tại'],['schedule','Khung giờ mong muốn'],['notes','Chia sẻ thêm']];
        openForm('Đăng ký '+esc(row.reference),`<dl class="admission-details">${fields.map(([key,label])=>`<div><dt>${label}</dt><dd>${esc(row.details[key]||'Chưa cung cấp')}</dd></div>`).join('')}</dl><p class="staff-note">Phụ huynh đã đồng ý lưu thông tin và liên hệ tư vấn · ${date(row.created_at)}.</p>${select('Tình trạng xử lý','status',admissionStates,row.status)}${text('Ghi chú tư vấn (nội bộ)','note',row.admin_note)}`,
            async data=>{await request('admissions/'+row.id,{status:data.get('status'),note:data.get('note'),revision:row.revision});});
    }

    function settingsView() {
        const cfg=payload.settings || {};
        const flags=[['registration_open','Đăng ký tài khoản mới'],['learning_open','Học online'],['practice_open','Tạo đề luyện tập'],['arena_open','Tạo và ghép trận đấu trí'],['leaderboard_open','Bảng xếp hạng']];
        return header('Cấu hình hệ thống','Thay đổi có hiệu lực cho các yêu cầu tiếp theo và được ghi vào nhật ký.')+
            `<form id="staff-settings-form"><div class="staff-grid-two">${panel('Trạng thái chức năng',`<div class="staff-switches">${flags.map(([key,title])=>`<label><span>${title}</span><input type="checkbox" name="${key}" ${cfg[key]?'checked':''}><i aria-hidden="true"></i></label>`).join('')}</div>`)}
            ${panel('Hạn mức Free mỗi ngày',`<div class="staff-form-grid">${[['content','Luyện theo nội dung'],['combined','Đề tổng hợp'],['human','Đấu với người'],['bot','Đấu với bot']].map(([key,label])=>input(label,key,cfg.free_limits?.[key]??0,'number','required min="0" max="100"')).join('')}</div><p class="staff-note">Tính theo ngày Việt Nam. VIP và SVip giữ quyền không giới hạn. Đề và trận đang làm vẫn có thể hoàn thành.</p>`)}</div><div class="staff-form-footer">${submit('Lưu cấu hình')}</div></form>`;
    }

    function auditView() {
        const entities={admission:'Đăng ký đầu vào',class:'Lớp học',enrollment:'Ghi danh',session:'Buổi học',assignment:'Bài tập',class_records:'Điểm danh / nhận xét / điểm',class_fee:'Học phí',class_tuition:'Tính học phí',notification_broadcast:'Thông báo',account:'Học sinh',staff:'Nhân sự',topic:'Chuyên đề',lesson:'Bài học',question:'Câu hỏi',payment:'Thanh toán',referral_reward:'Thưởng giới thiệu',settings:'Cấu hình'};
        return header('Nhật ký thay đổi','Theo dõi ai đã cập nhật dữ liệu và thời điểm thực hiện.')+
            panel('Hoạt động quản trị',(payload.rows?.length?table(['Thời điểm','Người thực hiện','Đối tượng','Nội dung'],payload.rows.map(row=>`<tr><td>${date(row.created_at)}</td><td>${esc(row.full_name)}</td><td>${esc(entities[row.entity]||row.entity)} #${esc(row.entity_id)}</td><td>${esc(row.summary)}</td></tr>`)):empty('Chưa có thay đổi'))+pagination());
    }

    function body() {
        if(!user) return '';
        if(loadError) return header('Chưa đọc được dữ liệu',esc(loadError),button('Thử lại','reload'));
        if(loading) return header(mode==='admin'?'Quản trị hệ thống':'Không gian giáo viên','Đang đọc dữ liệu…')+panel('Đang tải','<div class="staff-loading" role="status">Đang kết nối dữ liệu.</div>');
        if(detail) return classView();
        if(tab==='notifications') return notificationsView();
        if(mode==='teacher' || tab==='overview') return overview();
        return ({classes:classView,content:contentView,accounts:accountsView,users:usersView,payments:paymentsView,admissions:admissionsView,settings:settingsView,audit:auditView}[tab]||overview)();
    }

    function render(route) {
        mode=route;
        return shell(body());
    }

    function draw() {
        const root=document.querySelector('#app');
        if(!root || !document.body.classList.contains('staff-mode')) return;
        root.innerHTML=render(mode);
        host.passwordFields?.(root);
        bind();
    }

    async function loadTab() {
        const ticket=++generation;
        loading=true;loadError='';draw();
        try {
            if(detail && classId) {
                const result=await request('classes/'+classId);
                if(ticket!==generation) return;
                detail=result;
            } else if((mode==='teacher' && tab!=='notifications') || tab==='classes') {
                const result=await request('classes');
                if(ticket!==generation) return;
                classList=result.classes;teachers=result.teachers;
            } else {
                const query=new URLSearchParams({...filter,...(tab==='content'?{kind:topicKind}:{})});
                let result=await request(tab+(tab==='overview'||tab==='users'||tab==='settings'?'':'?'+query));
                if(ticket!==generation) return;
                if(tab==='accounts' && !result.rows?.length && filter.page>1) {
                    filter.page=Math.max(1,Math.ceil((result.total||0)/(result.pageSize||25)));
                    result=await request('accounts?'+new URLSearchParams(filter));
                    if(ticket!==generation) return;
                }
                payload=result;
                if(tab==='payments')await loadReceipts({render:false});
                if(tab==='notifications') {syncNotificationDraft();notificationPreview={target:'',count:null,label:'',pending:false,error:'',ticket:notificationPreview.ticket+1};}
            }
        } catch(error) {
            if(ticket!==generation) return;
            loadError=error.message;
        } finally {
            if(ticket===generation) {loading=false;draw();}
        }
    }

    async function changeTab(value) {
        receipts.ticket++;
        tab=value;detail=null;classId=null;filter={q:'',grade:'0',page:1};
        history.replaceState(null,'','#'+value);
        await loadTab();
    }

    function message(value) {
        host.toast(value);
    }

    function openForm(title,html,onSave,label='Lưu thay đổi') {
        host.showModal(`<div class="staff-dialog"><h2 class="modal-title">${title}</h2><form id="staff-modal-form">${html}<p class="staff-error" id="staff-form-error" role="alert"></p><div class="staff-form-footer">${submit(label)}${button('Đóng','close-modal')}</div></form></div>`);
        document.querySelector('#modal-body').onclick=handleClick;
        const form=document.querySelector('#staff-modal-form');
        form.onsubmit=async event=>{
            event.preventDefault();
            const control=form.querySelector('button[type=submit]');
            control.disabled=true;
            try {
                await onSave(new FormData(form),form);
                document.querySelector('#modal').close();
                await loadTab();
                message('Đã lưu thay đổi.');
            } catch(error) {
                document.querySelector('#staff-form-error').textContent=error.message;
            } finally {control.disabled=false;}
        };
        form.querySelector('input,select,textarea')?.focus();
    }

    async function classForm(row=null) {
        if(!teachers.length) teachers=(await request('classes')).teachers;
        if(!teachers.length) {await changeTab('users');message('Cấp tài khoản hoặc hồ sơ giáo viên trước khi tạo lớp.');return;}
        modalContext=row;
        openForm(row?'Chỉnh sửa lớp Zoom':'Tạo lớp Zoom',`<div class="staff-form-grid">${input('Tên lớp','name',row?.name||'','text','required maxlength="120"')}
            ${select('Khối','grade',gradeOptions,row?.grade_id||5)}${select('Giáo viên phụ trách','teacherId',teachers.map(teacher=>[teacher.id,teacher.full_name]),row?.teacher_id||teachers[0].id)}
            ${select('Trạng thái','status',[['active','Đang hoạt động'],['closed','Kết thúc lớp']],row?.status||'active')}</div>
            ${input('Học phí mỗi buổi · đồng','sessionFee',row?.session_fee??'','number','required min="0" max="1000000000" step="1"')}
            ${input('Lịch học định kỳ','schedule',row?.schedule||'','text','placeholder="Thứ, giờ học…" maxlength="3000"')}
            ${input('Liên kết Zoom / Meet','meetingUrl',row?.meeting_ref||'','url','placeholder="https://…"')}
            ${text('Nội dung / lộ trình lớp','curriculum',row?.curriculum||'')}
            <p class="staff-note">Kết thúc lớp sẽ dừng các ghi danh hiện tại. Lịch học và điểm đã lưu được giữ lại.</p>`,
            async values=>{
                const result=await request('classes',{id:row?.id,revision:row?.revision,name:values.get('name'),grade:Number(values.get('grade')),
                    teacherId:Number(values.get('teacherId')),status:values.get('status'),schedule:values.get('schedule'),
                    meetingUrl:values.get('meetingUrl'),curriculum:values.get('curriculum'),sessionFee:Number(values.get('sessionFee'))});
                if(detail) {detail=result;classId=result.class.id;}
            },row?'Lưu lớp':'Tạo lớp');
    }

    function sessionForm(row=null) {
        openForm(row?'Chỉnh sửa buổi học':'Thêm buổi học',`${input('Tên buổi học','title',row?.title||'','text','required maxlength="180"')}
            ${input('Ngày giờ học · giờ Việt Nam','startsAt',localTime(row?.starts_at),'datetime-local','required')}
            ${input('Liên kết video xem lại','videoUrl',row?.video_url||'','url','placeholder="https://…/video.mp4"')}
            ${text('Nhận xét buổi học','comment',row?.teacher_comment||'','maxlength="10000"')}`,
            async values=>{
                const result=await request('classes/'+classId+'/sessions',{id:row?.id,revision:row?.revision,title:values.get('title'),
                    startsAt:values.get('startsAt')+':00+07:00',videoUrl:values.get('videoUrl'),exampleText:values.get('exampleText'),exampleSteps:values.get('exampleSteps'),comment:values.get('comment')});
                detail=result;
            });
    }

    function assignmentsModal(identity) {
        const item=detail.sessions.find(session=>session.id===identity);
        modalContext=item;
        host.showModal(`<div class="staff-dialog"><h2 class="modal-title">Bài tập · ${esc(item.title)}</h2>
            ${item.assignments.length?table(['Bài tập','Loại',''],item.assignments.map(assignment=>`<tr><td>${esc(assignment.title)}</td><td>${esc(assignment.kind)}</td><td>${button('Sửa','edit-assignment','data-id="'+assignment.id+'"')}</td></tr>`)):empty('Chưa có bài tập')}
            <div class="staff-actions">${button('Thêm bài tập','new-assignment','','dark')}${button('Đóng','close-modal')}</div></div>`);
        document.querySelector('#modal-body').onclick=handleClick;
    }

    function assignmentForm(row=null) {
        const item=modalContext;
        openForm(row?'Chỉnh sửa bài tập':'Thêm bài tập',`${input('Tên bài tập','title',row?.title||'','text','required maxlength="180"')}
            ${select('Loại bài','kind',[['Bài tập về nhà','Bài tập về nhà'],['Kiểm tra','Kiểm tra'],['Luyện tập','Luyện tập']],row?.kind||'Bài tập về nhà')}
            ${input('Liên kết tài liệu','documentUrl',row?.document_url||'','url','placeholder="https://…"')}`,
            async values=>{detail=await request('sessions/'+item.id+'/assignments',{id:row?.id,revision:row?.revision,
                title:values.get('title'),kind:values.get('kind'),documentUrl:values.get('documentUrl')});});
    }

    async function enrollmentForm(search='') {
        const result=await request('accounts?'+new URLSearchParams({q:search,page:1}));
        const rows=result.rows.filter(row=>row.status==='active');
        openForm('Ghi danh học sinh',`<div class="staff-toolbar">${input('Tìm theo tên hoặc tài khoản','enrollmentSearch',search,'search')}
            ${button('Tìm học sinh','enroll-search')}</div>
            ${select('Học sinh','studentId',rows.length?rows.map(row=>[row.student_id,row.full_name+' · '+row.login_identifier+' · Khối '+row.grade_level]):[['','Không có học sinh phù hợp']])}
            <p class="staff-note">Ghi danh sẽ cấp quyền nội bộ trong thời gian theo học lớp.</p>`,
            async values=>{detail=await request('classes/'+classId+'/enroll',{action:'enroll',studentId:Number(values.get('studentId'))});},'Ghi danh');
    }

    function feeForm() {
        if(!detail.students.length) {message('Ghi danh học sinh trước khi lập học phí.');return;}
        openForm('Lập học phí theo tháng',`${select('Học sinh','studentId',detail.students.map(student=>[student.id,student.full_name]))}
            <div class="staff-form-grid">${input('Tháng','month','','month','required')}${input('Số tiền · đồng','amount','','number','required min="0" max="1000000000" step="1"')}</div>`,
            async values=>{detail=await request('classes/'+classId+'/fees',{revision:detail.class.revision,studentId:Number(values.get('studentId')),
                month:values.get('month'),amount:Number(values.get('amount'))});});
    }

    const tuitionStatus=value=>({charged:'Tính phí',free:'Miễn phí',absent:'Vắng',pending:'Chưa điểm danh'}[value]||'Chưa điểm danh');
    const tuitionMark=value=>({charged:'P',free:'M',absent:'V',pending:'?'}[value]||'?');

    function tuitionLegend() {
        return `<ul class="staff-tuition-legend" aria-label="Chú thích điểm danh">${['charged','free','absent','pending'].map(status=>`<li><span class="staff-tuition-mark ${status}" aria-hidden="true">${tuitionMark(status)}</span>${tuitionStatus(status)}</li>`).join('')}</ul>`;
    }

    function tuitionCalendar(month,sessions) {
        const first=new Date(month+'-01T00:00:00Z'),end=new Date(first);end.setUTCMonth(end.getUTCMonth()+1);end.setUTCDate(0);
        const offset=(first.getUTCDay()+6)%7,days=end.getUTCDate(),cells=[];
        for(let index=0;index<Math.ceil((offset+days)/7)*7;index++) {
            const day=index-offset+1;
            if(day<1||day>days) {cells.push('<td class="staff-tuition-empty" aria-hidden="true"></td>');continue;}
            const dateKey=month+'-'+String(day).padStart(2,'0'),lessons=sessions.filter(item=>item.date===dateKey),counts={};
            for(const item of lessons) {const status=['charged','free','absent'].includes(item.status)?item.status:'pending';counts[status]=(counts[status]||0)+1;}
            const marks=Object.entries(counts).map(([status,count])=>`<span class="staff-tuition-mark ${status}" title="${tuitionStatus(status)}: ${count} buổi">${tuitionMark(status)}${count}</span>`).join('');
            cells.push(`<td data-tuition-date="${dateKey}" ${lessons.length?'class="has-sessions"':''}><div><b>${day}</b>${lessons.length?`<span class="staff-tuition-day-marks">${marks}</span><small>${lessons.length} buổi</small>`:''}</div></td>`);
        }
        return `<table class="staff-tuition-calendar" aria-label="Lịch điểm danh tháng ${esc(month)}, chỉ xem"><thead><tr>${['T2','T3','T4','T5','T6','T7','CN'].map(day=>'<th scope="col">'+day+'</th>').join('')}</tr></thead><tbody>${Array.from({length:cells.length/7},(_,index)=>'<tr>'+cells.slice(index*7,index*7+7).join('')+'</tr>').join('')}</tbody></table>`;
    }

    function tuitionStudentView() {
        const invoice=tuition.invoice,student=tuition.selected,fee=invoice?.fee;
        const sessions=invoice?.sessions||student?.sessions||[],month=fee?.month||tuition.preview.month;
        const name=fee?.full_name||student?.fullName||'Học sinh';
        const charged=fee?.charged_count??student?.chargedCount??0,rate=fee?.session_fee??tuition.preview?.sessionFee;
        const amount=fee?.amount??student?.amount??0;
        const isCalculated=invoice?fee.source==='calculated':true;
        return `${invoice?'':button('← Quay lại bảng tính','tuition-back')}<h3 class="staff-tuition-student-name">${esc(name)}</h3>
            <div class="staff-tuition-total"><span>Học phí tháng ${esc(month)}</span><strong>${money(amount)}</strong><small>${student?.locked?'Số tiền đã lưu · Không thay đổi':isCalculated?charged+' buổi tính phí × '+money(rate):'Học phí nhập thủ công'}</small></div>
            ${amount===0?'<p class="staff-tuition-no-charge">Không phát sinh học phí</p>':''}
            <p class="staff-note">${invoice?(isCalculated?'Lịch đã lưu cùng bảng học phí. Thay đổi điểm danh sau đó không thay đổi lịch này.':'Học phí nhập thủ công; lịch dưới đây hiển thị điểm danh hiện tại.'):student?.locked?'Điểm danh dưới đây chỉ để tham khảo. Khoản học phí đã khóa được giữ nguyên khi lưu bảng tính.':'Lịch xem trước, chưa lưu học phí. Mỗi buổi có điểm danh Tính phí được tính riêng, kể cả nhiều buổi trong cùng ngày.'}</p>
            ${student?.locked||fee?.paid_at?'<p class="staff-tuition-lock">'+(student?.lockedReason==='inactive'?'Hồ sơ không còn hoạt động. Giữ nguyên học phí đã lưu.':'Đã hoàn thành thanh toán. Giữ nguyên số tiền đã lưu.')+'</p>':''}
            ${tuitionLegend()}${tuitionCalendar(month,sessions)}
            <h3 class="staff-tuition-sessions-title">Chi tiết các buổi học</h3><div class="staff-tuition-sessions">${sessions.length?sessions.map(item=>{
                const status=['charged','free','absent'].includes(item.status)?item.status:'pending';
                return `<article><div><b>${esc(item.title)}</b><time datetime="${esc(item.startsAt)}">${date(item.startsAt)}</time></div><span class="staff-tuition-status ${status}">${tuitionStatus(status)}</span></article>`;
            }).join(''):'<p>Không có buổi học thuộc tháng này.</p>'}</div>`;
    }

    function renderTuitionModal() {
        const preview=tuition.preview,rate=detail?.class.session_fee,unset=rate===null||rate===undefined;
        let html;
        if(tuition.selected||tuition.invoice) html=tuitionStudentView();
        else html=`<p>${esc(detail?.class.name||'')}</p><form id="staff-tuition-month-form" class="staff-toolbar">${input('Tháng cần tính','month',tuition.month,'month','required min="0001-01" max="9999-12" '+(tuition.busy?'disabled':''))}<button class="btn outline" id="staff-tuition-preview" type="submit" ${tuition.busy||unset?'disabled':''}>${tuition.busy?'Đang xử lý…':'Xem trước'}</button></form>
            ${unset?`<p class="staff-tuition-lock">Lớp chưa thiết lập học phí mỗi buổi. ${user.role==='admin'?'Nhập mức học phí trước khi tính.':'Liên hệ admin để cập nhật mức học phí của lớp.'}</p>${user.role==='admin'?button('Thiết lập học phí mỗi buổi','tuition-set-rate'):''}`:`<p class="staff-note">Mỗi buổi <b>${money(rate)}</b>. Chỉ buổi có điểm danh Tính phí được thu tiền. Xem trước chưa lưu học phí hoặc gửi thông báo.</p>`}
            ${preview?`<div class="staff-tuition-total"><span>Tổng học phí tháng ${esc(preview.month)}</span><strong>${money(preview.totals.totalAmount)}</strong><small>${preview.rows.length} học sinh · ${preview.totals.chargedCount} buổi tính phí${preview.totals.paidLocked?' · '+preview.totals.paidLocked+' khoản đã thanh toán giữ nguyên':''}</small></div>
            <div class="staff-tuition-roster">${preview.rows.length?preview.rows.map(row=>`<article><div><button type="button" class="staff-tuition-student-link" data-staff="tuition-student" data-id="${row.studentId}" ${tuition.busy?'disabled':''}>${esc(row.fullName)}</button><small>${row.locked?'Học phí đã lưu · Giữ nguyên':row.chargedCount+' buổi tính phí × '+money(preview.sessionFee)}${row.historical?' · Đã rời lớp':''}</small><small>${row.freeCount} miễn phí · ${row.absentCount} vắng · ${row.pendingCount} chưa điểm danh</small>${row.locked?'<span class="staff-tuition-lock-label">'+(row.lockedReason==='inactive'?'Hồ sơ ngừng hoạt động · giữ nguyên':'Đã thanh toán · giữ nguyên')+'</span>':row.source==='manual'&&row.existingAmount!==null?'<small class="staff-tuition-replace">Sẽ thay số nhập thủ công '+money(row.existingAmount)+'</small>':''}</div><strong>${money(row.amount)}</strong></article>`).join(''):empty('Chưa có học sinh trong tháng này')}</div>
            <p class="staff-note">Bấm tên học sinh để xem lịch điểm danh. Lưu tất cả sẽ cập nhật học phí chưa thanh toán theo bảng tính này và gửi thông báo cho học sinh có thay đổi. Khoản đã thanh toán được giữ nguyên.</p>`:''}
            <p id="staff-tuition-error" class="staff-error" role="alert">${esc(tuition.error)}</p>
            ${tuition.stale?'<p class="staff-tuition-lock">Dữ liệu đã thay đổi. Bấm Xem trước để kiểm tra lại trước khi lưu.</p>':''}
            ${preview?`<div class="staff-form-footer"><button class="btn dark" type="button" data-staff="tuition-save" ${tuition.busy||tuition.stale||!preview.rows.length?'disabled':''}>${tuition.busy?'Đang lưu…':'Lưu học phí & gửi thông báo'}</button></div>`:''}`;
        host.showModal(`<div class="staff-dialog staff-tuition-dialog"><h2 class="modal-title">${tuition.invoice?'Chi tiết học phí':tuition.selected?'Lịch điểm danh học sinh':'Tính học phí'}</h2>${html}<div class="staff-form-footer">${button('Đóng','close-modal',tuition.busy?'disabled':'')}</div></div>`);
        document.querySelector('#modal-body').onclick=handleClick;
        const form=document.querySelector('#staff-tuition-month-form');
        document.querySelector('#modal').scrollTop=0;
        if(form) {
            form.onsubmit=event=>{event.preventDefault();previewTuition();};
            form.elements.month.onchange=()=>{tuition.month=form.elements.month.value;tuition.preview=null;tuition.selected=null;tuition.error='';tuition.stale=false;tuition.requestKey='';tuition.signature='';renderTuitionModal();document.querySelector('#staff-tuition-month-form [name=month]')?.focus();};
        }
    }

    function openTuition() {
        const keep=tuition.owner===user.id&&tuition.classId===classId;
        tuition={owner:user.id,classId,month:keep?tuition.month:localTime(new Date()).slice(0,7),preview:null,selected:null,invoice:null,busy:false,stale:false,error:'',requestKey:'',signature:'',ticket:tuition.ticket+1};
        renderTuitionModal();document.querySelector('#staff-tuition-month-form [name=month]')?.focus();
    }

    async function previewTuition() {
        if(tuition.busy) return;
        const form=document.querySelector('#staff-tuition-month-form');if(!form?.reportValidity()) return;
        tuition.month=form.elements.month.value;tuition.busy=true;tuition.error='';tuition.stale=false;
        const ticket=++tuition.ticket,owner=user.id;
        renderTuitionModal();
        try {
            const result=await request('classes/'+tuition.classId+'/fees/preview',{month:tuition.month});
            if(user?.id!==owner||tuition.ticket!==ticket) return;
            tuition.preview=result;tuition.selected=null;
        } catch(error) {if(user?.id===owner&&tuition.ticket===ticket)tuition.error=error.message;}
        finally {if(user?.id===owner&&tuition.ticket===ticket){tuition.busy=false;if(document.querySelector('#modal').open)renderTuitionModal();}}
    }

    async function saveTuition() {
        if(tuition.busy||tuition.stale||!tuition.preview) return;
        const body={month:tuition.preview.month,previewToken:tuition.preview.previewToken},signature=JSON.stringify({classId:tuition.classId,...body}),owner=user.id,ticket=tuition.ticket;
        try {
            if(tuition.signature!==signature||!tuition.requestKey){tuition.signature=signature;tuition.requestKey=notificationRequestKey();}
            tuition.busy=true;tuition.error='';renderTuitionModal();
            const result=await request('classes/'+tuition.classId+'/fees/calculate',{...body,requestKey:tuition.requestKey});
            if(user?.id!==owner||tuition.ticket!==ticket) return;
            detail=result;tuition.preview=null;tuition.selected=null;tuition.requestKey='';tuition.signature='';
            document.querySelector('#modal').close();draw();
            message('Đã lưu học phí · '+result.calculation.notificationsSent+' thông báo cho học sinh.');
        } catch(error) {
            if(user?.id!==owner||tuition.ticket!==ticket) return;
            tuition.error=error.message;if(error.status===409)tuition.stale=true;
        } finally {if(user?.id===owner&&tuition.ticket===ticket){tuition.busy=false;if(document.querySelector('#modal').open&&tuition.preview)renderTuitionModal();}}
    }

    async function openSavedFee(identity) {
        tuition={owner:user.id,classId,month:'',preview:null,selected:null,invoice:null,busy:true,stale:false,error:'',requestKey:'',signature:'',ticket:tuition.ticket+1};
        const ticket=tuition.ticket,owner=user.id;
        host.showModal('<div class="staff-dialog"><h2 class="modal-title">Chi tiết học phí</h2><p role="status">Đang tải học phí…</p></div>');
        try {
            const result=await request('classes/'+classId+'/fees/'+identity);
            if(user?.id!==owner||tuition.ticket!==ticket) return;
            tuition.invoice=result;tuition.busy=false;if(document.querySelector('#modal').open)renderTuitionModal();
        } catch(error) {if(user?.id===owner&&tuition.ticket===ticket){tuition.busy=false;host.showModal('<div class="staff-dialog"><h2 class="modal-title">Chưa đọc được học phí</h2><p class="staff-error" role="alert">'+esc(error.message)+'</p>'+button('Đóng','close-modal')+'</div>');document.querySelector('#modal-body').onclick=handleClick;}}
    }

    async function userForm(row=null) {
        const result=await request('classes');
        teachers=result.teachers;
        openForm(row?'Cập nhật nhân sự':'Cấp tài khoản nhân sự',`<div class="staff-form-grid">
            ${input('Họ tên','fullName',row?.full_name||'','text','required maxlength="100"')}
            ${input('Tên đăng nhập','login',row?.login||'','text','required minlength="3" maxlength="100" autocomplete="off"')}
            ${select('Vai trò','role',[['teacher','Giáo viên'],['admin','Quản trị viên']],row?.role||'teacher')}
            ${select('Trạng thái','status',[['active','Đang hoạt động'],['disabled','Khóa truy cập']],row?.status||'active')}</div>
            ${select('Hồ sơ giáo viên khi cấp vai trò Giáo viên','teacherId',[[0,'Tạo hồ sơ giáo viên mới'],...teachers.map(teacher=>[teacher.id,teacher.full_name])],row?.teacher_id||0)}
            ${input(row?'Mật khẩu mới · để trống để giữ mật khẩu hiện tại':'Mật khẩu ban đầu','password','','password',(row?'':'required ')+'minlength="6" maxlength="128" autocomplete="new-password"')}
            <p class="staff-note">Giáo viên chỉ được mở lớp đã phân công. Đổi mật khẩu hoặc khóa truy cập sẽ kết thúc các phiên đăng nhập của nhân sự đó.</p>`,
            async values=>{await request('users',{id:row?.id,revision:row?.revision,fullName:values.get('fullName'),login:values.get('login'),
                role:values.get('role'),status:values.get('status'),teacherId:Number(values.get('teacherId')),password:values.get('password')});
                const session=await request('session');user=session.user||null;csrf=session.csrf||'';});
    }

    function accountForm(row=null) {
        const parts=Object.fromEntries(new Intl.DateTimeFormat('en-US',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'numeric'}).formatToParts(new Date()).map(part=>[part.type,part.value]));
        const year=Number(parts.year)-(Number(parts.month)<7?1:0);
        const mascots=(payload.mascots||[]).map(item=>[item.code,item.name]);
        if(!mascots.length) {message('Chưa tải được danh sách linh vật. Tải lại danh sách tài khoản rồi thử lại.');return;}
        const membership=row?.membership||'Free',initialExpiry=localTime(row?.membership_expires_at);
        openForm(row?'Chỉnh sửa tài khoản':'Thêm tài khoản học sinh',`<section class="staff-account-section"><h3>Thông tin học sinh</h3><div class="staff-form-grid">
            ${input('Biệt danh học sinh','name',row?.full_name||'','text','required minlength="2" maxlength="40" autocomplete="nickname"')}
            ${input('Tên đăng nhập','login',row?.login_identifier||'','text','required minlength="3" maxlength="100" autocomplete="off" autocapitalize="none" spellcheck="false"')}
            ${input('Năm sinh','birthYear',row?.birth_year||year-10,'number',`required min="${year-10}" max="${year-6}" step="1" aria-describedby="staff-grade-preview"`)}
            ${select('Trạng thái','status',[['active','Đang hoạt động'],['suspended','Tạm khóa']],row?.status||'active')}</div>
            <p id="staff-grade-preview" class="staff-grade-preview" role="status" aria-live="polite"></p>
            <p class="staff-note">Admin được sửa năm sinh để điều chỉnh khối theo mốc 01/07. Lịch sử học tập vẫn được giữ; học sinh cần đăng nhập lại khi thay đổi năm sinh.</p></section>
            <section class="staff-account-section"><h3>Quyền học</h3><div class="staff-form-grid">
            ${select('Loại tài khoản','membership',[['Free','Free'],['VIP','VIP'],['SVip','SVip']],membership)}
            ${input('Hạn quyền học · giờ Việt Nam','membershipExpiresAt',initialExpiry,'datetime-local','aria-describedby="staff-membership-help"')}</div>
            <p id="staff-membership-help" class="staff-note" aria-live="polite"></p>
            <p class="staff-note">Đây là cấp quyền thủ công, không ghi nhận thanh toán hoặc thưởng giới thiệu. SVip cho quyền học nội bộ; ghi danh vào lớp được quản lý riêng tại Lớp Zoom.</p></section>
            <section class="staff-account-section"><h3>Linh vật & kinh nghiệm</h3><div class="staff-form-grid">
            ${select('Linh vật','mascot',mascots,row?.mascot||'sprout')}
            ${input('Điểm kinh nghiệm','points',row?.points??1000,'number','required min="1000" max="1000000000" step="1"')}</div></section>
            <section class="staff-account-section"><h3>Thông tin đăng nhập</h3>
            ${input(row?'Mật khẩu mới · để trống để giữ mật khẩu hiện tại':'Mật khẩu ban đầu','password','','password',(row?'':'required ')+'minlength="6" maxlength="128" autocomplete="new-password"')}
            <p class="staff-note">Một tài khoản dành cho một học sinh. Tên đăng nhập gồm ít nhất 3 chữ cái không dấu, số hoặc . _ @ + -. Đổi tên đăng nhập, đổi mật khẩu hoặc tạm khóa sẽ kết thúc các phiên đăng nhập của học sinh. Mã tài khoản, mã giới thiệu và lịch sử được hệ thống quản lý.</p></section>`,
            async values=>{
                const login=String(values.get('login')||'').trim().toLowerCase();
                const plan=values.get('membership'),expiry=String(values.get('membershipExpiresAt')||'');
                const expiryStamp=plan==='Free'||!expiry?null:row && plan===membership && expiry===initialExpiry?row.membership_expires_at:expiry+':00+07:00';
                const body={login,name:values.get('name'),password:values.get('password'),status:values.get('status'),birthYear:Number(values.get('birthYear')),
                    membership:plan,membershipExpiresAt:expiryStamp,mascot:values.get('mascot'),points:Number(values.get('points'))};
                if(row) body.revision=row.revision;
                await request(row?'accounts/'+row.id:'accounts',body);
                filter={q:login,grade:'0',status:'all',page:1};
            },row?'Lưu tài khoản':'Tạo tài khoản');
        const accountForm=document.querySelector('#staff-modal-form'),birth=accountForm.elements.birthYear,plan=accountForm.elements.membership,expiry=accountForm.elements.membershipExpiresAt;
        const updateGrade=()=>{
            const grade=year-Number(birth.value)-5;
            document.querySelector('#staff-grade-preview').textContent=birth.value && Number.isInteger(grade) && grade>=1 && grade<=5?'Khối học sau khi lưu: Khối '+grade+' · Năm học '+year+'–'+(year+1):'Nhập năm sinh từ '+(year-10)+' đến '+(year-6)+' để xếp khối 1–5.';
        };
        const updateMembership=()=>{
            expiry.disabled=plan.value==='Free';expiry.required=plan.value==='VIP';
            expiry.min=localTime(new Date());
            document.querySelector('#staff-membership-help').textContent=plan.value==='VIP'?'VIP cần hạn trong tương lai. Khi chọn VIP, hệ thống gợi ý thêm một tháng lịch.':plan.value==='SVip'?'Để trống hạn nếu cấp SVip không giới hạn thời gian; nếu đặt hạn, chọn một thời điểm trong tương lai.':'Free dùng hạn mức miễn phí và không có thời hạn quyền trả phí.';
        };
        birth.oninput=updateGrade;
        plan.onchange=()=>{
            if(plan.value==='VIP' && (!expiry.value || new Date(expiry.value+':00+07:00').getTime()<=Date.now())) {
                const next=new Date(Date.now()+7*3600000),day=next.getUTCDate();
                next.setUTCDate(1);next.setUTCMonth(next.getUTCMonth()+1);
                const lastDay=new Date(Date.UTC(next.getUTCFullYear(),next.getUTCMonth()+1,0)).getUTCDate();
                next.setUTCDate(Math.min(day,lastDay));expiry.value=next.toISOString().slice(0,16);
            }
            updateMembership();
        };
        updateGrade();updateMembership();
    }

    function deleteAccountForm(row) {
        openForm('Xóa tài khoản học sinh',`<p><b>${esc(row.full_name)}</b> · ${esc(row.login_identifier)}</p>
            <p class="staff-note">Tài khoản sẽ chuyển sang mục Đã xóa, ngừng đăng nhập và kết thúc ghi danh lớp hiện tại. Lịch sử học tập, điểm và thanh toán vẫn được giữ. Có thể khôi phục tài khoản từ bộ lọc Đã xóa.</p>
            ${input('Nhập lại tên đăng nhập để xác nhận xóa','confirmLogin','','text','required maxlength="100" autocomplete="off" autocapitalize="none" spellcheck="false"')}`,
            async values=>{
                const confirmLogin=String(values.get('confirmLogin')||'').trim();
                if(confirmLogin!==row.login_identifier) throw new Error('Tên đăng nhập xác nhận chưa khớp.');
                await request('accounts/'+row.id+'/delete',{revision:row.revision,confirmLogin});
            },'Xác nhận xóa');
        document.querySelector('#staff-modal-form button[type=submit]').classList.add('staff-danger');
    }

    function restoreAccountForm(row) {
        openForm('Khôi phục tài khoản',`<p><b>${esc(row.full_name)}</b> · ${esc(row.login_identifier)}</p>
            <p class="staff-note">Tài khoản trở lại danh sách ở trạng thái Tạm khóa. Chọn Mở lại sau khi kiểm tra thông tin. Ghi danh lớp đã kết thúc không tự khôi phục.</p>`,
            async()=>{await request('accounts/'+row.id+'/restore',{revision:row.revision});filter={q:row.login_identifier,grade:'0',status:'suspended',page:1};},'Khôi phục tài khoản');
    }

    function contentForm(row=null) {
        const kind=topicKind;
        const grade=row?.grade_id||Number(filter.grade)||5;
        const topicOptions=value=>(payload.topics||[]).filter(topic=>topic.grade_id===Number(value)).map(topic=>[topic.id,topic.title]);
        const base=select('Khối','grade',gradeOptions,grade);
        let fields;
        if(kind==='topics') fields=base+input('Tên chuyên đề','title',row?.title||'','text','required maxlength="180"')+text('Nội dung mở đầu','intro',row?.intro||'');
        else if(kind==='lessons') fields=`<div class="staff-form-grid">${base}${select('Chuyên đề','topicId',topicOptions(grade),row?.topic_id)}${select('Loại bài','kind',[['weekly','Bài theo tuần'],['topic','Bài theo chuyên đề']],row?.kind||'weekly')}${input('Tuần học','week',row?.week_no||1,'number','required min="1" max="53"')}</div>
            ${input('Tiêu đề bài giảng','title',row?.title||'','text','required maxlength="180"')}${text('Nội dung mở đầu / quy tắc','intro',row?.intro||'','required maxlength="20000"')}
            ${text('Đề bài ví dụ (tùy chọn)','exampleText',row?.exampleText||'','maxlength="10000"')}
            ${text('Lời giải ví dụ · mỗi dòng một bước','exampleSteps',Array.isArray(row?.exampleSteps)?row.exampleSteps.join('\n'):(row?.exampleSteps||''),'maxlength="20000"')}
            <p class="staff-note">Chỉ nhập ví dụ và lời giải đã biên soạn. Bỏ trống khi bài học chưa có ví dụ.</p>
            ${input('Liên kết video','videoUrl',row?.videoUrl||row?.video_ref||'','url','placeholder="https://…"')}
            ${select('Phát hành','status',[['draft','Lưu bản nháp'],['published','Phát hành cho học sinh']],row?.publication_status||'draft')}`;
        else fields=`<div class="staff-form-grid">${base}${select('Chuyên đề','topicId',topicOptions(grade),row?.topic_id)}${select('Mức độ','difficulty',[[1,'Cơ bản'],[2,'Nâng cao'],[3,'Khó'],[4,'Tư duy']],row?.difficulty||1)}${input('Tuần kiến thức','week',row?.curriculum_week||1,'number','required min="1" max="53"')}</div>
            ${text('Nội dung câu hỏi','prompt',row?.prompt||'','required maxlength="10000"')}
            <div class="staff-form-grid">${text('Lựa chọn · mỗi dòng một đáp án','options',row?.options?.join('\n')||'','required')}${input('Đáp án đúng · khớp một lựa chọn','answer',row?.answer||'','text','required maxlength="500"')}</div>
            ${text('Lời giải · mỗi dòng một bước','steps',row?.steps||'','required maxlength="20000"')}${text('Hướng dẫn tư duy','thinking',row?.thinking||'')}
            ${select('Trạng thái','status',[['draft','Lưu bản nháp'],['published','Phát hành phiên bản mới'],['retired','Ngừng phát hành câu hỏi']],row?.status||'draft')}
            <p class="staff-note">Lưu câu hỏi tạo một phiên bản mới. Các đề đã sinh giữ nội dung và lời giải của phiên bản trước.</p>`;
        openForm((row?'Chỉnh sửa ':'Thêm ')+({topics:'chuyên đề',lessons:'bài giảng',questions:'câu hỏi'}[kind]),fields,async(values,form)=>{
            const body={id:row?.id,revision:row?.revision,grade:Number(values.get('grade')||row?.grade_id),topicId:Number(values.get('topicId')||row?.topic_id),
                title:values.get('title'),intro:values.get('intro'),kind:values.get('kind'),week:Number(values.get('week')),videoUrl:values.get('videoUrl'),exampleText:values.get('exampleText'),exampleSteps:values.get('exampleSteps'),
                status:values.get('status'),difficulty:Number(values.get('difficulty')),prompt:values.get('prompt'),answer:values.get('answer'),
                options:String(values.get('options')||'').split('\n').map(value=>value.trim()).filter(Boolean),steps:values.get('steps'),thinking:values.get('thinking')};
            await request(kind,body);
        });
        const form=document.querySelector('#staff-modal-form');
        const gradeInput=form.elements.grade;
        if(row && ['topics','questions'].includes(kind)) gradeInput.disabled=true;
        if(row && kind==='questions') form.elements.topicId.disabled=true;
        gradeInput.onchange=()=>{if(form.elements.topicId)form.elements.topicId.innerHTML=topicOptions(gradeInput.value).map(([key,title])=>'<option value="'+key+'">'+esc(title)+'</option>').join('');};
    }

    function referralSupportForm(row) {
        const referrer=row?.referrer,owner=user?.id;
        if(!referrer?.canConfirmSupport||referrer.supportConfirmedAt)return;
        const dialog=document.querySelector('#modal');
        let pending=false;
        const blockCancel=event=>{if(pending)event.preventDefault();};
        const blockBackdrop=event=>{if(pending&&event.target===dialog){event.preventDefault();event.stopImmediatePropagation();}};
        const trap=event=>{
            if(event.key!=='Tab')return;
            const controls=[...dialog.querySelectorAll('button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href]')].filter(control=>control.getClientRects().length),index=controls.indexOf(document.activeElement);
            if(!controls.length){event.preventDefault();return;}
            if(event.shiftKey&&index<=0){event.preventDefault();controls.at(-1).focus();}
            else if(!event.shiftKey&&index===controls.length-1){event.preventDefault();controls[0].focus();}
        };
        openForm('Xác nhận hỗ trợ nhận thưởng',`<div class="staff-referral-support-summary"><p>Xác nhận đã hỗ trợ nhận thưởng cho <b>${esc(referrer.login)}</b> (${esc(referrer.name)})?</p><p>Lượt giới thiệu học sinh: <b>${esc(row.login_identifier)} · ${esc(row.full_name)}</b>.</p></div>`,async()=>{
            if(user?.id!==owner)throw new Error('Phiên đăng nhập đã thay đổi. Vui lòng tải lại.');
            if(pending)return;
            pending=true;
            const controls=[...dialog.querySelectorAll('button')];
            controls.forEach(control=>control.disabled=true);
            try{
                const result=await request('referrals/'+referrer.referralId+'/confirm-support',{referrerAccountId:referrer.accountId});
                if(user?.id!==owner)return;
                for(const payment of payload.rows||[]){
                    if(payment.referrer?.referralId===referrer.referralId)Object.assign(payment.referrer,{canConfirmSupport:false,supportConfirmedAt:result.supportConfirmedAt,supportConfirmedBy:result.supportConfirmedBy});
                }
            }finally{pending=false;controls.forEach(control=>{if(control.isConnected)control.disabled=false;});}
        },'OK');
        dialog.addEventListener('cancel',blockCancel);
        dialog.addEventListener('click',blockBackdrop,true);
        dialog.addEventListener('keydown',trap);
        dialog.querySelector('#staff-modal-form').addEventListener('submit',event=>{if(pending){event.preventDefault();event.stopImmediatePropagation();}},true);
        dialog.addEventListener('close',()=>{
            dialog.removeEventListener('cancel',blockCancel);
            dialog.removeEventListener('click',blockBackdrop,true);
            dialog.removeEventListener('keydown',trap);
            const target=document.querySelector('[data-staff="confirm-referral-support"][data-id="'+referrer.referralId+'"]')||document.querySelector('.staff-payment-list h2');
            if(target){if(target.tagName==='H2')target.tabIndex=-1;target.focus({preventScroll:true});}
        },{once:true});
        dialog.querySelector('[data-staff="close-modal"]').textContent='Hủy';
        dialog.querySelector('button[type="submit"]').focus();
    }

    function paymentForm(row) {
        openForm('Đối soát đơn '+esc(row.reference),`<div class="staff-payment-summary"><b><span class="staff-payer-login">${esc(row.login_identifier)}</span> · ${esc(row.full_name)}</b><strong>${money(row.amount)}</strong><span>${row.fee_id?'Học phí '+esc(row.month):'VIP một tháng'}</span><div class="staff-payment-referrer"><h3>Người giới thiệu</h3>${paymentReferrerMarkup(row.referrer,true)}</div></div>
            <p>Chỉ xác nhận sau khi đã đối chiếu khoản tiền thực nhận.</p>${input('Nhập lại mã đơn','reference','','text','required autocomplete="off"')}${input('Số tiền đã nhận · đồng','amount','','number','required min="1" step="1"')}`,
            async values=>{await request('payments/'+row.id+'/confirm',{reference:values.get('reference').trim(),amount:Number(values.get('amount'))});},'Xác nhận đã nhận tiền');
    }

    function passwordForm() {
        openForm('Đổi mật khẩu',input('Mật khẩu hiện tại','currentPassword','','password','required autocomplete="current-password"')+
            input('Mật khẩu mới','newPassword','','password','required minlength="6" maxlength="128" autocomplete="new-password"'),
            async values=>{await request('password',{currentPassword:values.get('currentPassword'),newPassword:values.get('newPassword')});});
    }

    async function handleClick(event) {
        const tabButton=event.target.closest('[data-tab]');
        const classTabButton=event.target.closest('[data-class-tab]');
        const kindButton=event.target.closest('[data-content-kind]');
        const action=event.target.closest('[data-staff]');
        try {
            if(tabButton) {await changeTab(tabButton.dataset.tab);return;}
            if(classTabButton) {classTab=classTabButton.dataset.classTab;draw();return;}
            if(kindButton) {topicKind=kindButton.dataset.contentKind;filter.page=1;await loadTab();return;}
            if(!action || action.disabled) return;
            const value=action.dataset.staff;
            const id=Number(action.dataset.id);
            action.disabled=true;
            if(value==='reload') await loadTab();
            else if(value==='receipts-reload')await loadTab();
            else if(value==='receipts-previous'||value==='receipts-next'){receipts.page=Math.max(1,receipts.page+(value==='receipts-next'?1:-1));await loadReceipts();}
            else if(value==='settings'||value==='audit') await changeTab(value);
            else if(value==='logout') {await request('logout',{});user=null;csrf='';detail=null;resetNotificationDraft();location.assign(new URL('./',document.baseURI));}
            else if(value==='password') passwordForm();
            else if(value==='notification-preview') await previewNotifications(true);
            else if(value==='close-modal') document.querySelector('#modal').close();
            else if(value==='open-admission') admissionForm(payload.rows.find(row=>row.id===id));
            else if(value==='new-class') await classForm();
            else if(value==='edit-class') await classForm(classList.find(item=>item.id===id));
            else if(value==='open-class') {classId=id;detail={};classTab='sessions';sessionId=null;gradingSessionId=null;gradingAssignmentId=null;await loadTab();}
            else if(value==='back-classes') {detail=null;classId=null;await loadTab();}
            else if(value==='new-session') sessionForm();
            else if(value==='edit-session') sessionForm(detail.sessions.find(item=>item.id===id));
            else if(value==='assignments') assignmentsModal(id);
            else if(value==='new-assignment') assignmentForm();
            else if(value==='edit-assignment') assignmentForm(modalContext.assignments.find(item=>item.id===id));
            else if(value==='open-records') {sessionId=id;classTab='records';draw();}
            else if(value==='grade-sessions') {gradingSessionId=null;gradingAssignmentId=null;drawGrading();}
            else if(value==='grade-session') {gradingSessionId=id;gradingAssignmentId=null;drawGrading();}
            else if(value==='grade-assignment') {gradingAssignmentId=id;drawGrading();}
            else if(value==='enroll') await enrollmentForm();
            else if(value==='enroll-search') await enrollmentForm(document.querySelector('[name=enrollmentSearch]').value);
            else if(value==='leave-student') {
                const student=detail.students.find(item=>item.id===id);
                openForm('Cho học sinh rời lớp',`<p>${esc(student.full_name)} sẽ kết thúc ghi danh ở lớp ${esc(detail.class.name)}. Điểm và lịch sử học được giữ lại.</p>`,
                    async()=>{detail=await request('classes/'+classId+'/enroll',{action:'leave',studentId:id});},'Xác nhận rời lớp');
            } else if(value==='new-fee') feeForm();
            else if(value==='calculate-fees') openTuition();
            else if(value==='tuition-student') {tuition.selected=tuition.preview.rows.find(row=>row.studentId===id);renderTuitionModal();}
            else if(value==='tuition-back') {tuition.selected=null;renderTuitionModal();}
            else if(value==='tuition-save') await saveTuition();
            else if(value==='tuition-set-rate') {document.querySelector('#modal').close();await classForm(detail.class);}
            else if(value==='open-fee') await openSavedFee(id);
            else if(value==='new-user') await userForm();
            else if(value==='edit-user') await userForm(payload.users.find(item=>item.id===id));
            else if(value==='new-account') accountForm();
            else if(value==='edit-account') accountForm(payload.rows.find(item=>item.id===id));
            else if(value==='delete-account') deleteAccountForm(payload.rows.find(item=>item.id===id));
            else if(value==='restore-account') restoreAccountForm(payload.rows.find(item=>item.id===id));
            else if(value==='new-content') contentForm();
            else if(value==='edit-content') contentForm(payload.rows.find(item=>item.id===id));
            else if(value==='confirm-payment') paymentForm(payload.rows.find(item=>item.id===id));
            else if(value==='confirm-referral-support') referralSupportForm(payload.rows.find(item=>item.referrer?.referralId===id));
            else if(value==='account-status') {
                const row=payload.rows.find(item=>item.id===id),status=row.status==='active'?'suspended':'active';
                openForm(status==='active'?'Mở lại tài khoản':'Tạm khóa tài khoản',`<p>${esc(row.full_name)} · ${esc(row.login_identifier)}</p><p>${status==='suspended'?'Các phiên đăng nhập học sinh sẽ kết thúc khi tạm khóa.':'Học sinh có thể đăng nhập lại sau khi mở tài khoản.'}</p>`,
                    async()=>{await request('accounts/'+id,{status,revision:row.revision});},status==='active'?'Mở tài khoản':'Tạm khóa');
            } else if(value==='previous'||value==='next') {filter.page+=value==='next'?1:-1;await loadTab();}
        } catch(error) {
            message(error.message);
            if(!user) draw();
        } finally {if(action?.isConnected)action.disabled=false;}
    }

    function bind() {
        const root=document.querySelector('#app');
        root.onclick=handleClick;
        root.onchange=event=>{
            if(event.target.name==='record-session') {sessionId=Number(event.target.value);draw();}
        };
        bindNotificationComposer();
        bindReceipts();
        const login=document.querySelector('#staff-login-form');
        if(login) login.onsubmit=async event=>{
            event.preventDefault();
            const control=login.querySelector('button[type=submit]');
            control.disabled=true;
            try {
                const data=new FormData(login);
                const session=await request('login',{login:data.get('login'),password:data.get('password')});
                user=session.user;csrf=session.csrf;loadError='';await loadTab();
            } catch(error) {document.querySelector('#staff-login-error').textContent=error.message;}
            finally {control.disabled=false;}
        };
        const search=document.querySelector('#staff-filter-form');
        if(search) search.onsubmit=async event=>{
            event.preventDefault();const data=new FormData(search);
            filter={q:data.get('q')||'',grade:data.get('grade')||'0',page:1,...(tab==='accounts'?{status:data.get('status')||'all'}:{}),...(tab==='payments'?{referrer:data.get('referrer')||''}:{})};await loadTab();
        };
        const records=document.querySelector('#staff-records-form');
        if(records) records.onsubmit=async event=>{
            event.preventDefault();
            const control=records.querySelector('[type=submit]');control.disabled=true;
            try {
                const data=new FormData(records),item=selectedSession();
                const attendance=detail.students.map(student=>({studentId:student.id,status:data.get('attendance-'+student.id)||null,
                    comment:data.get('session-comment-'+student.id)||''}));
                detail=await request('sessions/'+item.id+'/records',{revision:item.revision,attendance});
                draw();message('Đã lưu điểm danh và nhận xét.');
            } catch(error) {message(error.message);}
            finally {if(control.isConnected)control.disabled=false;}
        };
        const grading=document.querySelector('#staff-grading-form');
        if(grading) grading.onsubmit=async event=>{
            event.preventDefault();
            const control=grading.querySelector('[type=submit]');control.disabled=true;
            try {
                const data=new FormData(grading),item=detail.sessions.find(value=>value.id===Number(gradingSessionId));
                const assignment=item?.assignments.find(value=>value.id===Number(gradingAssignmentId));
                if(!assignment) throw new Error('Chọn bài tập cần chấm điểm.');
                const scores=detail.students.map(student=>({studentId:student.id,assignmentId:assignment.id,
                    score:data.get('score-'+student.id)===''?null:Number(data.get('score-'+student.id)),
                    comment:data.get('score-comment-'+student.id)||''}));
                detail=await request('sessions/'+item.id+'/records',{revision:item.revision,scores});
                draw();message('Đã lưu điểm và nhận xét bài tập.');
            } catch(error) {message(error.message);}
            finally {if(control.isConnected)control.disabled=false;}
        };
        const settings=document.querySelector('#staff-settings-form');
        if(settings) settings.onsubmit=async event=>{
            event.preventDefault();const control=settings.querySelector('[type=submit]');control.disabled=true;
            try {
                const data=new FormData(settings),body={revision:payload.settings.revision,free_limits:{}};
                for(const key of ['registration_open','learning_open','practice_open','arena_open','leaderboard_open']) body[key]=data.has(key);
                for(const key of ['content','combined','human','bot']) body.free_limits[key]=Number(data.get(key));
                payload=await request('settings',body);draw();message('Cấu hình đã được cập nhật.');
            } catch(error) {message(error.message);}
            finally {if(control.isConnected)control.disabled=false;}
        };
    }

    async function mount(route,options) {
        mode=route;host=options;
        const selected=location.hash.slice(1);
        tab=mode==='teacher'?(selected==='notifications'?'notifications':'overview'):adminTabs.some(([key])=>key===selected)?selected:'overview';
        try {
            const session=await request('session');
            user=session.user||null;csrf=session.csrf||'';setupNeeded=session.setupNeeded||false;
            if(user && (mode==='teacher'||user.role==='admin')) await loadTab();
            else draw();
        } catch(error) {
            user=null;draw();
            const target=document.querySelector('#staff-login-error');
            if(target)target.textContent=error.message;
        }
    }

    function unmount() {
        receipts.ticket++;
        generation++;
        const target=browser?document.querySelector('#modal-body'):null;
        if(target?.onclick===handleClick) target.onclick=null;
    }

    return {routes,render,mount,unmount};
})();

if(typeof module!=='undefined' && module.exports) module.exports=StaffApp;
