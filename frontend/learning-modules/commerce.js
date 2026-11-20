/* commerce: extracted behavior; state and cross-feature services supplied explicitly. */
(function(global){'use strict';
function create(ctx){
function svipPlan(registration=false) {
        const features=['🌱 Không giới hạn chức năng trên 5bmath.vn','👩‍🏫 Lớp sĩ số nhỏ, giáo viên sát sao','💬 Review từng học sinh sau mỗi buổi học','📝 Mini test mỗi buổi học','🏆 Big test mỗi tháng'];
        return `<section class="card card-pad plan gold">${ctx.badge('👑 SVip','gold')}<h2>${registration?'Học Zoom online':'SVip / Học Zoom online'}</h2><strong class="plan-price">${registration?'Học phí: 100k/buổi':'100k/Buổi'}</strong><ul>${features.map(text=>`<li class="plan-highlight">${text}</li>`).join('')}</ul><p class="free-highlight"><mark>MIỄN PHÍ</mark> 1 buổi trao đổi 1-1 với giáo viên mỗi tháng</p>${registration?'<div class="actions"><a class="btn dark" href="dang-ky-kiem-tra-dau-vao/">Đăng ký kiểm tra đầu vào</a><a class="btn outline" href="https://zalo.me/0984763971" target="_blank" rel="noopener noreferrer">Đăng ký tư vấn · Zalo</a><a class="btn outline" href="https://www.facebook.com/5bmath" target="_blank" rel="noopener noreferrer">Đăng ký tư vấn · Facebook</a></div>':'<a class="btn dark" href="https://zalo.me/0984763971" target="_blank" rel="noopener noreferrer">Đăng ký tư vấn</a>'}</section>`;
    }

function upgradeView(beneficiary,account) {
        const period=ctx.query('period')==='year'?'year':'month',year=period==='year';
        const parent=Boolean(beneficiary),membership=account?.membership??ctx.member();
        const target=parent?{childId:beneficiary.id}:{};
        function purchaseButtons(plan){
            if(plan==='Free')return membership===plan?'<span class="tag sage">Gói hiện tại</span>':'<span class="tag">Miễn phí</span>';
            if(membership==='SVip')return '<span class="tag sage">Đã có quyền qua lớp Zoom</span>';
            if(membership==='VIP+'&&plan==='VIP')return '<span class="tag">Đã bao gồm trong VIP+</span>';
            const renewal=membership===plan;
            const buy='<a class="btn dark"'+(parent?' data-plan-buy':'')+' href="'+ctx.escape(ctx.href('payment',{...target,plan,period}))+'">'+(parent?'Mua ngay':renewal?'Gia hạn '+plan:'Chọn '+plan+' →')+'</a>';
            const add=parent?FamilyCart.planButton({studentId:beneficiary.id,plan,period}):'';
            return (renewal?'<span class="tag sage">Gói hiện tại</span>':'')+(add?'<div class="plan-purchase-actions">'+buy+add+'</div>':buy);
        }
        const plans=[
            {name:'Free',price:'0đ',style:'bronze',copy:'Bắt đầu xây nền tảng',features:['Học liệu miễn phí và lượt luyện tập theo gói Free','Xem 3 video đầu của mỗi series','Ôn theo trường và câu chuyên sâu: chưa mở']},
            {name:'VIP',price:year?'1.000.000đ':'100.000đ',style:'silver',copy:'Luyện đều, hiểu chắc',features:[year?'30 câu mới/ngày · 3.600 câu cho cả chu kỳ 12 tháng':'30 câu mới/ngày · 300 câu cho chu kỳ 30 ngày','Quyền luyện tập và tải tài liệu của VIP','Xem trọn các series video khi được phát hành','Nội dung video được sắp xếp trong Bài giảng','Ôn theo trường và câu chuyên sâu: dành cho VIP+']},
            {name:'VIP+',price:year?'2.000.000đ':'200.000đ',style:'gold vip-plus',copy:'Chinh phục mục tiêu cao',features:[year?'30 câu mới/ngày · 3.600 câu cho cả chu kỳ 12 tháng':'30 câu mới/ngày · 300 câu cho chu kỳ 30 ngày','Bao gồm quyền lợi VIP','Mở ôn luyện theo đề của trường · Khối 5','Mở câu siêu khó và câu phân loại học sinh','Mở nội dung thi học sinh giỏi']}
        ];
        return (parent?'':ctx.intro('Nâng cấp gói','Chọn hành trình học phù hợp với em.'))+'<nav class="billing-period-selector" aria-label="Kỳ đăng ký">'+[['month','Theo tháng'],['year','Theo năm']].map(([key,label])=>'<a class="btn '+(period===key?'dark':'outline')+'" href="'+ctx.escape(ctx.href('upgrade',{...target,period:key}))+'" '+(period===key?'aria-current="page"':'')+'>'+label+'</a>').join('')+'</nav><p class="billing-period-note">Gói năm có 12 tháng sử dụng. Hạn mức 30 câu mới/ngày, tổng 3.600 câu cả chu kỳ; không đặt lại mỗi tháng.</p>'+'<div class="plan-benefit-banner"><strong>✦ Học thêm mỗi ngày, tiến xa từng bước</strong><p>Free xem 3 video đầu mỗi series. VIP và VIP+ xem trọn series đã phát hành.</p></div><div class="grid3 plans subscription-plans">'+plans.map(p=>'<section class="card card-pad plan '+p.style+'">'+(p.name==='VIP+'?'<span class="plan-ribbon">TRỌN QUYỀN HỌC NÂNG CAO</span>':'')+ctx.badge(p.name,p.name==='Free'?'sage':'sand')+'<h2>'+p.name+'</h2><p>'+p.copy+'</p><p class="plan-price">'+p.price+(p.name==='Free'?'':'<small>/'+(year?'năm':'tháng')+'</small>')+'</p><ul>'+p.features.map(f=>'<li>'+f+'</li>').join('')+'</ul>'+purchaseButtons(p.name)+'</section>').join('')+'</div>'+(parent?FamilyCart.planCatalog(beneficiary.id):'')+'<section class="card card-pad premium-availability"><h2>Nội dung sẽ có gì?</h2><p>Các series, câu chuyên sâu và bộ đề chỉ mở khi nội dung tương ứng đã được biên tập và phát hành. Quyền gói không thay thế phí mua bộ đề riêng.</p><a class="btn outline" href="'+ctx.href('weekly',{tab:'giai-de-10-phut'})+'#premium-library">Xem series và kho đề</a></section><section class="card card-pad consultation"><h2>Học Zoom cùng giáo viên</h2><p>Lớp Zoom được tư vấn và đăng ký riêng.</p><a class="btn outline" href="'+ctx.href('zoomRegistration')+'">Đăng ký học Zoom</a></section>';
    }

function planChildSummary(child,account){
        const {membership}=account;
        const expiry=membership==='VIP+'?account.vipPlusExpiresAt:membership==='VIP'?account.vipExpiresAt:null;
        const quota=membership==='Free'?[['content','Ôn theo nội dung'],['combined','Đề tổng hợp']].map(([key,label])=>{
            const allowance=account.usage?.[key];
            return Number.isInteger(allowance?.limit)&&Number.isInteger(allowance.used)?`<p>${label} còn <strong>${Math.max(0,allowance.limit-allowance.used)}</strong> lượt hôm nay</p>`:'';
        }).join(''):'';
        return `<section class="card card-pad" data-plan-child-summary data-student-id="${ctx.escape(child.id)}"><h2>${ctx.escape(child.nickname||child.name)} · Lớp ${ctx.escape(child.grade)}</h2><p>Gói hiện tại <strong data-plan-membership>${membership==='SVip'?'SVip · Lớp Zoom':ctx.escape(membership)}</strong></p>${Date.parse(expiry)>Date.now()?`<p>Có hiệu lực đến <time datetime="${ctx.escape(expiry)}">${ctx.escape(ctx.accountDate(expiry))}</time></p>`:''}${quota}</section>`;
    }

function mountParentPlans(){
        const app=document.getElementById('learning-app'),picker=app?.querySelector('#parent-plan-picker');
        const panel=app?.querySelector('[data-parent-plan-details]');
        if(!picker||!panel)return;
        const profiles=window.FamilyProfiles;
        const selectedNote=picker.querySelector('[data-parent-plan-current]');
        const entry=app.querySelector('[data-family-cart-link]');
        const familyId=profiles.state.family?.id;
        let controller,context,beneficiaryId;
        const sameParent=family=>family.authenticated&&family.activeProfile?.type==='parent'&&family.scope==='parent_full'&&!family.device?.childOnly&&family.family?.id===familyId;
        function clear(message){
            controller?.abort();controller=null;context=null;beneficiaryId=null;
            panel.removeAttribute('aria-busy');
            panel.hidden=!message;panel.replaceChildren();
            if(message){const status=document.createElement('p');status.setAttribute('role','status');status.textContent=message;panel.append(status);}
        }
        function onLoading(child){
            ctx.stopPaymentWatch();
            const dialog=document.getElementById('modal');
            if(dialog?.open&&dialog.querySelector('.checkout-review,.tuition-detail,.payment-order'))dialog.close();
            clear('Đang tải gói học, số dư và học phí…');
            selectedNote.textContent='Đã chọn '+(child.nickname||child.name)+' · Lớp '+child.grade;
            panel.setAttribute('aria-busy','true');
        }
        function onError(child,error){
            if(!panel.isConnected||!sameParent(profiles.state))return;
            clear('Chưa tải được gói học của '+(child.nickname||child.name)+'. '+(error.message||'Ba mẹ vui lòng thử lại.'));
            const retry=document.createElement('button');retry.className='btn outline';retry.type='button';retry.dataset.planRetry='';retry.textContent='Thử lại';
            retry.onclick=()=>choose(child.id);panel.append(retry);
            if(error.code==='family_parent_pin_required')profiles.refresh().catch(()=>{});
        }
        async function load(family,initialSnapshot){
            const child=family.children?.find(profile=>String(profile.id)===String(family.selectedChildId));
            if(!child||!sameParent(family)||!family.context)return;
            const pending=context=family.context;
            beneficiaryId=String(child.id);
            const request=new AbortController();controller=request;
            const active=()=>panel.isConnected&&controller===request&&sameParent(profiles.state)&&profiles.state.context===pending&&String(profiles.state.selectedChildId)===String(child.id);
            try{
                const [snapshot,planData]=await Promise.all([
                    initialSnapshot||PlatformAPI.request('session',undefined,{signal:request.signal}),
                    FamilyCart.loadPlanData(child.id,request.signal)
                ]);
                if(!active())return;
                const account=snapshot.account;
                if(!snapshot.authenticated||snapshot.csrf!==family.csrf||!['Free','VIP','VIP+','SVip'].includes(account?.membership))throw new Error('Thông tin gói chưa sẵn sàng.');
                const url=new URL(location.href);url.searchParams.set('childId',child.id);url.searchParams.delete('child');
                history.replaceState(history.state,'',url);
                panel.innerHTML=planChildSummary(child,account)+upgradeView(child,account);
                FamilyCart.mountPlans(app,{...planData,context:pending});
                panel.removeAttribute('aria-busy');
                selectedNote.textContent='Đang xem gói học cho '+(child.nickname||child.name)+' · Lớp '+child.grade;
            }catch(error){if(active())onError(child,error);}
        }
        const choose=ParentPlanPicker.mount(picker,{onLoading,onSelected:load,onError});
        function invalidate(){
            clear();selectedNote.textContent='Ba mẹ chọn một con để xem gói học.';
            if(entry)entry.textContent='Giỏ hàng';
        }
        function stateChanged(event){
            const family=event.detail?.state||profiles.state;
            if(!sameParent(family)||(context&&(family.context!==context||String(family.selectedChildId)!==beneficiaryId)))invalidate();
        }
        function openSelected(snapshot){
            const family=profiles.state;
            if(!sameParent(family))return invalidate();
            const requested=ctx.query('childId')||ctx.query('child');
            const child=family.children?.find(profile=>String(profile.id)===String(family.selectedChildId));
            if(requested&&requested!==String(child?.id)){
                const select=picker.querySelector('select');
                if(family.children?.some(profile=>String(profile.id)===requested))select.value=requested;
                selectedNote.textContent='Ba mẹ xác nhận lại con trước khi tiếp tục.';
                return clear();
            }
            if(child){onLoading(child);load(family,snapshot?.csrf===family.csrf&&snapshot.account?.membership?snapshot:undefined);}
        }
        const restore=event=>{if(event.persisted)openSelected();};
        window.addEventListener('family-state-updated',stateChanged);
        window.addEventListener('family-access-invalidated',invalidate);
        window.addEventListener('pageshow',restore);
        ctx.unmountParentPlans=()=>{
            controller?.abort();controller=null;
            window.removeEventListener('family-state-updated',stateChanged);
            window.removeEventListener('family-access-invalidated',invalidate);
            window.removeEventListener('pageshow',restore);
        };
        openSelected(PlatformAPI.snapshot);
    }

function paymentMarkup(o) {
        const paid=o.status==='paid',cancelled=o.status==='cancelled',pending=o.status==='pending';
        const label=paid?'Đã hoàn thành':cancelled?'Đã hủy':'Chờ xác nhận thanh toán';
        const status=paid?(o.fee_id?'Học phí đã được ghi nhận thanh toán.':'Thanh toán thành công. Quyền học đã được ghi nhận cho tài khoản của em.'):cancelled?'Đơn này đã hủy. Em hãy liên hệ 5BMath để kiểm tra trước khi chuyển tiền.':o.automationEnabled?'Trang sẽ tự cập nhật khi giao dịch chuyển khoản được xác nhận.':'Quyền học được cập nhật sau khi 5BMath xác nhận khoản tiền đã nhận.';
        return `<div class="payment-order" data-payment-order="${Number(o.id)}" data-payment-status="${ctx.escape(o.status)}"><div class="payment-heading"><h3>${o.purchase_type==='exam'?ctx.escape(o.exam_title):o.fee_id?'Thanh toán học phí':'Nâng cấp '+ctx.escape(o.subscription_plan||'VIP')+' · '+(o.subscription_period==='year'?'1 năm · 12 tháng':Number(o.vip_months||1)+' tháng')}</h3>${ctx.badge(label,paid?'sage':'peach')}</div><dl class="payment-details"><div><dt>Số tiền</dt><dd><strong>${ctx.content.format(o.amount)}đ</strong></dd></div><div><dt>Đơn hàng</dt><dd><strong>Đơn #${Number(o.id)}</strong> · ${ctx.escape(o.reference)}</dd></div>${!o.fee_id&&o.purchase_type!=='exam'&&o.subscription_period==='year'?'<div><dt>Hạn mức câu VIP gói năm</dt><dd>30 câu mới/ngày · 3.600 câu cho cả chu kỳ 12 tháng, không đặt lại mỗi tháng.</dd></div>'+((o.subscription_starts_at&&o.subscription_ends_at)?'<div><dt>Chu kỳ hạn mức câu</dt><dd>'+ctx.escape(ctx.accountDate(o.subscription_starts_at))+' → '+ctx.escape(ctx.accountDate(o.subscription_ends_at))+'</dd></div>':'<div><dt>Cấp quyền</dt><dd>Sau xác nhận thanh toán; chu kỳ câu nối tiếp thời hạn VIP hiện có, không đặt lại chu kỳ đang dùng.</dd></div>'):''}${o.bankAccount?`<div><dt>Tài khoản nhận</dt><dd>${ctx.escape(o.bank)} · ${ctx.escape(o.bankAccount)}<br>${ctx.escape(o.bankName)}</dd></div>`:''}</dl>${checkoutEvidenceMarkup(o)}${pending?(o.qrUrl?`<img class="payment-qr" src="${ctx.escape(o.qrUrl)}" alt="QR chuyển khoản ${ctx.escape(o.reference)}" width="320" height="420"><p class="payment-transfer-note">Giữ nguyên số tiền và mã thanh toán khi chuyển khoản.</p>`:'<p class="learning-notice">Thông tin ngân hàng đang chờ cấu hình. Liên hệ 5BMath để được hướng dẫn thanh toán.</p>'):''}<p class="payment-confirmation ${paid?'is-paid':''}" role="status">${ctx.escape(status)}${paid&&o.paid_at?' Xác nhận lúc '+ctx.escape(ctx.accountDate(o.paid_at))+'.':''}</p><p class="payment-feedback" data-payment-feedback role="status" hidden></p><div class="actions payment-actions">${pending?'<button class="btn dark" type="button" data-payment-retry>Kiểm tra thanh toán</button>':''}<a class="btn outline" href="/lien-he/">Liên hệ hỗ trợ</a>${!o.fee_id?ctx.link('Chọn lại gói / kỳ','payment','outline'):''}${paid&&o.purchase_type==='exam'?'<button class="btn dark" type="button" data-open-purchased-exam>Mở đề đã mua</button>':''}${paid&&!o.fee_id?ctx.link('Xem tài khoản','profile','outline'):''}</div><p>Chọn lại không tự hủy đơn đang chờ. Nếu đã chuyển tiền, hãy liên hệ hỗ trợ trước khi tạo đơn khác.</p></div>`;
    }

function checkoutStyles(){
        if(document.querySelector('[data-checkout-styles]'))return;
        const sheet=document.createElement('link');sheet.rel='stylesheet';sheet.href=new URL('checkout-readiness.css',document.baseURI).href;sheet.dataset.checkoutStyles='true';document.head.append(sheet);
    }

function checkoutEvidenceMarkup(order){
        const s=order.checkoutSnapshot;
        if(!s)return '<p class="checkout-legacy">Đơn cũ: chưa lưu bằng chứng đồng ý theo phiên bản mới. Các thông tin giao dịch đã có vẫn được giữ.</p>';
        return `<details class="checkout-evidence"><summary>Thông tin đã xác nhận khi tạo đơn</summary><p><strong>${ctx.escape(s.title)}</strong> · ${ctx.escape(s.period==='year'?'12 tháng':s.period==='month'?'1 tháng':s.period)} · Tổng ${ctx.content.format(s.total)}đ</p><ul>${(s.rights||[]).map(right=>'<li>'+ctx.escape(right)+'</li>').join('')}</ul><p>Người mua: ${ctx.escape(s.purchaser?.name)} · ${ctx.escape(s.purchaser?.contact)}<br>Vai trò tự khai: ${ctx.escape(({self:'Mua cho bản thân',parent:'Phụ huynh',representative:'Người đại diện'})[s.purchaser?.relationship]||'')}.</p><p>Đồng ý chính sách ${ctx.escape(s.acceptedPolicyVersion)} lúc ${ctx.escape(ctx.accountDate(s.acceptedAt))}. Thông tin người đại diện là tự khai.</p><a href="/phap-ly/">Xem bộ chính sách và phiên bản</a></details>`;
    }

function checkoutSummaryMarkup(p){
        return `<h3>${ctx.escape(p.title)}${p.type==='subscription'?' · '+(p.period==='year'?'12 tháng':'1 tháng'):''}</h3><p class="checkout-total">Tổng thanh toán: <strong>${ctx.content.format(p.total)}đ</strong></p><ul>${p.rights.map(right=>'<li>'+ctx.escape(right)+'</li>').join('')}</ul><p>${ctx.escape(p.fulfillment)}</p>`;
    }

async function showCheckout(context){
        if(!ctx.paymentViewActive(context)||context.reviewRendered)return;
        checkoutStyles();context.reviewRendered=true;context.target.innerHTML='<p role="status">Đang đọc lựa chọn và giá từ máy chủ…</p>';
        try{
            const result=await PlatformAPI.request('payments/preview',context.body,{signal:context.controller.signal,owner:context.owner});
            if(!ctx.paymentViewActive(context))return;
            const p=result.preview;context.quoteHash=result.quoteHash;
            if(context.beneficiaryId&&String(p.studentId)!==context.beneficiaryId)throw new Error('Hồ sơ nhận gói đã thay đổi. Ba mẹ hãy chọn lại con.');
            if(p.referralCode)context.body.referralCode=p.referralCode;
            context.target.innerHTML=`<form class="checkout-review"><h2>Xem lại trước khi tạo đơn</h2><p>Chưa tạo đơn và chưa cấp quyền. Bạn có thể sửa lựa chọn bên dưới.</p>${p.type==='subscription'?`<div class="checkout-selection"><label class="field"><span>Gói học</span><select name="plan"><option value="VIP" ${p.plan==='VIP'?'selected':''}>VIP</option><option value="VIP+" ${p.plan==='VIP+'?'selected':''}>VIP+</option></select></label><label class="field"><span>Kỳ thanh toán</span><select name="period"><option value="month" ${p.period==='month'?'selected':''}>1 tháng</option><option value="year" ${p.period==='year'?'selected':''}>12 tháng</option></select></label></div>`:''}${p.referralEligible?`<label class="field checkout-referral"><span>Mã giới thiệu (không bắt buộc)</span><input name="referralCode" autocomplete="off" maxlength="40" value="${ctx.escape(context.body.referralCode||p.referralCode||'')}"><small>Chỉ áp dụng lần đầu thanh toán thành công VIP hoặc VIP+. Người giới thiệu nhận 7 ngày của loại gói bạn mua.</small></label>`:''}<section class="checkout-summary" aria-live="polite">${checkoutSummaryMarkup(p)}</section><fieldset class="checkout-purchaser"><legend>Người mua và liên hệ</legend><label class="field"><span>Họ tên người mua</span><input name="purchaserName" autocomplete="name" maxlength="120" required></label><label class="field"><span>Email hoặc số điện thoại liên hệ</span><input name="purchaserContact" autocomplete="email" maxlength="200" required></label><label class="field"><span>Bạn mua với vai trò nào?</span><select name="relationship" required><option value="">Chọn vai trò</option><option value="self">Mua cho bản thân</option><option value="parent">Phụ huynh mua cho trẻ</option><option value="representative">Người đại diện mua cho trẻ</option></select></label><label class="checkout-check" data-representative hidden><input type="checkbox" name="representativeDeclared"><span>Tôi tự khai là phụ huynh hoặc người đại diện mua thay trẻ. Thông tin này chưa được 5BMath xác minh.</span></label></fieldset><div class="checkout-policies"><p>Bộ chính sách bản nháp <strong>${ctx.escape(p.policyVersion)}</strong>. <a href="/dieu-khoan/" target="_blank" rel="noopener">Điều khoản</a> · <a href="/thanh-toan-va-cung-cap/" target="_blank" rel="noopener">Thanh toán và cung cấp</a> · <a href="/huy-va-hoan-tien/" target="_blank" rel="noopener">Hủy và hoàn tiền</a> · <a href="/bao-ve-du-lieu/" target="_blank" rel="noopener">Bảo vệ dữ liệu</a>.</p><label class="checkout-check"><input type="checkbox" name="accepted" required><span>Tôi đã xem lại lựa chọn, tổng tiền và đồng ý bộ chính sách phiên bản ${ctx.escape(p.policyVersion)} cho đơn này.</span></label></div><p data-checkout-error role="alert" hidden></p><div class="actions"><button class="btn dark" type="submit">Xác nhận và tạo đơn thanh toán</button><a class="btn outline" href="${ctx.href('upgrade')}">Xem lại các gói</a></div><p>Yêu cầu hủy hoặc hoàn tiền được hỗ trợ xét thủ công theo chính sách; gửi yêu cầu không tự động hoàn tiền hay thay đổi quyền học.</p></form>`;
            const form=context.target.querySelector('form'),error=form.querySelector('[data-checkout-error]'),submit=form.querySelector('[type="submit"]');
            form.elements.relationship.onchange=()=>{const other=form.elements.relationship.value!=='self'&&form.elements.relationship.value!=='';form.querySelector('[data-representative]').hidden=!other;form.elements.representativeDeclared.required=other;form.elements.representativeDeclared.checked=false;};
            let revision=0,referralTimer;
            const refresh=async()=>{
                if(!ctx.paymentViewActive(context))return;
                const generation=++revision;form.elements.accepted.checked=false;submit.disabled=true;context.quoteHash=null;error.hidden=true;
                context.body={plan:form.elements.plan.value,period:form.elements.period.value,...(form.elements.referralCode?{referralCode:form.elements.referralCode.value.trim()}:context.body.referralCode?{referralCode:context.body.referralCode}:{})};
                try{const updated=await PlatformAPI.request('payments/preview',context.body,{signal:context.controller.signal,owner:context.owner});if(!ctx.paymentViewActive(context)||generation!==revision)return;context.quoteHash=updated.quoteHash;context.target.querySelector('.checkout-summary').innerHTML=checkoutSummaryMarkup(updated.preview);}
                catch(problem){if(ctx.paymentViewActive(context)&&generation===revision){error.textContent=problem.message;error.hidden=false;}}
                finally{if(ctx.paymentViewActive(context)&&generation===revision)submit.disabled=!context.quoteHash;}
            };
            if(p.type==='subscription'){form.elements.plan.onchange=refresh;form.elements.period.onchange=refresh;}
            if(form.elements.referralCode)form.elements.referralCode.oninput=()=>{revision++;clearTimeout(referralTimer);form.elements.accepted.checked=false;context.quoteHash=null;submit.disabled=true;referralTimer=setTimeout(refresh,350);};
            form.onsubmit=async event=>{
                event.preventDefault();if(!context.quoteHash||!form.reportValidity()||context.busy)return;
                context.body={...context.body,checkout:{accepted:form.elements.accepted.checked,policyVersion:p.policyVersion,quoteHash:context.quoteHash,purchaser:{name:form.elements.purchaserName.value,contact:form.elements.purchaserContact.value,relationship:form.elements.relationship.value,representativeDeclared:form.elements.representativeDeclared.checked}}};
                await createPayment(context);if(ctx.paymentViewActive(context)&&context.order&&!context.dialog)loadPaymentHistory();
            };
        }catch(error){if(ctx.paymentViewActive(context)){context.reviewRendered=false;if(error.name!=='AbortError'){context.target.innerHTML=`<p role="alert">Chưa thể xem lại đơn. ${ctx.escape(error.message)}</p><button type="button" class="btn outline" data-review-retry>Thử lại</button>`;context.target.querySelector('[data-review-retry]').onclick=()=>showCheckout(context);}}}
    }

async function loadPaymentHistory(before=null){
        const target=document.querySelector('#payment-history'),owner=ctx.accountPageOwner;if(!target||!ctx.live)return;
        if(!before)target.innerHTML='<h2>Lịch sử đơn của tài khoản</h2><div data-order-history></div><p data-order-history-status role="status">Đang đọc lịch sử…</p>';
        const status=target.querySelector('[data-order-history-status]');
        try{const result=await PlatformAPI.request('payments'+(before?'?before='+before:''));if(!target.isConnected||owner!==ctx.accountPageOwner)return;status.textContent='';target.querySelector('[data-history-more]')?.remove();const list=target.querySelector('[data-order-history]');if(!before&&!result.orders.length)status.textContent='Tài khoản chưa có đơn thanh toán.';list.insertAdjacentHTML('beforeend',result.orders.map(o=>`<article class="checkout-history-row"><h3><a href="${ctx.href('payment',{order:o.id})}">Đơn #${Number(o.id)} · ${ctx.escape(o.reference)}</a></h3><p>${ctx.escape(o.exam_title||o.checkoutSnapshot?.title||o.subscription_plan||'Học phí')} · ${ctx.content.format(o.amount)}đ · ${ctx.escape(({pending:'Chờ thanh toán',paid:'Đã thanh toán',cancelled:'Đã hủy'})[o.status]||o.status)}</p><p>Tạo lúc ${ctx.escape(ctx.accountDate(o.created_at))}</p>${checkoutEvidenceMarkup(o)}<a class="btn outline" href="${ctx.href('payment',{order:o.id})}">Xem lại đơn</a></article>`).join(''));if(result.nextBefore){const more=document.createElement('button');more.type='button';more.className='btn outline';more.dataset.historyMore='true';more.textContent='Xem đơn cũ hơn';more.onclick=()=>{more.disabled=true;loadPaymentHistory(result.nextBefore);};target.append(more);}}
        catch(error){if(target.isConnected&&owner===ctx.accountPageOwner){status.textContent='Chưa đọc được lịch sử. '+error.message;const more=target.querySelector('[data-history-more]');if(more)more.disabled=false;}}
    }

function schedulePaymentCheck(context){
        clearTimeout(context.timer);context.timer=null;
        if(ctx.paymentAvailable(context)&&context.order?.status==='pending')context.timer=setTimeout(()=>checkPayment(context),Math.min(30000,5000*Math.max(1,context.failures)));
    }

function paymentFeedback(context,message,error=false){
        if(!ctx.paymentViewActive(context))return;
        const feedback=context.target.querySelector('[data-payment-feedback]');
        if(feedback){feedback.textContent=message;feedback.hidden=!message;feedback.classList.toggle('is-error',error);}
    }

function renderPaymentOrder(context,order){
        if(!ctx.paymentViewActive(context)||Number(order.account_id)!==Number(context.owner))return false;
        if(!['pending','paid','cancelled'].includes(order.status))throw new Error('Trạng thái đơn chưa hợp lệ. Em hãy thử lại.');
        context.order=order;
        if(!context.dialog&&typeof location!=='undefined'&&typeof history!=='undefined'){
            const address=new URL(location.href);
            if(address.searchParams.get('order')!==String(order.id)){address.searchParams.set('order',String(order.id));history.replaceState(null,'',address);}
            context.resumeOrderId=Number(order.id);
        }
        const markup=paymentMarkup(order);
        if(markup!==context.markup){
            const focused=context.target.querySelector('[data-payment-retry]')===document.activeElement;
            context.target.innerHTML=markup;context.markup=markup;
            if(focused)context.target.querySelector('[data-payment-retry]')?.focus({preventScroll:true});
        }
        const retry=context.target.querySelector('[data-payment-retry]');
        if(retry)retry.onclick=()=>checkPayment(context,true);
        const open=context.target.querySelector('[data-open-purchased-exam]');
        if(open)open.onclick=async()=>{if(!ctx.paymentViewActive(context))return;open.disabled=true;try{const result=await PlatformAPI.request('premium/purchases/'+context.order.id+'/start',{});if(!ctx.paymentViewActive(context))return;ctx.state.exams[result.exam.id]=result.exam;ctx.state.activeExam=result.exam.id;ctx.go('testing',{id:result.exam.id});}catch(error){if(ctx.paymentViewActive(context))paymentFeedback(context,error.message,true);open.disabled=false;}};
        return true;
    }

async function syncPaidPayment(context){
        if(context.synced||!ctx.paymentAvailable(context))return;
        const snapshot=await PlatformAPI.request('session',undefined,{signal:context.controller.signal,owner:context.owner});
        if(!ctx.paymentViewActive(context))return;
        ctx.applySnapshot(snapshot);ctx.entitlementRefreshPending=false;ctx.updateMembershipViews();ctx.updateUnreadBadge();ctx.updateClassUnread();
        if(context.order.fee_id){
            const targetClass=Number(context.classId),selectedClass=Number(document.querySelector('#class-select')?.value);
            if(ctx.classData&&Number(ctx.classData.class.id)===targetClass){
                const fee=ctx.classData.fees.find(item=>Number(item.id)===Number(context.order.fee_id));
                if(fee){fee.paid_at=context.order.paid_at;const label=context.target.closest('[data-fee-detail]')?.querySelector('.tuition-total .tag');if(label){label.textContent='Đã hoàn thành';label.classList.remove('peach');label.classList.add('sage');}}
            }
            if(selectedClass===targetClass){
                const position={x:scrollX,y:scrollY},dialogScroll=context.dialog?.scrollTop;
                await ctx.loadClass();
                if(!ctx.paymentViewActive(context))return;
                window.scrollTo({left:position.x,top:position.y,behavior:'instant'});
                if(context.dialog)context.dialog.scrollTop=dialogScroll;
            }
        }
        if(ctx.paymentViewActive(context)){context.synced=true;paymentFeedback(context,'');context.target.querySelector('[data-payment-retry]')?.remove();}
    }

async function checkPayment(context,manual=false){
        if(!ctx.paymentAvailable(context)||context.busy||!context.order)return;
        if(context.order.status==='cancelled'||context.order.status==='paid'&&context.synced)return;
        clearTimeout(context.timer);context.busy=true;context.lastCheck=Date.now();
        const retry=context.target.querySelector('[data-payment-retry]');if(retry)retry.disabled=true;
        try{
            if(manual)paymentFeedback(context,'Đang kiểm tra khoản thanh toán…');
            if(context.order.status==='pending'){
                const result=await PlatformAPI.request('payments/'+context.order.id,undefined,{signal:context.controller.signal,owner:context.owner});
                if(!renderPaymentOrder(context,result.order))return;
            }
            if(context.order.status==='paid')await syncPaidPayment(context);
            context.failures=0;
            if(ctx.paymentViewActive(context)&&context.order.status==='pending')paymentFeedback(context,manual?'Chưa có xác nhận thanh toán. Trang vẫn đang tự kiểm tra.':'');
        }catch(error){
            if(error.name!=='AbortError'&&ctx.paymentViewActive(context)){
                if([401,403,404].includes(error.status)){
                    context.target.innerHTML='<p class="payment-feedback is-error" role="alert">Chưa thể đọc đơn thanh toán của tài khoản này. Em hãy đăng nhập lại hoặc liên hệ 5BMath để kiểm tra.</p>';
                    ctx.stopPaymentWatch();return;
                }
                context.failures++;
                paymentFeedback(context,context.order.status==='paid'?'Thanh toán đã thành công; chưa cập nhật được quyền học. Em hãy bấm Cập nhật tài khoản để thử lại.':'Chưa kiểm tra được thanh toán. Trang sẽ thử lại. '+error.message,true);
                if(context.order.status==='paid'){
                    const actions=context.target.querySelector('.payment-actions');
                    if(!actions.querySelector('[data-payment-retry]'))actions.insertAdjacentHTML('afterbegin','<button class="btn dark" type="button" data-payment-retry>Cập nhật tài khoản</button>');
                    actions.querySelector('[data-payment-retry]').onclick=()=>checkPayment(context,true);
                }
            }
        }finally{
            context.busy=false;
            if(ctx.paymentViewActive(context)){const control=context.target.querySelector('[data-payment-retry]');if(control)control.disabled=false;if(context.resumeRequested){context.resumeRequested=false;ctx.resumePaymentCheck();}else schedulePaymentCheck(context);}
        }
    }

async function createPayment(context){
        if(!ctx.paymentAvailable(context)||context.busy)return;
        if(!context.resumeOrderId&&context.body.checkout?.accepted!==true){showCheckout(context);return;}
        context.busy=true;context.target.innerHTML='<p role="status">Đang chuẩn bị thông tin thanh toán…</p>';
        try{
            const result=await PlatformAPI.request(context.resumeOrderId?'payments/'+context.resumeOrderId:'payments',context.resumeOrderId?undefined:context.body,{signal:context.controller.signal,owner:context.owner});
            if(!renderPaymentOrder(context,result.order))return;
        }catch(error){
            if(ctx.paymentViewActive(context)&&error.name!=='AbortError'){
                context.target.innerHTML=`<p class="payment-feedback is-error" role="alert">Chưa tải được thông tin thanh toán. ${ctx.escape(error.message)}</p><div class="actions payment-actions"><button class="btn outline" type="button" data-payment-retry>Thử lại</button>${!context.resumeOrderId?'<button class="btn outline" type="button" data-checkout-edit>Xem lại và sửa</button>':''}${context.resumeOrderId&&error.status===404?ctx.link('Tạo đơn mua VIP','payment','outline'):''}</div>`;
                context.target.querySelector('[data-payment-retry]').onclick=()=>createPayment(context);
                const edit=context.target.querySelector('[data-checkout-edit]');if(edit)edit.onclick=()=>{delete context.body.checkout;context.reviewRendered=false;showCheckout(context);};
            }
        }finally{context.busy=false;if(ctx.paymentViewActive(context)){if(context.resumeRequested){context.resumeRequested=false;ctx.resumePaymentCheck();}else if(context.order?.status==='paid')checkPayment(context);else schedulePaymentCheck(context);}}
    }

async function startPaymentView(target,body,options={}){
        ctx.stopPaymentWatch();
        if(!target||!PlatformAPI.snapshot.authenticated)return;
        const context={target,body,...options,owner:ctx.accountPageOwner,csrf:PlatformAPI.snapshot.csrf,generation:ctx.paymentGeneration,controller:new AbortController(),timer:null,busy:false,order:null,markup:'',failures:0,synced:false,lastCheck:0};
        ctx.paymentWatch=context;
        if(!ctx.paymentAvailable(context)){target.innerHTML='<p class="payment-feedback" role="status">Kết nối mạng để tải thông tin thanh toán.</p>';return;}
        if(context.resumeOrderId)await createPayment(context);else await showCheckout(context);
    }

async function loadPayment() {
        const container=document.querySelector('#payment-content');if(!container)return;
        checkoutStyles();
        if(!document.querySelector('#payment-history'))container.insertAdjacentHTML('afterend','<section class="card card-pad checkout-history" id="payment-history" aria-label="Lịch sử đơn hàng"></section>');
        if(!ctx.live){container.textContent='Đăng nhập trên máy chủ để thanh toán theo tài khoản.';return;}
        const family=PlatformAPI.familyState,requested=ctx.query('childId')||ctx.query('child');
        let beneficiary={};
        if(family?.activeProfile?.type==='parent'){
            const childId=family.selectedChildId;
            if(!childId||(requested&&requested!==String(childId))||PlatformAPI.snapshot.csrf!==family.csrf){
                container.innerHTML='<p>Ba mẹ xác nhận lại con trước khi thanh toán.</p>'+ctx.link('Chọn hồ sơ con','upgrade','outline');
                return;
            }
            beneficiary={beneficiaryId:String(childId),familyContext:family.context};
        }
        const identity=ctx.query('order');
        if(identity!==null&&!/^[1-9][0-9]{0,14}$/.test(identity)){container.innerHTML='<p class="payment-feedback is-error" role="alert">Mã đơn thanh toán không hợp lệ.</p>'+ctx.link('Tạo đơn mua VIP','payment','outline');return;}
        const plan=ctx.query('plan')||'VIP',period=ctx.query('period')||'month';
        if(!['VIP','VIP+'].includes(plan)||!['month','year'].includes(period)){container.textContent='Gói hoặc kỳ đăng ký không hợp lệ.';return;}
        await startPaymentView(container,ctx.query('examProduct')?{examProduct:ctx.query('examProduct')}:{plan,period},{...beneficiary,resumeOrderId:identity===null?null:Number(identity)});
        if(!beneficiary.beneficiaryId||(ctx.paymentWatch&&ctx.paymentViewActive(ctx.paymentWatch)))loadPaymentHistory();
    }
const views = {
zoomRegistration() { return ctx.intro('Đăng ký học Zoom','Cùng thầy cô xây nền tảng Toán và phát triển tư duy.')+'<div class="zoom-svip-plan">'+svipPlan(true)+'</div>'; },
upgrade() { return upgradeView(); },
payment() { return ctx.intro('Thanh toán','Xem lại, sửa lựa chọn và xác nhận trước khi tạo đơn.')+'<section class="card card-pad" id="payment-content">Đang chuẩn bị thông tin…</section><section class="card card-pad checkout-history" id="payment-history" aria-label="Lịch sử đơn hàng"></section>'; }
};
const actions = {
'review-upgrade':async () => {await ctx.mutate('dev/upgrade',{requestKey:ctx.uid()});ctx.refresh();ctx.host.toast('Đã mô phỏng nâng cấp VIP để kiểm tra luồng giới thiệu.');}
};
return {views,actions,svipPlan,upgradeView,planChildSummary,mountParentPlans,paymentMarkup,checkoutStyles,checkoutEvidenceMarkup,checkoutSummaryMarkup,showCheckout,loadPaymentHistory,schedulePaymentCheck,paymentFeedback,renderPaymentOrder,syncPaidPayment,checkPayment,createPayment,startPaymentView,loadPayment};
}
const api={create};(global.LearningFeatures??={})['commerce']=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
