'use strict';

// Enable the screen only with JavaScript; server-rendered content stays readable without it.
(() => {
    const root=document.documentElement;
    root.classList.add('page-loading');
    let started=performance.now(),timer,finished=false;
    const hide=()=>{
        root.classList.remove('page-loading');
        document.getElementById('page-loader')?.setAttribute('aria-hidden','true');
        clearTimeout(timer);
    };
    const finish=()=>{
        if(finished)return;
        finished=true;
        clearTimeout(timer);
        timer=setTimeout(hide,Math.max(0,500-(performance.now()-started)));
    };
    window.PageLoading={finish};
    // A failed script or an unavailable API must never leave a permanent cover.
    timer=setTimeout(hide,8000);
    window.addEventListener('load',()=>{
        if(!document.querySelector('script[src="app.js"]'))finish();
    },{once:true});
    window.addEventListener('pageshow',event=>{
        if(!event.persisted)return;
        started=performance.now();finished=false;
        document.getElementById('page-loader')?.removeAttribute('aria-hidden');
        root.classList.add('page-loading');
        finish();
    });
})();
