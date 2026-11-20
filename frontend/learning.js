'use strict';
const PracticeScratchpad = typeof document==='undefined'?require('./practice-scratchpad.js'):{markup(...args){return window.PracticeScratchpad.markup(...args);},mount(...args){return window.PracticeScratchpad.mount(...args);},unmount(){window.PracticeScratchpad?.unmount();}};
const LearningApp = (() => {
const icons = {
  home: 'M3 10 12 3l9 7v10H3z M9 20v-7h6v7',
  book: 'M12 6C9 3 5 3 3 4v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-2-1-6-1-9 2zm0 0v14',
  file: 'M6 3h9l4 4v14H6z M10 10h5m-5 4h5m-5 4h4',
  zap: 'm13 2-9 12h7l-1 8 10-12h-7z',
  cup: 'M7 3h10v6a5 5 0 0 1-10 0z M7 5H3v2a4 4 0 0 0 4 4m10-6h4v2a4 4 0 0 1-4 4m-5 3v6m-4 1h8',
  leaf: 'M12 21v-9m0 2C7 14 4 10 4 6c5 0 8 3 8 7m0-2c0-5 3-8 8-8 0 5-3 8-8 8',
  users: 'M15 20v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2m15-6a4 4 0 0 1 4 4v2M12 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0zm4-4a4 4 0 0 1 0 8',
  video: 'M3 5h13v14H3z m13 5 5-3v10l-5-3',
  arrow: 'M4 12h15m-6-6 6 6-6 6',
  back: 'M20 12H5m6-6-6 6 6 6',
  chevron: 'm9 6 6 6-6 6',
  down: 'm6 9 6 6 6-6',
  clock: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z M12 7v5l3 2',
  play: 'm9 5 11 7-11 7z',
  check: 'm5 12 4 4 10-10',
  spark: 'M12 2c0 6 4 10 10 10-6 0-10 4-10 10 0-6-4-10-10-10 6 0 10-4 10-10z',
  lock: 'M5 11h14v10H5z m3 0V7a4 4 0 0 1 8 0v4',
  calendar: 'M4 5h16v16H4z M8 3v4m8-4v4M4 10h16',
  grid: 'M3 3h7v7H3z m11 0h7v7h-7z M3 14h7v7H3z m11 0h7v7h-7z',
  target: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0zm-4 0a5 5 0 1 1-10 0 5 5 0 0 1 10 0z',
  plus: 'M5 12h14m-7-7v14',
  copy: 'M8 8h13v13H8z M16 5V3H3v13h2',
  bot: 'M4 8h16v12H4z M12 8V4m-2 0h4M8 13h.01m8 0h.01m-8 4h8',
  heart: 'M12 21 4 13C-2 7 6 0 12 7c6-7 14 0 8 6z',
  flag: 'M5 22V3h14l-3 5 3 5H5',
  search: 'M17 10a7 7 0 1 1-14 0 7 7 0 0 1 14 0zm-2 5 6 6',
};

const icon = (name, size = 20) => `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${icons[name]}"/></svg>`;

    const browser = typeof document !== 'undefined';
    const mascotVisuals = browser ? window.BadgeMascots : require('./arena-art/badge-mascots/runtime.js');
    let groupGames = browser ? window.FivePlayerGames : require('./group-games.js');
    let arenaLobby = browser ? window.ArenaLobby : require('./arena-shared.js');
    let gameAllowance = browser ? window.GameAllowance : null;
    let lessonStudy = browser ? window.LessonStudy : require('./lesson-study.js');
    let stopLessonStudy=()=>{};
    const nicknames = browser ? NicknamePolicy : require('./nickname-policy.js');
    const live = browser && typeof PlatformAPI !== 'undefined' && PlatformAPI.enabled;
    const content = browser ? LearningContent : require('./learning-content.js');
    const solutionView = browser ? window.SolutionView : require('./solution-view.js');
    const controls = browser ? window.UIControls : require('./ui-controls.js');
    const studySolution = browser ? window.StudySolution : require('./solution-format.js');
    const questionFrame = browser ? window.QuestionFrame : require('./question-frame.js');
    let gameRulesView = browser ? window.GameRules : require('./game-rules.js');
    const storageKey = '5bmath-learning-v1';
    const themeSettings = () => browser && typeof ThemeManager !== 'undefined' ? ThemeManager.renderSettings() : '';
    const routes = {
        dashboard:['goc-hoc-tap/','Tổng quan'],
        weekly:['hoc-theo-tuan/','Bài giảng theo tuần'],
        topics:['chuyen-de/','Chuyên đề'],
        lesson:['bai-giang/','Bài giảng'],
        advanced:['bai-chuyen-de/','Bài chuyên đề'],
        exams:['thi-thu/','Luyện tập'],
        testing:['lam-de/','Làm đề'],
        lookup:['tra-cuu-cau-hoi/','Tra cứu câu hỏi'],
        results:['ket-qua-thi/','Kết quả thi thử'],
        arena:['dau-tri/','Đấu trí toán học'],
        room:['phong-dau/','Phòng chờ'],
        battle:['tran-dau/','Trận đấu'],
        battleResult:['ket-qua-tran/','Kết quả trận'],
        mascot:['linh-vat/','Linh vật'],
        rank:['xep-hang/','Bảng xếp hạng'],
        profile:['tai-khoan/','Tài khoản'],
        zoomRegistration:['dang-ky-hoc-zoom/','Đăng ký học Zoom'],
        classroom:['lop-zoom/','Lớp Zoom'], upgrade:['nang-cap/','Nâng cấp gói'], payment:['thanh-toan/','Thanh toán'],
    };
    const sections = {topics:'weekly',lesson:'weekly',advanced:'weekly',testing:'exams',results:'exams',room:'arena',battle:'arena',battleResult:'arena',rank:'arena',payment:'upgrade'};
    const emptyState = () => ({
        birthYear:null, inviteCode:'', invitedBy:'', mascot:'sprout', points:0, xpScale:2,
        completed:{}, exams:{}, battles:{}, activity:{}, lastLesson:'', activeExam:'',
    });
    let state = emptyState();
    let host = {};
    let currentRoute;
    let interval;
    let activityStarted;
    let currentBattle = null;
    let botLeaseReady=false,botLeaseEpoch=0,botValidation=null,botReleasePending=null,botStarting=false,roomStarting=false;
    const celebrationControllers=new Set();
    let emoteLock = {id:null,until:0,pending:false};
    let octopusFinaleUntil=0,octopusFinishTimer=null;
    let rankType = 'battle';
    let rankPeriod = 'all';
    let lessonRange = 'all';
    let topicSearch = '';
    let arenaMode='quick';
    if(browser)try{const saved=sessionStorage.getItem('5bmath-arena-mode');if(['quick','friends','bot'].includes(saved))arenaMode=saved;}catch{}
    let arenaScope='all',arenaDiscipline={availableAt:0,recentAbandons:0,recentStrikes:0,warning:''},arenaDisciplineUntil=0;
    let arenaPreflight=null,duelAllowance=null;
    const accountPages={notifications:{page:1,rows:null,total:0,error:'',request:0},referrals:{page:1,rows:null,total:0,error:'',request:0}};
    let accountPageOwner=null,notificationPollTimer=null,notificationPolling=false,notificationPollBusy=false;
    let notificationLifecycle=0,notificationVersion=0,notificationLastRefresh=0,notificationPending=null;
    let entitlementRefreshPending=false;
    const entitlementNoticeKinds=new Set(['referral_vip_reward','vip_subscription_success','vip_renewal_success']);
    let paymentWatch=null,paymentGeneration=0;

    const escape = value => String(value).replace(/[&<>"']/g, char => ({
        '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;',
    }[char]));
    const uid = () => {
        if(typeof crypto.randomUUID==='function')return crypto.randomUUID();
        const bytes=crypto.getRandomValues(new Uint8Array(16));
        bytes[6]=(bytes[6]&15)|64;bytes[8]=(bytes[8]&63)|128;
        const hex=Array.from(bytes,value=>value.toString(16).padStart(2,'0')).join('');
        return hex.slice(0,8)+'-'+hex.slice(8,12)+'-'+hex.slice(12,16)+'-'+hex.slice(16,20)+'-'+hex.slice(20);
    };
    // Reuse the approved idle artwork. Sprite viewBoxes isolate one mascot
    // without loading an animation renderer into either account header.
    const mascotAvatars = {
        dog:['Chó Vui Vẻ','arena-art/dog/idle.webp'],
        sprout:['Mầm Sách Ham Học','mascots.webp',[131,44,379,521],1200,600],
        fox:['Cáo Nâu Lanh Lợi','mascots.webp',[670,34,443,532],1200,600],
        horse:['Ngựa Tung Tăng','arena-art/horse/v1/idle.webp'],
        'cu-meo':['Cú Mèo Thông Thái','arena-art/owl/poses.webp',[69,18,210,274],1254,1254],
        dolphin:['Cá Heo Lém Lỉnh','arena-art/ca-heo-v1/actions.webp',[32,48,276,221],1278,1230],
        octopus:['Bạch Tuộc Khéo Léo','arena-art/bach-tuoc-idle.webp'],
        starfish:['Sao Biển Lấp Lánh','arena-art/sao-bien-v1/idle.webp'],
        bee:['Ong Chăm Chỉ','arena-art/bee/poses.webp',[29,32,260,255],1254,1254],
        butterfly:['Bướm Điệu Đà','arena-art/butterfly-poses.webp',[15,21,284,249],1254,1254],
        crab:['Cua Biển Vui Tính','arena-art/cua-bien-poses.webp',[66,82,202,172],1247,1261],
        'ca-map':['Cá Mập Mạnh Mẽ','arena-art/shark/idle.webp'],
        tiger:['Hổ Dũng Cảm','arena-art/ho-v1/reactions.webp',[52,959,220,283],1254,1254],
        sparrow:['Chim Sẻ Líu Lo','arena-art/chim-se/idle.webp'],
        lion:['Sư Tử Oai Phong','arena-art/lion-idle.webp'],
        eagle:['Đại Bàng Tinh Anh','arena-art/eagle/states.webp',[79,61,172,225],1254,1254],
        voi:['Voi Tốt Bụng','arena-art/voi-reactions.webp',[76,21,284,227],1536,1024],
        rabbit:['Thỏ Nhanh Nhẹn','arena-art/tho-idle.webp'],
        cat:['Mèo Tinh Nghịch','arena-art/meo-neutral.webp'],
        gau:['Gấu Ấm Áp','arena-art/gau-idle.webp'],
    };
    function avatar(pet=state.mascot,xp=state.points){const code=Object.hasOwn(mascotAvatars,pet)?pet:'sprout';return '<span class="avatar mascot-avatar" data-mascot="'+code+'" role="img" aria-label="Linh vật '+escape(mascotAvatars[code][0])+'">'+mascotVisuals.portrait(code,xp,'','mascot-avatar-picture')+'</span>';}
    const displayName = value => nicknames.safe(value);
    const name = () => host.progress?.name ? displayName(host.progress.name) : 'Học sinh';
    const grade = () => live ? state.grade || 5 : Math.max(1, Math.min(5, content.gradeFor(state.birthYear)));
    const week = () => live ? state.week || 1 : content.weekFor();
    const query = key => {
        if (!browser) return null;
        const search = location.protocol === 'file:' ? location.hash.split('?')[1] || '' : location.search;
        return new URLSearchParams(search).get(key);
    };
    const href = (route, parameters = {}) => {
        if(route==='mascot')route='profile';
        if(['upgrade','payment'].includes(route)&&browser){
            const childId=query('childId')||query('child');
            if(childId)parameters={childId,...parameters};
        }
        const search = new URLSearchParams(parameters).toString();
        const offline = browser && location.protocol === 'file:';
        const routePath = offline ? route === 'dashboard' ? '#dashboard' : '#learn-' + route : routes[route][0];
        return routePath + (search ? '?' + search : '');
    };
    const animatedArt = (pet, label = '') => pet === 'dog'
        ? `<img class="mascot-art dog" style="background:none;object-fit:contain" src="arena-art/dog/idle.webp" width="256" height="256" alt="${escape(label)}" loading="lazy">`
        : pet === 'horse'
        ? `<img class="mascot-art horse" src="arena-art/horse/v1/idle.webp" width="256" height="256" alt="${escape(label)}" loading="lazy">`
        : pet === 'voi'
        ? `<canvas class="mascot-art voi" data-voi width="256" height="256" ${label ? `role="img" aria-label="${escape(label)}"` : 'aria-hidden="true"'}></canvas>`
        : `<span class="mascot-art ${pet}" ${label ? `role="img" aria-label="${escape(label)}"` : 'aria-hidden="true"'}></span>`;
    function art(pet,label='',animated=false,xp=state.points){if(animated)return animatedArt(pet,label);const code=Object.hasOwn(mascotAvatars,pet)?pet:'sprout';return mascotVisuals.portrait(code,xp,label,'mascot-art '+code);}
    const evolutionRows={dog:[0,0],cat:[0,1],rabbit:[0,2],horse:[0,3],voi:[1,0],tiger:[1,1],lion:[1,2],gau:[1,3],sparrow:[2,0],eagle:[2,1],'cu-meo':[2,2],butterfly:[2,3],bee:[3,0],'ca-map':[3,1],dolphin:[3,2],octopus:[3,3],crab:[4,0],starfish:[4,1],fox:[4,2],sprout:[4,3]};
    const evolutionBoxes=[{x:[116,381,659,1018],y:[226,534,833,1125,1444]},{x:[140,370,638,1018],y:[199,495,790,1103,1451]},{x:[116,374,646,1018],y:[239,536,839,1139,1448]},{x:[127,367,630,1018],y:[217,517,816,1107,1444]},{x:[130,391,666,1018],y:[210,505,789,1117,1468]}];
    function showEvolution(...args) { return feature('profile').showEvolution(...args); }

    const scenery = [
        ['01-forest-clearing','Rừng xanh'], ['02-stream','Bên suối'],
        ['03-riverbank','Bờ sông'], ['04-mountains','Núi non'],
        ['05-bamboo','Rừng trúc'], ['06-waterfall','Thác nước'],
        ['07-lake','Hồ bình minh'], ['08-autumn','Rừng mùa thu'],
        ['09-meadow','Đồng cỏ hoa'], ['10-coast','Vịnh biển'],
    ];
    const artSeed = value => [...String(value)].reduce((sum,c)=>((sum*31)+c.charCodeAt(0))>>>0,0);
    const battleScenery = battle => scenery[artSeed(battle.id)%scenery.length];
    const battlePet=(pet,label,mood='idle',xp=state.points)=>mascotVisuals.markup(pet,xp,label,mood);
    const badge = (label, color = '') => `<span class="tag ${color}">${escape(label)}</span>`;
    const tile = (symbol, color = '') => `<span class="tile ${color}">${icon(symbol,23)}</span>`;
    const gardenActivityArt = symbol => {
        const shapes = symbol === 'book'
            ? '<path d="M8 19Q25 13 40 23Q55 13 72 19V65Q56 59 40 69Q24 59 8 65Z" fill="#61BDBA"/><path d="M12 15Q27 13 40 23V62Q26 53 12 57ZM68 15Q53 13 40 23V62Q54 53 68 57Z" fill="#B9E8DE"/><path d="M40 24V63M18 27q8-1 15 4m-15 7q8-1 15 4m14-11q7-5 15-4m-15 15q7-5 15-4" fill="none"/>'
            : symbol === 'file'
            ? '<g transform="rotate(38 40 40)"><path d="M29 17V58L40 74L51 58V17Z" fill="#FFD16A"/><path d="M29 17h22V8q-11-10-22 0Z" fill="#FFA97B"/><path d="M29 18h22v9H29Z" fill="#FFE6B7"/><path d="M40 28v30M29 58l11 16 11-16" fill="none"/><path d="m36 68 4 6 4-6Z" fill="#203A32" stroke="none"/></g>'
            : '<path d="M40 71V39" fill="none"/><path d="M40 49C13 49 8 32 9 17C29 15 43 27 40 49Z" fill="#8BCB55"/><path d="M40 41C37 18 52 7 71 7C73 26 61 41 40 41Z" fill="#68B74F"/><path d="M23 31q14 10 17 18m18-27q-14 10-18 19" fill="none"/>';
        const clayIcon = symbol === 'book' ? 'book' : symbol === 'file' ? 'pencil' : 'trophy';
        return `<span class="garden-activity-art" aria-hidden="true"><svg viewBox="0 0 80 80" width="80" height="80" fill="none" stroke="#164F3D" stroke-width="3" stroke-linejoin="round" stroke-linecap="round">${shapes}<path d="m6 5 4 5M2 15h6m61 53 5 4m0-13 3 2" stroke="#F5A14B" stroke-width="3.5"/></svg><img class="clay-activity-icon" src="theme-art/clay-${clayIcon}.webp" width="192" height="192" alt="" loading="lazy"></span>`;
    };
    const link = (label, to, kind = 'dark', symbol = 'arrow', parameters = {}) => `<a class="btn ${kind}" href="${href(to,parameters)}">${escape(label)}${symbol ? icon(symbol,17) : ''}</a>`;
    const button = (label, action, kind = 'outline', symbol = '', extra = '') => controls.markup(label, {kind, actionAttribute:'data-learning', action, icon:symbol ? icon(symbol,17) : '', extra});
    const heading = title => `<div class="section-head"><h2>${escape(title)}</h2></div>`;
    const intro = (title, copy, right = '') => `<header class="intro"><div><h1>${escape(title)}</h1><p>${escape(copy)}</p></div>${right}</header>`;
    const back = (label, route) => `<a class="back-link" href="${href(route)}">${icon('back',17)} ${escape(label)}</a>`;
    const meter = (value, label) => `<div class="meter" role="progressbar" aria-label="${escape(label)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${value}"><span style="--value:${value}%"></span></div>`;
    const stat = (symbol, value, label, color = '') => `<div class="stat card-pad">${tile(symbol,color)}<div><strong>${escape(value)}</strong><small>${escape(label)}</small></div></div>`;
    const field = (label, id, options, value = '') => `<label class="field"><span>${escape(label)}</span><select id="${id}">${options.map(([key,title]) => `<option value="${escape(key)}" ${String(value) === String(key) ? 'selected' : ''}>${escape(title)}</option>`).join('')}</select></label>`;
    const tabs = selected => `<nav class="tabs" aria-label="Cách học">${[['weekly','Theo tuần','calendar'],['topics','Chuyên đề','grid']].map(([route,title,symbol]) => `<a href="${href(route)}" ${selected === route ? 'aria-current="page"' : ''}>${icon(symbol,17)} ${title}</a>`).join('')}</nav>`;
    const notice = text => `<p class="learning-notice">${escape(text)}</p>`;
    const lessonList = () => live ? PlatformAPI.snapshot.lessons || [] : content.lessons(grade());
    const bankNotice = () => live && PlatformAPI.snapshot.questionBankReady === false ? notice((PlatformAPI.snapshot.arenaQuestionSource?.qaOnly||PlatformAPI.snapshot.arenaQuestionSource?.localTest)?'Bài tập đang được cập nhật. Em vẫn có thể xem lại bài đã làm; chưa thể tạo đề mới.':'Bài tập đang được cập nhật. Em vẫn có thể xem lại bài đã làm; chưa thể tạo đề hoặc bắt đầu trận mới.') : '';
    const selectedLesson = () => {const id=query('id'),lessons=lessonList();return id?lessons.find(lesson=>lesson.id===id):lessons[0];};
    const submittedExams = () => {
        const rows=new Map();for(const exam of Object.values(state.exams)){if(!exam.submittedAt)continue;const key=String(exam.rootExamId||exam.id),prior=rows.get(key);if(!prior||exam.submittedAt>prior.submittedAt||(exam.submittedAt===prior.submittedAt&&Number(exam.id)>Number(prior.id)))rows.set(key,exam);}return [...rows.values()];
    };
    const level = () => Math.min(15,Math.floor(Math.max(0,state.points)/20)+1);
    const petName = () => (mascotAvatars[state.mascot] || mascotAvatars.sprout)[0];

    function load() {
        if(live)return;
        try {
            const saved = JSON.parse(localStorage.getItem(storageKey));
            if (saved && typeof saved === 'object' && saved.version === 1) {state = {...emptyState(),...saved};if(saved.xpScale!==2)state.points=Math.max(0,(Number(saved.points)||0)-1000);state.xpScale=2;}
        } catch { state = emptyState(); }
        for (const property of ['completed','exams','battles','activity']) {
            if (!state[property] || typeof state[property] !== 'object' || Array.isArray(state[property])) state[property] = {};
        }
        if (!Object.hasOwn(mascotAvatars,state.mascot)) state.mascot = 'sprout';
        state.points = Math.max(0, Math.floor(Number(state.points)||0));
        if (!Number.isInteger(state.birthYear)) state.birthYear = null;
    }

    function save() {
        if(live)return;
        state.version = 1;
        try { localStorage.setItem(storageKey,JSON.stringify(state)); }
        catch { host.toast('Bộ nhớ trình duyệt đã đầy hoặc đang bị chặn. Em hãy giữ trang đang mở để tiếp tục.'); }
    }

    function configure(options) {
        if(browser){groupGames=window.FivePlayerGames;arenaLobby=window.ArenaLobby;gameAllowance=window.GameAllowance;lessonStudy=window.LessonStudy;gameRulesView=window.GameRules;}
        host = options;
        if(live){applySnapshot(PlatformAPI.snapshot);return;}
        load();
        if (!state.inviteCode) {
            state.inviteCode = '5B' + uid().replaceAll('-','').slice(0,8).toUpperCase();
            save();
        }
        const old = host.progress.completed || [];
        for (const [oldId,newId] of [['decimal','g5-decimal'],['percent','g5-percent']]) {
            if (old.includes(oldId) && !state.completed[newId]) {
                state.completed[newId] = {date:new Date().toISOString(),grade:5};
            }
        }
        for (const [index,attempt] of (host.progress.attempts || []).entries()) {
            const id = 'legacy-' + index;
            if (typeof attempt.type === 'string' && attempt.type.startsWith('Đề') &&
                Number.isFinite(attempt.score) && !Number.isNaN(Date.parse(attempt.date)) && !state.exams[id]) {
                state.exams[id] = {id,code:'CU-' + (index + 1),title:attempt.type,grade:5,
                    score:attempt.score,submittedAt:attempt.date,legacy:true,questions:[]};
            }
        }
        save();
    }

    function applySnapshot(snapshot) {
        state = {...emptyState(),...(snapshot.state || {})};
        host.progress.name = snapshot.name ? displayName(snapshot.name) : '';
        syncAccountPages(snapshot);
        if(snapshot.arenaDiscipline)setArenaDiscipline(snapshot.arenaDiscipline,snapshot.serverNow);
    }
    async function mutate(path, body={}) {
        const snapshot = await PlatformAPI.request(path,body);
        applySnapshot(snapshot);
        return snapshot;
    }
    const rich = (blocks,assets=[],solution=false) => {
        if(!browser || typeof appendRichContent !== 'function')return escape(blocks.map(block=>block.text || block.latex || '').join(' '));
        const element=document.createElement('div');
        appendRichContent(element,blocks,assets);
        if(solution)solutionView.decorate(element);
        return element.innerHTML;
    };

    function setBirthYear(value) {
        const birthYear = Number(value);
        const calculatedGrade = content.gradeFor(birthYear);
        if (!Number.isInteger(birthYear) || calculatedGrade < 1 || calculatedGrade > 5) {
            throw new Error('Em hãy nhập năm sinh tương ứng khối 1–5 trong năm học hiện tại.');
        }
        load();
        if (state.birthYear && state.birthYear !== birthYear) throw new Error('Năm sinh đã cố định sau khi đăng ký.');
        state.birthYear = birthYear;
        const invitedBy = query('invite');
        if (invitedBy && invitedBy !== state.inviteCode && !state.invitedBy) state.invitedBy = invitedBy.slice(0,20);
        save();
    }

    function accountGate() {
        return `${intro('Góc Học Tập 5BMath','Học theo tuần, luyện chuyên đề và chơi cùng Mầm Sách.')}
            <section class="hero-app"><div class="hero-copy"><h2>Gieo một hạt mầm Toán</h2><p>${live ? 'Đăng nhập hoặc tạo tài khoản để lưu tiến độ học theo khối của em.' : 'Đặt tên và năm sinh để thử khu học tập theo khối của em.'}</p><button class="btn orange" data-login type="button">${live ? 'Đăng nhập / Đăng ký' : 'Vào học thử'} ${icon('arrow',17)}</button></div><div class="hero-art">${art('sprout','Mầm Sách đang đọc sách')}</div></section>
            ${notice(live ? 'Tài khoản và tiến độ được lưu trên hệ thống 5BMath. Học liệu là các bài mẫu tự biên soạn.' : 'Tài khoản trải nghiệm lưu trên trình duyệt này. Học liệu trong khu học tập là các bài mẫu tự biên soạn.')}`;
    }

    function homeworkPanel(...args) { return feature('study').homeworkPanel(...args); }

    function lessonVideo(...args) { return feature('study').lessonVideo(...args); }
    function lessonExamples(...args) { return feature('study').lessonExamples(...args); }
    function lessonSamples(...args) { return feature('study').lessonSamples(...args); }

    const views = {
"dashboard"(...args){return feature('study').views["dashboard"](...args);},
"weekly"(...args){return feature('study').views["weekly"](...args);},
"topics"(...args){return feature('study').views["topics"](...args);},
"lesson"(...args){return feature('study').views["lesson"](...args);},
"exams"(...args){return feature('practice').views["exams"](...args);},
"testing"(...args){return feature('practice').views["testing"](...args);},
"results"(...args){return feature('practice').views["results"](...args);},
"arena"(...args){return feature('arena').views["arena"](...args);},
"room"(...args){return feature('arena').views["room"](...args);},
"battle"(...args){return feature('arena').views["battle"](...args);},
"battleResult"(...args){return feature('arena').views["battleResult"](...args);},
"mascot"(...args){return feature('profile').views["mascot"](...args);},
"rank"(...args){return feature('arena').views["rank"](...args);},
"profile"(...args){return feature('profile').views["profile"](...args);},
"zoomRegistration"(...args){return feature('commerce').views["zoomRegistration"](...args);},
"classroom"(...args){return feature('classroom').views["classroom"](...args);},
"upgrade"(...args){return feature('commerce').views["upgrade"](...args);},
"payment"(...args){return feature('commerce').views["payment"](...args);}
    };

    function syncAccountPages(snapshot) {
        const account=snapshot?.account,owner=snapshot?.authenticated?account?.id:null;
        if(accountPageOwner!==owner){
            entitlementRefreshPending=false;
            if(paymentWatch?.target.isConnected)paymentWatch.target.replaceChildren();
            stopPaymentWatch();
            accountPageOwner=owner;notificationVersion++;
            classData=null;classLoadTicket++;classUnreadVersion++;classTab='sessions';classFrom='';classTo='';
            for(const record of Object.values(accountPages))Object.assign(record,{page:1,rows:null,total:0,error:'',loading:false,request:record.request+1});
        }
        if(!account)return;
        for(const kind of ['notifications','referrals']){
            const record=accountPages[kind];
            record.total=Number(account[kind==='notifications'?'notificationTotal':'referralTotal'])||account[kind]?.length||0;
            if(record.page===1)record.rows=account[kind]||[];
        }
        notificationVersion++;
    }
    const accountDate=value=>value?new Date(value).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',dateStyle:'short',timeStyle:'short'}):'Chưa phát sinh';
    const notificationTitle=item=>item.title||({referral_vip_reward:'Em đã nhận thưởng VIP',referral_contact_support:'Hướng dẫn nhận thưởng giới thiệu'}[item.kind])||'Thông báo tài khoản';
    const notificationSender=item=>item.sender_name||'5BMath';
    function unreadNotificationCount(){
        if(!live||!PlatformAPI.snapshot.authenticated)return 0;
        const account=PlatformAPI.snapshot.account||{};
        return Math.max(0,Number(account.notificationUnreadCount??(account.notifications||[]).filter(item=>!item.read_at).length)||0);
    }
    function unreadBadge(){
        const count=unreadNotificationCount();
        return `<span class="account-unread-badge" data-unread-count ${count?'':'hidden'} aria-hidden="true">${count>99?'99+':count}</span>`;
    }
    function updateUnreadBadge(){
        const count=unreadNotificationCount();
        document.querySelectorAll('[data-account-nav]').forEach(link=>{
            link.setAttribute('aria-label',count?'Tài khoản, '+count+' thông báo chưa đọc':'Tài khoản');
            const badge=link.querySelector('[data-unread-count]');
            if(badge){badge.hidden=!count;badge.textContent=count>99?'99+':String(count);}
        });
        const label=document.querySelector('#account-notifications .account-record-count');if(label)label.textContent=count+' chưa đọc';
    }
    function classroomUnread(){
        return live&&PlatformAPI.snapshot.authenticated&&isInternal()?PlatformAPI.snapshot.account?.classroomUnread||{}:{};
    }
    const classUnreadCount=value=>Math.max(0,Number(value)||0);
    const classUnreadBadge=(count,section='')=>`<span class="account-unread-badge class-unread-badge" ${section?'data-class-unread="'+section+'"':'data-classroom-unread'} ${count?'':'hidden'} aria-hidden="true">${count>99?'99+':count}</span>`;
    function updateClassUnread(){
        const summary=classroomUnread(),total=classUnreadCount(summary.total);
        document.querySelectorAll('[data-classroom-nav]').forEach(link=>{
            link.setAttribute('aria-label','Lớp Zoom'+(total?', '+total+' thông báo chưa đọc':''));
            const badge=link.querySelector('[data-classroom-unread]');
            if(badge){badge.hidden=!total;badge.textContent=total>99?'99+':String(total);}
        });
        const identity=document.querySelector('#class-select')?.value;
        const counts=summary.classes?.[identity]||{};
        for(const section of ['assignments','fees']){
            const control=document.querySelector('[data-class-tab="'+section+'"]'),count=classUnreadCount(counts[section]);
            if(!control)continue;
            control.setAttribute('aria-label',(section==='assignments'?'Bài tập':'Học phí')+(count?', '+count+' thông báo chưa đọc':''));
            const badge=control.querySelector('[data-class-unread]');
            if(badge){badge.hidden=!count;badge.textContent=count>99?'99+':String(count);}
        }
    }
    function adoptClassUnread(summary){
        if(PlatformAPI.snapshot.account)PlatformAPI.snapshot.account.classroomUnread=summary;
        updateClassUnread();
    }
    function accountPagination(...args) { return feature('profile').accountPagination(...args); }
    function accountRecordsMarkup(...args) { return feature('profile').accountRecordsMarkup(...args); }
    function accountRecordsSection(...args) { return feature('profile').accountRecordsSection(...args); }
    function updateAccountSection(kind){
        const container=document.querySelector('#account-'+kind);if(!container)return;
        const position={x:scrollX,y:scrollY},focused=container.contains(document.activeElement)?document.activeElement:null;
        const selector=focused?.hasAttribute('data-notification')?`[data-notification="${focused.dataset.notification}"]`:focused?.hasAttribute('data-account-page')?`[data-account-page="${kind}"][data-page="${focused.dataset.page}"]`:null;
        container.innerHTML=accountRecordsMarkup(kind);
        if(selector&&!document.querySelector('#modal')?.open)container.querySelector(selector)?.focus({preventScroll:true});
        window.scrollTo({left:position.x,top:position.y,behavior:'instant'});
    }
    function adoptNotificationSummary(result){
        const account=PlatformAPI.snapshot.account;if(!account)return;
        account.notificationUnreadCount=result.unreadCount;
        account.notificationTotal=result.total;
        if(result.page===1)account.notifications=result.rows;
        accountPages.notifications.total=result.total;
        if(accountPages.notifications.page===1&&result.page===1)accountPages.notifications.rows=result.rows;
        updateUnreadBadge();
        const record=accountPages.notifications,pager=document.querySelector('#account-notifications .account-pagination');
        if(pager){
            const pages=Math.max(1,Math.ceil(record.total/5));
            pager.querySelector('span').textContent=record.total+' thông báo · Trang '+record.page+' / '+pages;
            for(const control of pager.querySelectorAll('[data-account-page]'))control.disabled=record.loading||(Number(control.dataset.page)<record.page?record.page<=1:record.page>=pages);
        }
    }
    function loadAccountPage(...args) { return feature('profile').loadAccountPage(...args); }
    function stopNotificationPolling(){
        notificationPolling=false;notificationLifecycle++;clearTimeout(notificationPollTimer);notificationPollTimer=null;
    }
    function scheduleNotificationPolling(){
        clearTimeout(notificationPollTimer);notificationPollTimer=null;
        if(notificationPolling&&!document.hidden&&navigator.onLine!==false&&PlatformAPI.snapshot.authenticated)notificationPollTimer=setTimeout(()=>refreshNotificationSummary(),30000);
    }
    function learnerBackgroundAllowed(){
        if(!live)return true;
        const family=PlatformAPI.familyState;
        return Boolean(PlatformAPI.snapshot.authenticated&&(!family||(family.activeProfile?.type==='child'&&family.scope==='child')));
    }
    async function refreshNotificationSummary({focus=false}={}){
        if(!learnerBackgroundAllowed())return;
        if(PlatformAPI.familyContext&&currentRoute==='profile'){await loadPersonalNotices();scheduleNotificationPolling();return;}
        if(!notificationPolling||document.hidden||navigator.onLine===false||!PlatformAPI.snapshot.authenticated)return;
        if(notificationPollBusy||notificationPending!==null||Date.now()-notificationLastRefresh<(focus?3000:15000)){scheduleNotificationPolling();return;}
        const lifecycle=notificationLifecycle,owner=accountPageOwner,version=notificationVersion,classVersion=classUnreadVersion;
        const sessionCsrf=PlatformAPI.snapshot.csrf;
        const knownEntitlementNotices=new Set((PlatformAPI.snapshot.account?.notifications||[]).filter(item=>entitlementNoticeKinds.has(item.kind)).map(item=>item.id));
        const referralPage=accountPages.referrals.page,referralRequest=accountPages.referrals.request;
        notificationPollBusy=true;
        try{
            const familyProfile=Boolean(PlatformAPI.familyContext);
            const [result,classResult,referralResult]=await Promise.all([familyProfile?Promise.resolve(null):PlatformAPI.request('notifications?page=1'),isInternal()?PlatformAPI.request('classes/unread').catch(()=>null):Promise.resolve(null),!familyProfile&&currentRoute==='profile'&&!accountPages.referrals.loading?PlatformAPI.request('referrals?page='+referralPage).catch(()=>null):Promise.resolve(null)]);
            if(!notificationPolling||lifecycle!==notificationLifecycle||owner!==accountPageOwner||version!==notificationVersion||notificationPending!==null)return;
            if(result?.rows.some(item=>entitlementNoticeKinds.has(item.kind)&&!knownEntitlementNotices.has(item.id)))entitlementRefreshPending=true;
            notificationLastRefresh=Date.now();if(result)adoptNotificationSummary(result);
            if(classResult&&!classReadBusy&&classVersion===classUnreadVersion)adoptClassUnread(classResult.classroomUnread);
            if(result&&currentRoute==='profile'&&accountPages.notifications.page===1&&!document.querySelector('#modal')?.open)updateAccountSection('notifications');
            if(referralResult&&referralPage===accountPages.referrals.page&&referralRequest===accountPages.referrals.request&&!(currentRoute==='profile'&&document.querySelector('#modal')?.open)){
                const changed=referralResult.total!==accountPages.referrals.total||JSON.stringify(referralResult.rows)!==JSON.stringify(accountPages.referrals.rows);
                Object.assign(accountPages.referrals,{rows:referralResult.rows,total:referralResult.total});
                if(referralResult.page===1){PlatformAPI.snapshot.account.referrals=referralResult.rows;PlatformAPI.snapshot.account.referralTotal=referralResult.total;}
                if(changed&&currentRoute==='profile'&&!document.querySelector('#modal')?.open)updateAccountSection('referrals');
            }
            if(entitlementRefreshPending&&!document.hidden&&navigator.onLine!==false&&PlatformAPI.snapshot.csrf===sessionCsrf){
                const snapshot=await PlatformAPI.request('session',undefined,{owner});
                if(!notificationPolling||lifecycle!==notificationLifecycle||owner!==accountPageOwner||PlatformAPI.snapshot.csrf!==sessionCsrf||version!==notificationVersion||notificationPending!==null||document.hidden||navigator.onLine===false)return;
                applySnapshot(snapshot);entitlementRefreshPending=false;updateMembershipViews();updateUnreadBadge();updateClassUnread();
            }
        }catch{}finally{notificationPollBusy=false;scheduleNotificationPolling();}
    }
    function startNotificationPolling(){
        if(!learnerBackgroundAllowed()){stopNotificationPolling();return;}
        if(!live||!PlatformAPI.snapshot.authenticated)return;
        notificationPolling=true;updateUnreadBadge();updateClassUnread();refreshNotificationSummary();scheduleNotificationPolling();
    }
    function updateMembershipViews(){
        const account=PlatformAPI.snapshot.account;
        if(!account)return;
        for(const label of document.querySelectorAll('.top-right > .tag,[data-account-membership]'))label.textContent=account.membership;
        for(const expiry of document.querySelectorAll('[data-vip-expiry]'))expiry.textContent=accountDate(account.vipExpiresAt);
    }
    function readNotification(...args) { return feature('profile').readNotification(...args); }

    let personalNotices={owner:null,rows:null,total:0,unreadCount:0,error:'',pending:null};
    function personalNoticeContext(...args) { return feature('profile').personalNoticeContext(...args); }
    function personalRewardNotices(...args) { return feature('profile').personalRewardNotices(...args); }
    function personalNotificationsPanel(...args) { return feature('profile').personalNotificationsPanel(...args); }
    function updatePersonalNotices(...args) { return feature('profile').updatePersonalNotices(...args); }
    function loadPersonalNotices(...args) { return feature('profile').loadPersonalNotices(...args); }
    function readPersonalNotice(...args) { return feature('profile').readPersonalNotice(...args); }
    function personalCount(...args) { return feature('profile').personalCount(...args); }
    function personalContinue(...args) { return feature('profile').personalContinue(...args); }
    function safeStudyHref(...args) { return feature('profile').safeStudyHref(...args); }
    function continueStudy(...args) { return feature('profile').continueStudy(...args); }
    function personalSummaryCard(...args) { return feature('profile').personalSummaryCard(...args); }
    function personalInvitePanel(...args) { return feature('profile').personalInvitePanel(...args); }
    function liveProfile(...args) { return feature('profile').liveProfile(...args); }
    function openCompanionDialog(...args) { return feature('profile').openCompanionDialog(...args); }

    let rankScope='all';
    function liveRank(...args) { return feature('arena').liveRank(...args); }
    const medal=n=>n&&n<=3?`<span class="medal medal-${n}" aria-label="Hạng ${n}">${n}</span>`:escape(n??'—');
    function loadRank(...args) { return feature('arena').loadRank(...args); }
    let classTab='sessions',classData=null,classFrom='',classTo='',classLoadTicket=0,classUnreadVersion=0,classReadBusy=0,classReadQueue=Promise.resolve();
    function liveClassroom(...args) { return feature('classroom').liveClassroom(...args); }

    const member=()=>live?PlatformAPI.snapshot.account?.membership||'Free':'Free';
    const isInternal=()=>member()==='SVip';
    const isPaid=()=>member()!=='Free';
    const petRank=n=>{const step=Math.max(0,Math.min(14,(Number(n)||1)-1));return ['Đồng','Bạc','Vàng'][Math.floor(step/5)]+' '+['I','II','III','IV','V'][step%5]};
    const rankProgress=()=>state.points>=280?'Đã đạt Vàng V · Tiếp tục tích lũy kinh nghiệm.':'Còn '+(20-state.points%20)+' kinh nghiệm đến '+petRank(level()+1);
    const rankPercent=()=>state.points>=280?100:state.points%20*5;
    const emotes=[['👋','Chào bạn!'],['🌟','Bạn giỏi quá!'],['💪','Cố lên nào!'],['👏','Tuyệt vời!'],['🤝','Cùng cố gắng!'],['😊','Vui quá!'],['🤔','Để mình nghĩ!'],['🔥','Hết mình nhé!'],['🍀','Chúc may mắn!'],['❤️','Không bỏ cuộc!']];
    const celebrationMarkup=options=>(browser?window.GamesArt:require('./games-art.js'))?.confettiMarkup?.(options)||'';
    function mountCelebration(root,options={}){if(!root||!browser||!window.GamesArt?.mountConfetti)return null;const effect=window.GamesArt.mountConfetti(root,{...options,repeat:false,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches});celebrationControllers.add(effect);return effect;}
    const audioButton=()=>`<button type="button" class="btn outline" data-game-audio-toggle aria-label="Bật hoặc tắt nhạc nền trò chơi" aria-pressed="${typeof ArenaAudio==='undefined'||!ArenaAudio.muted}">${typeof ArenaAudio!=='undefined'&&ArenaAudio.muted?'🔇 Nhạc: Tắt':'🎵 Nhạc: Bật'}</button>`;
    const lessonRow=l=>`<a class="list-row" href="${href('lesson',{id:l.id})}">${tile(state.completed[l.id]?'check':'book')}<div><strong>Tuần ${l.week}: ${escape(l.title)}</strong><small>Bài đọc có ví dụ</small></div>${badge(state.completed[l.id]?'Đã học':'Chưa học',state.completed[l.id]?'sage':'')}${icon('chevron',17)}</a>`;
    function quota(category) {
        if(live)return PlatformAPI.snapshot.account?.usage?.[category]||{used:0,limit:1};
        const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Ho_Chi_Minh'}).format(new Date());
        const used=(state.usage||{})[day+'-'+category]||0;
        return {used,limit:{content:1,combined:1,human:3,bot:5}[category]};
    }
    const canUse=category=>isPaid()||quota(category).limit===null||quota(category).used<quota(category).limit;
    const arenaScopeLabel=()=> 'Đề Đấu trí do máy chủ cấp';
    const arenaSourceNotice=()=>live&&(PlatformAPI.snapshot.arenaQuestionSource?.qaOnly||PlatformAPI.snapshot.arenaQuestionSource?.localTest)?'<p class="learning-notice" data-duel-test-notice role="status">'+(PlatformAPI.snapshot.arenaQuestionSource?.localTest?'Bản thử cục bộ':'Bản QA')+' · Bộ câu test riêng cho Đấu trí · Chưa duyệt học liệu.</p>':'';
    function setArenaDiscipline(value,serverNow) {
        arenaDiscipline=value;
        const remaining=Number.isFinite(serverNow)?Math.max(0,(Number(value.availableAt)||0)-serverNow):Number.isFinite(value.remainingSeconds)?Math.max(0,value.remainingSeconds)*1000:Math.max(0,(Number(value.availableAt)||0)-arenaNow());
        arenaDisciplineUntil=Date.now()+remaining;
    }
    const disciplineSeconds=()=>Math.max(0,Math.ceil((arenaDisciplineUntil-Date.now())/1000));
    const canPlayHuman=()=>canUse('human')&&disciplineSeconds()===0;
    function disciplinePanel() {
        const seconds=disciplineSeconds(),warning=seconds?arenaDiscipline.warning||'':'';
        return `<section class="arena-discipline" id="arena-discipline" role="status" ${seconds?'':'hidden'}><div>${icon('clock',23)}</div><div><strong id="arena-discipline-title">Tạm nghỉ đấu với người</strong><p id="arena-discipline-warning">${escape(warning)}</p><p id="arena-discipline-rest" ${seconds?'':'hidden'}>Có thể đấu lại sau <b id="arena-rest-countdown">${timeText(seconds)}</b>.</p><small>Em vẫn có thể học và luyện với máy.</small></div></section>`;
    }
    function updateArenaDiscipline() {
        const seconds=disciplineSeconds(),panel=document.querySelector('#arena-discipline');
        if(panel){
            const warning=seconds?arenaDiscipline.warning||'':'';
            panel.hidden=!seconds;
            panel.classList.toggle('resting',seconds>0);
            panel.querySelector('#arena-discipline-title').textContent='Tạm nghỉ đấu với người';
            panel.querySelector('#arena-discipline-warning').textContent=warning;
            panel.querySelector('#arena-discipline-rest').hidden=!seconds;
            panel.querySelector('#arena-rest-countdown').textContent=timeText(seconds);
        }
        document.querySelectorAll('[data-human-play]').forEach(control=>{
            const admission=control.hasAttribute('data-game-admission');
            const disabled=control.dataset.humanPending==='true'||seconds>0||(control.dataset.humanQuota==='true'&&!canUse('human'))||(admission&&(botStarting||roomStarting));
            if(admission&&gameAllowance)gameAllowance.setDisabled(control,disabled);else control.disabled=disabled;
            if(seconds)control.setAttribute('aria-describedby','arena-discipline');else control.removeAttribute('aria-describedby');
        });
        const bot=document.querySelector('[data-learning="start-bot"]');
        if(bot){const disabled=botStarting||roomStarting||!canUse('bot');if(gameAllowance)gameAllowance.setDisabled(bot,disabled);else bot.disabled=disabled;}
    }
    function receiveArenaDiscipline(result) {
        if(result?.serverNow)serverOffset=result.serverNow-Date.now();
        if(result?.arenaDiscipline)setArenaDiscipline(result.arenaDiscipline,result.serverNow);
        updateArenaDiscipline();
    }
    function requireHumanPlay() {
        if(disciplineSeconds()>0)throw new Error('Em đang tạm nghỉ đấu với người. Có thể đấu lại sau '+timeText(disciplineSeconds())+'.');
    }
    function updateDuelAllowance() {
        const message=document.querySelector('#arena-preflight-allowance');
        if(message)message.textContent=duelAllowance?.errorMessage()||'';
    }
    async function requireDuelAllowance() {
        const options={owner:PlatformAPI.snapshot.account?.id,expectedFamilyContext:PlatformAPI.familyContext,expectedCsrf:PlatformAPI.snapshot.csrf};
        if(!duelAllowance||!await duelAllowance.check())throw new Error(duelAllowance?.errorMessage()||'Chưa kiểm tra được lượt chơi. Em thử lại ở sảnh Đấu trí nhé.');
        return options;
    }
    async function recoverDuelAdmission(error, sent) {
        if(!live||!sent)return;
        duelAllowance?.refresh();
        if(error.name==='AbortError'||error.status===409||error.status===429)return;
        try {
            const claim=await window.GameSession.get();
            if(claim)window.GameSession.show(claim,'Phòng của em đang mở. Bấm Tiếp tục để vào lại.');
        } catch {}
    }
    function openArenaPreflight(...args) { return feature('arena').openArenaPreflight(...args); }
    const usagePanel=category=>{const q=quota(category);return `<p class="usage-note">${q.limit===null?'✦ Không giới hạn':q.used+' / '+q.limit+' lượt hôm nay'+(canUse(category)?'':' · Đã đạt giới hạn')}</p>${!canUse(category)?link('Nâng cấp gói','upgrade','outline','spark'):''}`;};
    function duelProductUsage(category){
        const q=quota(category);
        if(q.limit===null)return '';
        if(!live)return usagePanel(category);
        return isPaid()?'':`<p class="usage-note">Hạn mức gói ${category==='bot'?'luyện Bot':'đấu với người'} · ${q.used} / ${q.limit} lượt hôm nay${canUse(category)?'':' · Đã đạt giới hạn'}</p>`;
    }
    function consumeLocal(category) {
        if(!canUse(category))throw new Error('Em đã hết lượt hôm nay. Hãy vào Nâng cấp gói.');
        const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Ho_Chi_Minh'}).format(new Date());
        state.usage ||= {};state.usage[day+'-'+category]=(state.usage[day+'-'+category]||0)+1;save();
    }
    function examOptions(...args) { return feature('practice').examOptions(...args); }
    function svipPlan(...args) { return feature('commerce').svipPlan(...args); }
    function upgradeView(...args) { return feature('commerce').upgradeView(...args); }

    function planChildSummary(...args) { return feature('commerce').planChildSummary(...args); }

    let unmountParentPlans=()=>{};
    function mountParentPlans(...args) { return feature('commerce').mountParentPlans(...args); }
    function premiumLibrary() { return ''; }
    async function loadPremiumLibrary() {}
    const safeUrl=value=>/^https?:\/\//.test(value||'')?escape(value):'';
    const feeStatuses={charged:'Có học · tính phí',free:'Có học · miễn phí',absent:'Vắng',pending:'Chưa điểm danh'};
    const feeStatus=session=>Object.hasOwn(feeStatuses,session.status)?session.status:'pending';
    const feeSessionTime=session=>session.starts_at||session.startsAt;
    const feeDayKey=session=>{
        const instant=new Date(feeSessionTime(session));
        if(Number.isNaN(instant.getTime()))return /^\d{4}-\d{2}-\d{2}$/.test(session.date||'')?session.date:'';
        const parts=Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Ho_Chi_Minh',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(instant).filter(part=>part.type!=='literal').map(part=>[part.type,part.value]));
        return parts.year+'-'+parts.month+'-'+parts.day;
    };
    const feePaidLabel=fee=>fee.paid_at?'Đã hoàn thành':fee.amount===0?'Không phát sinh học phí':'Chưa nộp';
    const calendarHtml=(month,sessions)=>{
        const [y,m]=month.split('-').map(Number);if(!Number.isInteger(y)||m<1||m>12)return '';
        const days=new Date(Date.UTC(y,m,0)).getUTCDate(),first=(new Date(Date.UTC(y,m-1,1)).getUTCDay()+6)%7,groups=new Map();
        for(const session of sessions){const day=feeDayKey(session);if(day.slice(0,7)!==month)continue;if(!groups.has(day))groups.set(day,[]);groups.get(day).push(session);}
        return `<section class="fee-calendar" aria-label="Lịch điểm danh tháng ${escape(month)} theo giờ Việt Nam"><strong>Tháng ${escape(month.slice(5))}/${escape(month.slice(0,4))}</strong><div class="calendar-days">${['T2','T3','T4','T5','T6','T7','CN'].map(day=>'<b class="calendar-weekday" aria-hidden="true">'+day+'</b>').join('')}${'<span class="calendar-empty" aria-hidden="true"></span>'.repeat(first)}${Array.from({length:days},(_,i)=>{
            const date=month+'-'+String(i+1).padStart(2,'0'),items=groups.get(date)||[],counts={};
            for(const item of items){const status=feeStatus(item);counts[status]=(counts[status]||0)+1;}
            const statuses=Object.keys(counts),label='Ngày '+(i+1)+(items.length?', '+items.length+' buổi: '+statuses.map(status=>counts[status]+' '+feeStatuses[status].toLocaleLowerCase('vi')).join('; '):', không có buổi học');
            return `<div class="calendar-day ${statuses.length>1?'calendar-mixed':statuses.length?'calendar-'+statuses[0]:''}" data-fee-date="${date}" role="img" aria-label="${escape(label)}"><span class="calendar-day-number">${i+1}</span>${items.length?`<small class="calendar-session-count">${items.length} buổi</small><div class="calendar-status-markers" aria-hidden="true">${statuses.map(status=>`<i class="calendar-marker marker-${status}" data-fee-status="${status}">${counts[status]}</i>`).join('')}</div>`:''}</div>`;
        }).join('')}</div><ul class="fee-calendar-legend" aria-label="Chú thích điểm danh">${Object.entries(feeStatuses).map(([status,label])=>`<li><i class="calendar-marker marker-${status}" aria-hidden="true"></i><span>${label}</span></li>`).join('')}</ul><p class="fee-calendar-note">Ngày có nhiều buổi hiển thị đủ từng trạng thái; số trong ô màu là số buổi. Giờ Việt Nam.</p></section>`;
    };
    function trendChart(...args) { return feature('classroom').trendChart(...args); }
    function loadClass(...args) { return feature('classroom').loadClass(...args); }
    function readClassSection(...args) { return feature('classroom').readClassSection(...args); }
    const classFileUrl=value=>/^\/api\/v1\/class-submissions\/\d+\/file$/.test(value||'')?escape(value):'';
    const submissionMarkup=submission=>submission&&classFileUrl(submission.url)?`<a href="${classFileUrl(submission.url)}" target="_blank" rel="noopener noreferrer">Xem bài đã nộp: ${escape(submission.filename)}</a><small>Nộp lúc ${escape(accountDate(submission.submitted_at))}</small>`:'<span>Em chưa nộp bài này.</span>';
    function classAssignmentMarkup(...args) { return feature('classroom').classAssignmentMarkup(...args); }
    function submitClassAssignment(...args) { return feature('classroom').submitClassAssignment(...args); }
    function renderClassBody(...args) { return feature('classroom').renderClassBody(...args); }
    function showClassRanking(...args) { return feature('classroom').showClassRanking(...args); }
    function showFee(...args) { return feature('classroom').showFee(...args); }
    function paymentMarkup(...args) { return feature('commerce').paymentMarkup(...args); }
    function checkoutStyles(...args) { return feature('commerce').checkoutStyles(...args); }
    function checkoutEvidenceMarkup(...args) { return feature('commerce').checkoutEvidenceMarkup(...args); }
    function checkoutSummaryMarkup(...args) { return feature('commerce').checkoutSummaryMarkup(...args); }
    function showCheckout(...args) { return feature('commerce').showCheckout(...args); }
    function loadPaymentHistory(...args) { return feature('commerce').loadPaymentHistory(...args); }
    function stopPaymentWatch(){
        paymentGeneration++;
        if(paymentWatch){clearTimeout(paymentWatch.timer);paymentWatch.controller.abort();}
        paymentWatch=null;
    }
    function paymentViewActive(context){
        const family=PlatformAPI.familyState;
        return paymentWatch===context&&context.generation===paymentGeneration&&context.owner===accountPageOwner&&PlatformAPI.snapshot.authenticated&&PlatformAPI.snapshot.account?.id===context.owner&&PlatformAPI.snapshot.csrf===context.csrf&&context.target.isConnected&&(context.dialog?currentRoute==='classroom'&&context.dialog.open:currentRoute==='payment')&&(!context.beneficiaryId||(family?.scope==='parent_full'&&family.activeProfile?.type==='parent'&&family.context===context.familyContext&&String(family.selectedChildId)===context.beneficiaryId));
    }
    function paymentAvailable(context){return paymentViewActive(context)&&!document.hidden&&navigator.onLine!==false;}
    function schedulePaymentCheck(...args) { return feature('commerce').schedulePaymentCheck(...args); }
    function paymentFeedback(...args) { return feature('commerce').paymentFeedback(...args); }
    function renderPaymentOrder(...args) { return feature('commerce').renderPaymentOrder(...args); }
    function syncPaidPayment(...args) { return feature('commerce').syncPaidPayment(...args); }
    function checkPayment(...args) { return feature('commerce').checkPayment(...args); }
    function createPayment(...args) { return feature('commerce').createPayment(...args); }
    function startPaymentView(...args) { return feature('commerce').startPaymentView(...args); }
    function pausePaymentCheck(){
        if(!paymentWatch)return;
        clearTimeout(paymentWatch.timer);paymentWatch.timer=null;paymentWatch.controller.abort();paymentWatch.controller=new AbortController();
    }
    function resumePaymentCheck(){
        const context=paymentWatch;if(!context||!paymentAvailable(context))return;
        if(context.busy){context.resumeRequested=true;return;}
        if(!context.order){if(context.resumeOrderId)createPayment(context);else showCheckout(context);return;}
        if(Date.now()-context.lastCheck>1500)checkPayment(context);else schedulePaymentCheck(context);
    }
    function loadPayment(...args) { return feature('commerce').loadPayment(...args); }

    function initials(...args) { return feature('profile').initials(...args); }

    function getExam(...args) { return feature('practice').getExam(...args); }

    function timeText(seconds) {
        const value = Math.max(0,Math.ceil(seconds));
        return String(Math.floor(value / 60)).padStart(2,'0') + ':' + String(value % 60).padStart(2,'0');
    }

    function timeLeft(deadline) {
        return timeText((deadline - Date.now()) / 1000);
    }

    function battleTime(...args) { return feature('arena').battleTime(...args); }

    function updateBattleTimer(...args) { return feature('arena').updateBattleTimer(...args); }

    function updateBattleRound(...args) { return feature('arena').updateBattleRound(...args); }

    function resumeArena() {
        if(!learnerBackgroundAllowed())return;
        if(document.hidden||!currentRoute||!host.progress?.name||live&&!PlatformAPI.snapshot.authenticated)return;
        if(sessionStorage.getItem('5bmath-room'))pollRoom();
        else if(currentRoute==='battle'&&currentBattle?.mode==='bot'){
            ensureBotLease().then(ready=>{if(!ready||!currentBattle)return;tickBot();updateBattleTimer(currentBattle);updateBattleVisuals();});
        }
    }

    function emoteSeconds(...args) { return feature('arena').emoteSeconds(...args); }

    function updateEmoteControls(...args) { return feature('arena').updateEmoteControls(...args); }

    function sendEmote(...args) { return feature('arena').sendEmote(...args); }

    function isCorrect(question, answer) {
        if(typeof question.correct==='boolean')return question.correct;
        if(question.responseMode==='choice')return String(answer??'')===String(question.answer);
        return content.matches(answer,question.answer,question.answerKind||'auto');
    }

    function answerInput(value='',battle=false,kind='auto',question=null) {
        if(battle&&question?.responseMode==='choice')return `<fieldset class="battle-choices"><legend>Chọn đáp án để gửi ngay</legend>${question.options.map((option,i)=>`<label class="answer"><input type="radio" name="battle-choice" value="${escape(option)}" ${value===option?'checked':''}><b>${'ABCD'[i]}.</b><span>${escape(option)}</span></label>`).join('')}</fieldset>`;
        return `<div class="typed-answer"><label for="${battle?'battle-answer':'exam-answer'}">Đáp án của em</label><input id="${battle?'battle-answer':'exam-answer'}" name="${battle?'battle-answer':'learning-answer'}" type="text" inputmode="${kind==='number'?'decimal':'text'}" maxlength="500" autocomplete="off" autocapitalize="off" spellcheck="false" value="${escape(value)}" aria-describedby="${battle?'battle-answer-help':'exam-answer-help'}"><small id="${battle?'battle-answer-help':'exam-answer-help'}">${kind==='ordered'||kind==='unordered'?'Ngăn cách các kết quả bằng dấu ;':'Nhập số, phân số (ví dụ 3/4) hoặc dấu theo yêu cầu. Dùng dấu phẩy hoặc chấm cho phần thập phân.'}</small>${battle?'<button class="btn dark" type="submit">Gửi đáp án</button>':'<span id="answer-save-status" role="status"></span>'}</div>`;
    }
    const examDrafts=new Map();let draftTimer=null,draftSaving=null;
    function rememberExamAnswer(...args) { return feature('practice').rememberExamAnswer(...args); }
    function updateExamProgress(...args) { return feature('practice').updateExamProgress(...args); }
    function flushExamDrafts(...args) { return feature('practice').flushExamDrafts(...args); }

    function go(route, parameters = {}) {
        location.assign(href(route,parameters));
    }

    function refresh() {
        host.redraw();
    }

    function practiceCreateButton(...args) { return feature('practice').practiceCreateButton(...args); }
    function loadPurchasedPractice(...args) { return feature('practice').loadPurchasedPractice(...args); }
    function openCreatedExam(...args) { return feature('practice').openCreatedExam(...args); }
    function quotePurchasedExam(...args) { return feature('practice').quotePurchasedExam(...args); }
    function createExam(...args) { return feature('practice').createExam(...args); }

    let submitting = false,battleSending=false;
    function finishExam(...args) { return feature('practice').finishExam(...args); }

    function requestSubmit(...args) { return feature('practice').requestSubmit(...args); }

    async function copyText(text) {
        try {
            await navigator.clipboard.writeText(text);
            host.toast('Đã sao chép.');
        } catch {
            host.showModal(`<h2 class="modal-title">Sao chép nội dung</h2><label class="field"><span>Chọn và sao chép</span><input id="learning-copy-value" readonly value="${escape(text)}"></label>`);
            document.querySelector('#learning-copy-value').select();
        }
    }

    function recordActivity() {
        if(!learnerBackgroundAllowed()){activityStarted=null;return;}
        if(live){
            if(host.progress?.name && !document.hidden)PlatformAPI.request('heartbeat',{}).catch(()=>{});
            activityStarted = document.hidden ? null : Date.now();
            return;
        }
        if (!activityStarted) return;
        const now = Date.now();
        const seconds = Math.floor((now - activityStarted) / 1000);
        activityStarted = document.hidden ? null : now;
        if (seconds < 1) return;
        const {year,month,day} = content.schoolDate();
        const date = year + '-' + String(month).padStart(2,'0') + '-' + String(day).padStart(2,'0') + 'T00:00:00+07:00';
        load();
        state.activity[date] = (state.activity[date] || 0) + seconds;
        save();
    }

    function buildBotBattle(...args) { return feature('arena').buildBotBattle(...args); }
    function backupLegacyBot(...args) { return feature('arena').backupLegacyBot(...args); }
    function startBot(...args) { return feature('arena').startBot(...args); }
    function ensureBotLease(...args) { return feature('arena').ensureBotLease(...args); }

    function setBotRoundTiming(...args) { return feature('arena').setBotRoundTiming(...args); }

    function persistBot(...args) { return feature('arena').persistBot(...args); }

    function settleBotAttack(...args) { return feature('arena').settleBotAttack(...args); }
    function beginBotAttack(...args) { return feature('arena').beginBotAttack(...args); }
    function answerBot(...args) { return feature('arena').answerBot(...args); }
    function tickBot(...args) { return feature('arena').tickBot(...args); }

    function nextBot(...args) { return feature('arena').nextBot(...args); }

    const promotionOwner=()=>live?String(PlatformAPI.snapshot.account?.id||''):('offline:'+name());
    function queuePromotion(result,before,after){if(result.mode==='bot'||result.completed===false||result.outcome!=='win'||after<=before||Math.min(14,Math.floor(after/20))<=Math.min(14,Math.floor(before/20)))return;const owner=promotionOwner(),seen='5bmath-promotion-seen:'+owner+':'+result.id;if(sessionStorage.getItem(seen))return;sessionStorage.setItem('5bmath-promotion',JSON.stringify({id:result.id,owner,pet:state.mascot,before,after}));}
    function showPromotion(){let p;try{p=JSON.parse(sessionStorage.getItem('5bmath-promotion')||'null')}catch{return}if(!p||currentRoute!=='battleResult'||p.id!==query('id')||p.owner!==promotionOwner())return;const seen='5bmath-promotion-seen:'+p.owner+':'+p.id;if(sessionStorage.getItem(seen))return;sessionStorage.setItem(seen,'1');sessionStorage.removeItem('5bmath-promotion');setMobileMenu(false,false);host.showModal(`<section class="rank-promotion" role="status">${celebrationMarkup({seed:'promotion:'+p.id})}<span class="eyebrow">Một bước trưởng thành mới</span><h2 class="modal-title">Chúc mừng thăng hạng!</h2><p>${escape(mascotAvatars[p.pet]?.[0]||petName())} đã cùng em tiến bộ.</p><div class="promotion-evolution" data-from-form="${mascotVisuals.formFor(p.before)}" data-to-form="${mascotVisuals.formFor(p.after)}"><div class="promotion-old">${art(p.pet,'Trước khi thăng hạng',false,p.before)}</div><div class="promotion-spark" aria-hidden="true">✦ ✧ ✦</div><div class="promotion-new">${art(p.pet,'Sau khi thăng hạng',false,p.after)}</div></div><p class="promotion-ranks"><span>${mascotVisuals.rankFor(p.before)}</span><b aria-hidden="true">→</b><strong>${mascotVisuals.rankFor(p.after)}</strong></p><p>${content.format(p.before)} → ${content.format(p.after)} kinh nghiệm</p><button type="button" class="btn dark" id="promotion-close">Tiếp tục hành trình</button></section>`);const modal=document.getElementById('modal'),fx=mountCelebration(modal.querySelector('.rank-promotion'));modal.addEventListener('close',()=>{fx?.destroy();celebrationControllers.delete(fx);},{once:true});document.getElementById('promotion-close').onclick=()=>modal.close();}
    function challengeOpponent(...args) { return feature('arena').challengeOpponent(...args); }

    function finishBattle(...args) { return feature('arena').finishBattle(...args); }

    function arenaRequest(...args) { return feature('arena').arenaRequest(...args); }

    function roomSettings(...args) { return feature('arena').roomSettings(...args); }

    function enterRoom(...args) { return feature('arena').enterRoom(...args); }

    function openRoomLink(...args) { return feature('arena').openRoomLink(...args); }

    let polling=false,publicRefresh=0,serverOffset=0,lastCount=null;
    const arenaNow=()=>Date.now()+serverOffset;
    function overlay(...args) { return feature('arena').overlay(...args); }
    function countdown(...args) { return feature('arena').countdown(...args); }
    function ownPublicRoomCodes(...args) { return feature('arena').ownPublicRoomCodes(...args); }
    function loadPublicRooms(...args) { return feature('arena').loadPublicRooms(...args); }
    function inlineChallenge(...args) { return feature('arena').inlineChallenge(...args); }
    function roomPopup(...args) { return feature('arena').roomPopup(...args); }
    function pollRoom(...args) { return feature('arena').pollRoom(...args); }
    let visualHp=null,catFinaleUntil=0,catFinishTimer=null;
    let owlFinaleUntil=0,owlFinishTimer=null;
    const attackSpells=[['rock','Đá rơi'],['vine','Dây leo trói'],['lightning','Sét đánh']];
    const activeHitSpells=new Set(),shownHitSpells=new Set(),hitSpellImages=[];
    let hitSpellBattle=null;
    function recordBotAttack(...args) { return feature('arena').recordBotAttack(...args); }
    function attackSpell(...args) { return feature('arena').attackSpell(...args); }
    function clearHitSpells() {
        for(const effect of activeHitSpells){effect.timers.forEach(clearTimeout);effect.node?.remove();}
        activeHitSpells.clear();
    }
    function aimUltimateBeam(...args) { return feature('arena').aimUltimateBeam(...args); }
    function playHitSpell(...args) { return feature('arena').playHitSpell(...args); }
    function animateHit(...args) { return feature('arena').animateHit(...args); }
    function dispatchBattleHit(...args) { return feature('arena').dispatchBattleHit(...args); }
    function updateBattleVisuals(...args) { return feature('arena').updateBattleVisuals(...args); }

    const mobileNavigation=()=>browser&&matchMedia('(max-width:860px), (max-width:1100px) and (max-height:500px)').matches;
    function setMobileMenu(open,restoreFocus=true) {
        if(!browser)return;
        const drawer=document.querySelector('#learning-navigation'),toggle=document.querySelector('#learning-menu-toggle');
        if(!drawer||!toggle)return;
        const shown=Boolean(open&&mobileNavigation());
        document.body.classList.toggle('learning-drawer-open',shown);
        drawer.inert=mobileNavigation()&&!shown;
        const main=document.querySelector('#learning-app .app-main');if(main)main.inert=shown;
        toggle.setAttribute('aria-expanded',String(shown));toggle.setAttribute('aria-label',shown?'Đóng menu học tập':'Mở menu học tập');
        const backdrop=document.querySelector('#learning-menu-backdrop');if(backdrop)backdrop.hidden=!shown;
        if(shown){drawer.setAttribute('role','dialog');drawer.setAttribute('aria-modal','true');document.querySelector('#learning-menu-close')?.focus();}
        else {drawer.removeAttribute('role');drawer.removeAttribute('aria-modal');if(restoreFocus&&mobileNavigation())toggle.focus();}
    }
    function mountNavigation() {
        if(browser&&live&&PlatformAPI.familyContext)document.querySelectorAll('[data-family-profile-menu]').forEach(node=>window.FamilyProfiles?.mount?.(node));
        setMobileMenu(false,false);
        const toggle=document.querySelector('#learning-menu-toggle');if(!toggle)return;
        toggle.onclick=()=>setMobileMenu(toggle.getAttribute('aria-expanded')!=='true');
        document.querySelector('#learning-menu-close').onclick=()=>setMobileMenu(false);
        document.querySelector('#learning-menu-backdrop').onclick=()=>setMobileMenu(false);
        document.querySelector('#learning-navigation').onclick=event=>{if(event.target.closest('a'))setMobileMenu(false,false);};
    }
    function setArenaMode(...args) { return feature('arena').setArenaMode(...args); }
    function bindArenaModes() {
        const tabs=document.querySelector('.arena-modes');if(!tabs)return;
        tabs.onkeydown=event=>{
            if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;
            const buttons=[...tabs.querySelectorAll('[data-arena-mode]')],index=buttons.findIndex(b=>b===event.target);
            if(index<0)return;event.preventDefault();
            const next=event.key==='Home'?0:event.key==='End'?2:(index+(event.key==='ArrowRight'?1:2))%3;
            setArenaMode(buttons[next].dataset.arenaMode);buttons[next].focus();
        };
    }

    function render(route) {
        if(route==='mascot')route='profile';
        currentRoute = route;
        const title = routes[route][1];
        const selected = sections[route] || route;
        let body;
        const featureKey={weekly:'learning_open',topics:'learning_open',lesson:'learning_open',advanced:'learning_open',
            exams:'practice_open',arena:'arena_open',rank:'leaderboard_open'}[route];
        const parentPlans=browser&&live&&route==='upgrade'&&PlatformAPI.familyState?.activeProfile?.type==='parent'&&window.ParentPlanPicker;
        if(parentPlans)body=intro('Gói học','Chọn gói và kỳ đăng ký cho con.')+(window.FamilyCart?.planEntry()||'')+ParentPlanPicker.render()+'<div data-parent-plan-details hidden></div>';
        else if(live && featureKey && PlatformAPI.snapshot.features?.[featureKey]===false) body=intro(title,'Chức năng đang được tạm dừng. Em có thể chọn hoạt động khác.')+link('Về tổng quan','dashboard');
        else if (browser && !host.progress?.name && !['zoomRegistration','classroom'].includes(route)) body = accountGate();
        else if(browser && live && groupGames?.handles(route)) body=groupGames.shell(route);
        else if(browser&&live&&window.StudyLibrary?.handles(route))body=StudyLibrary.render(route);
        else if(browser && live && typeof LocalPilot!=='undefined' && LocalPilot.handles(route)) body=LocalPilot.shell();
        else if(browser && live && typeof LocalPilot!=='undefined' && LocalPilot.requested(route)) body=LocalPilot.enabled()?LocalPilot.shell():intro('Kho thí điểm chưa bật','Bài làm thí điểm dùng kho riêng. Em có thể trở về luyện tập chính.')+link('Về luyện tập','exams');
        else if(route==='lookup')body=(browser?window.PracticeExport:require('./practice-export.js')).lookupShell();
        else body = (route === 'advanced' ? views.lesson(true) : views[route]());

        const studyRoutes=['weekly','topics','lesson','advanced','exams','testing','results','lookup'];
        const studyNav=studyRoutes.includes(route)?`<nav class="student-study-tabs" aria-label="Học & Luyện">${[['weekly','Bài giảng'],['exams','Luyện tập']].map(([key,label])=>`<a href="${href(key)}" ${(['exams','testing','results','lookup'].includes(route)?key==='exams':key==='weekly')?'aria-current="page"':''}>${label}</a>`).join('')}</nav>`:'';
        const zoomFree=['zoomRegistration','classroom'].includes(route)&&!isPaid();
        if(zoomFree)body=intro('Cá nhân','Xem thông tin hồ sơ và Bạn Đồng Hành của em.')+link('Về Cá nhân','profile','outline');
        return `<div id="learning-app" class="student-shell-content"><div class="app-main"><div class="content">${studyNav}${body}</div></div></div>`;
    }

    let companionChanging=false;
    function companionRemaining(...args) { return feature('profile').companionRemaining(...args); }
    function chooseCompanion(...args) { return feature('profile').chooseCompanion(...args); }

    const actions = {
"retake-exam"(...args){return feature('practice').actions["retake-exam"](...args);},
"continue-study"(...args){return feature('profile').actions["continue-study"](...args);},
"open-companion"(...args){return feature('profile').actions["open-companion"](...args);},
"copy-personal-code"(...args){return feature('profile').actions["copy-personal-code"](...args);},
"complete"(...args){return feature('study').actions["complete"](...args);},
"practice"(...args){return feature('study').actions["practice"](...args);},
"video"(...args){return feature('study').actions["video"](...args);},
"create-exam"(...args){return feature('practice').actions["create-exam"](...args);},
"create-topic"(...args){return feature('practice').actions["create-topic"](...args);},
"create-school"(...args){return feature('practice').actions["create-school"](...args);},
"previous"(...args){return feature('practice').actions["previous"](...args);},
"next"(...args){return feature('practice').actions["next"](...args);},
"submit-exam"(...args){return feature('practice').actions["submit-exam"](...args);},
"start-bot"(...args){return feature('arena').actions["start-bot"](...args);},
"next-battle"(...args){return feature('arena').actions["next-battle"](...args);},
"create-room"(...args){return feature('arena').actions["create-room"](...args);},
"minimize-room"(...args){return feature('arena').actions["minimize-room"](...args);},
"download-material"(...args){return feature('study').actions["download-material"](...args);},
"quick-match"(...args){return feature('arena').actions["quick-match"](...args);},
"copy-room"(...args){return feature('arena').actions["copy-room"](...args);},
"copy-room-link"(...args){return feature('arena').actions["copy-room-link"](...args);},
"leave-room"(...args){return feature('arena').actions["leave-room"](...args);},
"leave-battle"(...args){return feature('arena').actions["leave-battle"](...args);},
"choose-sparrow"(...args){return feature('profile').actions["choose-sparrow"](...args);},
"choose-butterfly"(...args){return feature('profile').actions["choose-butterfly"](...args);},
"choose-dolphin"(...args){return feature('profile').actions["choose-dolphin"](...args);},
"choose-cu-meo"(...args){return feature('profile').actions["choose-cu-meo"](...args);},
"choose-sprout"(...args){return feature('profile').actions["choose-sprout"](...args);},
"choose-voi"(...args){return feature('profile').actions["choose-voi"](...args);},
"choose-lion"(...args){return feature('profile').actions["choose-lion"](...args);},
"choose-starfish"(...args){return feature('profile').actions["choose-starfish"](...args);},
"choose-fox"(...args){return feature('profile').actions["choose-fox"](...args);},
"choose-tiger"(...args){return feature('profile').actions["choose-tiger"](...args);},
"choose-eagle"(...args){return feature('profile').actions["choose-eagle"](...args);},
"choose-ca-map"(...args){return feature('profile').actions["choose-ca-map"](...args);},
"choose-bee"(...args){return feature('profile').actions["choose-bee"](...args);},
"choose-octopus"(...args){return feature('profile').actions["choose-octopus"](...args);},
"choose-rabbit"(...args){return feature('profile').actions["choose-rabbit"](...args);},
"choose-crab"(...args){return feature('profile').actions["choose-crab"](...args);},
"choose-gau"(...args){return feature('profile').actions["choose-gau"](...args);},
"choose-cat"(...args){return feature('profile').actions["choose-cat"](...args);},
"choose-dog"(...args){return feature('profile').actions["choose-dog"](...args);},
"choose-horse"(...args){return feature('profile').actions["choose-horse"](...args);},
"refresh-account"(...args){return feature('profile').actions["refresh-account"](...args);},
"review-upgrade"(...args){return feature('commerce').actions["review-upgrade"](...args);},
"copy-invite"(...args){return feature('profile').actions["copy-invite"](...args);},
"copy-invite-link"(...args){return feature('profile').actions["copy-invite-link"](...args);},
"class-preview"(...args){return feature('classroom').actions["class-preview"](...args);},
"rename"(...args){return feature('profile').actions["rename"](...args);},
async logout() { if(live){await PlatformAPI.logout();sessionStorage.removeItem('5bmath-room');sessionStorage.removeItem('5bmath-bot-battle');}host.progress.name = ''; host.saveProgress(); location.assign(new URL(location.protocol==='file:'?'index.html#home':'./',document.baseURI)); }
    };

    function mount(route) {
        if(route==='mascot')route='profile';
        if(!learnerBackgroundAllowed()){
            if(browser)window.GameSession?.unmountGlobal();clearInterval(interval);activityStarted=null;stopNotificationPolling();stopPaymentWatch();
            if(route==='upgrade'&&browser&&window.ParentPlanPicker&&window.FamilyCart)mountParentPlans();
            if(route==='payment')loadPayment();
            mountNavigation();return;
        }
        if(['zoomRegistration','classroom'].includes(route)&&!isPaid()){mountNavigation();return;}
        if(typeof ArenaAudio!=='undefined')ArenaAudio.setActive(['arena','rank'].includes(sections[route]||route));
        if(browser&&live)window.GameSession?.mountGlobal();
        if(browser&&live&&route==='arena')window.GameSession?.syncInline?.();
        document.querySelectorAll('[data-games-audio-slot]').forEach(slot=>{slot.innerHTML=audioButton();});
        if(browser && live && groupGames?.handles(route) && host.progress?.name){stopPaymentWatch();clearInterval(interval);groupGames.mount(route,snapshot=>{applySnapshot(snapshot);const pet=document.querySelector('.sidebar-pet');if(pet)pet.innerHTML=art(state.mascot)+'<div><b>'+escape(petName())+'</b><small>'+content.format(state.points)+' kinh nghiệm</small></div>'+icon('chevron',15);const profile=document.querySelector('.profile .mascot-avatar');if(profile)profile.outerHTML=avatar();});mountNavigation();return;}
        if(browser&&live&&window.StudyLibrary?.handles(route)&&host.progress?.name){stopPaymentWatch();clearInterval(interval);StudyLibrary.mount(route).catch(error=>host.toast(error.message));mountNavigation();return;}
        if(browser && live && typeof LocalPilot!=='undefined' && host.progress?.name && LocalPilot.handles(route)){stopPaymentWatch();clearInterval(interval);LocalPilot.mount(route);mountNavigation();return;}
        stopPaymentWatch();
        clearInterval(interval);
        if (!host.progress?.name){mountNavigation();return;}
        const openingRoomLink=route==='room'&&query('code')&&!sessionStorage.getItem('5bmath-room');
        if(live&&(document.querySelector('[data-game-allowance="duel"]')||openingRoomLink)){
            duelAllowance?.unmount();
            duelAllowance=gameAllowance?.mount('duel',document.querySelector('#learning-app'),updateDuelAllowance);
        }
        if(['lesson','advanced'].includes(route)&&selectedLesson()){
            const lesson=selectedLesson();
            stopLessonStudy=lessonStudy.mount(document.querySelector('[data-lesson-study]'),{
                videoLesson:live&&lesson.video?.provider==='bunny'?{provider:'main',lessonKey:lesson.id,revision:lesson.revision,title:lesson.title}:null,
                onComplete:async()=>{if(live){await mutate('lessons/'+lesson.id+'/complete');return {completed:true};}await actions.complete();return {completed:true};}
            });
        }
        if(route==='profile') {
            if(typeof ThemeManager !== 'undefined') ThemeManager.mountSettings();
            if(live)loadPersonalNotices();
        }
        startNotificationPolling();
        if(route==='rank')loadRank();
        if(route==='classroom')loadClass();
        if(route==='exams'&&live)loadPurchasedPractice();
        if(route==='payment')loadPayment();
        if(route==='arena')loadPublicRooms();
            if(route==='battleResult'){ArenaAudio.setActive(true);const victory=document.querySelector('.victory');setTimeout(()=>ArenaAudio.effect(victory?'win':'lose'),100);const resultNode=document.querySelector('.battle-result'),fx=mountCelebration(resultNode);setTimeout(()=>{fx?.destroy();celebrationControllers.delete(fx);resultNode?.querySelector('[data-garden-confetti]')?.remove();},3000);}
        ArenaAudio.setActive(['arena','rank'].includes(sections[route]||route));
        if(live && !document.hidden)PlatformAPI.request('heartbeat',{}).catch(()=>{});
        if (!document.hidden) activityStarted = Date.now();
        if (['lesson','advanced'].includes(route) && selectedLesson()) {
            state.lastLesson = selectedLesson().id;
            if(live)PlatformAPI.request('lessons/'+state.lastLesson+'/open',{}).catch(error=>host.toast(error.message));
            save();
        }
        if (route === 'battle') {
            botLeaseReady=!live;
            if(live&&query('bot')&&!sessionStorage.getItem('5bmath-bot-battle')){window.GameSession.get().then(claim=>{if(currentRoute==='battle'&&claim?.claimId===query('bot')&&claim.game==='duel'&&claim.playMode==='bot'){currentBattle={...buildBotBattle(claim.botBattle.questions,1,claim.claimId,claim.botBattle.grade),...claim.botBattle,gameClaimId:claim.claimId,gameClaimRevision:claim.checkpointRevision};sessionStorage.setItem('5bmath-bot-battle',JSON.stringify(currentBattle));refresh();}else window.GameSession.show(claim,'Chưa tìm thấy phòng luyện Bot của tài khoản.');}).catch(error=>window.GameSession.show(null,error.message));}
            // Per-species Canvas effects replace the old shared random normal spells.
            try {
                if (!sessionStorage.getItem('5bmath-room')) currentBattle = JSON.parse(sessionStorage.getItem('5bmath-bot-battle') || 'null');
            }
            catch { currentBattle = null; }
            if (currentBattle) {
                document.querySelector('#app').innerHTML = render(route);visualHp=[currentBattle.hp,currentBattle.opponentHp];
                updateBattleRound(currentBattle);
                updateEmoteControls(currentBattle);
                if(currentBattle.mode==='bot')ensureBotLease();
            }
        }
        if(typeof RuntimeAssets==='undefined'||!RuntimeAssets.managed){
            if(typeof ArenaLion!=='undefined')ArenaLion.mount();
            if(browser)window.ArenaBeeAnimation?.sync();
        }
        if(route==='testing'&&browser)window.PracticeLayout?.mount();
        document.querySelectorAll('[data-solution-toggle]').forEach(button=>button.onclick=()=>{const panel=document.getElementById(button.dataset.solutionToggle);if(!panel)return;panel.hidden=!panel.hidden;button.setAttribute('aria-expanded',String(!panel.hidden));button.textContent=panel.hidden?'Xem lời giải':'Ẩn lời giải';});
        mascotVisuals.mount(document);
        if(route==='battleResult')setTimeout(showPromotion,150);
        mountNavigation();
        bindArenaModes();
        updateArenaDiscipline();
        if(typeof RuntimeAssets==='undefined'||!RuntimeAssets.managed){
        if(typeof TigerAnimation!=='undefined')TigerAnimation.hydrate();
        if(typeof ArenaVoi!=='undefined')ArenaVoi.mount(document);
        window.HorseAnimation?.mount(document);
        if(typeof RabbitAnimation!=='undefined')RabbitAnimation.mount();
        if(typeof OwlAnimation!=='undefined')OwlAnimation.mount();
        window.ArenaDolphin?.mount();
        window.ButterflyAnimation?.mount();
        if(browser)window.SharkAnimation?.mount();
        if(typeof BearAnimation!=='undefined')BearAnimation.mount();
        }
        document.querySelector('#learning-app').onclick = async event => {
            const navigation=event.target.closest('a[href]');
            if(navigation&&(examDrafts.size||draftSaving)){
                event.preventDefault();
                try{await flushExamDrafts();location.assign(navigation.href);}catch(error){host.toast(error.message);}
                return;
            }
            const action = event.target.closest('[data-learning]');
            const questionButton = event.target.closest('[data-question]');
            const answer = event.target.closest('[data-battle-answer]');
            const rankButton = event.target.closest('[data-rank]');
            const challenge=event.target.closest('[data-challenge]'),emote=event.target.closest('[data-emote]'),classButton=event.target.closest('[data-class-tab]'),classRanking=event.target.closest('[data-class-ranking]'),fee=event.target.closest('[data-fee]');
            const mode=event.target.closest('[data-arena-mode]');
            const notification = event.target.closest('[data-notification]');
            const accountPage=event.target.closest('[data-account-page]');
            let actionLocked=false;
            try {
                if(examDrafts.size)await flushExamDrafts();
                if(mode){setArenaMode(mode.dataset.arenaMode);}
                else if(challenge){if(challenge.disabled)return;await enterRoom('join',{code:challenge.dataset.challenge});}
                else if(classButton){
                    const section=classButton.dataset.classTab;
                    classTab=section;document.querySelectorAll('[data-class-tab]').forEach(b=>{b.classList.toggle('selected',b===classButton);b.setAttribute('aria-pressed',String(b===classButton));});
                    renderClassBody();
                    if(['assignments','fees'].includes(section)){
                        const data=await loadClass();
                        if(classTab===section)await readClassSection(data,section);
                    }
                }
                else if(classRanking){await showClassRanking(classRanking.dataset.classRanking,classRanking.dataset.value);}
                else if(fee){await showFee(fee.dataset.fee);}
                else if(emote){await sendEmote(Number(emote.dataset.emote));}
                else if(notification){if(!notification.disabled)await readNotification(notification);}
                else if(accountPage){if(!accountPage.disabled)await loadAccountPage(accountPage.dataset.accountPage,Number(accountPage.dataset.page));}
                else if(event.target.closest('[data-evolution]')){showEvolution(event.target.closest('[data-evolution]').dataset.evolution);}
                else if (questionButton) {
                    getExam().index = Number(questionButton.dataset.question);
                    save(); refresh();
                } else if (answer) {
                    if (currentBattle.mode === 'bot') answerBot(answer.dataset.battleAnswer);
                    else { await arenaRequest('answer',{answer:answer.dataset.battleAnswer,index:currentBattle.index}); await pollRoom();if(currentBattle?.feedback?.includes('chưa đúng'))ArenaAudio.effect('wrong'); }
                } else if (rankButton) { rankType = rankButton.dataset.rank; refresh(); }
                else if (action && actions[action.dataset.learning]) {
                    if(action.disabled)return;
                    if(action.hasAttribute('data-human-play'))action.dataset.humanPending='true';
                    actionLocked=true;
                    if(gameAllowance&&action.hasAttribute('data-game-admission'))gameAllowance.setDisabled(action,true);else action.disabled=true;
                    if(action.dataset.botLevel!==undefined)document.querySelector('#bot-level').value=action.dataset.botLevel;
                    await actions[action.dataset.learning](action);
                }
            } catch (error) { host.toast(error.message); }
            finally { if(actionLocked&&action.isConnected){delete action.dataset.humanPending;if(!action.hasAttribute('data-game-admission'))action.disabled=false;}updateArenaDiscipline(); }
        };
        if(currentRoute==='testing'){const exam=getExam();if(exam&&!exam.submittedAt)PracticeScratchpad.mount('main:'+exam.id+':'+((exam.index||0)+1));}
        const examInput=document.querySelector('#exam-answer');
        if(examInput){const exam=getExam(),q=exam.questions[exam.index||0];examInput.dataset.position=String((exam.index||0)+1);examInput.dataset.questionId=q.id;examInput.oninput=()=>rememberExamAnswer(examInput);}
        const battleForm=document.querySelector('#battle-answer-form');
        if(battleForm){
            const input=battleForm.querySelector('input[name="battle-answer"]');
            if(input)input.oninput=()=>{if(currentBattle)currentBattle.draftAnswer=input.value;};
            battleForm.querySelectorAll('[name="battle-choice"]').forEach(radio=>radio.onchange=()=>{if(currentBattle)currentBattle.draftAnswer=radio.value;battleForm.requestSubmit();});
            battleForm.onsubmit=async event=>{
                event.preventDefault();const value=input?input.value:battleForm.querySelector('[name="battle-choice"]:checked')?.value;
                if(battleSending||!currentBattle||currentBattle.answer!==null||!value?.trim())return;
                const battle=currentBattle,index=battle.index,answer=value;battleSending=true;updateBattleVisuals();
                try{if(battle.mode==='bot')answerBot(answer);else{await arenaRequest('answer',{answer,index});await pollRoom();}}
                catch(error){host.toast(error.message);}finally{battleSending=false;updateBattleVisuals();}
            };
        }
        document.querySelector('#learning-app').onchange = async event => {
            const target = event.target;
            if(target.id==='review-incorrect'){document.querySelectorAll('[data-review-correct]').forEach(el=>el.hidden=target.checked&&el.dataset.reviewCorrect==='true');return;}
            if(target.id==='class-select'){stopPaymentWatch();document.querySelector('#modal')?.close();loadClass();return;}
            if(target.id==='exam-scope'){document.querySelector('#exam-content-search').value='';document.querySelector('#exam-topic').innerHTML=examOptions(target.value);return;}
            if (target.name === 'learning-answer' && target.type==='radio') {
                const exam = getExam();
                if (Date.now() >= exam.expiresAt) { finishExam(exam); return; }
                if(live){
                    const controls=[...document.querySelectorAll('[name=learning-answer], [data-learning=submit-exam], [data-learning=next], [data-learning=previous], [data-question]')];
                    controls.forEach(control=>control.disabled=true);
                    try{
                        const result=await PlatformAPI.request('exams/'+exam.id+'/answers',{position:exam.index+1,answer:target.value,revision:exam.revision??0});
                        state.exams[exam.id]={...result.exam,index:exam.index};refresh();
                    }catch(error){host.toast('Chưa lưu được câu trả lời: '+error.message);refresh();}
                    return;
                }
                const latest = state.exams[exam.id];
                latest.answers[latest.questions[latest.index].id] = target.value;
                save();
                refresh();
            } else if (target.id === 'learning-range') { lessonRange = target.value; refresh(); }
            else if (target.id === 'rank-period') { rankPeriod = target.value; refresh(); }
            else if (target.id === 'rank-scope') {
                if(live){rankScope=target.value;refresh();return;}
                document.querySelector('#rank-table').hidden = target.value === 'class';
                if (target.value === 'class') host.toast('Tài khoản thử chưa được gán vào lớp Zoom.');
            }
        };
        const search=document.querySelector('#topic-search');
        let searchDelay;
        const filterTopics=()=>{
            topicSearch=search.value;let count=0;
            document.querySelectorAll('[data-topic-title]').forEach(el=>{const show=el.dataset.topicTitle.includes(topicSearch.toLocaleLowerCase('vi').trim());el.hidden=!show;if(show)count++;});
            document.querySelector('#topic-empty').hidden=count>0;document.querySelector('#topic-count').textContent=count+' chuyên đề';
        };
        if(search){filterTopics();search.oninput=e=>{if(e.isComposing)return;clearTimeout(searchDelay);searchDelay=setTimeout(filterTopics,220);};search.oncompositionend=()=>{clearTimeout(searchDelay);searchDelay=setTimeout(filterTopics,220);};}
        const contentSearch=document.querySelector('#exam-content-search');
        if(contentSearch)contentSearch.oninput=()=>{const select=document.querySelector('#exam-topic'),old=select.value;select.innerHTML=examOptions(document.querySelector('#exam-scope').value,contentSearch.value);if([...select.options].some(o=>o.value===old))select.value=old;};
        const join = document.querySelector('#learning-join-form');
        if (join) join.onsubmit = async event => {
            event.preventDefault();
            const button = join.querySelector('button');
            if(button.disabled)return;
            try { const raw=document.querySelector('#learning-room-code').value.trim();let code=raw;try{code=new URL(raw).searchParams.get('code')||'';}catch{}if(!/^[a-z0-9]{6}$/i.test(code))throw new Error('Nhập mã gồm 6 ký tự hoặc liên kết phòng hợp lệ.');await enterRoom('join',{code:code.toUpperCase()}); }
            catch (error) { host.toast(error.message); }
        };
        const birthForm = document.querySelector('#learning-birth-form');
        if (birthForm) birthForm.onsubmit = event => {
            event.preventDefault();
            try { setBirthYear(new FormData(birthForm).get('birthYear')); refresh(); }
            catch (error) { host.toast(error.message); }
        };
        if(sessionStorage.getItem('5bmath-room'))pollRoom();
        else if(openingRoomLink)openRoomLink(query('code').toUpperCase());
        interval = setInterval(() => {
            if(!learnerBackgroundAllowed()){clearInterval(interval);activityStarted=null;stopNotificationPolling();return;}
            updateArenaDiscipline();
            if (route === 'testing') {
                const exam = getExam();
                if (!exam || exam.submittedAt) return;
                const timer = document.querySelector('#learning-timer');
                if (timer) timer.textContent = timeLeft(exam.expiresAt);
                if (Date.now() >= exam.expiresAt) finishExam(exam);
            }
            if(route==='battle'&&currentBattle){
                const b=currentBattle;
                updateBattleTimer(b);
                updateBattleRound(b);
                updateEmoteControls(b);
                if(b.mode==='bot'){
                    if(Date.now()<(b.readyAt||0))countdown(b.readyAt,Date.now());else{overlay('');tickBot();}
                }
            }
            if(sessionStorage.getItem('5bmath-room'))pollRoom();
            if(route==='arena'&&++publicRefresh%5===0)loadPublicRooms();
            if (activityStarted && Date.now() - activityStarted >= 60000) recordActivity();
        },500);
    }

    function unmount() {
        stopLessonStudy();stopLessonStudy=()=>{};
        unmountParentPlans();unmountParentPlans=()=>{};
        if(browser)window.ParentPlanPicker?.unmount();
        if(browser)window.StudyLibrary?.unmount();
        if(browser)window.PracticeLayout?.unmount();
        PracticeScratchpad.unmount();
        botLeaseEpoch++;botLeaseReady=false;if(browser)window.GameSession?.unwatch();for(const effect of celebrationControllers)effect.destroy();celebrationControllers.clear();
        groupGames?.unmount();
        duelAllowance?.unmount();duelAllowance=null;
        if(browser && typeof LocalPilot!=='undefined')LocalPilot.unmount();
        mascotVisuals.destroy();
        if(browser && typeof ThemeManager !== 'undefined') ThemeManager.unmountSettings();
        stopPaymentWatch();
        stopNotificationPolling();
        arenaPreflight?.close(false);
        clearHitSpells();
        clearTimeout(octopusFinishTimer);octopusFinishTimer=null;octopusFinaleUntil=0;
        clearTimeout(owlFinishTimer);owlFinishTimer=null;owlFinaleUntil=0;
        if(typeof OwlAnimation!=='undefined')OwlAnimation.destroy();
        if(typeof ArenaStarfish!=='undefined')ArenaStarfish.stop();
        if(typeof BearAnimation!=='undefined')BearAnimation.unmount();
        if(typeof ArenaLion!=='undefined')ArenaLion.destroy();
        clearTimeout(catFinishTimer);catFinishTimer=null;catFinaleUntil=0;
        if(browser)window.ArenaBeeAnimation?.stop();
        if(browser)window.ArenaCatAnimation?.stop();
        if(typeof ArenaVoi!=='undefined')ArenaVoi.stop();
        window.HorseAnimation?.stop();
        if(typeof RabbitAnimation!=='undefined')RabbitAnimation.destroy();
        window.ArenaDolphin?.destroy();
        window.ButterflyAnimation?.destroy();
        if(browser)window.SharkAnimation?.destroy();
        setMobileMenu(false,false);
        clearInterval(interval);
        if(typeof TigerAnimation!=='undefined')TigerAnimation.cancelAll();
        if(typeof ArenaAudio!=='undefined')ArenaAudio.setActive(false);
        recordActivity();
        activityStarted = null;
    }


    const featureInstances=new Map();
    const featureContext={get questionFrame(){return questionFrame;},get PracticeScratchpad(){return PracticeScratchpad;},
get accountDate(){return accountDate;},
get accountPageOwner(){return accountPageOwner;},set accountPageOwner(value){accountPageOwner=value;},
get accountPages(){return accountPages;},
get actions(){return actions;},
get activeHitSpells(){return activeHitSpells;},
get adoptClassUnread(){return adoptClassUnread;},
get adoptNotificationSummary(){return adoptNotificationSummary;},
get answerInput(){return answerInput;},
get applySnapshot(){return applySnapshot;},
get arenaLobby(){return arenaLobby;},
get arenaMode(){return arenaMode;},set arenaMode(value){arenaMode=value;},
get arenaNow(){return arenaNow;},
get arenaPreflight(){return arenaPreflight;},set arenaPreflight(value){arenaPreflight=value;},
get arenaScope(){return arenaScope;},set arenaScope(value){arenaScope=value;},
get arenaScopeLabel(){return arenaScopeLabel;},
get art(){return art;},
get artSeed(){return artSeed;},
get attackSpells(){return attackSpells;},
get back(){return back;},
get badge(){return badge;},
get bankNotice(){return bankNotice;},
get battlePet(){return battlePet;},
get battleScenery(){return battleScenery;},
get battleSending(){return battleSending;},set battleSending(value){battleSending=value;},
get botLeaseEpoch(){return botLeaseEpoch;},set botLeaseEpoch(value){botLeaseEpoch=value;},
get botLeaseReady(){return botLeaseReady;},set botLeaseReady(value){botLeaseReady=value;},
get botReleasePending(){return botReleasePending;},set botReleasePending(value){botReleasePending=value;},
get botStarting(){return botStarting;},set botStarting(value){botStarting=value;},
get botValidation(){return botValidation;},set botValidation(value){botValidation=value;},
get browser(){return browser;},
get button(){return button;},
get calendarHtml(){return calendarHtml;},
get canPlayHuman(){return canPlayHuman;},
get canUse(){return canUse;},
get catFinaleUntil(){return catFinaleUntil;},set catFinaleUntil(value){catFinaleUntil=value;},
get catFinishTimer(){return catFinishTimer;},set catFinishTimer(value){catFinishTimer=value;},
get celebrationMarkup(){return celebrationMarkup;},
get classData(){return classData;},set classData(value){classData=value;},
get classFrom(){return classFrom;},set classFrom(value){classFrom=value;},
get classLoadTicket(){return classLoadTicket;},set classLoadTicket(value){classLoadTicket=value;},
get classReadBusy(){return classReadBusy;},set classReadBusy(value){classReadBusy=value;},
get classReadQueue(){return classReadQueue;},set classReadQueue(value){classReadQueue=value;},
get classTab(){return classTab;},set classTab(value){classTab=value;},
get classTo(){return classTo;},set classTo(value){classTo=value;},
get classUnreadBadge(){return classUnreadBadge;},
get classUnreadVersion(){return classUnreadVersion;},set classUnreadVersion(value){classUnreadVersion=value;},
get clearHitSpells(){return clearHitSpells;},
get companionChanging(){return companionChanging;},set companionChanging(value){companionChanging=value;},
get consumeLocal(){return consumeLocal;},
get content(){return content;},
get copyText(){return copyText;},
get createExam(){return createExam;},
get currentBattle(){return currentBattle;},set currentBattle(value){currentBattle=value;},
get currentRoute(){return currentRoute;},set currentRoute(value){currentRoute=value;},
get disciplinePanel(){return disciplinePanel;},
get displayName(){return displayName;},
get draftSaving(){return draftSaving;},set draftSaving(value){draftSaving=value;},
get draftTimer(){return draftTimer;},set draftTimer(value){draftTimer=value;},
get duelAllowance(){return duelAllowance;},set duelAllowance(value){duelAllowance=value;},
get duelProductUsage(){return duelProductUsage;},
get emoteLock(){return emoteLock;},set emoteLock(value){emoteLock=value;},
get emotes(){return emotes;},
get entitlementRefreshPending(){return entitlementRefreshPending;},set entitlementRefreshPending(value){entitlementRefreshPending=value;},
get escape(){return escape;},
get evolutionBoxes(){return evolutionBoxes;},
get evolutionRows(){return evolutionRows;},
get examDrafts(){return examDrafts;},
get feePaidLabel(){return feePaidLabel;},
get feeSessionTime(){return feeSessionTime;},
get feeStatus(){return feeStatus;},
get feeStatuses(){return feeStatuses;},
get field(){return field;},
get gameAllowance(){return gameAllowance;},
get gameRulesView(){return gameRulesView;},
get gardenActivityArt(){return gardenActivityArt;},
get go(){return go;},
get grade(){return grade;},
get groupGames(){return groupGames;},
get heading(){return heading;},
get hitSpellBattle(){return hitSpellBattle;},set hitSpellBattle(value){hitSpellBattle=value;},
get homeworkPanel(){return homeworkPanel;},
get host(){return host;},set host(value){host=value;},
get href(){return href;},
get icon(){return icon;},
get intro(){return intro;},
get isCorrect(){return isCorrect;},
get isInternal(){return isInternal;},
get isPaid(){return isPaid;},
get lastCount(){return lastCount;},set lastCount(value){lastCount=value;},
get learnerBackgroundAllowed(){return learnerBackgroundAllowed;},
get lessonList(){return lessonList;},
get lessonRange(){return lessonRange;},set lessonRange(value){lessonRange=value;},
get lessonRow(){return lessonRow;},
get lessonStudy(){return lessonStudy;},
get level(){return level;},
get link(){return link;},
get live(){return live;},
get load(){return load;},
get loadClass(){return loadClass;},
get mascotAvatars(){return mascotAvatars;},
get mascotVisuals(){return mascotVisuals;},
get medal(){return medal;},
get member(){return member;},
get meter(){return meter;},
get mutate(){return mutate;},
get name(){return name;},
get nicknames(){return nicknames;},
get notice(){return notice;},
get notificationLifecycle(){return notificationLifecycle;},set notificationLifecycle(value){notificationLifecycle=value;},
get notificationPending(){return notificationPending;},set notificationPending(value){notificationPending=value;},
get notificationSender(){return notificationSender;},
get notificationTitle(){return notificationTitle;},
get notificationVersion(){return notificationVersion;},set notificationVersion(value){notificationVersion=value;},
get octopusFinaleUntil(){return octopusFinaleUntil;},set octopusFinaleUntil(value){octopusFinaleUntil=value;},
get octopusFinishTimer(){return octopusFinishTimer;},set octopusFinishTimer(value){octopusFinishTimer=value;},
get owlFinaleUntil(){return owlFinaleUntil;},set owlFinaleUntil(value){owlFinaleUntil=value;},
get owlFinishTimer(){return owlFinishTimer;},set owlFinishTimer(value){owlFinishTimer=value;},
get paymentAvailable(){return paymentAvailable;},
get paymentGeneration(){return paymentGeneration;},set paymentGeneration(value){paymentGeneration=value;},
get paymentViewActive(){return paymentViewActive;},
get paymentWatch(){return paymentWatch;},set paymentWatch(value){paymentWatch=value;},
get personalNotices(){return personalNotices;},set personalNotices(value){personalNotices=value;},
get petName(){return petName;},
get petRank(){return petRank;},
get polling(){return polling;},set polling(value){polling=value;},
get query(){return query;},
get queuePromotion(){return queuePromotion;},
get rankPercent(){return rankPercent;},
get rankPeriod(){return rankPeriod;},set rankPeriod(value){rankPeriod=value;},
get rankProgress(){return rankProgress;},
get rankScope(){return rankScope;},set rankScope(value){rankScope=value;},
get rankType(){return rankType;},set rankType(value){rankType=value;},
get receiveArenaDiscipline(){return receiveArenaDiscipline;},
get recoverDuelAdmission(){return recoverDuelAdmission;},
get refresh(){return refresh;},
get requireDuelAllowance(){return requireDuelAllowance;},
get requireHumanPlay(){return requireHumanPlay;},
get resumePaymentCheck(){return resumePaymentCheck;},
get rich(){return rich;},
get roomStarting(){return roomStarting;},set roomStarting(value){roomStarting=value;},
get safeUrl(){return safeUrl;},
get save(){return save;},
get scheduleNotificationPolling(){return scheduleNotificationPolling;},
get selectedLesson(){return selectedLesson;},
get serverOffset(){return serverOffset;},set serverOffset(value){serverOffset=value;},
get setMobileMenu(){return setMobileMenu;},
get shownHitSpells(){return shownHitSpells;},
get solutionView(){return solutionView;},
get startPaymentView(){return startPaymentView;},
get stat(){return stat;},
get state(){return state;},set state(value){state=value;},
get stopPaymentWatch(){return stopPaymentWatch;},
get studySolution(){return studySolution;},
get submissionMarkup(){return submissionMarkup;},
get submittedExams(){return submittedExams;},
get submitting(){return submitting;},set submitting(value){submitting=value;},
get syncAccountPages(){return syncAccountPages;},
get tabs(){return tabs;},
get themeSettings(){return themeSettings;},
get tile(){return tile;},
get timeLeft(){return timeLeft;},
get timeText(){return timeText;},
get topicSearch(){return topicSearch;},set topicSearch(value){topicSearch=value;},
get uid(){return uid;},
get unmountParentPlans(){return unmountParentPlans;},set unmountParentPlans(value){unmountParentPlans=value;},
get unreadNotificationCount(){return unreadNotificationCount;},
get updateAccountSection(){return updateAccountSection;},
get updateArenaDiscipline(){return updateArenaDiscipline;},
get updateClassUnread(){return updateClassUnread;},
get updateDuelAllowance(){return updateDuelAllowance;},
get updateMembershipViews(){return updateMembershipViews;},
get updateUnreadBadge(){return updateUnreadBadge;},
get usagePanel(){return usagePanel;},
get views(){return views;},
get visualHp(){return visualHp;},set visualHp(value){visualHp=value;},
get week(){return week;}};
    function feature(name){
        if(featureInstances.has(name))return featureInstances.get(name);
        const factory=browser?window.LearningFeatures?.[name]:require('./learning-modules/'+name+'.js');
        if(!factory)throw new Error('Chưa tải được phần học tập. Em hãy mở lại trang.');
        const instance=factory.create(featureContext);featureInstances.set(name,instance);return instance;
    }
if (browser) {
        window.addEventListener('resize',()=>setMobileMenu(false,false));
        document.addEventListener('keydown',event=>{
            if(!document.body.classList.contains('learning-drawer-open'))return;
            if(event.key==='Escape'){event.preventDefault();setMobileMenu(false);return;}
            if(event.key==='Tab'){
                const drawer=document.querySelector('#learning-navigation');
                const items=[...drawer.querySelectorAll('a[href],button:not([disabled])')].filter(node=>node.getClientRects().length);
                const index=items.indexOf(document.activeElement);
                if(event.shiftKey&&index<=0){event.preventDefault();items.at(-1)?.focus();}
                else if(!event.shiftKey&&index===items.length-1){event.preventDefault();items[0]?.focus();}
            }
        });
        document.addEventListener('visibilitychange',() => {
            if(document.hidden){pausePaymentCheck();if(live&&currentBattle?.mode==='bot'){botLeaseReady=false;window.GameSession?.unwatch();}}else resumePaymentCheck();
            if (document.hidden) {recordActivity();clearTimeout(notificationPollTimer);notificationPollTimer=null;}
            else if (learnerBackgroundAllowed()&&document.body.classList.contains('learning-mode') && host.progress?.name) {activityStarted = Date.now();resumeArena();refreshNotificationSummary({focus:true});}
        });
        window.addEventListener('pagehide',recordActivity);
        window.addEventListener('beforeunload',event=>{if(learnerBackgroundAllowed()&&(examDrafts.size||draftSaving)){event.preventDefault();event.returnValue='';}});
        window.addEventListener('pagehide',pausePaymentCheck);
        window.addEventListener('pageshow',resumeArena);
        window.addEventListener('pageshow',resumePaymentCheck);
        window.addEventListener('focus',resumeArena);
        window.addEventListener('focus',()=>refreshNotificationSummary({focus:true}));
        window.addEventListener('focus',resumePaymentCheck);
        window.addEventListener('online',()=>refreshNotificationSummary({focus:true}));
        window.addEventListener('online',resumePaymentCheck);
        window.addEventListener('offline',pausePaymentCheck);
        window.addEventListener('offline',()=>{clearTimeout(notificationPollTimer);notificationPollTimer=null;});
        window.addEventListener('storage',event => {
            if (event.key === storageKey && currentRoute) load();
        });
    }

    return {routes,configure,render,mount,unmount,setBirthYear,avatar,premiumLibrary,loadPremiumLibrary};
})();

if (typeof module !== 'undefined' && module.exports) module.exports = LearningApp;
