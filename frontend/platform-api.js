'use strict';
const PlatformAPI = (() => {
    const enabled = document.documentElement.dataset.backend === 'database';
    let snapshot = {authenticated:false};
    let sessionRevision = 0;
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
        const sessionCsrf = snapshot.csrf;
        const revision = sessionRevision;
        const authMutation = body !== undefined && ['auth/login','auth/register','auth/logout'].includes(path.split('?')[0]);
        const pending = requestSignal(options.signal);
        try {
            const response = await fetch('/api/v1/' + path, {
                method:body === undefined ? 'GET' : 'POST', credentials:'same-origin',
                headers:body === undefined ? {} : {'Content-Type':'application/json','X-CSRF-Token':snapshot.csrf || ''},
                body:body === undefined ? undefined : JSON.stringify(body),signal:pending.signal,
            });
            const result = await response.json();
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
            return result;
        } finally {
            pending.cleanup();
        }
    }
    async function refresh({compact=false}={}) {
        await request('session'+(compact?'?view=identity':''));
        const id=new URLSearchParams(location.search).get('id');
        if(snapshot.authenticated && /^\/(lam-de|ket-qua-thi)\/$/.test(location.pathname) && /^\d+$/.test(id || '')) {
            const result=await request('exams/'+id);
            snapshot.state.exams[id]=result.exam;
        }
        return snapshot;
    }
    return {enabled,request,get snapshot(){return snapshot;},
        refresh,logout:() => request('auth/logout',{}),
        async authenticate(kind, values,{compact=false}={}) { return request('auth/' + kind+(compact?'?view=identity':''),values); }};
})();
