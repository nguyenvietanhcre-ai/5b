'use strict';
(() => {
    if (window.FamilyCart) return;
    const path = '/gia-dinh/?view=cart';
    const plans = ['VIP','VIP+'];
    const periods = {month:'1 tháng',year:'12 tháng'};
    const actions = {subscribe:'Đăng ký',renew:'Gia hạn',upgrade:'Nâng gói'};
    const packLabels = {'questions-100':'Gói 100 câu luyện tập','exams-10':'Gói 10 lượt tạo đề tự chọn'};
    const packNotes = {'questions-100':'Dùng cho từng câu mới tính phí trong đề luyện tập.','exams-10':'Mỗi lượt tạo một đề tự chọn gồm 10 câu.'};
    const itemKinds = {subscription:'Gói học',credits:'Gói lượt luyện',tuition:'Học phí Zoom',exam:'Bộ đề bán riêng'};
    const vnd = new Intl.NumberFormat('vi-VN',{style:'currency',currency:'VND'});
    const dates = new Intl.DateTimeFormat('vi-VN',{day:'2-digit',month:'2-digit',year:'numeric',timeZone:'Asia/Ho_Chi_Minh'});
    const datesWithTime = new Intl.DateTimeFormat('vi-VN',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',timeZone:'Asia/Ho_Chi_Minh'});
    const escape = value => String(value ?? '').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const state = () => window.FamilyProfiles?.state || {};
    const unlocked = () => state().authenticated && state().scope==='parent_full' && state().activeProfile?.type==='parent' && !state().device?.childOnly;
    const child = id => state().children?.find(item=>String(item.id)===String(id));
    function announceCart(context,count){
        if(context&&unlocked()&&state().context===context)window.dispatchEvent(new CustomEvent('family-cart-updated',{detail:{context,count}}));
    }
    async function request(suffix,body,signal){
        const context=state().context;
        const result=await window.FamilyProfiles.request('cart'+suffix,body,{signal});
        if(Array.isArray(result.cart?.items))announceCart(context,result.cart.items.length);
        return result;
    }
    const control = (label,action,extra='') => `<button class="secondary" type="button" data-cart-action="${action}" ${extra}>${label}</button>`;
    const choice = (value,label,selected) => `<option value="${escape(value)}"${selected===value?' selected':''}>${escape(label)}</option>`;
    let current;

    function date(value,withTime=false){
        const parsed=new Date(value||'');
        return Number.isNaN(parsed.getTime())?'':(withTime?datesWithTime:dates).format(parsed);
    }
    function editPath(item){
        const query={edit:String(item.studentId)};
        if(itemType(item)==='subscription')Object.assign(query,{plan:item.plan,period:item.period});
        if(itemType(item)==='tuition')query.fee=String(item.feeId);
        if(itemType(item)==='credits')query.pack=item.sku;
        if(itemType(item)==='exam')query.examProduct=item.examProduct;
        return path+'&'+new URLSearchParams(query);
    }
    const itemType = item => item.type||'subscription';
    const lineKey = item => item.lineId||`${item.studentId}:subscription`;
    const titleFor = item => itemType(item)==='subscription'?item.plan+' · '+(periods[item.period]||item.period):itemType(item)==='tuition'?'Học phí tháng '+item.month:packLabels[item.sku]||item.title||itemKinds[itemType(item)];
    const balanceText = value => value==null?'—':Number(value);
    const catalogItems = catalog => [...(catalog?.creditPacks||[]),...(catalog?.tuition||[]),...(catalog?.exams||[])];
    const availableItem = item => item.available!==false&&(itemType(item)!=='tuition'||(item.amount>0&&!item.paidAt&&!item.paid_at));
    const itemBody = item => {
        const studentId=validId(item.studentId),type=itemType(item);
        if(type==='credits')return {studentId,type,sku:item.sku,quantity:Number(item.quantity)||1};
        if(type==='tuition')return {studentId,type,feeId:item.feeId};
        if(type==='exam')return {studentId,type,examProduct:item.examProduct};
        return {studentId,plan:item.plan,period:item.period,referralCode:item.referralCode};
    };
    function validId(value){
        return /^[1-9]\d{0,14}$/.test(String(value??''))?Number(value):null;
    }
    function orderState(order){
        if(order.fulfillmentStatus==='granted')return 'granted';
        if(order.status==='review'||order.fulfillmentStatus==='review'||(order.status==='cancelled'&&order.paymentReceived))return 'review';
        if(order.status==='paid'||order.paymentReceived||order.fulfillmentStatus==='processing')return 'processing';
        if(order.status==='cancelled'||order.fulfillmentStatus==='cancelled')return 'cancelled';
        return 'pending';
    }
    const orderLabels = {granted:'Đã hoàn tất đơn hàng',processing:'Đã nhận tiền · Đang xử lý',review:'Đang đối soát',cancelled:'Đã hủy',pending:'Chờ thanh toán'};
    function pendingLink(order){
        if(!order)return '';
        const status=order.checkoutBlocked?'Tạm dừng thanh toán':orderLabels[orderState(order)];
        return `<aside class="family-cart-pending"><div><strong>${status}</strong><p>${escape(order.reference)} · ${vnd.format(order.amount)}</p></div>${control('Mở đơn','order',`data-order-id="${Number(order.id)}"`)}</aside>`;
    }
    function beneficiary(item){
        const profile=child(item.studentId),grade=item.grade??profile?.grade;
        return `${escape(item.studentName||profile?.nickname||profile?.name||'Hồ sơ con')}${grade?'<small>Lớp '+escape(grade)+'</small>':''}`;
    }
    function lineDates(item,receipt){
        const start=date(receipt?item.subscriptionStartsAt:item.estimatedStartsAt);
        const end=date(receipt?item.subscriptionEndsAt:item.estimatedEndsAt);
        if(!start)return receipt?'Hiệu lực sau khi đơn được xác nhận':'Có hiệu lực sau khi xác nhận thanh toán';
        return (receipt?'Hiệu lực ':'Dự kiến ')+start+(end?' – '+end:'');
    }
    function lines(items,{editable=false,receipt=false}={}){
        const groups=new Map();
        for(const item of items){
            const id=String(item.studentId);
            if(!groups.has(id))groups.set(id,[]);
            groups.get(id).push(item);
        }
        return `<div class="family-cart-groups">${[...groups.values()].map(group=>`<section class="family-cart-group"><h3>${beneficiary(group[0])}</h3><ul class="family-cart-lines">${group.map(item=>lineMarkup(item,editable,receipt)).join('')}</ul></section>`).join('')}</div>`;
    }
    function lineMarkup(item,editable,receipt){
        const type=itemType(item),key=escape(lineKey(item)),title=escape(titleFor(item));
        const who=escape(item.studentName||child(item.studentId)?.name||'con');
        const attributes=`data-line-id="${key}" data-student-id="${Number(item.studentId)}"`;
        const edit=editable&&availableItem(item)&&['subscription','credits'].includes(type)?control('Sửa','edit',`${attributes} aria-label="Sửa ${title} của ${who}"`):'';
        const remove=editable?control('Xóa','remove',`${attributes} aria-label="Xóa ${title} của ${who}"`):'';
        const quantity=item.quantity||1;
        const timing={subscription:()=>[actions[item.subscriptionAction],lineDates(item,receipt)].filter(Boolean).join(' · '),credits:()=>`${quantity} gói × ${vnd.format(item.unitAmount??item.amount)} · Không hết hạn`,tuition:()=>item.className,exam:()=>[item.questionCount&&item.questionCount+' câu',item.durationMinutes&&item.durationMinutes+' phút'].filter(Boolean).join(' · ')}[type];
        const status=item.fulfillmentStatus||(receipt?'granted':'');
        const statusLabel={granted:type==='tuition'?'Đã nộp học phí':type==='credits'?'Đã cộng lượt':type==='exam'?'Đã mở bộ đề':'Đã cấp gói',pending:'Chờ xử lý',processing:'Đang xử lý',review:'Đang đối soát',cancelled:'Đã hủy'}[status];
        const unavailable=editable&&!availableItem(item);
        const note=unavailable?item.unavailableReason||'Khoản này chưa thể thanh toán. Xóa để tiếp tục.':timing?.();
        return `<li class="family-cart-line" ${attributes} data-item-type="${escape(type)}"><div class="family-cart-line-info"><strong>${title}</strong>${note?`<p class="${unavailable?'family-cart-line-warning':'family-cart-muted'}">${escape(note)}</p>`:''}${item.referralApplied?'<p class="family-cart-muted">Đã áp dụng mã giới thiệu.</p>':''}${statusLabel?`<p class="family-cart-line-state" data-line-state="${escape(status)}">${statusLabel}</p>`:''}</div><strong class="family-cart-line-price">${vnd.format(item.amount)}</strong>${editable?`<div class="family-cart-line-actions">${edit}${remove}</div>`:''}</li>`;
    }
    function editForm(context){
        const item=context.edit;
        if(!item)return '';
        const type=itemType(item),existing=context.cart.items.some(line=>lineKey(line)===lineKey(item));
        const back=context.catalogOpen?'Quay lại lựa chọn':'Hủy';
        const actions=valid=>`<div class="family-cart-actions family-cart-editor-actions">${valid?`<button type="submit"${type==='credits'||type==='subscription'?'':' autofocus'}>${existing?'Lưu thay đổi':'Thêm vào giỏ'}</button>`:''}${control(back,'discard-edit')}</div>`;
        const profile=`<p class="family-cart-editor-child">${beneficiary(item)}</p>`;
        if(type==='subscription'){
            return `<form class="family-cart-editor" data-cart-form="edit">${profile}<div class="family-cart-fields"><label class="family-field"><span>Gói học</span><select name="plan" autofocus>${plans.map(plan=>choice(plan,plan,item.plan)).join('')}</select></label><label class="family-field"><span>Kỳ đăng ký</span><select name="period">${Object.entries(periods).map(([value,label])=>choice(value,label,item.period)).join('')}</select></label></div><label class="family-field"><span>Mã giới thiệu (không bắt buộc)</span><input name="referralCode" maxlength="40" autocomplete="off" value="${escape(item.referralCode)}"></label>${actions(true)}</form>`;
        }
        const unitAmount=item.unitAmount??item.amount;
        const note=type==='tuition'?item.className:type==='credits'?(packNotes[item.sku]||'')+' Không hết hạn.':null;
        const valid=availableItem(item);
        const quantityField=type==='credits'?`<label class="family-field"><span>Số gói</span><input name="quantity" type="number" min="1" max="10" value="${escape(item.quantity??1)}" required autofocus></label>`:'';
        return `<form class="family-cart-editor" data-cart-form="edit">${profile}${note?`<p class="family-cart-muted">${escape(note)}</p>`:''}${quantityField}<strong class="family-cart-line-price">${vnd.format(unitAmount)}${type==='credits'?' / gói':''}</strong>${valid?'':`<p class="family-cart-line-warning">${escape(item.unavailableReason||'Khoản này hiện không thể thanh toán.')}</p>`}${actions(valid)}</form>`;
    }
    function catalogMarkup(catalog,id,cart,inCart){
        if(!catalog||!child(id))return '';
        const balance=catalog.balances?.[id],belongs=item=>String(item.studentId)===String(id);
        const packs=(catalog.creditPacks||[]).filter(belongs),fees=(catalog.tuition||[]).filter(belongs),exams=(catalog.exams||[]).filter(belongs);
        function buying(item){
            const key=lineKey(item),exists=cart?.items.some(line=>lineKey(line)===key);
            if(exists)return inCart?'<span class="family-cart-muted">Đã có trong giỏ</span>':`<a class="family-cart-link" href="${path}">Đã có trong giỏ</a>`;
            if(!availableItem(item))return '';
            const title=escape(titleFor(item));
            return inCart?control('Chọn','add-catalog',`data-line-id="${escape(key)}" aria-label="Chọn ${title}"`):`<button class="btn outline" type="button" data-add-catalog="${escape(key)}" aria-label="Thêm ${title} vào giỏ">Thêm vào giỏ</button>`;
        }
        function catalogLine(item,note){
            return `<article class="family-cart-option" data-catalog-type="${escape(itemType(item))}" data-catalog-line-id="${escape(lineKey(item))}"><div><h4>${escape(titleFor(item))}</h4><p>${escape(note)}</p></div><strong>${vnd.format(item.unitAmount??item.amount)}</strong>${buying(item)}</article>`;
        }
        const feeStatus={paid:'Đã nộp',pending:'Có đơn đang chờ','no-fee':'Không phát sinh học phí',available:'Chưa nộp'};
        const feeSection=fees.length||!inCart?`<section><h3>Học phí Zoom</h3>${fees.length?`<div class="family-cart-options">${fees.map(item=>catalogLine(item,[item.className,feeStatus[item.availability]||feeStatus[item.paidAt?'paid':item.amount===0?'no-fee':'available']].filter(Boolean).join(' · '))).join('')}</div>`:'<p>Chưa có khoản học phí của con.</p>'}</section>`:'';
        return `<div class="family-cart-catalog-content">${balance&&!inCart?`<p class="family-cart-balances"><span>Câu luyện tập còn <b>${balanceText(balance.questionsRemaining)}</b></span><span>Lượt tạo đề tự chọn còn <b>${balanceText(balance.examsRemaining)}</b></span></p>`:''}${packs.length?`<section><h3>Gói lượt luyện</h3><div class="family-cart-options">${packs.map(item=>catalogLine(item,(packNotes[item.sku]||'')+' Không hết hạn.')).join('')}</div></section>`:''}${feeSection}${exams.length?`<section><h3>Bộ đề bán riêng</h3><div class="family-cart-options">${exams.map(item=>catalogLine(item,`${item.questionCount} câu · ${item.durationMinutes} phút`)).join('')}</div></section>`:''}</div>`;
    }
    function cartCatalog(context){
        const children=state().children||[];
        const id=context.catalogStudentId;
        const existing=context.cart.items.find(item=>String(item.studentId)===String(id)&&itemType(item)==='subscription');
        const subscriptions=`<section><h3>Gói học</h3><article class="family-cart-option"><div><h4>VIP và VIP+</h4>${existing?`<p>Trong giỏ: ${escape(titleFor(existing))}</p>`:''}</div>${control(existing?'Sửa gói':'Chọn gói','select-plan')}</article></section>`;
        const products=context.catalog?catalogMarkup(context.catalog,id,context.cart,true):context.catalogError?`<div class="family-cart-catalog-error"><p>${escape(context.catalogError)}</p>${control('Thử tải lại','reload-catalog')}</div>`:'<p role="status">Đang tải lựa chọn…</p>';
        return `<div class="family-cart-catalog" id="family-cart-catalog"><label class="family-field"><span>Mua cho con</span><select data-cart-beneficiary autofocus>${children.map(profile=>choice(String(profile.id),`${profile.nickname||profile.name}${profile.grade?' · Lớp '+profile.grade:''}`,String(id))).join('')}</select></label>${subscriptions}${products}</div>`;
    }
    function dialogMarkup(context){
        const item=context.edit;
        const title=item?(itemType(item)==='subscription'?'Chọn gói học':titleFor(item)):'Thêm vào giỏ';
        return `<dialog class="family-cart-dialog" aria-labelledby="family-cart-dialog-title"><div class="family-cart-dialog-heading"><h3 id="family-cart-dialog-title">${escape(title)}</h3>${control('Đóng','close-dialog')}</div>${statusMarkup(context)}${item?editForm(context):cartCatalog(context)}</dialog>`;
    }
    function summary(total,detail,actions=''){
        return `<aside class="family-cart-total" aria-label="Tổng thanh toán"><p>Tổng thanh toán</p><strong>${vnd.format(total)}</strong>${detail?`<p class="family-cart-muted">${escape(detail)}</p>`:''}${actions}</aside>`;
    }
    function cartMarkup(context){
        if(!context.cart)return '<p>Chưa đọc được giỏ hàng.</p>'+control('Tải lại giỏ','reload');
        const {cart,pendingOrder}=context;
        const hasChildren=Boolean(state().children?.length);
        const add=hasChildren?control('Thêm khoản','open-catalog'):'<a class="family-cart-link" href="/gia-dinh/?view=parent">Quản lý hồ sơ con</a>';
        const pending=pendingLink(pendingOrder);
        if(!cart.items.length)return `${pending}<section class="family-cart-empty"><h3>Giỏ hàng đang trống</h3><p>${hasChildren?'Chọn gói học, lượt luyện hoặc học phí cho các con.':'Thêm hồ sơ con để chọn gói học và các khoản cần thanh toán.'}</p>${hasChildren?'<button type="button" data-cart-action="open-catalog">Chọn khoản để thêm</button>':add}</section>`;
        const available=cart.items.every(availableItem);
        const detail=pendingOrder?'Xử lý đơn đang chờ trước khi tạo đơn mới.':available?'Thanh toán một lần cho '+cart.items.length+' khoản.':'Xử lý các khoản chưa thể thanh toán để tiếp tục.';
        const checkout=pendingOrder||!available?'':'<button type="button" data-cart-action="preview">Xem lại và thanh toán</button>';
        return `${pending}<div class="family-cart-columns"><section aria-label="Các khoản trong giỏ"><div class="family-cart-section-heading"><h3>Các khoản trong giỏ <span>${cart.items.length}</span></h3>${add}</div>${lines(cart.items,{editable:true})}</section>${summary(cart.total,detail,checkout)}</div>`;
    }
    function purchaserForm(context){
        const {name,contact,relationship,representativeDeclared,accepted}=context.buyer;
        const version=escape(context.preview.policyVersion);
        return `<fieldset><legend>Người thanh toán</legend><div class="family-cart-fields"><label class="family-field"><span>Họ tên</span><input name="name" required maxlength="120" autocomplete="name" value="${escape(name)}"></label><label class="family-field"><span>Email hoặc số điện thoại</span><input name="contact" required maxlength="200" value="${escape(contact)}"></label></div><label class="family-field family-cart-relationship"><span>Vai trò</span><select name="relationship" required>${choice('parent','Phụ huynh',relationship)}${choice('representative','Người đại diện',relationship)}</select></label><label class="family-check"><input name="representativeDeclared" type="checkbox" required ${representativeDeclared?'checked':''}><span>Tôi tự khai là phụ huynh hoặc người đại diện mua thay trẻ.</span></label></fieldset><fieldset class="family-cart-policies"><legend>Chính sách bản nháp</legend><div class="family-cart-policy-links"><a href="/dieu-khoan/" target="_blank" rel="noopener">Điều khoản</a><a href="/thanh-toan-va-cung-cap/" target="_blank" rel="noopener">Thanh toán và cung cấp</a><a href="/huy-va-hoan-tien/" target="_blank" rel="noopener">Hủy và hoàn tiền</a><a href="/bao-ve-du-lieu/" target="_blank" rel="noopener">Bảo vệ dữ liệu</a></div><label class="family-check"><input name="accepted" type="checkbox" required ${accepted?'checked':''}><span>Tôi đã xem lại các khoản, tổng tiền và đồng ý bộ chính sách phiên bản ${version} cho đơn này.</span></label></fieldset>`;
    }
    function reviewMarkup(context){
        return `<form class="family-cart-checkout family-cart-columns" data-cart-form="checkout"><div class="family-cart-review-main"><section aria-label="Các khoản đã chọn"><div class="family-cart-section-heading"><h3>Các khoản đã chọn</h3></div>${lines(context.preview.items)}</section>${purchaserForm(context)}</div>${summary(context.preview.total,'Một đơn thanh toán cho tất cả các khoản.','<button type="submit">Xác nhận và tạo đơn</button>')}</form>`;
    }
    function ordersMarkup(context){
        if(!context.orders)return '<p>Chưa đọc được lịch sử đơn.</p>'+control('Tải lại lịch sử','orders');
        if(!context.orders.length)return '<section class="family-cart-empty"><h3>Chưa có đơn hàng</h3><p>Các đơn tạo từ giỏ hàng sẽ xuất hiện ở đây.</p></section>';
        return `<ul class="family-cart-lines family-cart-history">${context.orders.map(order=>`<li class="family-cart-line"><div class="family-cart-line-info"><strong>${escape(order.reference)}</strong><p class="family-cart-muted">${date(order.created_at,true)} · ${escape(order.checkoutBlocked?'Tạm dừng thanh toán':orderLabels[orderState(order)])}</p></div><strong class="family-cart-line-price">${vnd.format(order.amount)}</strong><div class="family-cart-line-actions">${control('Xem đơn','order',`data-order-id="${Number(order.id)}" aria-label="Xem đơn ${escape(order.reference)}"`)}</div></li>`).join('')}</ul>`;
    }
    function qrURL(value){
        try {
            const url=new URL(value,location.origin);
            if(url.protocol==='https:'&&url.hostname==='img.vietqr.io'&&url.pathname.startsWith('/image/'))return escape(url.href);
        } catch {}
        return '';
    }
    function orderMarkup(order){
        if(!order)return '<p>Chưa đọc được đơn này.</p>'+control('Kiểm tra lại','check');
        const status=orderState(order),pending=status==='pending',blocked=pending&&order.checkoutBlocked,qr=pending&&!blocked&&qrURL(order.qrUrl);
        const note={
            pending:blocked?'Chi tiết đơn đã thay đổi. Nếu chưa chuyển tiền, ba mẹ có thể hủy đơn và xem lại giỏ. Nếu đã chuyển, liên hệ 5BMath để đối soát.':order.automationEnabled?'Trang sẽ tự kiểm tra khi giao dịch được xác nhận.':'5BMath sẽ xác nhận khoản chuyển trước khi xử lý đơn.',
            granted:'Các khoản trong đơn đã được xử lý cho từng con.',
            processing:'5BMath đã nhận khoản chuyển và đang xử lý đơn. Vui lòng chờ cập nhật và giữ chứng từ chuyển khoản.',
            review:'5BMath đang đối soát khoản chuyển của đơn này. Vui lòng giữ chứng từ và liên hệ hỗ trợ trước khi thực hiện thêm giao dịch.',
            cancelled:'Đơn đã hủy. Nếu ba mẹ đã chuyển tiền, hãy liên hệ 5BMath để đối soát.'
        }[status];
        const snapshot=order.checkoutSnapshot;
        const observed=status==='review'&&Number.isFinite(order.receivedAmount)?`<p>Khoản chuyển ghi nhận để đối soát <strong>${vnd.format(order.receivedAmount)}</strong>.</p>`:'';
        const banner=`<div class="family-cart-order-banner" role="status" data-order-state="${status}"><strong>${blocked?'Tạm dừng thanh toán':orderLabels[status]}</strong><p>${note}</p>${observed}${(status==='review'||blocked)&&order.reviewReason?`<p>${escape(order.reviewReason)}</p>`:''}</div>`;
        const bankDetails=pending&&!blocked&&order.bankAccount?`<div><dt>Tài khoản nhận</dt><dd>${escape(order.bank)} · ${escape(order.bankAccount)}<br>${escape(order.bankName)}</dd></div>`:'';
        const qrBlock=qr?`<img class="family-cart-qr" src="${qr}" width="320" height="420" alt="Mã QR chuyển khoản đơn ${escape(order.reference)}">`:'';
        const instructions=qr||bankDetails?'<p class="family-cart-muted">Chuyển đúng số tiền và ghi mã đơn trong nội dung chuyển khoản.</p>':pending&&!blocked?'<p class="family-cart-muted">Liên hệ 5BMath để được hướng dẫn chuyển khoản.</p>':'';
        const cancel=pending?`<details class="family-cart-cancel"><summary>Hủy đơn đang chờ</summary><p>Chỉ hủy nếu ba mẹ chưa chuyển tiền. Nếu đã chuyển, hãy giữ đơn để 5BMath đối soát.</p>${control('Xác nhận hủy đơn','cancel-order')}</details>`:'';
        const evidence=snapshot?.purchaser?`<details class="family-cart-evidence"><summary>Thông tin đã xác nhận</summary><p>${escape(snapshot.purchaser.name)} · ${escape(snapshot.purchaser.contact)}</p><p>Chính sách ${escape(snapshot.acceptedPolicyVersion)} · ${date(snapshot.acceptedAt,true)}</p></details>`:'';
        return `${banner}<div class="family-cart-columns family-cart-order"><section class="family-cart-total" aria-label="Thông tin đơn hàng"><h3>${status==='granted'?'Biên nhận thanh toán':'Thông tin thanh toán'}</h3><strong>${vnd.format(order.amount)}</strong><dl class="family-cart-order-details"><div><dt>Mã đơn</dt><dd>${escape(order.reference)}</dd></div><div><dt>Tạo lúc</dt><dd>${date(order.created_at,true)}</dd></div>${order.paid_at?`<div><dt>Ghi nhận tiền</dt><dd>${date(order.paid_at,true)}</dd></div>`:''}${bankDetails}</dl>${qrBlock}${instructions}<div class="family-cart-actions">${control('Kiểm tra trạng thái','check')}<a class="family-cart-link" href="/lien-he/">Liên hệ hỗ trợ</a></div>${cancel}</section><section aria-label="Các khoản của từng con"><div class="family-cart-section-heading"><h3>Các khoản của từng con</h3></div>${lines(order.items,{receipt:status==='granted'})}${evidence}</section></div>`;
    }

    function active(context){
        return current===context&&context.host.isConnected&&unlocked()&&state().family?.id===context.familyId;
    }
    function setMessage(context,message,error=false){
        context.message=message;
        context.error=error;
        const status=context.host.querySelector('[data-cart-status]');
        if(status){
            status.textContent=message;
            status.dataset.error=String(error);
            if(error)status.scrollIntoView({block:'nearest'});
        }
    }
    function statusMarkup(context){
        return `<p class="family-cart-status" data-cart-status role="status" aria-atomic="true" data-error="${Boolean(context.error)}">${escape(context.message)}</p>`;
    }
    function focusHeading(context){
        const heading=context.host.querySelector('[data-cart-heading]');
        heading?.focus({preventScroll:true});
        heading?.scrollIntoView({block:'nearest'});
    }
    function focusCartOrigin(context,key){
        const edits=context.host.querySelectorAll('[data-cart-action="edit"]');
        const trigger=[...edits].find(button=>button.dataset.lineId===key)||context.host.querySelector('[data-cart-action="open-catalog"]');
        if(trigger)trigger.focus({preventScroll:true});
        else focusHeading(context);
    }
    function closeDialog(context){
        const key=context.edit&&lineKey(context.edit);
        context.edit=null;
        context.catalogOpen=false;
        setMessage(context,'');
        render(context);
        focusCartOrigin(context,key);
    }
    function render(context){
        if(!active(context))return;
        const stage=context.stage;
        const titles={cart:'Giỏ hàng',review:'Xem lại đơn hàng',orders:'Lịch sử đơn',order:context.order&&orderState(context.order)==='granted'?'Đơn đã hoàn tất':'Chi tiết đơn hàng'};
        const markup=context.loading?'<p class="family-cart-loading">Đang tải thông tin…</p>':stage==='order'?orderMarkup(context.order):stage==='orders'?ordersMarkup(context):stage==='review'?reviewMarkup(context):cartMarkup(context);
        const showDialog=!context.loading&&context.cart&&stage==='cart'&&(context.edit||context.catalogOpen);
        const navigation=stage==='cart'?control('Lịch sử đơn','orders'):control('Về giỏ','cart')+(stage==='order'?control('Lịch sử đơn','orders'):'');
        context.host.innerHTML=`<div class="family-cart-header"><h2 tabindex="-1" data-cart-heading>${titles[stage]}</h2><nav class="family-cart-nav" aria-label="Giỏ hàng và đơn">${navigation}</nav></div>${showDialog?'':statusMarkup(context)}${markup}${showDialog?dialogMarkup(context):''}`;
        const dialog=context.host.querySelector('dialog');
        if(dialog){
            dialog.addEventListener('cancel',event=>{
                event.preventDefault();
                if(active(context)&&!context.busy)closeDialog(context);
            });
            dialog.showModal();
        }
    }
    function markBusy(context,busy){
        context.busy=busy;
        if(busy)context.host.setAttribute('aria-busy','true');
        else context.host.removeAttribute('aria-busy');
        const controls=context.host.querySelectorAll(busy?'button:enabled,[data-cart-beneficiary]:enabled':'[data-cart-busy-disabled]');
        for(const control of controls){
            control.toggleAttribute('data-cart-busy-disabled',busy);
            control.disabled=busy;
        }
    }
    function setOrderURL(id){
        const url = new URL(location.href);
        url.search=id?'?view=cart&order='+id:'?view=cart';
        history.replaceState(null,'',url.pathname+url.search);
    }
    function adoptCart(context,result){
        context.cart=result.cart;
        context.pendingOrder=result.pendingOrder;
    }
    function resetConsent(context){context.buyer.accepted=false;context.buyer.representativeDeclared=false;}
    function handleEditQuery(context,query){
        const id=validId(query.get('edit')),plan=query.get('plan'),period=query.get('period');
        if(!id||!child(id))return;
        context.catalogStudentId=id;
        const fee=validId(query.get('fee')),pack=query.get('pack'),exam=query.get('examProduct');
        if(fee||pack||exam){
            const candidate=catalogItems(context.catalog).find(item=>Number(item.studentId)===id&&((fee&&item.feeId===fee)||(pack&&item.sku===pack)||(exam&&item.examProduct===exam)));
            if(candidate){
                const existing=context.cart.items.find(item=>lineKey(item)===lineKey(candidate));
                if(existing&&itemType(candidate)!=='credits')setMessage(context,'Khoản này đã có trong giỏ.');
                else context.edit={...candidate,...(existing?{quantity:existing.quantity}:{})};
            } else setMessage(context,'Khoản đã chọn hiện không có trong danh sách thanh toán của con.',true);
        }else if(plans.includes(plan)&&Object.hasOwn(periods,period)){
            const existing=context.cart.items.find(item=>Number(item.studentId)===id&&itemType(item)==='subscription');
            context.edit={...existing,studentId:id,plan,period};
        }
        setOrderURL();
    }
    function saveInputs(context,form){
        if(form.dataset.cartForm==='edit'){
            if(!context.edit)return;
            const {plan,period,referralCode,quantity}=form.elements;
            if(plan)Object.assign(context.edit,{plan:plan.value,period:period.value,referralCode:referralCode.value.trim()});
            if(quantity)context.edit.quantity=quantity.value;
        } else {
            const {name,contact,relationship,representativeDeclared,accepted}=form.elements;
            context.buyer={name:name.value,contact:contact.value,relationship:relationship.value,representativeDeclared:representativeDeclared.checked,accepted:accepted.checked};
        }
    }
    function schedule(context){
        clearTimeout(context.timer);
        if(active(context)&&!document.hidden&&context.stage==='order'&&context.order&&['pending','processing','review'].includes(orderState(context.order))){
            context.timer=setTimeout(()=>checkOrder(context),8000);
        }
    }
    async function loadCart(context){
        await readCart(context);
        if(!active(context))return;
        context.stage='cart';
        setOrderURL();
        render(context);
        focusHeading(context);
    }
    async function readCart(context){
        const result=await request('');
        if(active(context))adoptCart(context,result);
        return result;
    }
    async function readCatalog(context){
        try{
            const catalog=await request('/catalog');
            if(active(context)){context.catalog=catalog;context.catalogError='';}
        }catch(error){
            if(error.code==='family_parent_pin_required'||error.familyAccessChanged)throw error;
            if(active(context)){context.catalog=null;context.catalogError='Chưa tải được gói lượt luyện, học phí và bộ đề.';}
        }
    }
    async function openCatalog(context){
        if(!child(context.catalogStudentId))context.catalogStudentId=state().children?.[0]?.id;
        if(!child(context.catalogStudentId))return;
        await readCatalog(context);
        if(!active(context))return;
        context.catalogOpen=true;
        render(context);
    }
    async function refreshEditor(context){
        const edit=context.edit;
        if(!edit||itemType(edit)==='subscription')return;
        const latest=catalogItems(context.catalog).find(item=>lineKey(item)===lineKey(edit));
        if(latest)context.edit={...latest,quantity:edit.quantity};
        else if(context.catalog)context.edit=null;
    }
    async function readOrder(context,id){
        const accessContext=state().context;
        const {order}=await request('/orders/'+id);
        if(!active(context))return;
        if(context.order?.id===order.id&&orderState(context.order)!=='granted'&&orderState(order)==='granted')announceCart(accessContext);
        const same=context.stage==='order'&&JSON.stringify(context.order)===JSON.stringify(order);
        const wasChecking=document.activeElement===context.host.querySelector('[data-cart-action="check"]');
        context.order=order;
        context.orderId=order.id;
        context.stage='order';
        setOrderURL(id);
        if(!same){
            render(context);
            if(wasChecking)context.host.querySelector('[data-cart-action="check"]')?.focus({preventScroll:true});
        }
    }
    async function run(context,task,{quiet=false}={}){
        if(!active(context)||context.busy)return;
        clearTimeout(context.timer);
        markBusy(context,true);
        if(!quiet)setMessage(context,'Đang xử lý…');
        try {
            await task();
            if(active(context)&&context.message==='Đang xử lý…')setMessage(context,'');
        } catch(error) {
            if(!active(context))return;
            if(error.code==='family_parent_pin_required'){
                setMessage(context,'Nhập PIN phụ huynh để tiếp tục.');
                await window.FamilyProfiles.refresh().catch(()=>{});
            } else if(error.status===409){
                try {
                    await readCart(context);
                    if(!active(context))return;
                    if(context.stage==='review'){
                        resetConsent(context);
                        context.stage='cart';
                    }
                    if(context.catalogOpen||context.edit&&itemType(context.edit)!=='subscription')await readCatalog(context);
                    if(!active(context))return;
                    refreshEditor(context);
                    const message=error.code==='cart_revision_conflict'?'Giỏ hàng vừa được cập nhật trên thiết bị khác. Kiểm tra lại các khoản trước khi tiếp tục.':error.message;
                    render(context);
                    setMessage(context,message,true);
                } catch(refreshError) {
                    if(active(context))setMessage(context,refreshError.message,true);
                }
            } else setMessage(context,error.message||'Chưa thể kết nối. Vui lòng thử lại.',true);
        } finally {
            markBusy(context,false);
            schedule(context);
        }
    }
    function checkOrder(context,manual=false){
        const id=context.order?.id||context.orderId;
        if(!id)return;
        return run(context,async()=>{
            await readOrder(context,id);
            if(active(context))setMessage(context,manual?'Đã kiểm tra trạng thái đơn.':'');
        },{quiet:!manual});
    }
    const handlers = {
        cart:loadCart,
        reload:loadCart,
        'open-catalog':openCatalog,
        'reload-catalog':openCatalog,
        'close-dialog':closeDialog,
        async orders(context){
            const {orders}=await request('/orders');
            if(!active(context))return;
            context.orders=orders;
            context.stage='orders';
            setOrderURL();
            render(context);
            focusHeading(context);
        },
        async order(context,button){await readOrder(context,validId(button.dataset.orderId));if(active(context))focusHeading(context);},
        check:checkOrder,
        edit(context,button){
            const line=context.cart.items.find(item=>lineKey(item)===button.dataset.lineId);
            if(!line)return;
            context.edit={...line};
            render(context);
        },
        'select-plan'(context){
            const id=validId(context.catalogStudentId);
            if(!context.catalogOpen||!child(id))return;
            const existing=context.cart.items.find(item=>Number(item.studentId)===id&&itemType(item)==='subscription');
            context.edit={studentId:id,plan:plans[0],period:'month',...existing};
            render(context);
        },
        'add-catalog'(context,button){
            const line=catalogItems(context.catalog).find(item=>lineKey(item)===button.dataset.lineId);
            if(!line||String(line.studentId)!==String(context.catalogStudentId)||!availableItem(line))return;
            context.edit={...line};
            render(context);
        },
        'discard-edit'(context){
            if(!context.catalogOpen)return closeDialog(context);
            context.edit=null;
            setMessage(context,'');
            render(context);
        },
        async remove(context,button){
            const line=context.cart.items.find(item=>lineKey(item)===button.dataset.lineId);
            if(!line)return;
            const result=await request('/items/remove',{revision:context.cart.revision,...(line.lineId?{lineId:line.lineId}:{studentId:line.studentId})});
            if(!active(context))return;
            adoptCart(context,result);
            if(context.edit&&lineKey(context.edit)===lineKey(line))context.edit=null;
            render(context);
            setMessage(context,'Đã xóa khoản đã chọn khỏi giỏ.');
            const nextRemove=context.host.querySelector('[data-cart-action="remove"]');
            if(nextRemove)nextRemove.focus({preventScroll:true});
            else focusCartOrigin(context);
        },
        async preview(context){
            const {preview,quoteHash}=await request('/preview',{revision:context.cart.revision});
            if(!active(context))return;
            resetConsent(context);
            context.preview=preview;
            context.quoteHash=quoteHash;
            context.stage='review';
            render(context);
            focusHeading(context);
        },
        async 'cancel-order'(context){
            const {order}=await request('/orders/'+context.order.id+'/cancel',{});
            if(!active(context))return;
            context.order=order;
            render(context);
            focusHeading(context);
        }
    };
    async function submit(context,form){
        saveInputs(context,form);
        if(form.dataset.cartForm==='edit'){
            if(!context.edit||!availableItem(context.edit))return;
            const result=await request('/items/upsert',{revision:context.cart.revision,...itemBody(context.edit)});
            if(!active(context))return;
            adoptCart(context,result);
            closeDialog(context);
            setMessage(context,'Đã lưu vào giỏ.');
            return;
        }
        const {accepted,...purchaser}=context.buyer;
        const {revision,policyVersion}=context.preview;
        const {order}=await request('/checkout',{revision,checkout:{accepted,policyVersion,quoteHash:context.quoteHash,purchaser}});
        if(!active(context))return;
        context.order=order;
        context.orderId=order.id;
        context.stage='order';
        setOrderURL(order.id);
        render(context);
        focusHeading(context);
    }
    async function mount(host){
        unmount();
        if(!host||!unlocked())return;
        const query=new URLSearchParams(location.search),family=state().family,wantsCatalog=location.hash==='#family-cart-catalog';
        const orderId=validId(query.get('order'));
        const context=current={host,familyId:family?.id,stage:orderId?'order':'cart',orderId,loading:true,catalogStudentId:child(state().selectedChildId)?.id||state().children?.[0]?.id,buyer:{name:family?.parentName||'',contact:family?.email||'',relationship:'parent'}};
        host.onclick=event=>{
            const button=event.target.closest('button[data-cart-action]');
            if(!button||!active(context)||!Object.hasOwn(handlers,button.dataset.cartAction))return;
            const action=button.dataset.cartAction;
            if(action==='check')checkOrder(context,true);
            else run(context,()=>handlers[action](context,button),{quiet:['edit','add-catalog','select-plan','close-dialog','discard-edit'].includes(action)});
        };
        host.onsubmit=event=>{
            event.preventDefault();
            if(event.target.reportValidity())run(context,()=>submit(context,event.target));
        };
        host.oninput=event=>{
            const form=event.target.closest('form[data-cart-form]');
            if(form)saveInputs(context,form);
        };
        host.onchange=event=>{
            if(!active(context)||context.busy||!event.target.matches('[data-cart-beneficiary]'))return;
            const id=validId(event.target.value);
            if(!child(id))return;
            context.catalogStudentId=id;
            render(context);
            host.querySelector('[data-cart-beneficiary]')?.focus({preventScroll:true});
        };
        render(context);
        await run(context,async()=>{
            try {
                if(orderId)await readOrder(context,orderId);
                else {
                    await readCart(context);
                    if(!active(context))return;
                    const catalogLink=wantsCatalog&&Boolean(state().children?.length);
                    if(catalogLink||query.has('fee')||query.has('pack')||query.has('examProduct'))await readCatalog(context);
                    if(active(context)){
                        context.catalogOpen=catalogLink;
                        handleEditQuery(context,query);
                    }
                }
            } finally {
                context.loading=false;
                render(context);
            }
        });
    }
    function unmount(){
        if(!current)return;
        clearTimeout(current.timer);
        current.host.onclick=current.host.onsubmit=current.host.oninput=current.host.onchange=null;
        current=null;
    }
    async function resume(){
        const context=current;
        if(!context||!active(context))return;
        const focused=document.activeElement;
        if(context.stage==='order'){
            context.host.querySelector('.family-cart-qr')?.remove();
            context.order=null;
            render(context);
            return checkOrder(context,true);
        }
        await run(context,async()=>{
            const result=await readCart(context);
            if(!active(context))return;
            if(context.catalogOpen||context.edit&&itemType(context.edit)!=='subscription')await readCatalog(context);
            if(!active(context))return;
            refreshEditor(context);
            if(context.stage==='review'&&(context.preview.revision!==result.cart.revision||result.pendingOrder)){
                resetConsent(context);
                context.stage='cart';
                setMessage(context,'Giỏ đã thay đổi. Kiểm tra lại các khoản trước khi tiếp tục.');
            }
            if(context.stage!=='orders'&&(!focused||!context.host.contains(focused)||context.stage==='cart'))render(context);
        });
    }
    document.addEventListener('visibilitychange',()=>{if(current)schedule(current);});

    function planButton({studentId,plan,period}){
        const id=validId(studentId);
        if(!id)return '';
        return `<button class="btn outline" type="button" data-add-family-cart data-student-id="${id}" data-plan="${escape(plan)}" data-period="${escape(period)}" aria-label="Thêm vào giỏ · ${escape(plan)} · ${escape(periods[period])}">Thêm vào giỏ</button><p class="family-cart-status family-cart-plan-status" data-plan-cart-status role="status" aria-atomic="true"></p>`;
    }
    function planEntry(){
        return `<section class="family-cart-entry"><div><a class="btn dark" href="${path}" data-family-cart-link>Giỏ hàng</a><p>Thanh toán chung gói học, lượt luyện và học phí của các con.</p></div><p class="family-cart-status" data-plan-cart-status role="status" aria-atomic="true"></p></section>`;
    }
    function feeLink({studentId,feeId}){
        if(!child(validId(studentId))||!validId(feeId)||state().device?.childOnly)return '';
        const url=escape(editPath({studentId,type:'tuition',feeId}));
        return `<a class="btn outline" data-fee-cart href="${url}">Ba mẹ thêm học phí vào giỏ</a>`;
    }
    function planCatalog(studentId){
        const id=validId(studentId);
        if(!child(id))return '';
        return `<section class="family-cart-catalog"><div data-plan-cart-catalog data-student-id="${id}"></div><p class="family-cart-status" data-catalog-status role="status" aria-atomic="true"></p></section>`;
    }
    function fundingPanel(wallet,selected='',id='exam-funding'){
        if(!wallet)return '';
        const products=wallet.products||[];
        const balances={ 'questions-100':wallet.questionsRemaining,'exams-10':wallet.examsRemaining };
        const labels={'questions-100':'Dùng câu luyện tập đã mua','exams-10':'Dùng lượt tạo đề tự chọn đã mua'};
        const options=products.filter(product=>labels[product.sku]).map(product=>{
            const sku=product.sku,enabled=wallet.available!==false&&product.eligible&&balances[sku]>0;
            return `<option value="${escape(sku)}" ${enabled?'':'disabled'} ${enabled&&selected===sku?'selected':''}>${labels[sku]}</option>`;
        });
        const description=wallet.available===false?['Chưa đọc được số dư lượt đã mua.']:products.filter(product=>packLabels[product.sku]&&!product.eligible&&product.reason).map(product=>packLabels[product.sku]+' · '+product.reason);
        const activeChild=validId(state().activeProfile?.childId??state().selectedChildId);
        const purchase=state().authenticated&&!state().device?.childOnly?`<a class="family-cart-link" href="${path}${activeChild?'&amp;edit='+activeChild:''}#family-cart-catalog">Ba mẹ mua gói lượt</a>`:'';
        return `<h2>Lượt luyện tập đã mua</h2><p class="family-cart-balances"><span>Câu luyện tập còn <b data-questions-remaining>${balanceText(wallet.questionsRemaining)}</b></span><span>Lượt tạo đề tự chọn còn <b data-exams-remaining>${balanceText(wallet.examsRemaining)}</b></span></p>${options.length?`<label class="field"><span>Nguồn lượt khi tạo đề</span><select id="${escape(id)}"><option value="">Dùng quyền luyện tập hiện có</option>${options.join('')}</select></label><p>Mỗi lượt tạo đề tự chọn dùng cho một đề 10 câu.</p>`:''}${description.map(note=>`<p>${escape(note)}</p>`).join('')}${purchase}`;
    }
    function mountPurchasedExams(host,purchases,onOpen){
        if(!host?.isConnected)return;
        const orders=(purchases||[]).filter(item=>item.status==='paid'&&validId(item.id));
        if(!orders.length)return;
        const owner=PlatformAPI.snapshot.account?.id;
        host.innerHTML=`<h2>Bộ đề đã mua</h2><div class="family-cart-options">${orders.map(order=>`<article class="family-cart-option"><h3>${escape(order.exam_title)}</h3><button class="btn outline" type="button" data-start-bought-exam="${Number(order.id)}">Mở đề đã mua</button></article>`).join('')}</div><p role="alert" data-bought-exam-error></p>`;
        host.hidden=false;
        host.onclick=async event=>{
            const trigger=event.target.closest('[data-start-bought-exam]');
            if(!trigger||host.getAttribute('aria-busy')==='true'||owner!==PlatformAPI.snapshot.account?.id)return;
            const error=host.querySelector('[data-bought-exam-error]');
            const buttons=host.querySelectorAll('button');
            host.setAttribute('aria-busy','true');
            buttons.forEach(button=>button.disabled=true);
            error.textContent='';
            try{
                const result=await PlatformAPI.request('premium/purchases/'+validId(trigger.dataset.startBoughtExam)+'/start',{},{owner});
                if(host.isConnected)onOpen(result.exam);
            }catch(problem){if(problem.name!=='AbortError'&&host.isConnected)error.textContent=problem.message;}
            finally{host.removeAttribute('aria-busy');buttons.forEach(button=>button.disabled=false);}
        };
    }
    function loadPlanData(studentId,signal){
        return Promise.all([request('',undefined,signal),request('/catalog',undefined,signal)]).then(([result,catalog])=>{
            if(!Array.isArray(result.cart?.items)||!Object.hasOwn(catalog.balances||{},studentId))throw new Error('Chưa đọc được giỏ hàng và danh sách gói của con.');
            return {cart:result.cart,catalog};
        });
    }
    function mountPlans(host,{cart,catalog,context}={}){
        if(!host||!cart||!catalog||!context)return;
        const entry=host?.querySelector('.family-cart-entry');
        const link=entry?.querySelector('[data-family-cart-link]'),message=entry?.querySelector('[data-plan-cart-status]');
        const buttons=[...host.querySelectorAll('[data-add-family-cart]')];
        const catalogHost=host.querySelector('[data-plan-cart-catalog]');
        const beneficiaryId=validId(catalogHost?.dataset.studentId);
        let busy=false;
        const current=()=>catalogHost?.isConnected&&unlocked()&&state().context===context&&validId(state().selectedChildId)===beneficiaryId;
        const renderCatalog=()=>{
            if(current())catalogHost.innerHTML=catalogMarkup(catalog,beneficiaryId,cart,false);
        };
        const update=result=>{
            if(!current())return;
            cart=result.cart;
            if(link)link.textContent='Giỏ hàng ('+cart.items.length+')';
            renderCatalog();
        };
        const saveDraft=(item,label,notice)=>{
            const draft=document.createElement('a');
            draft.href=editPath(item);
            draft.textContent='Xem và lưu lựa chọn';
            notice.replaceChildren(document.createTextNode(label+' '),draft);
        };
        async function add(button,selectedItem){
            if(!current()||!button.isConnected||busy)return;
            const item=selectedItem||{studentId:validId(button.dataset.studentId),plan:button.dataset.plan,period:button.dataset.period};
            const type=itemType(item);
            const profile=child(item.studentId);
            const notice=type==='subscription'?button.parentElement.querySelector('[data-plan-cart-status]')||message:catalogHost?.parentElement.querySelector('[data-catalog-status]')||message;
            if(!profile||validId(item.studentId)!==beneficiaryId||!notice)return;
            busy=true;
            for(const itemButton of [...buttons,...(catalogHost?.querySelectorAll('[data-add-catalog]')||[])])itemButton.disabled=true;
            const name=profile.nickname||profile.name;
            notice.textContent='Đang thêm gói cho '+name+'…';
            try {
                if(!cart)update(await request(''));
                if(!current())return;
                const existing=cart.items.find(line=>Number(line.studentId)===Number(item.studentId)&&(type==='subscription'?itemType(line)===type:lineKey(line)===lineKey(item)));
                if(existing&&(type!=='subscription'||(existing.plan===item.plan&&existing.period===item.period))){
                    notice.textContent='Khoản này của '+name+' đã có trong giỏ.';
                    return;
                }
                if(existing){saveDraft(item,'Giỏ đã có gói của '+name+'.',notice);return;}
                const result=await request('/items/upsert',{revision:cart.revision,...itemBody(item)});
                if(!current())return;
                update(result);
                notice.textContent='Đã thêm '+titleFor(item)+' cho '+name+'.';
            } catch(error){
                if(!current())return;
                if(error.code==='family_parent_pin_required'){location.assign(editPath(item));return;}
                if(error.code==='cart_revision_conflict'){
                    cart=null;
                    saveDraft(item,'Giỏ vừa thay đổi. Lựa chọn của ba mẹ vẫn được giữ.',notice);
                    request('').then(update).catch(()=>{});
                } else if(!error.familyAccessChanged)saveDraft(item,error.message||'Chưa thể cập nhật giỏ.',notice);
            } finally {
                busy=false;
                for(const itemButton of [...buttons,...(catalogHost?.querySelectorAll('[data-add-catalog]')||[])])itemButton.disabled=false;
            }
        }
        if(!current())return;
        update({cart});
        buttons.forEach(button=>button.onclick=()=>add(button));
        if(catalogHost)catalogHost.onclick=event=>{
            const button=event.target.closest('[data-add-catalog]');
            const item=button&&catalogItems(catalog).find(line=>lineKey(line)===button.dataset.addCatalog);
            if(item&&Number(item.studentId)===beneficiaryId&&availableItem(item))add(button,item);
        };
    }
    window.FamilyCart={mount,unmount,resume,planButton,planEntry,planCatalog,loadPlanData,mountPlans,feeLink,fundingPanel,mountPurchasedExams};
})();
