'use strict';
const PlatformAPI = (() => {
    const enabled = document.documentElement.dataset.backend === 'database';
    function maintenance(response) {
        if(response.headers.get('X-5BMath-Maintenance')==='1') {
            location.reload();
            throw new Error('Hệ thống đang được cập nhật, vui lòng quay lại sau.');
        }
    }
    if(enabled) {
        let checking=false;
        const check=async()=>{if(checking||document.visibilityState==='hidden')return;checking=true;try{maintenance(await fetch('/api/site-visibility/check',{cache:'no-store',credentials:'same-origin'}));}catch{}finally{checking=false;}};
        addEventListener('hashchange',check);addEventListener('popstate',check);addEventListener('focus',check);
        document.addEventListener('visibilitychange',check);setInterval(check,15000);
    }
    let snapshot = {authenticated:false};
    let sessionRevision = 0;
    let familyContext = '', familyBootstrap, familyState=null, familyKnown=false, invalidating=false, familyChannel;
    function adoptFamily(result) {
        familyState=result?.authenticated?result:null;
        familyContext=familyState?.context||'';
        if(familyState)familyKnown=true;
        document.documentElement.classList.toggle('family-signed-in',Boolean(familyState));
        return familyState;
    }
    function unlockParentHere(current) {
        const entry=document.documentElement.dataset.page||'home';
        if(current?.activeProfile?.type!=='parent'||current.scope==='parent_full'||!(entry==='dashboard'||entry.startsWith('learn-')))return false;
        const app=document.querySelector('#app');
        if(app){
            app.replaceChildren();const section=document.createElement('section');section.className='card card-pad family-locked-shell';
            const heading=document.createElement('h2');heading.textContent='Ba mẹ xác nhận bằng PIN';
            const message=document.createElement('p');message.textContent='Góc phụ huynh đã khóa. Nhập PIN để tiếp tục tại trang này.';
            const button=document.createElement('button');button.className='btn dark';button.textContent='Mở bằng PIN';button.type='button';
            button.onclick=()=>window.FamilyProfiles?.open({target:'parent',stay:true,onSuccess:()=>location.reload()});
            section.append(heading,message,button);app.append(section);button.click();
        }
        return true;
    }
    function invalidateFamily() {
        if(invalidating)return;invalidating=true;
        sessionRevision++;snapshot={authenticated:false};familyContext='';familyBootstrap=null;
        document.querySelector('#app')?.replaceChildren();document.querySelector('#modal-body')?.replaceChildren();
        document.querySelector('#modal')?.close();
        prepareFamily({force:true}).then(current=>{
            if(unlockParentHere(current))return;
            const destination=current?(window.FamilyProfiles?.destination(current)||((current.activeProfile?.type==='parent')?'/gia-dinh/?view=parent':current.activeProfile?.type==='child'?'/tai-khoan/':'/gia-dinh/')):'/gia-dinh/?mode=login';
            location.replace(destination);
        }).catch(()=>location.replace('/gia-dinh/?session=changed'));
    }
    if(enabled&&typeof BroadcastChannel==='function'){
        familyChannel=new BroadcastChannel('5bmath-family-context');
        familyChannel.onmessage=event=>{if(event.data?.type==='changed'&&event.data.source!==window.FamilyProfiles?.source&&familyKnown)invalidateFamily();};
    }
    if(enabled){
        addEventListener('family-state-updated',event=>adoptFamily(event.detail?.state));
        addEventListener('family-access-invalidated',()=>{if(familyKnown)invalidateFamily();});
        addEventListener('family-guest',()=>{if(familyKnown)invalidateFamily();});
        addEventListener('family-privilege-expired',event=>{adoptFamily(event.detail?.state);if(unlockParentHere(familyState))invalidating=true;});
        addEventListener('family-profile-changed',()=>{sessionRevision++;snapshot={authenticated:false};document.querySelector('#app')?.replaceChildren();});
    }
    async function prepareFamily({force=false}={}) {
        if(force)familyBootstrap=null;
        if(!familyBootstrap)familyBootstrap=(async()=>{
            if(typeof window.FamilyProfiles?.refresh==='function')return adoptFamily(await window.FamilyProfiles.refresh({force}));
            const response=await fetch('/api/family/state',{credentials:'same-origin',cache:'no-store'});
            maintenance(response);
            if(response.status===404){familyContext='';return null;}
            const result=await response.json();
            if(!response.ok)throw new Error(result.error||'Chưa thể kiểm tra hồ sơ gia đình.');
            window.FamilyProfiles?.accept?.(result);
            return adoptFamily(result);
        })().catch(error=>{familyBootstrap=null;throw error;});
        return familyBootstrap;
    }
    function requestSignal(parent) {
        if(typeof AbortSignal.timeout === 'function' && (!parent || typeof AbortSignal.any === 'function')) {
            const timeout = AbortSignal.timeout(20000);
            return {signal:parent ? AbortSignal.any([parent,timeout]) : timeout,cleanup(){}};
        }
        const controller = new AbortController();
        const abort = () => controller.abort(parent.reason);
        const timer = setTimeout(() => controller.abort(),20000);
        if(parent?.aborted) abort();
        else parent?.addEventListener('abort',abort,{once:true});
        return {signal:controller.signal,cleanup(){clearTimeout(timer);parent?.removeEventListener('abort',abort);}};
    }
    async function request(path, body, options = {}) {
        await prepareFamily();
        // Media requests bind to the profile that opened the player. Recheck
        // after the asynchronous family bootstrap and before sending a write.
        const boundContext = options.expectedFamilyContext !== undefined || options.expectedCsrf !== undefined;
        const checkBoundContext = () => {
            if (boundContext && (
                (options.expectedFamilyContext !== undefined && options.expectedFamilyContext !== familyContext) ||
                (options.expectedCsrf !== undefined && options.expectedCsrf !== snapshot.csrf) ||
                (options.owner !== undefined && options.owner !== snapshot.account?.id)
            )) throw new DOMException('Hồ sơ hoặc phiên học đã thay đổi.','AbortError');
        };
        checkBoundContext();
        const sessionCsrf = snapshot.csrf;
        const revision = sessionRevision;
        const authMutation = body !== undefined && ['auth/login','auth/register','auth/logout'].includes(path.split('?')[0]);
        const pending = requestSignal(options.signal);
        try {
            const response = await fetch('/api/v1/' + path, {
                method:body === undefined ? 'GET' : 'POST', credentials:'same-origin',
                headers:{...(familyContext?{'X-Family-Context':familyContext}:{}),...(body===undefined?{}:{'Content-Type':'application/json','X-CSRF-Token':snapshot.csrf || ''})},
                body:body === undefined ? undefined : JSON.stringify(body),signal:pending.signal,
            });
            maintenance(response);
            const result = await response.json();
            checkBoundContext();
            if(familyKnown&&(response.status===401||result.familyAccessChanged||(Object.hasOwn(result,'authenticated')&&!result.authenticated&&snapshot.authenticated))){invalidateFamily();throw new DOMException('Hồ sơ hoặc quyền vừa thay đổi.','AbortError');}
            // A response sent for the previous login must not restore its profile/theme.
            if(!authMutation && revision !== sessionRevision) {
                throw new DOMException('Phiên tài khoản đã thay đổi.','AbortError');
            }
            if(options.owner !== undefined && (snapshot.account?.id !== options.owner || snapshot.csrf !== sessionCsrf)) {
                throw new DOMException('Phiên tài khoản đã thay đổi.','AbortError');
            }
            if(result.arenaDiscipline)snapshot={...snapshot,arenaDiscipline:result.arenaDiscipline};
            if (!response.ok) {const error=new Error(result.error || 'Không thể kết nối máy chủ.');error.status=response.status;error.details=result;throw error;}
            if(authMutation) sessionRevision++;
            if (Object.hasOwn(result,'authenticated')) {
                if(!authMutation && (snapshot.authenticated !== result.authenticated || snapshot.account?.id !== result.account?.id || snapshot.csrf !== result.csrf)) sessionRevision++;
                snapshot = result;
                if(typeof ThemeManager !== 'undefined') ThemeManager.sync(result);
            }
            if(body!==undefined&&path.split('?')[0]==='mascot'&&familyState)await window.FamilyProfiles?.refresh?.();
            return result;
        } finally {
            pending.cleanup();
        }
    }
    async function refresh({compact=false}={}) {
        const family=await prepareFamily({force:true});
        if(family&&family.activeProfile?.type!=='child'&&(compact||!family.selectedChildId||family.scope!=='parent_full')){
            snapshot={authenticated:true,familyParent:true,csrf:family.csrf,name:'',account:null,state:{}};
            return snapshot;
        }
        await request('session'+(compact?'?view=identity':''));
        const id=new URLSearchParams(location.search).get('id');
        if(snapshot.authenticated && /^\/(lam-de|ket-qua-thi)\/$/.test(location.pathname) && /^\d+$/.test(id || '')) {
            const result=await request('exams/'+id);
            snapshot.state.exams[id]=result.exam;
        }
        return snapshot;
    }
    async function logout() {
        const family=await prepareFamily({force:true});
        if(!family)return request('auth/logout',{});
        const response=await fetch('/api/family/logout',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json','X-CSRF-Token':family.csrf,'X-Family-Context':family.context},body:'{}'});
        const result=await response.json();if(!response.ok)throw new Error(result.error||'Chưa đăng xuất được.');
        familyChannel?.postMessage({type:'changed',source:window.FamilyProfiles?.source});invalidateFamily();return result;
    }
    return {enabled,request,prepareFamily,adoptFamily,invalidateFamily,unlockParentHere,get familyContext(){return familyContext;},get familyState(){return familyState;},get snapshot(){return snapshot;},
        refresh,logout,
        async authenticate(kind, values,{compact=false}={}) { return request('auth/' + kind+(compact?'?view=identity':''),values); }};
})();
