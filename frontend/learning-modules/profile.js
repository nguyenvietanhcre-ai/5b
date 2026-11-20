/* profile: extracted behavior; state and cross-feature services supplied explicitly. */
(function(global){'use strict';
function create(ctx){
function showEvolution(pet){
        if(!Object.hasOwn(ctx.evolutionRows,pet))return;
        const [board,row]=ctx.evolutionRows[pet],box=ctx.evolutionBoxes[board],title=ctx.mascotAvatars[pet][0];
        ctx.host.showModal(`<section class="pet-evolution"><p class="eyebrow">Hành trình trưởng thành</p><h2 class="modal-title">Tiến hóa của ${ctx.escape(title)}</h2><p>Bắt đầu với 0 kinh nghiệm ở Đồng I. Mỗi 20 kinh nghiệm lên một bậc. Chọn linh vật khác vẫn giữ kinh nghiệm đã tích lũy.</p><div class="pet-evolution-grid">${['Đồng','Bạc','Vàng'].map((name,i)=>{const x=box.x[i]+5,y=box.y[row]+5,w=box.x[i+1]-box.x[i]-10,h=box.y[row+1]-box.y[row]-10;return `<article class="pet-evolution-form">${ctx.mascotVisuals.portrait(pet,i*100,title+' dạng '+name)}<div><h3>${name} I–V</h3><strong>Từ ${i*100} kinh nghiệm</strong><ul>${['I','II','III','IV','V'].map((roman,k)=>`<li><span>${name} ${roman}</span><b>${i*100+k*20} XP</b></li>`).join('')}</ul></div></article>`}).join('')}</div><p class="learning-notice">Vàng V là bậc cao nhất hiện tại, đạt từ 280 kinh nghiệm. Em vẫn tích lũy kinh nghiệm sau mốc này.</p></section>`);
    }

function accountPagination(kind,record){
        const pages=Math.max(1,Math.ceil(record.total/5)),label=kind==='notifications'?'thông báo':'lượt giới thiệu';
        return record.total?`<nav class="account-pagination" aria-label="Trang ${label}"><span>${record.total} ${label} · Trang ${record.page} / ${pages}</span><div class="actions"><button type="button" class="btn outline" data-account-page="${kind}" data-page="${record.page-1}" ${record.page<=1||record.loading?'disabled':''}>Trang trước</button><button type="button" class="btn outline" data-account-page="${kind}" data-page="${record.page+1}" ${record.page>=pages||record.loading?'disabled':''}>Trang sau</button></div></nav>`:'';
    }

function accountRecordsMarkup(kind){
        const record=ctx.accountPages[kind],rows=record.rows||[];
        const title=kind==='notifications'?'Thông báo tài khoản':'Lịch sử giới thiệu';
        let body;
        if(kind==='notifications')body=rows.map(item=>`<article class="account-notification ${item.read_at?'is-read':'is-unread'}" data-notification-row="${Number(item.id)}"><div class="account-notification-copy"><div class="account-notification-state">${item.read_at?'Đã đọc':'Chưa đọc'}<time datetime="${ctx.escape(item.created_at)}">${ctx.escape(ctx.accountDate(item.created_at))}</time></div><h3>${ctx.escape(ctx.notificationTitle(item))}</h3><p class="account-notification-sender"><span>Người gửi</span><strong>${ctx.escape(ctx.notificationSender(item))}</strong></p></div><button class="btn ${item.read_at?'outline':'dark'}" type="button" data-notification="${Number(item.id)}" aria-label="Xem thông báo: ${ctx.escape(ctx.notificationTitle(item))}" ${ctx.notificationPending===item.id?'disabled':''}>${ctx.notificationPending===item.id?'Đang mở…':'Xem'}</button></article>`).join('');
        else body=rows.map(item=>{
            const supported=Boolean(item.support_confirmed_at),granted=item.reward_status==='granted',support=item.reward_status==='customer_service';
            const label=supported||granted?'Đã nhận thưởng':support?'Cần hỗ trợ nhận thưởng':'Chờ nâng cấp VIP';
            return `<article class="account-referral" data-referral-row="${Number(item.id)}"><header><h3>${ctx.escape(ctx.displayName(item.full_name))}</h3><span class="referral-status ${supported||granted?'is-granted':support?'needs-support':'is-pending'}">${label}</span></header><dl class="referral-dates"><div><dt>Ngày đăng ký</dt><dd>${ctx.escape(ctx.accountDate(item.registered_at))}</dd></div><div><dt>Nâng cấp VIP lần đầu</dt><dd>${ctx.escape(ctx.accountDate(item.first_vip_upgraded_at))}</dd></div></dl><div class="referral-reward ${supported||granted?'is-granted':support?'needs-support':''}">${supported?`<strong>Đã được hỗ trợ nhận thưởng</strong><span>Ngày xác nhận hỗ trợ: ${ctx.escape(ctx.accountDate(item.support_confirmed_at))}</span>`:granted?`<strong>Đã cộng 1 tháng VIP</strong><span>Ngày cộng thưởng: ${ctx.escape(ctx.accountDate(item.reward_granted_at))}</span><b>VIP sau cộng thưởng đến: ${item.reward_vip_expires_at?ctx.escape(ctx.accountDate(item.reward_vip_expires_at)):'Chờ cập nhật thời hạn'}</b>`:support?'<strong>Liên hệ chăm sóc khách hàng</strong><span>Đội ngũ 5BMath sẽ hỗ trợ tài khoản nội bộ nhận thưởng.</span>':'<strong>Chưa phát sinh thưởng</strong><span>Thưởng được ghi nhận khi bạn nâng cấp VIP lần đầu.</span>'}</div></article>`;
        }).join('');
        const empty=kind==='notifications'?'Em chưa có thông báo.':'Chưa có tài khoản đăng ký qua mã của em.';
        return `<div class="account-records-head"><h2 data-account-heading tabindex="-1">${title}</h2>${kind==='notifications'?`<span class="account-record-count">${ctx.unreadNotificationCount()} chưa đọc</span>`:''}</div><div class="account-records-list">${body||`<p class="account-records-empty">${empty}</p>`}</div><p class="account-records-feedback" id="${kind}-feedback" role="alert" ${record.error?'':'hidden'}>${ctx.escape(record.error)}</p>${record.loading?'<p class="account-records-loading" role="status">Đang tải…</p>':''}${accountPagination(kind,record)}`;
    }

function accountRecordsSection(kind){return `<section class="card card-pad account-records" id="account-${kind}" aria-label="${kind==='notifications'?'Thông báo tài khoản':'Lịch sử giới thiệu'}">${accountRecordsMarkup(kind)}</section>`;}

async function loadAccountPage(kind,page=ctx.accountPages[kind].page,{quiet=false}={}){
        if(!ctx.live||!PlatformAPI.snapshot.authenticated)return;
        if(PlatformAPI.familyContext){Object.assign(ctx.accountPages[kind],{rows:[],total:0,loading:false,error:''});ctx.updateAccountSection(kind);return;}
        const record=ctx.accountPages[kind],owner=ctx.accountPageOwner,ticket=++record.request;
        record.loading=!quiet;record.error='';if(!quiet)ctx.updateAccountSection(kind);
        try{
            let result=await PlatformAPI.request(kind+'?page='+Math.max(1,page));
            const last=Math.max(1,Math.ceil(result.total/5));
            if(result.page>last)result=await PlatformAPI.request(kind+'?page='+last);
            if(owner!==ctx.accountPageOwner||ticket!==record.request)return;
            Object.assign(record,{page:result.page,rows:result.rows,total:result.total,error:''});
            if(kind==='notifications')ctx.adoptNotificationSummary(result);
            else if(result.page===1){PlatformAPI.snapshot.account.referrals=result.rows;PlatformAPI.snapshot.account.referralTotal=result.total;}
        }catch(error){if(owner===ctx.accountPageOwner&&ticket===record.request){record.error='Chưa tải được '+(kind==='notifications'?'thông báo':'lịch sử giới thiệu')+'. '+error.message;}}
        finally{if(owner===ctx.accountPageOwner&&ticket===record.request){record.loading=false;ctx.updateAccountSection(kind);}}
    }

async function readNotification(control){
        if(ctx.notificationPending!==null)return;
        const identity=Number(control.dataset.notification),owner=ctx.accountPageOwner,lifecycle=ctx.notificationLifecycle;
        const selected=ctx.accountPages.notifications.rows?.find(item=>item.id===identity);
        ctx.notificationPending=identity;ctx.notificationVersion++;control.disabled=true;control.textContent='Đang mở…';
        try{
            const result=await PlatformAPI.request('notifications/'+identity+'/read',{});
            if(owner!==ctx.accountPageOwner)return;
            ctx.syncAccountPages(result);ctx.updateUnreadBadge();
            const detail=result.notification||selected;
            await loadAccountPage('notifications',ctx.accountPages.notifications.page,{quiet:true});
            if(ctx.currentRoute!=='profile'||lifecycle!==ctx.notificationLifecycle||!detail)return;
            const dialog=document.querySelector('#modal'),oldLabel=dialog.getAttribute('aria-labelledby');
            ctx.host.showModal(`<article class="account-notification-detail"><p class="account-detail-kicker">Thông báo tài khoản</p><h2 class="modal-title" id="account-notification-title">${ctx.escape(ctx.notificationTitle(detail))}</h2><dl class="notification-detail-meta"><div><dt>Người gửi</dt><dd>${ctx.escape(ctx.notificationSender(detail))}</dd></div><div><dt>Ngày gửi</dt><dd>${ctx.escape(ctx.accountDate(detail.created_at))}</dd></div></dl><div class="notification-detail-body">${ctx.escape(detail.body||'')}</div><div class="actions"><button class="btn dark" type="button" id="close-notification-detail">Đóng thông báo</button></div></article>`);
            dialog.setAttribute('aria-labelledby','account-notification-title');
            document.querySelector('#close-notification-detail').onclick=()=>dialog.close();
            dialog.addEventListener('close',()=>{if(oldLabel===null)dialog.removeAttribute('aria-labelledby');else dialog.setAttribute('aria-labelledby',oldLabel);const next=document.querySelector(`[data-notification="${identity}"]`)||document.querySelector('#account-notifications [data-account-heading]');next?.focus({preventScroll:true});},{once:true});
            document.querySelector('#close-notification-detail').focus();
        }catch(error){
            ctx.accountPages.notifications.error='Chưa mở được thông báo. '+error.message;ctx.updateAccountSection('notifications');ctx.host.toast(error.message);
        }finally{ctx.notificationPending=null;const next=document.querySelector(`[data-notification="${identity}"]`);if(next){next.disabled=false;next.textContent='Xem';}ctx.scheduleNotificationPolling();}
    }

function personalNoticeContext(){
        const owner=PlatformAPI.snapshot.account?.id;
        if(ctx.personalNotices.owner!==owner)ctx.personalNotices={owner,rows:null,total:0,unreadCount:0,error:'',pending:null};
        return ctx.personalNotices;
    }

function personalRewardNotices(){
        const rewards=PlatformAPI.snapshot.personalSummary?.referral?.rewards;
        if(!Array.isArray(rewards))return '';
        const rows=rewards.filter(item=>item&&['VIP','VIP+'].includes(item.tier)&&Number.isFinite(Number(item.days))&&Number(item.days)>0);
        if(!rows.length)return '';
        const date=value=>value&&Number.isFinite(Date.parse(value))?ctx.escape(ctx.accountDate(value)):'Chờ xếp lịch';
        const labels={queued:'Đã xếp lịch',active:'Đang sử dụng',used:'Đã sử dụng','held-internal':'Đang bảo lưu'};
        return `<div class="personal-reward-notices"><h3>Phần thưởng giới thiệu của em</h3>${rows.map(item=>`<article class="account-notification personal-reward-notice"><div><h3>Đã nhận ${personalCount(item.days)} ngày ${ctx.escape(item.tier)}</h3><p>${labels[item.status]||'Đã ghi nhận'}</p>${item.status==='held-internal'?'<p>Phần thưởng được bảo lưu trong thời gian em có quyền học Zoom.</p>':`<p>Từ ${date(item.startsAt)}<br>Đến ${date(item.endsAt)}</p>`}</div></article>`).join('')}</div>`;
    }

function personalNotificationsPanel(){
        const context=personalNoticeContext();
        return `<section class="card card-pad account-records" id="account-notifications" aria-label="Thông báo của em"><h2>Thông báo của em</h2><p>${personalCount(context.unreadCount)} chưa đọc</p>${personalRewardNotices()}${context.error?`<p role="alert">${ctx.escape(context.error)}</p>`:''}${context.rows===null?'<p role="status">Đang tải thông báo…</p>':context.rows.length?context.rows.map(item=>`<article class="account-notification ${item.readAt?'is-read':'is-unread'}"><div><h3>${ctx.escape(item.title||'Thông báo')}</h3><p>${ctx.escape(item.senderName||'5BMath')} · ${ctx.escape(ctx.accountDate(item.createdAt))}</p><small>${item.readAt?'Đã đọc':'Chưa đọc'}</small></div><button type="button" class="btn outline" data-personal-notice="${Number(item.id)}">Xem</button></article>`).join(''):'<p>Em chưa có thông báo lớp học.</p>'}</section>`;
    }

function updatePersonalNotices(){
        const node=document.querySelector('#account-notifications');if(!node)return;
        node.outerHTML=personalNotificationsPanel();
        document.querySelectorAll('[data-personal-notice]').forEach(button=>button.onclick=()=>readPersonalNotice(button));
    }

async function loadPersonalNotices(){
        if(!ctx.live||ctx.currentRoute!=='profile'||!ctx.learnerBackgroundAllowed())return;
        const context=personalNoticeContext();if(context.pending)return context.pending;
        context.pending=(async()=>{
            try{const result=await PlatformAPI.request('personal/notifications');
                if(context!==ctx.personalNotices||context.owner!==PlatformAPI.snapshot.account?.id||ctx.currentRoute!=='profile'||!ctx.learnerBackgroundAllowed())return;
                Object.assign(context,{rows:result.rows||[],total:result.total||0,unreadCount:result.unreadCount||0,error:''});
            }catch(error){if(context===ctx.personalNotices)context.error='Chưa tải được thông báo. '+error.message;}
            finally{context.pending=null;if(context===ctx.personalNotices&&context.owner===PlatformAPI.snapshot.account?.id&&ctx.currentRoute==='profile')updatePersonalNotices();}
        })();return context.pending;
    }

async function readPersonalNotice(button){
        const context=personalNoticeContext(),id=Number(button.dataset.personalNotice);if(button.disabled||!ctx.learnerBackgroundAllowed())return;
        button.disabled=true;
        try{const result=await PlatformAPI.request('personal/notifications/read',{ids:[id]});
            if(context!==ctx.personalNotices||context.owner!==PlatformAPI.snapshot.account?.id||ctx.currentRoute!=='profile'||!ctx.learnerBackgroundAllowed())return;
            const detail=(result.rows||[]).find(item=>Number(item.id)===id);Object.assign(context,{rows:result.rows||[],total:result.total||0,unreadCount:result.unreadCount||0,error:''});updatePersonalNotices();
            if(detail){ctx.host.showModal(`<article><h2 class="modal-title">${ctx.escape(detail.title||'Thông báo')}</h2><p>${ctx.escape(detail.senderName||'5BMath')} · ${ctx.escape(ctx.accountDate(detail.createdAt))}</p><p class="notification-detail-body">${ctx.escape(detail.body||'')}</p><button type="button" class="btn outline" id="personal-notice-close">Đóng</button></article>`);document.querySelector('#personal-notice-close').onclick=()=>document.querySelector('#modal')?.close();}
        }catch(error){if(context===ctx.personalNotices){context.error='Chưa mở được thông báo. '+error.message;updatePersonalNotices();}}
        finally{if(button.isConnected)button.disabled=false;}
    }

function personalCount(value){return Number.isInteger(Number(value))&&Number(value)>=0?ctx.content.format(Number(value)):'—';}

function personalContinue(){
        const item=PlatformAPI.snapshot.personalSummary?.continueStudy;
        if(!item)return '<section class="personal-study-next"><h3>Hành trình học</h3><p>Chưa có bài đang học dở. Em có thể chọn một bài mới.</p>'+ctx.link('Chọn bài giảng','weekly','outline')+'</section>';
        const title=item.kind==='retake'?'Làm lại đề':'Học tiếp';
        return '<section class="personal-study-next"><h3>'+title+'</h3><p>'+ctx.escape(item.title||'Bài học của em')+'</p>'+(item.kind==='retake'?ctx.button('Làm lại đề','continue-study','dark'):('<a class="btn dark" href="'+safeStudyHref(item.href)+'">Học tiếp</a>'))+'</section>';
    }

function safeStudyHref(value){return typeof value==='string'&&/^\/(?!\/)/.test(value)&&!/[\\\s]/.test(value)?ctx.escape(value):ctx.href('weekly');}

async function continueStudy(){
        const item=PlatformAPI.snapshot.personalSummary?.continueStudy;if(!item)return;
        if(item.kind!=='retake'){location.assign(item.href);return;}
        if(item.provider==='pilot'&&typeof LocalPilot!=='undefined'&&LocalPilot.retakeOwned)return LocalPilot.retakeOwned(item.examId);
        const result=await PlatformAPI.request('exams/'+encodeURIComponent(item.examId)+'/retake',{requestKey:ctx.uid()});
        location.assign(ctx.href('testing',{id:result.exam.id}));
    }

function personalSummaryCard(){
        const summary=PlatformAPI.snapshot.personalSummary||{},study=summary.study||{};
        return `<section class="card card-pad personal-overview"><div class="personal-identity">${ctx.art(ctx.state.mascot,ctx.petName())}<div><span class="tag sage" data-account-membership>${ctx.escape(ctx.member())}</span><h2>${ctx.escape(ctx.name())}</h2><p>Khối ${ctx.grade()}${ctx.state.birthYear?' · Sinh năm '+ctx.escape(ctx.state.birthYear):''}</p><p>${ctx.escape(ctx.petName())} · ${ctx.content.format(ctx.state.points)} XP</p></div></div><div class="actions">${ctx.button('Đổi tên','rename','outline')}${companionRemaining()>0?ctx.button('Đổi Bạn Đồng Hành','open-companion','outline'):''}</div><p class="personal-companion-note">${companionRemaining()>0?'Còn 1 lần chọn lại Bạn Đồng Hành.':'Đã dùng lượt chọn lại Bạn Đồng Hành.'}</p><dl class="personal-summary" aria-label="Tổng kết học tập"><div><dt>Bài đã học</dt><dd>${personalCount(study.completedLessons)}</dd></div><div><dt>Bài luyện đã nộp</dt><dd>${personalCount(study.submittedExams)}</dd></div><div><dt>Câu đã trả lời</dt><dd>${personalCount(study.answeredQuestions)}</dd></div></dl>${personalContinue()}${!summary.study?'<p class="learning-notice">Tổng kết đang chờ dữ liệu từ máy chủ.</p>':''}</section>`;
    }

function personalInvitePanel(){
        const referral=PlatformAPI.snapshot.personalSummary?.referral||{};
        return `<section class="card card-pad personal-invite"><h2>Mã giới thiệu của em</h2>${referral.code?`<label class="field"><span>Mã của em</span><input id="personal-referral-code" readonly value="${ctx.escape(referral.code)}"></label>${ctx.button('Sao chép mã','copy-personal-code','outline','copy')}`:'<p>Mã giới thiệu đang được chuẩn bị.</p>'}<p>Mời bạn nhập mã khi thanh toán gói VIP hoặc VIP+ lần đầu. Khi thanh toán được xác nhận, em nhận 7 ngày của loại gói bạn mua theo điều kiện chương trình.</p></section>`;
    }

function liveProfile() {
        return ctx.intro('Cá nhân','Một góc riêng cho hành trình học của em.')+personalSummaryCard()+personalNotificationsPanel()+ctx.themeSettings()+personalInvitePanel();
    }

function openCompanionDialog(){
        if(!companionRemaining())return;
        ctx.host.showModal(ctx.views.mascot());
        document.querySelectorAll('#modal-body [data-learning^="choose-"]').forEach(node=>node.onclick=async()=>{
            try{const pet=node.dataset.learning.slice(7);await chooseCompanion(pet);if(ctx.state.mascot===pet)document.querySelector('#modal')?.close();}
            catch(error){ctx.host.toast(error.message);}
        });
        document.querySelectorAll('#modal-body [data-evolution]').forEach(node=>node.onclick=()=>showEvolution(node.dataset.evolution));
    }

function initials() {
        return ctx.name().trim().split(/\s+/).slice(-2).map(part => part[0]).join('').toLocaleUpperCase('vi');
    }

function companionRemaining(){
        const value=ctx.live?PlatformAPI.snapshot.account?.companionChangesRemaining??PlatformAPI.snapshot.state?.companionChangesRemaining:ctx.state.companionChangesRemaining??1;
        return Number(value)===1?1:0;
    }

async function chooseCompanion(pet){
        if(ctx.companionChanging||pet===ctx.state.mascot)return;
        if(!companionRemaining()){ctx.host.toast('Em đã dùng lượt chọn lại Bạn Đồng Hành.');return;}
        if(ctx.browser&&!window.confirm('Em chỉ được chọn lại Bạn Đồng Hành một lần. Chọn '+ctx.mascotAvatars[pet][0]+'?'))return;
        ctx.companionChanging=true;
        if(ctx.browser)document.querySelectorAll('[data-learning^="choose-"]').forEach(node=>node.disabled=true);
        try{if(ctx.live)await ctx.mutate('mascot',{mascot:pet});else{ctx.state.mascot=pet;ctx.state.companionChangesRemaining=0;ctx.save();}}
        finally{ctx.companionChanging=false;ctx.refresh();}
    }
const views = {
mascot() {
            return `<section class="personal-companion" aria-labelledby="companion-heading"><h2 id="companion-heading">Bạn Đồng Hành</h2><p>${companionRemaining()>0?'Em còn 1 lần chọn lại Bạn Đồng Hành sau lựa chọn ban đầu.':'Em đã dùng lượt chọn lại Bạn Đồng Hành.'} Kinh nghiệm và quyền học được giữ nguyên.</p>
            <section class="card feature-row sage mascot-feature"><div>${ctx.badge('Đang đồng hành · '+ctx.petRank(ctx.level()),'white')}<h2>${ctx.escape(ctx.petName())}</h2><p>${ctx.content.format(ctx.state.points)} kinh nghiệm · Mỗi 20 kinh nghiệm lên một bậc</p>${ctx.meter(ctx.rankPercent(),'Tiến độ huy hiệu')}<small>${ctx.rankProgress()}</small></div>${ctx.art(ctx.state.mascot,ctx.petName())}</section>
            ${ctx.heading('Chọn lại Bạn Đồng Hành')}<div class="grid2">${['dog','horse','dolphin','octopus','starfish','bee','butterfly','ca-map','tiger','crab','eagle','sparrow','sprout','cu-meo','fox','voi','rabbit','cat','gau','lion'].map(pet => {const title=ctx.mascotAvatars[pet][0];return `<section class="card card-pad pet-option">${ctx.art(pet,title)}<div><h3>${title}</h3>${pet === ctx.state.mascot ? ctx.badge('Đang chọn','sage') : companionRemaining()>0?ctx.button('Chọn ' + title,'choose-' + pet,'outline'):'<span class="tag">Đã hết lượt đổi</span>'}<button type="button" class="btn outline pet-evolution-button" data-evolution="${pet}" aria-label="Xem tiến hóa của ${title}">Xem tiến hóa</button></div></section>`;}).join('')}</div></section>`;
        },
profile() {
            if(ctx.live)return liveProfile();
            return ctx.intro('Cá nhân','Hồ sơ trải nghiệm trên trình duyệt.')+`<section class="card card-pad personal-overview"><div class="personal-identity">${ctx.art(ctx.state.mascot,ctx.petName())}<div><h2>${ctx.escape(ctx.name())}</h2><p>${ctx.escape(ctx.petName())}</p></div></div><div class="actions">${ctx.button('Đổi tên','rename','outline')}${companionRemaining()>0?ctx.button('Đổi Bạn Đồng Hành','open-companion','outline'):''}</div><p>Kết nối máy chủ để xem tổng kết và mã giới thiệu riêng của em.</p></section>`+ctx.themeSettings();
        }
};
const actions = {
'continue-study':continueStudy,
'open-companion':openCompanionDialog,
'copy-personal-code':()=>ctx.copyText(PlatformAPI.snapshot.personalSummary?.referral?.code||''),
'choose-sparrow':()=>chooseCompanion('sparrow'),
'choose-butterfly':()=>chooseCompanion('butterfly'),
'choose-dolphin':()=>chooseCompanion('dolphin'),
'choose-cu-meo':()=>chooseCompanion('cu-meo'),
'choose-sprout':()=>chooseCompanion('sprout'),
'choose-voi':()=>chooseCompanion('voi'),
'choose-lion':()=>chooseCompanion('lion'),
'choose-starfish':()=>chooseCompanion('starfish'),
'choose-fox':()=>chooseCompanion('fox'),
'choose-tiger':()=>chooseCompanion('tiger'),
'choose-eagle':()=>chooseCompanion('eagle'),
'choose-ca-map':()=>chooseCompanion('ca-map'),
'choose-bee':()=>chooseCompanion('bee'),
'choose-octopus':()=>chooseCompanion('octopus'),
'choose-rabbit':()=>chooseCompanion('rabbit'),
'choose-crab':()=>chooseCompanion('crab'),
'choose-gau':()=>chooseCompanion('gau'),
'choose-cat':()=>chooseCompanion('cat'),
'choose-dog':()=>chooseCompanion('dog'),
'choose-horse':()=>chooseCompanion('horse'),
'refresh-account':async () => {ctx.applySnapshot(await PlatformAPI.refresh());ctx.refresh();},
'copy-invite':() => ctx.copyText(ctx.state.inviteCode),
'copy-invite-link':() => ctx.copyText(new URL('./?invite=' + ctx.state.inviteCode,document.baseURI).href),
rename() {
            ctx.host.showModal(`<h2 class="modal-title">Đổi biệt danh</h2><form id="learning-name-form"><label class="field"><span>Biệt danh của em</span><input name="name" value="${ctx.escape(ctx.name())}" minlength="2" maxlength="40" autocomplete="nickname" aria-describedby="nickname-help nickname-error" required></label><p class="modal-copy" id="nickname-help">${ctx.escape(ctx.nicknames.help)}</p><p id="nickname-error" role="alert"></p><button class="btn dark" type="submit">Lưu tên</button></form>`);
            const nameInput = document.querySelector('#learning-name-form [name=name]');
            nameInput.oninput = () => {nameInput.removeAttribute('aria-invalid');document.querySelector('#nickname-error').textContent='';};
            document.querySelector('#learning-name-form').onsubmit = async event => {
                event.preventDefault();
                const error = ctx.nicknames.error(nameInput.value);
                if (error) {document.querySelector('#nickname-error').textContent=error;nameInput.setAttribute('aria-invalid','true');nameInput.focus();return;}
                const value = ctx.nicknames.normalize(nameInput.value);
                if(ctx.live){
                    try{await ctx.mutate('profile',{name:value});document.querySelector('#modal').close();ctx.refresh();}
                    catch(error){document.querySelector('#nickname-error').textContent=error.message;}
                    return;
                }
                ctx.host.progress.name = value;
                ctx.host.saveProgress();
                document.querySelector('#modal').close();
                ctx.refresh();
            };
        }
};
return {views,actions,showEvolution,accountPagination,accountRecordsMarkup,accountRecordsSection,loadAccountPage,readNotification,personalNoticeContext,personalRewardNotices,personalNotificationsPanel,updatePersonalNotices,loadPersonalNotices,readPersonalNotice,personalCount,personalContinue,safeStudyHref,continueStudy,personalSummaryCard,personalInvitePanel,liveProfile,openCompanionDialog,initials,companionRemaining,chooseCompanion};
}
const api={create};(global.LearningFeatures??={})['profile']=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
