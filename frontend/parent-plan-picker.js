'use strict';
(() => {
  if(window.ParentPlanPicker)return;
  const mounted=new Map();
  const escape=value=>String(value??'').replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
  const family=()=>window.FamilyProfiles?.state||{};
  const isParent=state=>Boolean(state.authenticated&&state.activeProfile?.type==='parent');
  const selectedChild=state=>(state.children||[]).find(child=>String(child.id)===String(state.selectedChildId));
  function render({state=family()}={}){
    if(!isParent(state))return '';
    const selected=selectedChild(state);
    return '<section id="parent-plan-picker" class="parent-plan-picker" aria-labelledby="parent-plan-picker-title"><div class="parent-plan-picker-heading"><h2 id="parent-plan-picker-title">Mua gói học cho con nào?</h2><p>Gói học và quyền sử dụng được áp dụng riêng cho con đã chọn.</p></div><form class="parent-plan-picker-form"><label for="parent-plan-child">Hồ sơ con</label><div class="parent-plan-picker-controls"><select id="parent-plan-child" name="childId" required><option value=""'+(!selected?' selected':'')+' disabled>Chọn con để xem gói học</option>'+(state.children||[]).map(child=>'<option value="'+escape(child.id)+'"'+(String(child.id)===String(selected?.id)?' selected':'')+'>'+escape(child.nickname||child.name)+' · Lớp '+escape(child.grade)+'</option>').join('')+'</select><button type="submit" class="btn dark">Xem gói cho con</button></div></form><p class="parent-plan-picker-current" data-parent-plan-current>'+escape(selected?'Đang xem gói học cho '+(selected.nickname||selected.name)+' · Lớp '+selected.grade:'Ba mẹ chọn một con để xem gói hiện tại và tiếp tục mua gói.')+'</p><p class="parent-plan-picker-status" role="status" aria-live="polite" hidden></p><a href="/gia-dinh/?view=parent">Quản lý các con</a></section>';
  }
  function mount(host=document.getElementById('parent-plan-picker'),{navigate=url=>location.assign(url),onLoading,onSelected,onError}={}){
    if(!host)return;
    unmount(host);
    const form=host.querySelector('form'),select=host.querySelector('select[name=childId]'),message=host.querySelector('.parent-plan-picker-status');
    if(!form||!select||!message)return;
    const context={disposed:false,busy:false,attempt:0};mounted.set(host,context);
    const inPlace=Boolean(onLoading);
    const controls=[select,form.querySelector('[type=submit]')];
    const choose=async(value=select.value)=>{
      if(context.disposed||(!inPlace&&context.busy))return;
      const profiles=window.FamilyProfiles,childId=Number(value),current=family();
      const child=(current.children||[]).find(child=>Number(child.id)===childId);
      if(!isParent(current)||current.device?.childOnly||!Number.isSafeInteger(childId)||!child)return;
      if(current.scope!=='parent_full'){profiles.open({target:'parent',stay:true,onSuccess:()=>choose(value)});return;}
      const attempt=++context.attempt;
      const latest=()=>!context.disposed&&host.isConnected&&attempt===context.attempt;
      context.busy=true;host.setAttribute('aria-busy','true');
      if(inPlace)onLoading(child);
      else {
        controls.forEach(control=>control.disabled=true);
        message.hidden=false;message.textContent='Đang mở gói học cho con…';delete message.dataset.error;
      }
      try{
        // Keep the adult capability; this endpoint only selects the purchase beneficiary.
        await profiles.request('parent/select',{childId});
        const updated=family();
        if(!latest())return;
        if(!isParent(updated)||updated.scope!=='parent_full'||updated.device?.childOnly||updated.family?.id!==current.family?.id||String(updated.selectedChildId)!==String(childId))throw new Error('Hồ sơ vừa thay đổi. Ba mẹ mở lại Gói học để chọn đúng con.');
        if(onSelected)await onSelected(updated);
        if(!latest()||inPlace)return;
        const params=new URLSearchParams({childId:String(childId)}),period=new URLSearchParams(location.search).get('period');
        if(['month','year'].includes(period))params.set('period',period);
        navigate('/nang-cap/?'+params.toString());
      }catch(error){
        if(!latest())return;
        if(inPlace)onError?.(child,error);
        else {message.textContent=error.message||'Chưa chọn được con. Ba mẹ vui lòng thử lại.';message.dataset.error='true';}
      }finally{
        if(latest()){
          context.busy=false;host.removeAttribute('aria-busy');
          if(!inPlace)controls.forEach(control=>control.disabled=false);
        }
      }
    };
    const submit=event=>{event.preventDefault();if(form.reportValidity())choose();};
    const change=()=>choose();
    const invalidate=()=>unmount(host);
    context.cleanup=()=>{form.removeEventListener('submit',submit);select.removeEventListener('change',change);window.removeEventListener('family-access-invalidated',invalidate);window.removeEventListener('family-guest',invalidate);};
    form.addEventListener('submit',submit);window.addEventListener('family-access-invalidated',invalidate);window.addEventListener('family-guest',invalidate);
    if(inPlace)select.addEventListener('change',change);
    return choose;
  }
  function unmount(host){for(const [target,context] of mounted){if(host&&target!==host)continue;context.disposed=true;context.cleanup?.();mounted.delete(target);}}
  window.ParentPlanPicker={render,mount,unmount,hasSelected:(state=family())=>Boolean(isParent(state)&&selectedChild(state))};
})();
