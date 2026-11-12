'use strict';
(() => {
    const form=document.querySelector('#intake-form');
    if(!form)return;
    const status=document.querySelector('#intake-status');
    const errorBox=document.querySelector('#intake-error');
    const submit=document.querySelector('#intake-submit');
    let token='',lastPayload='',requestKey='';
    const enabled=location.protocol!=='file:' && document.documentElement.dataset.backend==='database';
    async function request(path,body) {
        const response=await fetch('api/v1/admissions'+path,{method:body?'POST':'GET',credentials:'same-origin',signal:AbortSignal.timeout(20000),
            headers:body?{'Content-Type':'application/json','X-Intake-Token':token}:{},body:body?JSON.stringify(body):undefined});
        const result=await response.json();
        if(!response.ok) {const error=new Error(result.error||'Chưa gửi được đăng ký. Vui lòng thử lại.');error.status=response.status;throw error;}
        return result;
    }
    async function prepare() {
        token=(await request('/token')).token;
        if(!token)throw new Error('Chưa kết nối được máy chủ nhận đăng ký.');
    }
    if(!enabled){status.textContent='Biểu mẫu trên bản tĩnh chưa nhận đăng ký. Vui lòng liên hệ Zalo hoặc Facebook bên dưới.';}
    else {submit.disabled=false;status.textContent='Thông tin được gửi khi bạn bấm nút đăng ký.';}
    form.addEventListener('submit',async event=>{
        event.preventDefault();
        if(!enabled || submit.disabled || !form.reportValidity())return;
        submit.disabled=true;errorBox.textContent='';status.textContent='Đang gửi đăng ký…';
        const fields=Object.fromEntries(new FormData(form));
        fields.grade=Number(fields.grade);fields.consent=form.elements.consent.checked;
        const packed=JSON.stringify(fields);
        if(packed!==lastPayload){requestKey=crypto.randomUUID?crypto.randomUUID():Array.from(crypto.getRandomValues(new Uint8Array(24)),x=>x.toString(16).padStart(2,'0')).join('');lastPayload=packed;}
        fields.requestKey=requestKey;
        try {
            // Refresh the short-lived form token on each attempt; the request key makes retries safe.
            await prepare();
            const result=await request('',fields);
            if(!result.saved || !result.reference)throw new Error('Máy chủ chưa xác nhận lưu đăng ký. Vui lòng thử lại.');
            document.querySelector('#intake-reference').textContent=result.reference;
            form.hidden=true;
            const success=document.querySelector('#intake-success');success.hidden=false;success.focus();
        } catch(error) {
            errorBox.textContent=error instanceof TypeError || error instanceof SyntaxError || ['TimeoutError','AbortError'].includes(error.name)?'Chưa kết nối được máy chủ nhận đăng ký. Thông tin vẫn còn trên biểu mẫu; bạn có thể thử lại hoặc liên hệ Zalo.':error.message;
            errorBox.focus();status.textContent='Chưa gửi thành công.';
        } finally {submit.disabled=false;}
    });
})();
