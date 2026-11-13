'use strict';
// The same literal manifest is read by the browser, Python allowlist and static build.
const RuntimeAssets = (() => {
    const manifest = /* RUNTIME_MANIFEST_START */
{
    "files": [
        "page-loading.js",
        "runtime-assets.js",
        "learning-content.js",
        "arena-audio.js",
        "learning.js",
        "learning.css",
        "staff.js",
        "staff.css",
        "mam-sach-animation.js",
        "mam-sach-animation.css",
        "arena-starfish.js",
        "arena-starfish.css",
        "bear-frames.js",
        "bear-animation.js",
        "bear-animation.css",
        "butterfly-renderer.js",
        "butterfly-animation.js",
        "butterfly-animation.css",
        "fox-animation.js",
        "fox-animation.css",
        "tiger-animation.js",
        "arena-voi-renderer.js",
        "arena-voi-poses.js",
        "arena-voi.js",
        "arena-voi.css",
        "eagle-animation.js",
        "eagle-animation.css",
        "arena-lion.js",
        "arena-lion.css",
        "rabbit-animation.js",
        "owl-animation.js",
        "arena-sparrow-animation.js",
        "arena-sparrow-animation.css",
        "arena-bee-animation.js",
        "arena-bee-animation.css",
        "arena-dolphin.js",
        "arena-dolphin.css",
        "horse-animation.js",
        "horse-animation.css",
        "arena-cat-animation.js",
        "arena-cat-animation.css",
        "arena-crab-animation.js",
        "arena-crab-animation.css",
        "shark-animation.js",
        "octopus-animation.js",
        "octopus-animation.css"
    ],
    "groups": {
        "learning": {
            "scripts": [
                "learning-content.js",
                "arena-audio.js",
                "learning.js"
            ],
            "styles": [
                "learning.css"
            ]
        },
        "staff": {
            "scripts": [
                "staff.js"
            ],
            "styles": [
                "staff.css"
            ]
        }
    },
    "mascots": {
        "sprout": {
            "scripts": [
                "mam-sach-animation.js"
            ],
            "styles": [
                "mam-sach-animation.css"
            ],
            "api": "MamSachAnimation",
            "activate": "mountManaged",
            "cleanup": "destroy"
        },
        "starfish": {
            "scripts": [
                "arena-starfish.js"
            ],
            "styles": [
                "arena-starfish.css"
            ],
            "api": "ArenaStarfish",
            "activate": "mount",
            "cleanup": "destroy"
        },
        "gau": {
            "scripts": [
                "bear-frames.js",
                "bear-animation.js"
            ],
            "styles": [
                "bear-animation.css"
            ],
            "api": "BearAnimation",
            "activate": "mount",
            "cleanup": "unmount"
        },
        "butterfly": {
            "scripts": [
                "butterfly-renderer.js",
                "butterfly-animation.js"
            ],
            "styles": [
                "butterfly-animation.css"
            ],
            "api": "ButterflyAnimation",
            "activate": "mount",
            "cleanup": "destroy"
        },
        "fox": {
            "scripts": [
                "fox-animation.js"
            ],
            "styles": [
                "fox-animation.css"
            ],
            "api": "FoxAnimation",
            "activate": "mountManaged",
            "cleanup": "destroy"
        },
        "tiger": {
            "scripts": [
                "tiger-animation.js"
            ],
            "styles": [],
            "api": "TigerAnimation",
            "activate": "hydrate",
            "cleanup": "cancelAll"
        },
        "voi": {
            "scripts": [
                "arena-voi-renderer.js",
                "arena-voi-poses.js",
                "arena-voi.js"
            ],
            "styles": [
                "arena-voi.css"
            ],
            "api": "ArenaVoi",
            "activate": "mount",
            "cleanup": "stop"
        },
        "eagle": {
            "scripts": [
                "eagle-animation.js"
            ],
            "styles": [
                "eagle-animation.css"
            ],
            "api": "EagleAnimation",
            "activate": "mountManaged",
            "cleanup": "destroy"
        },
        "lion": {
            "scripts": [
                "arena-lion.js"
            ],
            "styles": [
                "arena-lion.css"
            ],
            "api": "ArenaLion",
            "activate": "mount",
            "cleanup": "destroy"
        },
        "rabbit": {
            "scripts": [
                "rabbit-animation.js"
            ],
            "styles": [],
            "api": "RabbitAnimation",
            "activate": "mount",
            "cleanup": "destroy"
        },
        "cu-meo": {
            "scripts": [
                "owl-animation.js"
            ],
            "styles": [],
            "api": "OwlAnimation",
            "activate": "mount",
            "cleanup": "destroy"
        },
        "sparrow": {
            "scripts": [
                "arena-sparrow-animation.js"
            ],
            "styles": [
                "arena-sparrow-animation.css"
            ],
            "api": "ArenaSparrowAnimation",
            "activate": "mountManaged",
            "cleanup": "destroy"
        },
        "bee": {
            "scripts": [
                "arena-bee-animation.js"
            ],
            "styles": [
                "arena-bee-animation.css"
            ],
            "api": "ArenaBeeAnimation",
            "activate": "start",
            "cleanup": "destroy"
        },
        "dolphin": {
            "scripts": [
                "arena-dolphin.js"
            ],
            "styles": [
                "arena-dolphin.css"
            ],
            "api": "ArenaDolphin",
            "activate": "mount",
            "cleanup": "destroy"
        },
        "horse": {
            "scripts": [
                "horse-animation.js"
            ],
            "styles": [
                "horse-animation.css"
            ],
            "api": "HorseAnimation",
            "activate": "mount",
            "cleanup": "stop"
        },
        "cat": {
            "scripts": [
                "arena-cat-animation.js"
            ],
            "styles": [
                "arena-cat-animation.css"
            ],
            "api": "ArenaCatAnimation",
            "activate": "mountManaged",
            "cleanup": "destroy"
        },
        "crab": {
            "scripts": [
                "arena-crab-animation.js"
            ],
            "styles": [
                "arena-crab-animation.css"
            ],
            "api": "ArenaCrabAnimation",
            "activate": "mountManaged",
            "cleanup": "destroy"
        },
        "ca-map": {
            "scripts": [
                "shark-animation.js"
            ],
            "styles": [],
            "api": "SharkAnimation",
            "activate": "mount",
            "cleanup": "destroy"
        },
        "octopus": {
            "scripts": [
                "octopus-animation.js"
            ],
            "styles": [
                "octopus-animation.css"
            ],
            "api": "OctopusAnimation",
            "activate": "mount",
            "cleanup": "destroy"
        }
    },
    "routes": {
        "learning": {
            "dashboard": [
                "goc-hoc-tap/",
                "Tổng quan"
            ],
            "weekly": [
                "hoc-theo-tuan/",
                "Bài giảng theo tuần"
            ],
            "topics": [
                "chuyen-de/",
                "Chuyên đề"
            ],
            "lesson": [
                "bai-giang/",
                "Bài giảng"
            ],
            "advanced": [
                "bai-chuyen-de/",
                "Bài chuyên đề"
            ],
            "exams": [
                "thi-thu/",
                "Luyện tập"
            ],
            "testing": [
                "lam-de/",
                "Làm đề"
            ],
            "results": [
                "ket-qua-thi/",
                "Kết quả thi thử"
            ],
            "arena": [
                "dau-tri/",
                "Đấu trí toán học"
            ],
            "room": [
                "phong-dau/",
                "Phòng chờ"
            ],
            "battle": [
                "tran-dau/",
                "Trận đấu"
            ],
            "battleResult": [
                "ket-qua-tran/",
                "Kết quả trận"
            ],
            "mascot": [
                "linh-vat/",
                "Linh vật"
            ],
            "rank": [
                "xep-hang/",
                "Bảng xếp hạng"
            ],
            "profile": [
                "tai-khoan/",
                "Tài khoản"
            ],
            "zoomRegistration": [
                "dang-ky-hoc-zoom/",
                "Đăng ký học Zoom"
            ],
            "classroom": [
                "lop-zoom/",
                "Lớp Zoom"
            ],
            "upgrade": [
                "nang-cap/",
                "Nâng cấp gói"
            ],
            "payment": [
                "thanh-toan/",
                "Thanh toán"
            ]
        },
        "staff": {
            "teacher": [
                "giao-vien/",
                "Không gian giáo viên"
            ],
            "admin": [
                "quan-tri/",
                "Quản trị hệ thống"
            ]
        }
    }
}
    /* RUNTIME_MANIFEST_END */;
    if (typeof document === 'undefined') return {manifest};
    const base = new URL('.',document.currentScript.src);
    const scripts = new Map(), styles = new Map(), active = new Map();
    let observer = null, observedRoot = null, generation = 0, queued = false;
    const api = name => ({
        ArenaVoi:typeof ArenaVoi === 'undefined' ? null : ArenaVoi,
        ArenaLion:typeof ArenaLion === 'undefined' ? null : ArenaLion,
        TigerAnimation:typeof TigerAnimation === 'undefined' ? null : TigerAnimation,
        RabbitAnimation:typeof RabbitAnimation === 'undefined' ? null : RabbitAnimation,
        OwlAnimation:typeof OwlAnimation === 'undefined' ? null : OwlAnimation,
        OctopusAnimation:typeof OctopusAnimation === 'undefined' ? null : OctopusAnimation,
    }[name] || window[name]);
    function asset(path,kind) {
        const cache=kind==='script'?scripts:styles;
        if(cache.has(path))return cache.get(path);
        const promise=new Promise((resolve,reject)=>{
            const node=document.createElement(kind==='script'?'script':'link');
            if(kind==='script'){node.src=new URL(path,base).href;node.async=false;}
            else {node.rel='stylesheet';node.href=new URL(path,base).href;}
            node.onload=()=>resolve();
            node.onerror=()=>{node.remove();cache.delete(path);reject(new Error('Chưa tải được tài nguyên. Vui lòng thử lại.'));};
            const theme=kind==='style'?[...document.querySelectorAll('link[rel="stylesheet"]')].find(link=>new URL(link.href).pathname.endsWith('/themes.css')):null;
            if(theme)theme.before(node);else document.head.append(node);
        });
        cache.set(path,promise);return promise;
    }
    async function group(entry) {
        // Start independent transfers together; async=false preserves execution order.
        await Promise.all([...entry.styles.map(path=>asset(path,'style')),...entry.scripts.map(path=>asset(path,'script'))]);
    }
    const ensureLearning=()=>group(manifest.groups.learning);
    const ensureStaff=()=>group(manifest.groups.staff);
    async function ensureRoute(route) {
        if(route==='dashboard'||route.startsWith('learn-'))await ensureLearning();
        else if(route.startsWith('staff-'))await ensureStaff();
    }
    function unmountMascots() {
        generation++;observer?.disconnect();observer=null;observedRoot=null;queued=false;
        for(const code of active.keys()){const entry=manifest.mascots[code];api(entry.api)?.[entry.cleanup]?.();}
        active.clear();
    }
    function relevant(record) {
        return record.type==='attributes' ? record.target.matches?.('.battle-pet') :
            [...record.addedNodes,...record.removedNodes].some(node=>node.nodeType===1&&(node.matches?.('.battle-pet')||node.querySelector?.('.battle-pet')));
    }
    function schedule() {
        if(queued)return;queued=true;
        queueMicrotask(()=>{queued=false;if(observedRoot?.isConnected)syncMascots(observedRoot).catch(()=>{});});
    }
    async function syncMascots(root=document.querySelector('#app')) {
        if(!root?.isConnected)return;
        if(observedRoot!==root){unmountMascots();observedRoot=root;}
        const token=generation;
        const nodes=[...root.querySelectorAll('.battle-pet')], desired=new Map();
        for(const [code,entry]of Object.entries(manifest.mascots)) {
            const pets=nodes.filter(node=>node.classList.contains(code));
            if(pets.length)desired.set(code,{entry,pets});
        }
        for(const code of active.keys())if(!desired.has(code)){const entry=manifest.mascots[code];api(entry.api)?.[entry.cleanup]?.();active.delete(code);}
        if(!desired.size){observer?.disconnect();observer=null;return;}
        if(!observer){observer=new MutationObserver(records=>{if(records.some(relevant))schedule();});observer.observe(root,{subtree:true,childList:true,attributes:true,attributeFilter:['data-mood']});}
        await Promise.all([...desired].map(async([code,{entry,pets}])=>{
            await group(entry);
            if(token!==generation||observedRoot!==root||!pets.every(node=>node.isConnected))return;
            const previous=active.get(code), controller=api(entry.api);
            if(typeof controller?.[entry.activate]!=='function')throw new Error('Chưa khởi tạo được linh vật. Vui lòng tải lại trang.');
            const changed=!previous||previous.nodes.length!==pets.length||pets.some((node,index)=>node!==previous.nodes[index]);
            const moods=pets.map(node=>node.dataset.mood||'idle');
            if(changed) {
                if(previous)controller?.[entry.cleanup]?.();
                controller?.[entry.activate]?.(root);
            } else if(moods.some((mood,index)=>mood!==previous.moods[index])) {
                if(['rabbit','cu-meo','butterfly'].includes(code))pets.forEach((node,index)=>{if(moods[index]!==previous.moods[index])controller?.play?.(node,moods[index]);});
                else if(code==='tiger')pets.forEach((node,index)=>{if(moods[index]!==previous.moods[index])controller?.play?.(node,({hit:'hurt',lose:'defeat',win:'victory'}[moods[index]]||moods[index]));});
                else if(!['lion','voi','gau'].includes(code))controller?.[entry.activate]?.(root);
            }
            active.set(code,{nodes:pets,moods});
        }));
    }
    window.addEventListener('pagehide',unmountMascots);
    return {manifest,managed:true,ensureRoute,ensureLearning,ensureStaff,syncMascots,unmountMascots,
        inspect:()=>({scripts:[...scripts.keys()],activeMascots:[...active.keys()],observerActive:Boolean(observer)})};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=RuntimeAssets;
