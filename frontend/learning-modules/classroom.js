/* classroom: extracted behavior; state and cross-feature services supplied explicitly. */
(function(global){'use strict';
function create(ctx){
function liveClassroom() {
        if(!ctx.isInternal())return ctx.intro('Lớp Zoom','Lớp học dành cho tài khoản SVip.')+ctx.link('Đăng ký học Zoom','zoomRegistration');
        const classes=PlatformAPI.snapshot.account.classes;
        return `${ctx.intro('Lớp Zoom','Lịch học và kết quả của lớp em.')}${classes.length?ctx.field('Lớp đang học','class-select',classes.map(c=>[c.id,c.name]),ctx.query('class')||classes[0].id):''}<section class="card card-pad" id="class-info">${classes.length?'Đang tải lớp học…':'Chưa có lớp được gán. Liên hệ chăm sóc khách hàng để được xếp lớp.'}</section><div class="tabs class-tabs">${[['sessions','Buổi học'],['assignments','Bài tập'],['summary','Tổng kết'],['fees','Học phí']].map(([key,label])=>`<button type="button" data-class-tab="${key}" aria-pressed="${ctx.classTab===key}" class="${ctx.classTab===key?'selected':''}">${label}${['assignments','fees'].includes(key)?ctx.classUnreadBadge(0,key):''}</button>`).join('')}</div><p id="class-read-feedback" class="class-read-feedback" role="status" hidden></p><div id="class-body"></div>`;
    }

function trendChart(months) {
        if(!months.length)return '<p>Biểu đồ sẽ xuất hiện khi bài tập được chấm điểm.</p>';
        const x=i=>55+i*(500/Math.max(1,months.length-1)),y=v=>215-v*18;
        return `<figure class="trend-chart"><svg viewBox="0 0 620 270" role="img" aria-label="Điểm trung bình theo tháng"><path d="M40 25V215H590" fill="none" stroke="currentColor"/>${[0,5,10].map(v=>`<text x="10" y="${y(v)+5}">${v}</text><path d="M40 ${y(v)}H590" stroke="#e4e8d8"/>`).join('')}<polyline points="${months.map((m,i)=>x(i)+','+y(m.average)).join(' ')}" fill="none" stroke="var(--green)" stroke-width="4"/>${months.map((m,i)=>`<circle cx="${x(i)}" cy="${y(m.average)}" r="6" fill="var(--orange)"/><text x="${x(i)}" y="${y(m.average)-14}" text-anchor="middle">${m.average}</text><text x="${x(i)}" y="245" text-anchor="middle">${ctx.escape(m.month)}</text>`).join('')}</svg><figcaption>Điểm trung bình các bài đã chấm (thang 10)</figcaption></figure>`;
    }

async function loadClass() {
        const select=document.querySelector('#class-select'),info=document.querySelector('#class-info');
        if(!ctx.live||!select||!info)return;
        const identity=select.value,ticket=++ctx.classLoadTicket,owner=ctx.accountPageOwner;
        if(String(ctx.classData?.class.id)!==identity){ctx.classData=null;const body=document.querySelector('#class-body');if(body)body.innerHTML='';}
        ctx.updateClassUnread();
        try{
            const data=await PlatformAPI.request('classes/'+identity+'?'+new URLSearchParams({from:ctx.classFrom,to:ctx.classTo}));
            if(!info.isConnected||ticket!==ctx.classLoadTicket||owner!==ctx.accountPageOwner)return;ctx.classData=data;
            info.innerHTML=`<h2>${ctx.escape(data.class.name)}</h2><div class="grid2"><p>Học sinh: <strong>${ctx.escape(ctx.name())}</strong><br>Giáo viên: ${ctx.escape(data.class.teacher)}</p><p>Lịch học: ${ctx.escape(data.class.schedule||'Chờ cập nhật')}<br>Chương trình: ${ctx.escape(data.class.curriculum||'Chờ cập nhật')}</p></div>${ctx.safeUrl(data.class.meeting_ref)?`<a class="btn dark" href="${ctx.safeUrl(data.class.meeting_ref)}" target="_blank" rel="noopener noreferrer">Vào lớp Zoom</a>`:''}`;
            renderClassBody();
            return data;
        }catch(e){if(info.isConnected&&ticket===ctx.classLoadTicket){info.textContent=e.message;ctx.classData=null;}}
    }

async function readClassSection(data,section){
        if(!data||!['assignments','fees'].includes(section))return;
        const through=Number(data.readThrough?.[section])||0;
        if(!through)return;
        const owner=ctx.accountPageOwner,feedback=document.querySelector('#class-read-feedback');
        ctx.classUnreadVersion++;ctx.classReadBusy++;
        if(feedback)feedback.hidden=true;
        const perform=async()=>{
            if(owner!==ctx.accountPageOwner)return;
            try{
                const result=await PlatformAPI.request('classes/'+data.class.id+'/read',{section,through});
                if(owner===ctx.accountPageOwner)ctx.adoptClassUnread(result.classroomUnread);
            }catch(error){
                if(owner===ctx.accountPageOwner&&feedback?.isConnected){feedback.textContent='Chưa đánh dấu đã đọc. Em có thể bấm lại mục này. '+error.message;feedback.hidden=false;}
            }
        };
        const operation=ctx.classReadQueue.then(perform,perform);ctx.classReadQueue=operation;
        try{await operation;}finally{ctx.classReadBusy--;ctx.classUnreadVersion++;}
    }

function classAssignmentMarkup(a){
        return `<article class="assignment-row class-assignment" data-assignment="${a.id}"><div class="class-assignment-heading"><div><h3>${ctx.escape(a.title)}</h3><small>${ctx.escape(a.kind)}</small>${ctx.safeUrl(a.document_url)?`<a href="${ctx.safeUrl(a.document_url)}" target="_blank" rel="noopener noreferrer">Mở đề bài</a>`:''}</div>${ctx.badge(a.score==null?'Chưa có điểm':a.score+'/10','sage')}<button class="btn outline" type="button" data-class-ranking="assignment" data-value="${a.id}">Bảng điểm</button></div><p class="class-personal-comment"><strong>Nhận xét bài làm:</strong> ${ctx.escape(a.comment||'Thầy cô chưa nhận xét bài này.')}</p><div class="class-submission-current">${ctx.submissionMarkup(a.submission)}</div><form data-class-submit="${a.id}" class="class-submission-form"><label class="field"><span>${a.submission?'Chọn tệp để nộp lại':'Chọn bài làm để nộp'}</span><input name="file" type="file" accept=".jpg,.jpeg,.png,.webp,.pdf" required aria-label="Bài làm ${ctx.escape(a.title)}"></label><p>Ảnh JPG, PNG, WebP hoặc PDF, tối đa 10 MB.${a.submission&&a.score!=null?' Nộp lại vẫn giữ điểm và nhận xét hiện tại để thầy cô xem lại.':''}</p><button class="btn dark" type="submit">${a.submission?'Nộp lại bài':'Nộp bài'}</button><p class="class-submit-status" role="status" hidden></p></form></article>`;
    }

async function submitClassAssignment(form){
        if(form.dataset.pending)return;
        const data=ctx.classData,identity=Number(form.dataset.classSubmit),assignment=data?.sessions.flatMap(s=>s.assignments).find(a=>a.id===identity),owner=ctx.accountPageOwner;
        if(!assignment)return;
        const control=form.querySelector('button[type="submit"]'),input=form.querySelector('input[type="file"]'),status=form.querySelector('[role="status"]'),file=input.files[0];
        status.hidden=false;
        if(!file){status.textContent='Em hãy chọn bài làm trước khi nộp.';return;}
        const mime=file.type||({'jpg':'image/jpeg','jpeg':'image/jpeg','png':'image/png','webp':'image/webp','pdf':'application/pdf'}[file.name.split('.').pop().toLowerCase()]);
        if(!['image/jpeg','image/png','image/webp','application/pdf'].includes(mime)||!file.size||file.size>10*1024*1024){status.textContent='Chọn ảnh JPG, PNG, WebP hoặc PDF từ 1 byte đến 10 MB.';return;}
        form.dataset.pending='true';control.disabled=true;input.disabled=true;status.textContent='Đang gửi bài đến thầy cô…';
        try{
            const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('Chưa đọc được tệp. Em hãy chọn lại.'));reader.readAsDataURL(file);});
            if(owner!==ctx.accountPageOwner||!form.isConnected)return;
            const result=await PlatformAPI.request('classes/'+data.class.id+'/assignments/'+identity+'/submissions',{filename:file.name,mimeType:mime,data:encoded});
            if(owner!==ctx.accountPageOwner||!form.isConnected)return;
            assignment.submission=result.submission;
            form.closest('[data-assignment]').querySelector('.class-submission-current').innerHTML=ctx.submissionMarkup(result.submission);
            input.value='';control.textContent='Nộp lại bài';status.textContent='Đã gửi bài đến thầy cô.';
        }catch(error){if(form.isConnected)status.textContent='Chưa gửi được bài. '+error.message;}
        finally{delete form.dataset.pending;if(form.isConnected){control.disabled=false;input.disabled=false;}}
    }

