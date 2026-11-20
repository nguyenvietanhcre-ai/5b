'use strict';
(() => {
  if (window.AppShell) return;
  let nav, viewOverride, cartContext, cartRead, cartCount = 0, cartBlocked = false;
  const cartPath = '/gia-dinh/?view=cart';
  const privatePaths = new Set(['gia-dinh','goc-hoc-tap','hoc-theo-tuan','chuyen-de','bai-giang','bai-chuyen-de','thi-thu','lam-de','tra-cuu-cau-hoi','ket-qua-thi','dau-tri','phong-dau','tran-dau','ket-qua-tran','linh-vat','xep-hang','tai-khoan','lop-zoom','dang-ky-hoc-zoom','nang-cap','thanh-toan']);
  const paths = {
    book:'M3 4h6a3 3 0 0 1 3 2 3 3 0 0 1 3-2h6v15h-6a3 3 0 0 0-3 2 3 3 0 0 0-3-2H3V4Zm9 2v15',
    game:'M8 8h8a5 5 0 0 1 4.8 3.6l1 4a3 3 0 0 1-5 2.9L15 17H9l-1.8 1.5a3 3 0 0 1-5-2.9l1-4A5 5 0 0 1 8 8Zm-1 3v5m-2.5-2.5h5M16 12h.01M19 15h.01',
    package:'M3 7l9-4 9 4-9 4-9-4Zm0 0v10l9 4 9-4V7M12 11v10',
    cart:'M2 3h3l3 12h11l2-8H6m3 12a1 1 0 1 0 2 0 1 1 0 1 0-2 0Zm8 0a1 1 0 1 0 2 0 1 1 0 1 0-2 0Z',
    user:'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM4 21v-3a8 8 0 0 1 16 0v3',
    children:'M9 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6ZM3 21v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 1 1 0 6M18 13a5 5 0 0 1 3 4.6V21',
    add:'M15 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM3 21v-3a8 8 0 0 1 12-6M19 13v8m-4-4h8',
    devices:'M3 3h14v11H3V3Zm4 15h6m-3-4v4m7-9h5v12h-7V9h2Z'
  };
  function icon(name) {
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
    svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('aria-hidden','true');
    const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',paths[name]||paths.user);svg.append(path);return svg;
  }
  function currentView() {
    const path=location.pathname.split('/')[1];
    if (viewOverride) return viewOverride;
    if (path==='gia-dinh') return new URLSearchParams(location.search).get('view')||'overview';
    if (['nang-cap','thanh-toan'].includes(path)) return 'package';
    if (['dau-tri','phong-dau','tran-dau','ket-qua-tran','xep-hang'].includes(path)) return 'games';
    if (['tai-khoan','linh-vat','lop-zoom','dang-ky-hoc-zoom'].includes(path)) return 'personal';
    return 'learn';
  }
  function validCartContext() {
    const fp=window.FamilyProfiles,s=fp?.state;
    return !cartBlocked&&s?.authenticated&&s.scope==='parent_full'&&!s.parentLocked&&!s.device?.childOnly&&
      fp.profileOf(s).type==='parent'&&typeof s.context==='string'&&s.context===cartContext;
  }
  function renderCartBadge() {
    const badge=nav?.querySelector('[data-cart-badge]');
    if (!badge) return;
    const count=validCartContext()?cartCount:0;
    badge.hidden=count===0;
    badge.textContent=count?String(count):'';
    badge.closest('a').setAttribute('aria-label',count?`Giỏ hàng, ${count} khoản`:'Giỏ hàng');
  }
  async function refreshCartCount() {
    if (!validCartContext()||cartRead||document.visibilityState==='hidden') return;
    const fp=window.FamilyProfiles,read={};
    cartRead=read;
    try {
      const result=await fp.request('cart');
      if (cartRead!==read||!validCartContext()) return;
      cartCount=Array.isArray(result?.cart?.items)?result.cart.items.length:0;
      renderCartBadge();
    } catch (error) {
      if (cartRead!==read||!validCartContext()) return;
      cartCount=0;
      renderCartBadge();
      if (error.code==='family_parent_pin_required') fp.refresh().catch(()=>{});
    } finally {
      if (cartRead===read) cartRead=null;
    }
  }
  function updateCartContext(context) {
    if (cartContext===context) return;
    cartContext=context;
    cartRead=null;
    cartCount=0;
    if (context) queueMicrotask(refreshCartCount);
  }
  function cartUpdated(event) {
    const {context,count}=event.detail||{};
    if (!validCartContext()||context!==cartContext) return;
    if (count===undefined) {
      cartRead=null;
      refreshCartCount();
    } else if (Number.isSafeInteger(count)&&count>=0) {
      // A newer cart response supersedes any pending badge read.
      cartRead=null;
      cartCount=count;
      renderCartBadge();
    }
  }
  async function resumeCartBadge() {
    if (!validCartContext()||document.visibilityState==='hidden') return;
    const context=cartContext;
    try {
      await window.FamilyProfiles.refresh();
      refreshCartCount();
    } catch {
      if (cartContext===context) {
        cartRead=null;
        cartCount=0;
        renderCartBadge();
      }
    }
  }
  function appendCartIcon(link) {
    const graphic=document.createElement('span'),badge=document.createElement('span');
    graphic.className='app-bottom-cart-icon';
    graphic.setAttribute('aria-hidden','true');
    badge.dataset.cartBadge='';
    badge.hidden=true;
    graphic.append(icon('cart'),badge);
    link.append(graphic);
    link.addEventListener('click',event=>{
      if (event.button!==0||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey) return;
      if (window.FamilyApp?.retainCart?.()) event.preventDefault();
    });
  }
  function sync() {
    const fp=window.FamilyProfiles,s=fp?.state||{},path=location.pathname.split('/')[1];
    const active=Boolean(s.authenticated&&privatePaths.has(path));
    document.body.classList.toggle('app-shell-private',active);
    document.documentElement.classList.toggle('user-signed-in',Boolean(s.authenticated));
    const signedReady=active&&s.children?.length&&!s.onboarding?.needsParentPin&&!s.onboarding?.needsChild;
    const ready=privatePaths.has(path);
    document.body.classList.toggle('app-shell-with-nav',Boolean(ready));
    document.documentElement.classList.toggle('app-shell-with-nav',Boolean(ready));
    const role=signedReady?(!s.device?.childOnly&&fp.profileOf(s).type==='parent'?'parent':'child'):'guest';
    updateCartContext(role==='parent'&&!cartBlocked&&s.scope==='parent_full'&&!s.parentLocked&&s.context?s.context:null);
    if (!ready) { nav?.remove();nav=null;return; }
    const view=role==='guest'&&path==='gia-dinh'?'personal':currentView();
    const items=role==='parent'?[
      ['children','Các con','/gia-dinh/?view=parent','children'],
      ['package','Gói học','/nang-cap/','package'],
      ['cart','Giỏ hàng',cartPath,'cart'],
      ['account','Tài khoản','/gia-dinh/?view=account','user']
    ]:[
      ['learn','Học & Luyện','/hoc-theo-tuan/','book'],
      ['games','Vườn tranh tài','/dau-tri/','game'],
      ['package','Gói học','/nang-cap/','package'],
      ['personal',role==='guest'?'Đăng nhập':'Cá nhân',role==='guest'?'/gia-dinh/':'/tai-khoan/','user']
    ];
    const signature=JSON.stringify([role,view,s.context,(s.children||[]).map(c=>[c.id,c.nickname,c.mascotCode]),s.activeProfile]);
    if (nav?.dataset.signature===signature) {renderCartBadge();return;}
    if (!nav) {nav=document.createElement('nav');nav.className='app-bottom-nav';document.body.append(nav);}
    nav.setAttribute('aria-label',role==='parent'?'Điều hướng phụ huynh':'Điều hướng học tập');
    nav.dataset.signature=signature;nav.dataset.role=role;nav.replaceChildren();
    for (const [key,label,href,art] of items) {
      const a=document.createElement('a');a.href=href;a.className='app-bottom-tab';
      const selected=key===view||(key==='children'&&['parent','overview','addchild','create-child','children'].includes(view))||(key==='account'&&view==='devices');
      if (selected) a.setAttribute('aria-current','page');
      if (key==='cart') {a.classList.add('app-bottom-tab--cart');appendCartIcon(a);} else a.append(icon(art));
      const text=document.createElement('span');text.className='app-bottom-label';text.textContent=label;a.append(text);nav.append(a);
    }
    if(role!=='guest'){const profile=document.createElement('div');profile.className='app-bottom-profile';profile.dataset.familyProfileMenu='';nav.append(profile);fp.mount(profile);}
    renderCartBadge();
  }
  window.AppShell={sync,init:sync,setView(options={}){viewOverride=options.view;sync();}};
  window.addEventListener('family-state-updated',()=>{cartBlocked=false;sync();});
  function clearCartAccess(){cartBlocked=true;sync();}
  window.addEventListener('family-access-invalidated',clearCartAccess);
  window.addEventListener('family-privilege-expired',clearCartAccess);
  window.addEventListener('family-guest',clearCartAccess);
  window.addEventListener('family-cart-updated',cartUpdated);
  window.addEventListener('focus',resumeCartBadge);
  document.addEventListener('visibilitychange',resumeCartBadge);
  window.addEventListener('pageshow',event=>{if(event.persisted)resumeCartBadge();});
  window.addEventListener('popstate',()=>{viewOverride=null;sync();});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',sync,{once:true});else sync();
})();
