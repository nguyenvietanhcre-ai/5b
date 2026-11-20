(() => {
    'use strict';
    const app=document.getElementById('support-app'), notice=document.getElementById('support-status');
    if(!app||!notice)return;
    const admin=location.pathname.startsWith('/quan-tri/website');
    const base='/api/website/'+(admin?'admin':'support');
    const kinds={support:'Hỗ trợ tài khoản / học tập',order:'Vấn đề về đơn hàng',refund:'Đề nghị hoàn tiền',data_access:'Yêu cầu truy cập dữ liệu',data_correct:'Yêu cầu chỉnh sửa dữ liệu',data_delete:'Yêu cầu xóa dữ liệu',consent_withdraw:'Rút lại sự đồng ý'};
    const statuses={received:'Đã tiếp nhận',reviewing:'Đang kiểm tra',waiting_user:'Chờ bổ sung',resolved:'Đã kết luận',rejected:'Không chấp nhận'};
    let csrf='',familyContext='',busy=false,leaving=false,familyRevision=0,checkingFamily=false,pinPromptOpen=false;
    function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
    function button(text,fn,secondary=false){const n=el('button',text,secondary?'secondary':'');n.type='button';n.addEventListener('click',()=>run(fn));return n;}
    function status(text){notice.textContent=text;}
    function invalidateFamily() {
        if(leaving)return;
        leaving=true;familyRevision++;csrf='';familyContext='';app.replaceChildren();app.style.visibility='hidden';
        status('Quyền phụ huynh đã thay đổi. Đang mở lại góc gia đình…');
        location.replace('/gia-dinh/?next=%2Fho-tro%2F');
    }
    async function request(path='',body){
        if(leaving)throw Object.assign(new Error('Phiên gia đình đã thay đổi.'),{status:403});
        const context=familyContext,revision=familyRevision;
        const r=await fetch(base+path,{credentials:'same-origin',cache:'no-store',method:body===undefined?'GET':'POST',headers:{...(context?{'X-Family-Context':context}:{}),...(body===undefined?{}:{'Content-Type':'application/json','X-CSRF-Token':csrf})},body:body===undefined?undefined:JSON.stringify(body)});
        if(context&&[401,403].includes(r.status))invalidateFamily();
        let data={};try{data=await r.json();}catch{}
        if(leaving||revision!==familyRevision)throw Object.assign(new Error('Phiên gia đình đã thay đổi.'),{status:[401,403].includes(r.status)?r.status:403});
        if(!r.ok)throw Object.assign(new Error(data.error||data.message||'Chưa thực hiện được yêu cầu.'),{status:r.status});
        return data;
    }
    async function run(fn){if(busy||leaving)return;busy=true;app.querySelectorAll('button').forEach(n=>n.disabled=true);try{await fn();}catch(e){if(!leaving)status(e.message);}finally{busy=false;if(!leaving)app.querySelectorAll('button').forEach(n=>n.disabled=false);}}
    async function readFamily(){
        if(window.FamilyProfiles){
            await FamilyProfiles.init();const family=await FamilyProfiles.refresh();
            if(family?.authenticated&&!admin){
                const header=document.querySelector('.support-header');
                if(header){let host=header.querySelector('[data-family-profile-menu]');if(!host){host=el('div');host.dataset.familyProfileMenu='';header.append(host);}FamilyProfiles.mount(host);}
                const link=header?.querySelector('a[href="/goc-hoc-tap/"]');if(link&&family.activeProfile?.type==='parent'){link.href='/gia-dinh/?view=parent';link.textContent='Góc Phụ Huynh';}
            }
            return family;
        }
        const response=await fetch('/api/family/state',{credentials:'same-origin',cache:'no-store'});
        if(!response.ok)throw new Error('Chưa thể xác nhận phiên.');return response.json();
    }
    function parentPinHere(){
        if(pinPromptOpen&&document.querySelector('dialog.family-profile-dialog[open]'))return;
        pinPromptOpen=true;familyRevision++;checkingFamily=false;
        app.style.visibility='hidden';status('Nhập PIN phụ huynh để tiếp tục tại trang này.');notice.append(button('Mở bằng PIN',parentPinHere,true));
        if(!window.FamilyProfiles)return;
        FamilyProfiles.open({target:'parent',stay:true,onSuccess:async()=>{
            pinPromptOpen=false;
            const family=await readFamily();if(!family.authenticated||family.scope!=='parent_full'){invalidateFamily();return;}
            csrf=family.csrf;familyContext=family.context;familyRevision++;app.style.visibility='';
            if(!app.querySelector('form')&&!app.querySelector('.support-tabs')){app.replaceChildren();await run(boot);}
            else status('Đã mở bằng PIN. Ba mẹ có thể tiếp tục.');
        }});
    }
    async function validateFamily(){
        if(admin||!familyContext||leaving||checkingFamily)return;
        checkingFamily=true;app.style.visibility='hidden';
        const context=familyContext,revision=familyRevision,controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
        try{
            const family=await readFamily();
            if(leaving||revision!==familyRevision)return;
            if(family.authenticated&&family.activeProfile?.type==='parent'&&family.scope!=='parent_full'){parentPinHere();return;}
            if(!family.authenticated||family.scope!=='parent_full'||family.context!==context){invalidateFamily();return;}
            csrf=family.csrf;app.style.visibility='';status('Phiên phụ huynh đã được xác nhận.');
        }catch{if(!leaving){status('Chưa thể xác nhận phiên phụ huynh. Kiểm tra mạng rồi thử lại.');notice.append(button('Thử kiểm tra lại',validateFamily,true));}}
        finally{clearTimeout(timer);checkingFamily=false;}
    }
    if(!admin&&typeof BroadcastChannel==='function'){
        const channel=new BroadcastChannel('5bmath-family-context');
        channel.addEventListener('message',event=>{if(event.data?.type==='changed'&&event.data.source!==window.FamilyProfiles?.source&&familyContext)invalidateFamily();});
    }
    addEventListener('blur',()=>{if(familyContext&&!leaving)app.style.visibility='hidden';});
    addEventListener('focus',validateFamily);
    addEventListener('family-privilege-expired',()=>{if(familyContext&&!leaving)parentPinHere();});
    addEventListener('family-profile-changed',event=>{const before=event.detail?.previous,after=event.detail?.state;if(!admin&&before?.activeProfile?.type==='parent'&&after?.activeProfile?.type!=='parent'){leaving=true;familyRevision++;csrf='';familyContext='';app.replaceChildren();app.style.visibility='hidden';}});
    document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='visible')validateFamily();else if(familyContext&&!leaving)app.style.visibility='hidden';});
    function field(form,name,label,type='text',value='',options){const wrap=el('label',label),n=el(type==='textarea'?'textarea':type==='select'?'select':'input');n.name=name;if(n.tagName==='INPUT')n.type=type;n.value=value;n.maxLength=type==='textarea'?4000:200;if(options)Object.entries(options).forEach(([key,text])=>{const o=el('option',text);o.value=key;n.append(o);});n.value=value;wrap.append(n);form.append(wrap);return n;}
    function submit(form,label,fn){const b=el('button',label);b.type='submit';form.append(b);form.addEventListener('submit',e=>{e.preventDefault();run(()=>fn(Object.fromEntries(new FormData(form))));});}
    function card(title){const c=el('section',undefined,'support-card');c.append(el('h2',title));return c;}
    function tabs(){app.replaceChildren();const nav=el('nav',undefined,'support-tabs');nav.setAttribute('aria-label','Chức năng hỗ trợ');nav.append(button('Danh sách yêu cầu',list));if(!admin)nav.append(button('Gửi yêu cầu mới',create),button('Dữ liệu của tôi',exports));else nav.append(button('Thông tin chủ quản',config),button('Chính sách nháp',policies));app.append(nav);return app;}
    async function list(cursor){tabs();const data=await request('/requests'+(cursor?'?before='+encodeURIComponent(cursor):''));const section=card(admin?'Yêu cầu của người dùng':'Yêu cầu của tôi');if(!data.requests.length)section.append(el('p','Chưa có yêu cầu.'));const grid=el('div',undefined,'support-grid');data.requests.forEach(row=>{const c=card(row.subject);c.append(el('p',row.ticket,'support-ticket'),el('p',`${kinds[row.kind]||row.kind} · ${statuses[row.status]||row.status}`),el('p',new Date(row.updated_at).toLocaleString('vi-VN')),button('Xem lịch sử và phản hồi',()=>detail(row.id)));grid.append(c);});section.append(grid);if(data.nextCursor)section.append(button('Xem yêu cầu cũ hơn',()=>list(data.nextCursor)));app.append(section);status('Đã tải yêu cầu.');}
    async function create(){tabs();const c=card('Gửi yêu cầu'),f=el('form',undefined,'support-form');field(f,'kind','Loại yêu cầu','select','support',kinds);const subject=field(f,'subject','Tiêu đề');subject.required=true;subject.maxLength=150;const order=field(f,'orderId','ID đơn hàng (bắt buộc với đơn hàng / hoàn tiền)','number');order.min=1;c.append(el('p','Có thể xem ID đơn ở lịch sử thanh toán. Yêu cầu xóa/sửa dữ liệu và rút đồng ý cần nêu phạm vi, lý do và phần cần kiểm tra.'));const m=field(f,'message','Nội dung và phạm vi cần hỗ trợ','textarea');m.required=true;submit(f,'Gửi và nhận mã yêu cầu',async b=>{b.orderId=b.orderId?Number(b.orderId):null;const data=await request('/requests',b);await detail(data.request.id);status('Đã tiếp nhận '+data.request.ticket+'. Theo dõi phản hồi tại trang này.');});c.append(f);app.append(c);status('Điền thông tin cần hỗ trợ.');}
    async function detail(id){const {request:row}=await request('/requests/'+id);tabs();const c=card(row.subject);c.append(el('p',`${row.ticket} · ${statuses[row.status]} · ${kinds[row.kind]}`,'support-ticket'));if(row.order_id)c.append(el('p','ID đơn: '+row.order_id));row.events.forEach(e=>{const n=el('div',undefined,'support-event');n.append(el('strong',`${e.actor==='admin'?'5BMath':'Bạn'} · ${statuses[e.status]} · ${new Date(e.created_at).toLocaleString('vi-VN')}`),el('p',e.message));c.append(n);});row.refunds.forEach(r=>c.append(el('p',`Ghi nhận hoàn thủ công: ${r.amount.toLocaleString('vi-VN')}đ · ${r.reference}. Không tự điều chỉnh quyền học.`)));const open=!['resolved','rejected'].includes(row.status);if(open){const f=el('form',undefined,'support-form'),m=field(f,'message','Bổ sung / phản hồi','textarea');m.required=true;submit(f,'Gửi phản hồi',async b=>{await request('/requests/'+id+'/reply',{...b,revision:row.revision});await detail(id);status('Đã lưu phản hồi.');});c.append(f);}if(admin&&open){const f=el('form',undefined,'support-form');f.append(el('h3','Cập nhật trạng thái và kết luận'));const allowed=row.status==='received'?['reviewing','waiting_user','resolved','rejected']:row.status==='reviewing'?['waiting_user','resolved','rejected']:['reviewing','resolved','rejected'];field(f,'status','Trạng thái','select',allowed[0],Object.fromEntries(allowed.map(s=>[s,statuses[s]])));const m=field(f,'message','Lý do / kết luận bắt buộc','textarea');m.required=true;f.append(el('p','Kết luận chỉ ghi nhận xử lý. Không tự xóa dữ liệu, thu hồi đồng ý hay thay đổi quyền. Ghi rõ việc đã thực hiện và việc còn chờ.'));submit(f,'Lưu trạng thái',async b=>{await request('/requests/'+id+'/status',{...b,revision:row.revision});await detail(id);status('Đã lưu trạng thái có lịch sử.');});c.append(f);if(row.kind==='refund'){const f2=el('form',undefined,'support-form');f2.append(el('h3','Ghi khoản đã hoàn tiền thủ công'));const a=field(f2,'amount','Số tiền đã hoàn (VND)','number');a.min=1;a.step=1;a.required=true;field(f2,'reference','Mã giao dịch hoàn tiền').required=true;field(f2,'message','Kết quả đối soát / lý do','textarea').required=true;f2.append(el('p','Chỉ dùng sau khi đã hoàn tiền ngoài hệ thống. Không gọi ngân hàng và không tự thay đổi quyền. Tổng ghi nhận không được vượt số tiền đơn đã thanh toán.'));submit(f2,'Ghi nhận khoản đã hoàn',async b=>{b.amount=Number(b.amount);await request('/requests/'+id+'/refund',{...b,revision:row.revision});await detail(id);status('Đã ghi khoản hoàn thủ công.');});c.append(f2);}}app.append(c);status('Đã tải lịch sử yêu cầu.');}
    async function exports(){tabs();const c=card('Xem và tải dữ liệu của chính tôi');c.append(el('p','Bản trích xuất một phần gồm hồ sơ, đơn thanh toán và hỗ trợ. Chưa gồm toàn bộ tiến trình học hay tệp nộp bài; gửi yêu cầu truy cập dữ liệu nếu cần bổ sung. File có dữ liệu cá nhân, hãy lưu trên thiết bị riêng.'));const {export:data}=await request('/export/preview');c.append(el('p',data.scope));const preview=el('details');preview.append(el('summary','Xem trước nội dung file'),el('pre',JSON.stringify(data,null,2)));c.append(preview,button('Tải file JSON',async()=>{const result=await request('/export/download');const url=URL.createObjectURL(new Blob([JSON.stringify(result.export,null,2)],{type:'application/json'}));const a=el('a');a.href=url;a.download=result.filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);status('Đã tạo file tải xuống trên thiết bị này.');}));app.append(c);status('Đã tạo bản xem trước.');}
    async function config(){tabs();const data=await request('/config'),c=card('Thông tin chủ quản website'),f=el('form',undefined,'support-form');c.append(el('p','Trường trống là thông tin chưa có. Lưu thông tin không đồng nghĩa hồ sơ Bộ Công Thương đã được duyệt.'));const labels={legal_name:'Tên hộ kinh doanh / chủ quản',registration_number:'Số đăng ký',tax_code:'Mã số thuế',representative:'Người chịu trách nhiệm website (không nhập CCCD)',address:'Địa chỉ',phone:'Điện thoại',email:'Email hỗ trợ'};Object.entries(labels).forEach(([key,label])=>field(f,key,label,key==='email'?'email':'text',data.business[key]));submit(f,'Lưu thông tin',async b=>{await request('/config',{...b,revision:data.revision});await config();status('Đã lưu thông tin chủ quản.');});c.append(f);app.append(c);status('Thông tin cần chủ quản xác nhận.');}
    async function policies(){tabs();const {policies:rows}=await request('/policies'),c=card('Phiên bản chính sách nháp');c.append(el('p','Các phiên bản ở đây chỉ là bản nháp nội bộ. Lưu bản nháp không cập nhật chính sách công khai hoặc đánh dấu đã duyệt.'));rows.forEach(r=>{const d=el('details');d.append(el('summary',`${r.version} · ${r.title} · Bản nháp`),el('pre',r.content));c.append(d);});const f=el('form',undefined,'support-form');field(f,'version','Mã phiên bản nháp mới').required=true;field(f,'title','Tiêu đề').required=true;const content=field(f,'content','Nội dung nháp','textarea');content.maxLength=30000;content.required=true;submit(f,'Lưu phiên bản nháp',async b=>{await request('/policies',b);await policies();status('Đã lưu bản nháp, chưa phát hành.');});c.append(f);app.append(c);status('Đang xem các bản nháp nội bộ.');}
    async function boot(){if(!admin){const family=await readFamily();if(family){if(family.authenticated){familyContext=family.context;csrf=family.csrf;if(family.scope!=='parent_full'){app.append(button('Mở bằng PIN phụ huynh',parentPinHere));parentPinHere();return;}}}}if(admin){document.querySelector('h1').textContent='Quản trị website';document.title='Quản trị website | 5BMath';const r=await fetch('/api/staff/session',{credentials:'same-origin',cache:'no-store'}),s=await r.json();if(!s.authenticated||s.user?.role!=='admin'){status('Cần đăng nhập tài khoản quản trị để tiếp tục.');const a=el('a','Mở trang đăng nhập quản trị','support-button');a.href='/quan-tri/';app.append(a);return;}csrf=s.csrf;}else{try{const s=await request('/session');csrf=s.csrf;}catch(e){if(leaving)return;status('Đăng nhập tài khoản học sinh hiện có để gửi và theo dõi yêu cầu.');const a=el('a','Đăng nhập ở Góc học tập','support-button');a.href='/goc-hoc-tap/';app.append(a);return;}}await list();}
    run(boot);
})();