function renderClassBody() {
        const body=document.querySelector('#class-body');if(!body||!ctx.classData)return;
        const d=ctx.classData;
        if(ctx.classTab==='sessions'||ctx.classTab==='assignments'){
            body.innerHTML=`<form id="class-filter" class="actions"><label class="field"><span>Từ ngày</span><input name="from" type="date" value="${ctx.escape(ctx.classFrom)}"></label><label class="field"><span>Đến ngày</span><input name="to" type="date" value="${ctx.escape(ctx.classTo)}"></label><button class="btn dark" type="submit">Tìm kiếm</button></form><div class="solution-list">${d.sessions.map(s=>`<details class="card card-pad class-session"><summary><strong>${ctx.escape(s.title)}</strong><span>${new Date(s.starts_at).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'})}</span>${ctx.classTab==='assignments'?ctx.badge(s.complete?'Đã chấm đủ':'Chưa chấm đủ',s.complete?'sage':'peach'):''}</summary>${ctx.classTab==='sessions'?`<h3>Nhận xét dành cho em</h3><p class="class-personal-comment">${ctx.escape(s.personal_comment||'Thầy cô chưa có nhận xét riêng sau buổi học này.')}</p><p>Điểm danh: <strong>${{charged:'Có học · tính phí',free:'Có học · miễn phí',absent:'Vắng'}[s.attendance_status]||'Chưa điểm danh'}</strong></p><h3>Nội dung buổi học</h3><p class="class-personal-comment">${ctx.escape(s.teacher_comment||'Chưa có nội dung tổng kết chung.')}</p>${ctx.safeUrl(s.video_url)?`<video controls preload="none" src="${ctx.safeUrl(s.video_url)}" aria-label="Video bài giảng"></video><a href="${ctx.safeUrl(s.video_url)}" target="_blank" rel="noopener noreferrer">Mở video bài giảng</a>`:'<p>Video bài giảng chưa được cập nhật.</p>'}`:s.assignments.map(classAssignmentMarkup).join('')||'<p>Chưa giao bài tập cho buổi học này.</p>'}</details>`).join('')||'<p class="card card-pad">Chưa có buổi học trong khoảng ngày này.</p>'}</div>`;
            body.querySelector('#class-filter').onsubmit=e=>{e.preventDefault();const f=new FormData(e.currentTarget);ctx.classFrom=f.get('from');ctx.classTo=f.get('to');loadClass();};
            body.querySelectorAll('[data-class-submit]').forEach(form=>form.onsubmit=event=>{event.preventDefault();submitClassAssignment(form);});
            if(ctx.classTab==='assignments'&&ctx.grade()===5)body.insertAdjacentHTML('beforeend',ctx.homeworkPanel());
        }else if(ctx.classTab==='summary')body.innerHTML=`<section class="card card-pad"><h2>Kết quả học tập theo tháng</h2>${trendChart(d.months)}</section><section class="card card-pad"><h2>Chu kỳ học · mỗi 2 tuần</h2>${d.cycles.map(c=>`<div class="list-row"><div><strong>${c.from} ~ ${c.to}</strong><small>Trung bình: ${c.average??'Chưa có điểm'}</small></div><button type="button" class="btn outline" data-class-ranking="cycle" data-value="${c.index}">Xếp hạng</button></div>`).join('')||'<p>Chưa có chu kỳ học.</p>'}</section>`;
        else body.innerHTML=`<section class="card card-pad"><h2>Học phí theo tháng</h2><div class="table-scroll"><table><thead><tr><th>Tháng</th><th>Số buổi tính phí</th><th>Học phí</th><th>Trạng thái</th></tr></thead><tbody>${d.fees.map(f=>`<tr><td><button type="button" class="btn outline" data-fee="${f.id}">${ctx.escape(f.month)}</button><small class="tuition-source-label">${f.source==='calculated'?'Theo điểm danh đã lưu':'Nhập thủ công'}</small></td><td>${f.charged_count??f.count}<small>${f.source==='calculated'?'Đơn giá: '+ctx.content.format(f.session_fee)+'đ/buổi':'Điểm danh hiện tại'}</small></td><td><strong>${ctx.content.format(f.amount)}đ</strong></td><td>${ctx.badge(ctx.feePaidLabel(f),f.paid_at||f.amount===0?'sage':'peach')}</td></tr>`).join('')}</tbody></table></div>${d.fees.length?'':'<p>Chưa có học phí được cập nhật.</p>'}</section>`;
    }

async function showClassRanking(kind,value) {
        const result=await PlatformAPI.request('classes/'+ctx.classData.class.id+'/ranking?'+new URLSearchParams({[kind]:value}));
        ctx.host.showModal(`<h2 class="modal-title">${kind==='cycle'?'Xếp hạng chu kỳ':'Bảng điểm bài tập'}</h2><div class="table-scroll"><table><thead><tr><th>Hạng</th><th>Học sinh</th><th>Điểm</th></tr></thead><tbody>${result.rows.map(r=>`<tr class="${r.mine?'mine':''}"><td>${ctx.medal(r.rank)}</td><td>${ctx.escape(ctx.displayName(r.name))}</td><td>${r.value??'Chưa chấm'}</td></tr>`).join('')}</tbody></table></div>`);
    }

async function showFee(id) {
        ctx.stopPaymentWatch();
        const f=ctx.classData.fees.find(f=>f.id===Number(id));if(!f)return;
        const calculated=f.source==='calculated',sessions=[...(f.sessions||[])].sort((a,b)=>String(ctx.feeSessionTime(a)).localeCompare(String(ctx.feeSessionTime(b)))||a.id-b.id),charged=f.charged_count??f.count??0;
        const source=calculated?'Tính theo điểm danh đã lưu':'Học phí nhập thủ công';
        const family=ctx.live?PlatformAPI.familyState:null;
        const studentId=family?.activeProfile?.childId??family?.selectedChildId;
        const addToCart=f.amount>0&&!f.paid_at?(window.FamilyCart?.feeLink({studentId,feeId:f.id})||''):'';
        const formula=calculated?`<div class="tuition-formula" aria-label="Đơn giá đã lưu nhân số buổi tính phí"><span><b>${ctx.content.format(f.session_fee)}đ</b><small>Đơn giá / buổi</small></span><i aria-hidden="true">×</i><span><b>${charged} buổi</b><small>Có học · tính phí</small></span></div>`:'<p class="tuition-manual-note">Số tiền do thầy cô cập nhật. Điểm danh bên dưới là thông tin hiện tại để tham khảo.</p>';
        ctx.host.showModal(`<article class="tuition-detail" data-fee-detail="${f.id}"><p class="tuition-kicker">${source}</p><h2 class="modal-title" id="fee-detail-title">Học phí tháng ${ctx.escape(f.month)}</h2><section class="tuition-bill-summary" aria-label="Thông tin học phí">${formula}<div class="tuition-total"><span>Tổng học phí</span><strong data-fee-amount>${ctx.content.format(f.amount)}đ</strong>${ctx.badge(ctx.feePaidLabel(f),f.paid_at||f.amount===0?'sage':'peach')}</div></section>${calculated?`<p class="tuition-snapshot-note">Bảng kê đã lưu${f.calculated_at?' lúc '+ctx.escape(ctx.accountDate(f.calculated_at)):''}. Đơn giá và điểm danh dưới đây thuộc lần lập học phí này.</p>`:''}${ctx.calendarHtml(f.month,sessions)}<section class="tuition-session-section" aria-labelledby="fee-session-heading"><h3 id="fee-session-heading">Chi tiết từng buổi${calculated?' đã lưu':''}</h3><ol class="tuition-session-list">${sessions.map(session=>`<li data-fee-session="${session.id}"><div><time datetime="${ctx.escape(ctx.feeSessionTime(session)||session.date||'')}">${ctx.escape(ctx.feeSessionTime(session)?ctx.accountDate(ctx.feeSessionTime(session)):session.date||'Chưa có thời gian')}</time><strong>${ctx.escape(session.title)}</strong></div><span class="tuition-attendance attendance-${ctx.feeStatus(session)}">${ctx.feeStatuses[ctx.feeStatus(session)]}</span></li>`).join('')||'<li>Chưa có buổi học trong tháng này.</li>'}</ol></section><div id="fee-payment" class="tuition-payment" aria-live="polite">${f.amount===0?'<p>Tháng này không phát sinh học phí. Em không cần tạo giao dịch thanh toán.</p>':f.paid_at?'<p>Học phí đã được thầy cô ghi nhận thanh toán.</p>':'<p>Đang chuẩn bị thông tin thanh toán…</p>'}</div><div class="actions tuition-close"><button class="btn outline" type="button" id="close-fee-detail">Đóng chi tiết</button></div></article>`);
        const dialog=document.querySelector('#modal'),article=document.querySelector('[data-fee-detail]'),oldLabel=dialog.getAttribute('aria-labelledby');
        dialog.setAttribute('aria-labelledby','fee-detail-title');dialog.scrollTop=0;
        const trap=event=>{
            if(event.key!=='Tab')return;
            const controls=[...dialog.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')].filter(node=>node.getClientRects().length),index=controls.indexOf(document.activeElement);
            if(!controls.length)return;
            if(event.shiftKey&&index<=0){event.preventDefault();controls.at(-1).focus();}
            else if(!event.shiftKey&&(index<0||index===controls.length-1)){event.preventDefault();controls[0].focus();}
        };
        dialog.addEventListener('keydown',trap);
        document.querySelector('#close-fee-detail').onclick=()=>dialog.close();
        dialog.addEventListener('close',()=>{if(ctx.paymentWatch?.target.closest('[data-fee-detail]')===article)ctx.stopPaymentWatch();dialog.removeEventListener('keydown',trap);if(oldLabel===null)dialog.removeAttribute('aria-labelledby');else dialog.setAttribute('aria-labelledby',oldLabel);document.querySelector(`[data-fee="${f.id}"]`)?.focus({preventScroll:true});},{once:true});
        if(!f.paid_at&&f.amount>0){
            const target=article.querySelector('#fee-payment'),classId=ctx.classData.class.id;
            target.innerHTML=`<div class="actions">${addToCart}<button class="btn ${addToCart?'outline':'dark'}" type="button" data-fee-pay-separately>Thanh toán riêng</button></div>`;
            target.querySelector('[data-fee-pay-separately]').onclick=()=>ctx.startPaymentView(target,{feeId:f.id},{dialog,classId});
        }
    }
const views = {
classroom() { return liveClassroom(); }
};
const actions = {
'class-preview':() => document.querySelector('#live-class')?.click() || ctx.host.showModal('<h2 class="modal-title">Buổi học mẫu 45 phút</h2><ol><li>5 phút khởi động.</li><li>10 phút giải thích bằng ví dụ.</li><li>15 phút học sinh tự làm.</li><li>10 phút chữa bài.</li><li>5 phút củng cố.</li></ol><p>Lịch học và phòng Zoom đang chờ thiết lập.</p>')
};
return {views,actions,liveClassroom,trendChart,loadClass,readClassSection,classAssignmentMarkup,submitClassAssignment,renderClassBody,showClassRanking,showFee};
}
const api={create};(global.LearningFeatures??={})['classroom']=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
