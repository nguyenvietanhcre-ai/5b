'use strict';
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
    const nicknames = browser ? NicknamePolicy : require('./nickname-policy.js');
    const live = browser && typeof PlatformAPI !== 'undefined' && PlatformAPI.enabled;
    const content = browser ? LearningContent : require('./learning-content.js');
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
    const navigation = [
        ['dashboard','Tổng quan','home'], ['weekly','Học online','book'],
        ['exams','Luyện tập','file'], ['arena','Đấu trí','zap'],
        ['rank','Xếp hạng','cup'], ['mascot','Linh vật','leaf'],
        ['profile','Tài khoản','users'], ['upgrade','Nâng cấp gói','spark'], ['zoomRegistration','Đăng ký học Zoom','calendar'], ['classroom','Lớp Zoom','video'],
    ];
    const sections = {topics:'weekly',lesson:'weekly',advanced:'weekly',testing:'exams',results:'exams',room:'arena',battle:'arena',battleResult:'arena',payment:'upgrade'};
    const emptyState = () => ({
        birthYear:null, inviteCode:'', invitedBy:'', mascot:'sprout', points:1000,
        completed:{}, exams:{}, battles:{}, activity:{}, lastLesson:'', activeExam:'',
    });
    let state = emptyState();
    let host = {};
    let currentRoute;
    let interval;
    let activityStarted;
    let currentBattle = null;
    let emoteLock = {id:null,until:0,pending:false};
    let octopusFinaleUntil=0,octopusFinishTimer=null;
    let rankType = 'battle';
    let rankPeriod = 'all';
    let lessonRange = 'all';
    let topicSearch = '';
    let arenaMode='quick';
    if(browser)try{const saved=sessionStorage.getItem('5bmath-arena-mode');if(['quick','friends','bot'].includes(saved))arenaMode=saved;}catch{}
    let arenaScope='weekly',arenaDiscipline={availableAt:0,recentAbandons:0,recentStrikes:0,warning:''},arenaDisciplineUntil=0;
    let arenaPreflight=null;
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
        dog:['Chó','arena-art/dog/idle.webp'],
        sprout:['Mầm Sách','mascots.webp',[131,44,379,521],1200,600],
        fox:['Cáo Nâu','mascots.webp',[670,34,443,532],1200,600],
        horse:['Ngựa','arena-art/horse/v1/idle.webp'],
        'cu-meo':['Cú mèo','arena-art/owl/poses.webp',[69,18,210,274],1254,1254],
        dolphin:['Cá heo','arena-art/ca-heo-v1/actions.webp',[32,48,276,221],1278,1230],
        octopus:['Bạch tuộc','arena-art/bach-tuoc-idle.webp'],
        starfish:['Sao biển','arena-art/sao-bien-v1/idle.webp'],
        bee:['Ong','arena-art/bee/poses.webp',[29,32,260,255],1254,1254],
        butterfly:['Bướm','arena-art/butterfly-poses.webp',[15,21,284,249],1254,1254],
        crab:['Cua biển','arena-art/cua-bien-poses.webp',[66,82,202,172],1247,1261],
        'ca-map':['Cá mập','arena-art/shark/idle.webp'],
        tiger:['Hổ','arena-art/ho-v1/reactions.webp',[52,959,220,283],1254,1254],
        sparrow:['Chim sẻ','arena-art/chim-se/idle.webp'],
        lion:['Sư tử','arena-art/lion-idle.webp'],
        eagle:['Đại bàng','arena-art/eagle/states.webp',[79,61,172,225],1254,1254],
        voi:['Voi','arena-art/voi-reactions.webp',[76,21,284,227],1536,1024],
        rabbit:['Thỏ','arena-art/tho-idle.webp'],
        cat:['Mèo','arena-art/meo-neutral.webp'],
        gau:['Gấu','arena-art/gau-idle.webp'],
    };
    function avatar(pet = state.mascot) {
        const code = Object.hasOwn(mascotAvatars,pet) ? pet : 'sprout';
        const [label,source,box,width,height] = mascotAvatars[code];
        const picture = box
            ? `<svg viewBox="0 0 ${box[2]} ${box[3]}" aria-hidden="true" focusable="false"><svg width="${box[2]}" height="${box[3]}" viewBox="${box.join(' ')}" overflow="hidden"><image href="${source}" width="${width}" height="${height}"/></svg></svg>`
            : `<img src="${source}" width="34" height="34" alt="">`;
        return `<span class="avatar mascot-avatar" data-mascot="${code}" role="img" aria-label="Linh vật ${escape(label)}">${picture}</span>`;
    }
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
    function art(pet,label='',animated=false) {
        if(animated)return animatedArt(pet,label);
        const code=Object.hasOwn(mascotAvatars,pet)?pet:'sprout';
        const [,source,box,width,height]=mascotAvatars[code];
        const attributes=label?'role="img" aria-label="'+escape(label)+'"':'aria-hidden="true"';
        return box
            ? '<svg class="mascot-art '+code+'" style="background:none;height:auto" viewBox="0 0 '+box[2]+' '+box[3]+'" '+attributes+'><svg width="'+box[2]+'" height="'+box[3]+'" viewBox="'+box.join(' ')+'" overflow="hidden"><image href="'+source+'" width="'+width+'" height="'+height+'"/></svg></svg>'
            : '<img class="mascot-art '+code+'" style="background:none;height:auto" src="'+source+'" width="256" height="256" alt="'+escape(label)+'" loading="lazy">';
    }
    const scenery = [
        ['01-forest-clearing','Rừng xanh'], ['02-stream','Bên suối'],
        ['03-riverbank','Bờ sông'], ['04-mountains','Núi non'],
        ['05-bamboo','Rừng trúc'], ['06-waterfall','Thác nước'],
        ['07-lake','Hồ bình minh'], ['08-autumn','Rừng mùa thu'],
        ['09-meadow','Đồng cỏ hoa'], ['10-coast','Vịnh biển'],
    ];
    const artSeed = value => [...String(value)].reduce((sum,c)=>((sum*31)+c.charCodeAt(0))>>>0,0);
    const battleScenery = battle => scenery[artSeed(battle.id)%scenery.length];
    const battlePet = (pet,label,mood='idle') => `<span class="pet-turn face-${pet}"><span class="battle-pet ${pet}" data-mood="${mood}" role="img" aria-label="${escape(label)}">${pet==='gau'?`${art(pet,'',true)}<canvas data-bear data-mode="${mood==='lose'?'defeat':mood}" width="512" height="512" aria-hidden="true"></canvas>`:art(pet,'',true)+'<span class="motion-sprite" aria-hidden="true"></span>'}</span></span>`;
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
    const button = (label, action, kind = 'outline', symbol = '', extra = '') => `<button class="btn ${kind}" type="button" data-learning="${action}" ${extra}>${symbol ? icon(symbol,17) : ''}${escape(label)}</button>`;
    const heading = title => `<div class="section-head"><h2>${escape(title)}</h2></div>`;
    const intro = (title, copy, right = '') => `<header class="intro"><div><h1>${escape(title)}</h1><p>${escape(copy)}</p></div>${right}</header>`;
    const back = (label, route) => `<a class="back-link" href="${href(route)}">${icon('back',17)} ${escape(label)}</a>`;
    const meter = (value, label) => `<div class="meter" role="progressbar" aria-label="${escape(label)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${value}"><span style="--value:${value}%"></span></div>`;
    const stat = (symbol, value, label, color = '') => `<div class="stat card-pad">${tile(symbol,color)}<div><strong>${escape(value)}</strong><small>${escape(label)}</small></div></div>`;
    const field = (label, id, options, value = '') => `<label class="field"><span>${escape(label)}</span><select id="${id}">${options.map(([key,title]) => `<option value="${escape(key)}" ${String(value) === String(key) ? 'selected' : ''}>${escape(title)}</option>`).join('')}</select></label>`;
    const tabs = selected => `<nav class="tabs" aria-label="Cách học">${[['weekly','Theo tuần','calendar'],['topics','Chuyên đề','grid']].map(([route,title,symbol]) => `<a href="${href(route)}" ${selected === route ? 'aria-current="page"' : ''}>${icon(symbol,17)} ${title}</a>`).join('')}</nav>`;
    const notice = text => `<p class="learning-notice">${escape(text)}</p>`;
    const lessonList = () => live ? PlatformAPI.snapshot.lessons || [] : content.lessons(grade());
    const selectedLesson = () => lessonList().find(lesson => lesson.id === query('id')) || lessonList()[0];
    const submittedExams = () => Object.values(state.exams).filter(exam => exam.submittedAt);
    const level = () => Math.floor((state.points - 1000) / 20) + 1;
    const petName = () => (mascotAvatars[state.mascot] || mascotAvatars.sprout)[0];

    function load() {
        if(live)return;
        try {
            const saved = JSON.parse(localStorage.getItem(storageKey));
            if (saved && typeof saved === 'object' && saved.version === 1) state = {...emptyState(),...saved};
        } catch { state = emptyState(); }
        for (const property of ['completed','exams','battles','activity']) {
            if (!state[property] || typeof state[property] !== 'object' || Array.isArray(state[property])) state[property] = {};
        }
        if (!Object.hasOwn(mascotAvatars,state.mascot)) state.mascot = 'sprout';
        state.points = Math.max(1000, Number(state.points) || 1000);
        if (!Number.isInteger(state.birthYear)) state.birthYear = null;
    }

    function save() {
        if(live)return;
        state.version = 1;
        try { localStorage.setItem(storageKey,JSON.stringify(state)); }
        catch { host.toast('Bộ nhớ trình duyệt đã đầy hoặc đang bị chặn. Em hãy giữ trang đang mở để tiếp tục.'); }
    }

    function configure(options) {
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
    const rich = (blocks,assets=[]) => {
        if(!browser || typeof appendRichContent !== 'function')return escape(blocks.map(block=>block.text || block.latex || '').join(' '));
        const element=document.createElement('div');
        appendRichContent(element,blocks,assets);
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

    function homeworkPanel() {
        return `<details class="card card-pad"><summary>Phiếu luyện tập mẫu · Khối 5</summary><p>Phiếu luyện tập tự biên soạn để tham khảo. Nộp bài cho thầy cô ở đúng bài tập của buổi học phía trên.</p>${button('Tải phiếu bài tập','download-material','outline')}</details>`;
    }

    function lessonVideoUrl(lesson) {
        try {
            const url=new URL(lesson.videoRef||lesson.video_ref||'');
            return ['https:','http:'].includes(url.protocol)&&!url.username&&!url.password?url.href:'';
        } catch {return '';}
    }
    function lessonVideo(lesson) {
        const url=lessonVideoUrl(lesson);
        if(!url)return '<div class="video-art"><div class="formula">'+escape(lesson.symbol||'Toán')+'</div><p>Video bài giảng đang được chuẩn bị.</p></div>';
        const parsed=new URL(url),direct=/\.(mp4|webm|ogv|ogg)$/i.test(parsed.pathname);
        return '<div class="lesson-video">'+(direct?'<video controls preload="none" playsinline src="'+escape(url)+'" aria-label="Video bài giảng '+escape(lesson.title)+'"></video>':'')+'<a class="btn outline" href="'+escape(url)+'" target="_blank" rel="noopener noreferrer">Mở video bài giảng ↗</a></div>';
    }
    function lessonExample(example) {
        if(!example||typeof example.text!=='string'||!example.text.trim())return '<p class="learning-notice">Ví dụ đang được biên soạn.</p>';
        const steps=Array.isArray(example.steps)?example.steps.filter(step=>typeof step==='string'):[];
        return '<p>'+escape(example.text)+'</p>'+(steps.length?'<ol>'+steps.map(step=>'<li>'+escape(step)+'</li>').join('')+'</ol>':'')+(example.thinking?'<details class="hint"><summary>Hướng dẫn tư duy</summary><p>'+escape(example.thinking)+'</p></details>':'');
    }

    const views = {
        dashboard() {
            const lesson = lessonList().find(item => item.id === state.lastLesson) || lessonList()[0];
            const learned = Object.values(state.completed).filter(item => item.grade === grade()).length;
            return `<div class="garden-dashboard"><section class="hero-app garden-welcome"><div class="hero-copy"><div class="garden-welcome-kicker">${badge('GÓC HỌC TẬP','light')}<span>Chào ${escape(name())}! · Khối ${grade()} · Tuần ${week()}</span></div><h1 class="garden-welcome-heading">Mỗi ngày một<br><span class="garden-heading-emphasis">mầm tri thức</span></h1><p class="garden-welcome-description">Cùng khám phá <strong>${escape(lesson.title)}</strong>.</p><div class="garden-welcome-actions">${link('Học tiếp','lesson','orange','arrow',{id:lesson.id})}${link('Xem bài học','weekly','outline','')}</div></div><div class="hero-art">${art('sprout','Mầm Sách đang đọc sách')}<span class="orbit" aria-hidden="true">✦</span></div></section>
            <div class="grid3 stats garden-stats">${stat('book',learned + ' bài','Đã học')}${stat('file',submittedExams().length + ' đề','Đã hoàn thành','peach')}${stat('zap',content.format(state.points) + ' điểm','Kinh nghiệm linh vật','sand')}</div>
            <div class="section-head garden-activities-heading"><h2>Hôm nay em muốn làm gì?</h2></div><div class="grid3 garden-shortcuts">${[['book','Học online','Bài giảng theo tuần và chuyên đề.','weekly','sage'],['file','Luyện tập','Làm đề ngẫu nhiên và xem lời giải.','exams','peach'],['zap','Đấu trí','Luyện phản xạ toán học cùng linh vật.','arena','sand']].map(([symbol,title,copy,route,color]) => `<a class="card card-pad shortcut garden-shortcut" href="${href(route)}">${gardenActivityArt(symbol)}<span class="garden-classic-icon">${tile(symbol,color)}</span><h3>${title}</h3><p>${copy}</p><span class="inline-arrow">${icon('arrow')}</span></a>`).join('')}</div>
            <aside class="garden-tip"><strong class="garden-tip-label">${icon('leaf',23)}Mẹo học tốt</strong><p class="garden-tip-copy">Đọc kỹ đề, làm <mark>từng bước.</mark></p></aside></div>`;
        },

        weekly() {
            const lessons=lessonList();
            const filtered=lessons.filter(l=>l.week<=week() && (lessonRange==='all'||(lessonRange==='current'?l.week<=week():!state.completed[l.id]))).sort((a,b)=>b.week-a.week);
            const upcoming=lessons.filter(l=>l.week===week()+1).slice(0,3);
            return `${intro('Học online',live?'Học liệu tự biên soạn, sắp xếp từ tuần gần nhất.':'Demo ngoại tuyến · Học liệu mẫu tự biên soạn, chỉ lưu trên trình duyệt này.',badge('Khối '+grade(),'sage'))}<div class="toolbar">${tabs('weekly')}${field('Hiển thị','learning-range',[['all','Tất cả bài mẫu'],['current','Đến tuần hiện tại'],['unfinished','Bài chưa học']],lessonRange)}</div>
            ${heading('Bài giảng theo tuần')}<div class="card list">${filtered.map(lesson=>lessonRow(lesson)).join('')||'<p class="card-pad">Chưa có bài trong bộ lọc này.</p>'}</div>
            ${heading('Khám phá tuần sau')}<div class="grid3">${upcoming.map(l=>`<a class="card card-pad" href="${href('lesson',{id:l.id})}">${badge('HỌC TRƯỚC','peach')}<h3>Tuần ${l.week}: ${escape(l.title)}</h3><p>${escape(l.description)}</p></a>`).join('')||'<p>Ba bài học tuần sau đang được biên soạn.</p>'}</div>`;
        },

        topics() {
            const lessons=[...new Map(lessonList().map(l=>[l.topic,l])).values()];
            return `${intro('Học online','Chọn một chuyên đề để đọc lý thuyết và tự luyện.',badge('Khối '+grade(),'sage'))}<div class="toolbar">${tabs('topics')}<label class="search">${icon('search',17)}<input id="topic-search" type="search" value="${escape(topicSearch)}" placeholder="Tìm chuyên đề" aria-label="Tìm chuyên đề"></label></div><p id="topic-count" role="status"></p>
            <div class="grid3 topic-results">${lessons.map((lesson,index)=>`<a data-topic-title="${escape(lesson.title.toLocaleLowerCase('vi'))}" class="card topic" href="${href('advanced',{id:lesson.id})}"><div class="topic-art ${index%2?'sage':'peach'}" aria-hidden="true">${escape(lesson.symbol)}</div><div class="card-pad"><h3>${escape(lesson.title)}</h3><p>${escape(lesson.description)}</p><small>Lý thuyết · Ví dụ · Luyện tập</small></div></a>`).join('')}</div><p id="topic-empty" hidden>Chưa tìm thấy chuyên đề phù hợp.</p>`;
        },

        lesson(advanced = false) {
            const lesson = selectedLesson();
            const example = live ? lesson.example : content.problem(grade(),lesson.topic,1,0);
            const isDone = Boolean(state.completed[lesson.id]);
            return `${back(advanced ? 'Chuyên đề' : 'Học online',advanced ? 'topics' : 'weekly')}${intro(lesson.title,'Khối ' + grade() + ' · ' + (advanced ? 'Chuyên đề' : 'Tuần ' + lesson.week),badge('Học liệu tự biên soạn','peach'))}
            <div class="grid-wide"><article class="card video-card">${lessonVideo(lesson)}<div class="card-pad"><h2>Nhớ quy tắc</h2>${live && lesson.body ? rich(lesson.body,lesson.assets || []) : '<p>'+escape(lesson.theory)+'</p>'}<h3>Ví dụ</h3>${lessonExample(example)}</div></article>
            <aside class="card card-pad self-start"><h2>Trong bài này</h2><div class="steps"><div>${tile('book')}<span><b>Lý thuyết và ví dụ</b><small>Đọc và thử giải lại</small></span></div><div>${tile('target','peach')}<span><b>Luyện tập</b><small>3 câu theo chuyên đề</small></span></div></div>${button(isDone ? 'Đã học xong' : 'Đánh dấu đã học','complete',isDone ? 'outline' : 'dark','check')}${button('Luyện 3 câu','practice','outline','target')}${isPaid()?button('Tải tài liệu','download-material','outline'):link('Mở quyền tải tài liệu','upgrade','outline','lock')}${notice(lessonVideoUrl(lesson)?'Đọc bài và xem video để ôn lại từng bước.':'Video đang chờ bản quay. Em có thể đọc bài học tại đây.')}</aside></div>`;
        },

        exams() {
            const history=submittedExams().sort((a,b)=>b.submittedAt.localeCompare(a.submittedAt));
            const active=state.exams[state.activeExam];
            return `${intro('Luyện tập','Chọn nội dung, làm đề và xem lại lời giải.',badge('Khối '+grade(),'sage'))}
            ${active&&!active.submittedAt?`<section class="card card-pad"><h2>Tiếp tục đề đang làm</h2><p>${escape(active.code)}</p>${link('Làm tiếp','testing','dark','arrow',{id:active.id})}</section>`:''}
            <div class="grid3 exam-types"><section class="card card-pad">${tile('target')}<h2>Ôn theo nội dung</h2><p>Luyện tập theo chương trình trên lớp hoặc theo chuyên đề nâng cao</p>${usagePanel('content')}${field('Phạm vi','exam-scope',[['weekly','Theo chương trình học trên lớp'],['topic','Chuyên đề nâng cao']])}<label class="field"><span>Nội dung · Tìm kiếm</span><input id="exam-content-search" type="search" placeholder="Tìm tuần hoặc nội dung" aria-label="Tìm nội dung luyện tập"></label><label class="field"><span>Nội dung</span><select id="exam-topic" size="5" aria-label="Nội dung luyện tập">${examOptions('weekly')}</select></label>${canUse('content')?button('Tạo đề theo nội dung','create-topic','dark','arrow'):link('Nâng cấp gói','upgrade')}</section>
            <section class="card card-pad">${tile('file','peach')}<h2>Đề tổng hợp</h2><p>Thi thử với mẫu đề thi cấp 2 CLC trên cả nước</p>${usagePanel('combined')}${field('Độ khó','exam-difficulty',content.levels.slice(0,3).map((label,index)=>[index,label]))}${canUse('combined')?button('Tạo đề ngẫu nhiên','create-exam','dark','arrow'):link('Nâng cấp gói','upgrade')}<small>Đề luyện mẫu tự biên soạn.</small></section>
            <section class="card card-pad"><div class="split">${tile('lock','sand')}${badge('Chỉ dành cho khối 5','peach')}</div><h2>Đề theo trường</h2><p>Đề theo mẫu chuẩn của các trường cấp 2 CLC trên địa bàn Hà Nội. Phù hợp với học sinh có mục tiêu trường cụ thể hoặc các bạn HSG trên cả nước muốn thử sức.</p>${badge(isPaid()?'Đã mở khóa · VIP / SVip':'Dành cho VIP','sand')}${field('Trường','exam-school',[['cau-giay','THCS Cầu Giấy'],['ngoai-ngu','THCS Ngoại ngữ'],['ntt','Nguyễn Tất Thành']])}${isPaid()&&grade()===5?button('Luyện đề theo trường','create-school','dark'):isPaid()?notice('Chức năng dành cho học sinh khối 5.'):link('Nâng cấp gói','upgrade','outline','lock')}<small>Hiện dùng ngân hàng mẫu tự biên soạn; cấu trúc chuẩn theo từng trường đang được biên tập, chưa phải đề chính thức.</small></section></div>
            ${heading('Đề đã làm')}<div class="card list">${history.map(exam=>`<a class="list-row" href="${href('results',{id:exam.id})}">${tile('file','peach')}<div><strong>${escape(exam.title)}</strong><small>${escape(exam.code)} · ${new Date(exam.submittedAt).toLocaleDateString('vi-VN')}</small></div>${badge(exam.score+'/10','sage')}${icon('chevron',17)}</a>`).join('')||'<p class="card-pad">Em chưa hoàn thành đề nào.</p>'}</div>`;
        },

        testing() {
            const exam = getExam();
            if (!exam) return intro('Làm đề','Chọn một đề để bắt đầu.') + link('Chọn cách luyện','exams');
            if (exam.submittedAt) return views.results();
            const index = Math.min(exam.index || 0,exam.questions.length - 1);
            const question = exam.questions[index];
            const count = exam.questions.filter(item => String(exam.answers[item.id] || '').trim()).length;
            return `${back('Thi thử','exams')}${intro(exam.title,'Khối ' + exam.grade + ' · ' + exam.code,`<div class="timer" id="learning-timer">${icon('clock')} ${timeLeft(exam.expiresAt)}</div>`)}
            <div class="grid-wide"><section class="card card-pad question"><div class="split">${badge('Câu ' + (index + 1) + ' / ' + exam.questions.length,'sage')}${badge(question.topicTitle)}</div><div class="question-prompt">${live && question.prompt ? rich(question.prompt,exam.assets) : '<h2>'+escape(question.text)+'</h2>'}</div><div class="answers">${question.options.map((option,optionIndex) => `<label class="answer"><input type="radio" name="learning-answer" value="${escape(option)}" ${exam.answers[question.id] === option ? 'checked' : ''}><b>${'ABCD'[optionIndex]}</b>${escape(typeof question.answer === 'number' ? content.format(Number(option)) : option)}</label>`).join('')}</div><div class="split wrap-row">${button('Câu trước','previous','outline','back',index === 0 ? 'disabled' : '')}${button('Câu tiếp theo','next','dark','arrow',index === exam.questions.length - 1 ? 'disabled' : '')}</div></section>
            <aside class="card card-pad self-start"><h2>Phiếu làm bài</h2><p id="learning-answered">${count} / ${exam.questions.length} câu đã trả lời</p><div class="question-grid">${exam.questions.map((item,n) => `<button type="button" data-question="${n}" class="${n === index ? 'current' : exam.answers[item.id] ? 'done' : ''}" aria-label="Câu ${n + 1}">${n + 1}</button>`).join('')}</div>${button('Nộp bài','submit-exam','dark','check')}</aside></div>`;
        },

        results() {
            const exam = getExam();
            if (!exam?.submittedAt) return intro('Kết quả thi thử','Chưa có kết quả cho đề này.') + link('Về thi thử','exams');
            if (exam.legacy) {
                return `${back('Thi thử','exams')}${intro('Kết quả đã lưu',exam.title + ' · ' + new Date(exam.submittedAt).toLocaleDateString('vi-VN'))}<section class="card card-pad"><h2>${exam.score} / 10 điểm</h2><p>Bản ghi trước đây lưu điểm và ngày làm. Em có thể xem lại đề mẫu và lời giải ở trang thi thử ban đầu.</p><a class="btn outline" href="${browser && location.protocol === 'file:' ? '#exam' : 'de-thi-thu-toan-vao-lop-6/'}">Mở đề mẫu ban đầu</a></section>`;
            }
            return `${back('Thi thử','exams')}${intro('Kết quả thi thử',exam.title + ' · ' + exam.code)}<section class="result-band sage"><div class="score-circle"><strong>${exam.score}<span>/10</span></strong><small>Điểm của em</small></div><div><h2>Đã chấm xong!</h2><p>${exam.correct} / ${exam.questions.length} câu đúng · Thời gian ${timeText(exam.duration)}</p>${link('Tạo đề khác','exams')}</div></section>${heading('Lời giải theo câu')}
            <div class="solution-list">${exam.questions.map((question,index) => `<article class="card card-pad solution"><div class="split">${badge('Câu ' + (index + 1) + ' · ' + question.topicTitle,'sage')}${badge(isCorrect(question,exam.answers[question.id]) ? 'Trả lời đúng' : 'Cần xem lại',isCorrect(question,exam.answers[question.id]) ? 'sage' : 'peach')}</div><div>${live && question.prompt ? rich(question.prompt,exam.assets) : '<h3>'+escape(question.text)+'</h3>'}</div><p>Em chọn ${escape(exam.answers[question.id] ?? 'chưa trả lời')} · Đáp án ${escape(question.answer)}</p><div class="solution-grid"><div><b>Hướng dẫn tư duy</b><p>${escape(question.thinking)}</p></div><div><b>Lời giải từng bước</b>${live && question.solution ? rich(question.solution,exam.assets) : '<ol>'+question.steps.map(step => '<li>'+escape(step)+'</li>').join('')+'</ol>'}</div></div></article>`).join('')}</div>`;
        },

        arena() {
            const controls=[['quick','zap','Đấu nhanh'],['friends','users','Với bạn'],['bot','bot','Với máy']];
            return `${intro('Đấu trí toán học','Chọn cách chơi và đồng hành cùng linh vật của em.',audioButton())}
            <div class="arena-lobby"><section class="card card-pad arena-player"><a href="${href('mascot')}" class="arena-player-pet">${art(state.mascot)}<div><strong>${escape(petRank(level()))}</strong><small>Cấp ${level()} · ${content.format(state.points)} kinh nghiệm</small></div></a><div class="arena-player-usage" id="arena-mode-usage">${usagePanel(arenaMode==='bot'?'bot':'human')}</div>${meter((state.points-1000)%20*5,'Tiến độ linh vật')}<small>Còn ${20-(state.points-1000)%20} kinh nghiệm đến cấp ${level()+1}</small></section>
            ${disciplinePanel()}<div class="arena-modes" role="tablist" aria-label="Chế độ đấu trí">${controls.map(([key,symbol,label])=>`<button type="button" role="tab" id="arena-tab-${key}" data-arena-mode="${key}" aria-controls="arena-panel-${key}" aria-selected="${arenaMode===key}" tabindex="${arenaMode===key?'0':'-1'}" class="${arenaMode===key?'selected':''}">${icon(symbol,25)}<span>${label}</span></button>`).join('')}</div>
            <section class="arena-mode-panel" id="arena-panel-quick" role="tabpanel" aria-labelledby="arena-tab-quick" ${arenaMode==='quick'?'':'hidden'}>
              <h2 class="arena-panel-title">Tìm trận nhanh</h2><button type="button" class="arena-action arena-action-quick" data-human-play data-human-quota="true" data-learning="quick-match" ${canPlayHuman()?'':'disabled'}>${icon('search',30)}<span><strong>Tìm đối thủ</strong><small>Ghép với bạn cùng lớp ${grade()} hoặc mở phòng công khai</small></span></button>
              <div class="section-head arena-rooms-heading"><h3>Phòng đang mở</h3>${badge('Lớp '+grade(),'sage')}</div><section class="card card-pad" id="public-rooms" aria-live="polite">Đang tìm phòng…</section>
            </section>
            <section class="arena-mode-panel" id="arena-panel-friends" role="tabpanel" aria-labelledby="arena-tab-friends" ${arenaMode==='friends'?'':'hidden'}>
              <h2 class="arena-panel-title">Đấu với bạn</h2><button type="button" class="arena-action arena-action-friends" data-human-play data-human-quota="true" data-learning="create-room" ${canPlayHuman()?'':'disabled'}>${art('sprout')}<span><strong>Tạo phòng đấu</strong><small>Mời bạn bằng mã hoặc mở phòng cho tất cả</small></span>${icon('plus',24)}</button>
              <section class="card card-pad arena-join"><h3>Có mã phòng?</h3><form id="learning-join-form"><label class="field"><span>Mã phòng hoặc liên kết</span><input id="learning-room-code" placeholder="Nhập mã hoặc dán liên kết" required maxlength="500" autocomplete="off"></label><button class="btn dark" data-human-play data-human-quota="true" type="submit" ${canPlayHuman()?'':'disabled'}>Vào phòng</button></form><small>Dán liên kết bạn gửi cũng được. Nội dung của trận do chủ phòng chọn.</small></section>
            </section>
            <section class="arena-mode-panel" id="arena-panel-bot" role="tabpanel" aria-labelledby="arena-tab-bot" ${arenaMode==='bot'?'':'hidden'}>
              <h2 class="arena-panel-title">Đấu với máy</h2><p class="arena-bot-note">Demo tự biên soạn · Mức độ minh họa · Không tính kinh nghiệm</p><input type="hidden" id="bot-level" value="0">
              <div class="arena-bots">${[['0','Dễ · Tập sự','Luyện nhẹ nhàng, làm quen nhịp đấu','sprout'],['1','Trung bình','Cùng thử sức và rèn phản xạ','fox'],['2','Khó · Thử thách','Tập trung suy nghĩ, sẵn sàng chinh phục','sprout']].map(([value,label,copy,pet])=>`<button type="button" class="arena-action arena-bot arena-bot-${value}" data-learning="start-bot" data-bot-level="${value}" ${canUse('bot')?'':'disabled'}>${art(pet)}<span><strong>${label}</strong><small>${copy}</small></span>${icon('play',22)}</button>`).join('')}</div>
            </section>
            <details class="card rules arena-rules" open><summary>${icon('book',23)}<span>Luật đấu trí<small>Nắm luật thật nhanh, sẵn sàng tranh tài!</small></span>${icon('down')}</summary>
              <div class="arena-rules-body"><ul class="arena-rule-grid">
                <li><span class="arena-rule-icon" aria-hidden="true">❤️</span><div><strong>100 máu</strong><p>Mỗi linh vật có <b>100 máu</b> khi bắt đầu trận.</p></div></li>
                <li><span class="arena-rule-icon" aria-hidden="true">⚡</span><div><strong>Đúng và nhanh hơn</strong><p>Trả lời đúng và nhanh hơn đối thủ gây <b>20 sát thương</b>.</p></div></li>
                <li><span class="arena-rule-icon" aria-hidden="true">🏳️</span><div><strong>Khi nào thua?</strong><p>Linh vật hết máu là thua. <b>Rời trận giữa chừng tính là thua.</b></p></div></li>
                <li><span class="arena-rule-icon" aria-hidden="true">🤝</span><div><strong>Khi nào hòa?</strong><p>Hết <b>20 câu hỏi</b> mà hai linh vật vẫn còn máu là hòa.</p></div></li>
              </ul><h3>Kinh nghiệm sau trận</h3><ul class="arena-rule-rewards">
                <li><span aria-hidden="true">🏆</span><strong>Thắng</strong><b>+2</b><small>kinh nghiệm</small></li>
                <li><span aria-hidden="true">🌱</span><strong>Thua</strong><b>−1</b><small>kinh nghiệm</small></li>
                <li><span aria-hidden="true">🤝</span><strong>Hòa</strong><b>0</b><small>kinh nghiệm</small></li>
              </ul></div>
            </details></div>`;
        },

        room() {
            return `${back('Đấu trí','arena')}${intro('Phòng chờ','Chia sẻ mã hoặc chờ một lời thách đấu.',audioButton())}<section class="card card-pad"><h2>Phòng của em</h2><div id="learning-room-status" role="status">Đang kết nối phòng…</div><div id="learning-room-content"></div><div class="actions">${button('Đi học tiếp trong thời gian chờ','minimize-room','dark','book')}${button('Rời phòng','leave-room','outline')}</div></section>`;
        },

        battle() {
            if(!currentBattle)return intro('Trận đấu','Đang kết nối trận đấu…')+link('Về đấu trí','arena');
            const b=currentBattle,q=b.questions[b.index],scene=battleScenery(b),time=battleTime(b);
            return `${intro('Đấu trí toán học','Khối '+b.grade+' · '+(b.mode==='bot'?'Demo với máy · Không tính kinh nghiệm':'Đấu với bạn'),audioButton())}
            <div class="battle-play-layout"><div class="battle-stage illustrated-arena" id="battle-stage" data-scenery="${scene[0]}" style="--arena-background:url('arena-art/${scene[0]}.webp')"><span class="arena-scene-name">${escape(scene[1])}</span><span class="spell-announcement" id="spell-announcement" role="status"></span><div class="fighter" id="fighter-me"><div class="split"><b>${escape(name())}</b><b id="my-hp">${b.hp} / 100 ♥</b></div>${meter(b.hp,'Máu của em')}<div class="pet-body">${battlePet(state.mascot,petName())}<span class="spell-effect" aria-hidden="true"></span><span class="damage" aria-hidden="true">−20 ♥</span><span class="emote-bubble" id="my-emote"></span></div><strong>${escape(petName())}</strong></div><div class="versus">VS</div><div class="energy-beam" aria-hidden="true"></div><div class="fighter right" id="fighter-opponent"><div class="split"><b>${escape(displayName(b.opponent))}</b><b id="opponent-hp">${b.opponentHp} / 100 ♥</b></div>${meter(b.opponentHp,'Máu đối thủ')}<div class="pet-body">${battlePet(b.opponentMascot||(state.mascot==='fox'?'sprout':'fox'),'Linh vật đối thủ')}<span class="spell-effect" aria-hidden="true"></span><span class="damage" aria-hidden="true">−20 ♥</span><span class="emote-bubble" id="opponent-emote"></span></div><strong>${b.mode==='bot'?'Bot luyện tập':'Đối thủ'}</strong></div></div>
            <section class="card card-pad battle-question"><div class="battle-round-content"><div class="battle-question-content"><div class="battle-question-meta">${badge('Câu '+(b.index+1)+' / '+b.questions.length,'sage')}<div class="battle-countdown"><div class="meter battle-time-meter" id="learning-battle-time-meter" role="progressbar" aria-label="Thời gian còn lại" aria-valuemin="0" aria-valuemax="${time.duration}" aria-valuenow="${time.remaining}" aria-valuetext="${timeText(time.remaining)} còn lại"><span style="--value:${time.percent}%"></span></div><span class="battle-time-remaining" id="learning-battle-timer">${timeText(time.remaining)}</span></div></div><h2>${escape(q.text)}</h2><div class="answers four">${q.options.map((option,i)=>`<button type="button" class="answer" data-battle-answer="${escape(option)}" ${b.answer!==null||b.resolved?'disabled':''}><b>${'ABCD'[i]}</b>${escape(typeof q.answer==='number'?content.format(Number(option)):option)}</button>`).join('')}</div><p id="learning-battle-feedback" class="learning-feedback ${b.feedback?.includes('chưa đúng')?'wrong':''}" role="status">${escape(b.feedback||'Em hãy chọn một đáp án.')}</p></div><section class="battle-round-status" aria-labelledby="battle-round-title" hidden><div class="battle-round-message" role="status" aria-atomic="true"><span class="battle-round-symbol" aria-hidden="true"></span><h2 id="battle-round-title"></h2><p id="battle-round-detail"></p></div><p class="battle-round-next" id="battle-round-next"></p><div class="battle-round-countdown" aria-live="off"><strong id="next-round-count"></strong></div><p class="battle-round-wait" id="battle-round-wait"></p></section></div><div class="emote-bar" role="group" aria-label="Gửi lời cổ vũ">${emotes.map(([symbol,text],i)=>`<button type="button" data-emote="${i}" title="${escape(text)}" aria-label="${escape(text)}" ${emoteSeconds(b)>0?'disabled':''}>${symbol}<small>${text}</small></button>`).join('')}</div>${button('Rời trận','leave-battle','outline')}</section></div>`;
        },

        battleResult() {
            let cached=null; if(browser)try{cached=JSON.parse(sessionStorage.getItem('5bmath-last-battle')||'null');}catch{}
            const result=state.battles[query('id')]||(cached?.id===query('id')?cached:null)||Object.values(state.battles).at(-1);
            if(!result)return intro('Kết quả trận','Chưa có trận hoàn thành.')+link('Vào đấu trí','arena');
            const win=result.outcome==='win',lose=result.outcome==='lose',unfinished=result.mode!=='bot'&&result.completed===false;
            const resultTitle=unfinished?(result.reason==='server_restart'?'Trận đấu đã dừng':win?(result.reason==='disconnect'?'Đối thủ đã mất kết nối':'Đối thủ đã rời trận'):result.reason==='disconnect'?'Trận đấu bị gián đoạn':'Em đã rời trận'):(win?'Chúc mừng! Em đã chiến thắng!':lose?'Cố lên, em sẽ tiến bộ mỗi ngày!':result.outcome==='left'?'Đã rời trận':'Hai bạn đã rất cố gắng!');
            const interruptionNote=unfinished?`<p class="battle-interruption-note">${result.reason==='server_restart'?'Trận đấu đã dừng do máy chủ khởi động lại. Em không bị trừ kinh nghiệm.':win?'Em thắng do đối thủ rời trận và không nhận kinh nghiệm.':result.penalty?.disconnectForgiven?'Lần mất kết nối kéo dài đầu tiên trong 24 giờ được bỏ qua; em không bị trừ kinh nghiệm.':result.points<0?'Em bị trừ 1 kinh nghiệm vì bỏ trận.':lose?'Rời trận tính là thua.':'Trận đấu chưa hoàn thành.'} Trận này không cộng vào số trận thắng/thua của cả hai.${result.quotaRefunded?' Em đã được hoàn lượt đấu trong ngày.':''}</p>${result.penalty?.kind&&!result.penalty?.disconnectForgiven?`<p class="battle-penalty-note">${result.penalty.cooldownSeconds?'Em cần nghỉ đấu với người '+Math.ceil(result.penalty.cooldownSeconds/60)+' phút.':'Đây là lần vi phạm đầu tiên trong 24 giờ. Hãy chơi trọn trận cùng bạn nhé.'}</p>`:''}`:'';
            return `${back('Đấu trí','arena')}${intro('Kết quả trận đấu',result.mode==='bot'?'Luyện với máy · Không tính kinh nghiệm':'Đấu với bạn')}
            <section class="result-band sage battle-result ${win&&!unfinished?'victory':lose?'defeat':''}"><div class="score-circle"><strong>${result.points>0?'+':''}${result.points}</strong><small>Kinh nghiệm</small></div><div><h2>${resultTitle}</h2><p>${result.correct} câu đúng · ${Math.max(0,result.rounds-result.correct)} câu chưa đúng · ${result.rounds} câu đã chơi</p>${interruptionNote}${link('Chơi tiếp','arena')}</div><div class="result-pet">${battlePet(state.mascot,petName(),win?'win':lose?'lose':'idle')}</div>${win&&!unfinished?'<div class="confetti" aria-hidden="true">🎊 ✨ 🎉 ✦ 🎊 ✨ 🎉</div>':''}</section>${disciplinePanel()}
            ${heading('Xem lại câu hỏi')}<label class="review-filter"><input type="checkbox" id="review-incorrect"> Chỉ xem câu chưa đúng</label><div class="solution-list">${(result.review||[]).map((item,i)=>`<article class="card card-pad" data-review-correct="${Boolean(item.correct)}"><div class="split"><b>Câu ${i+1}. ${escape(item.text)}</b>${badge(item.correct?'Đúng':'Cần xem lại',item.correct?'sage':'peach')}</div><p>Em chọn: ${escape(item.myAnswer??'Chưa trả lời')}</p><details class="hint"><summary>Xem cách giải</summary><p>Đáp án: ${escape(item.answer)}</p><ol>${(item.steps||[]).map(step=>'<li>'+escape(step)+'</li>').join('')}</ol></details></article>`).join('')||'<p>Chưa có câu hỏi để xem lại.</p>'}</div>`;
        },

        mascot() {
            const history = Object.values(state.battles).filter(battle => battle.mode !== 'bot' && battle.outcome !== 'left' && battle.completed !== false);
            return `${intro('Linh vật của em','Chọn bạn đồng hành và xem kinh nghiệm sau mỗi trận.')}
            <section class="card feature-row sage mascot-feature"><div>${badge('Đang đồng hành · Cấp ' + level(),'white')}<h2>${escape(petName())}</h2><p>${content.format(state.points)} / ${content.format(1000 + level() * 20)} điểm kinh nghiệm để lên cấp ${level() + 1}</p>${meter((state.points - 1000) % 20 * 5,'Tiến độ lên cấp tiếp theo')}<small>Còn ${20 - (state.points - 1000) % 20} điểm để lên cấp tiếp theo.</small></div>${art(state.mascot,petName())}</section>
            <div class="grid3 stats">${stat('cup',history.filter(item => item.outcome === 'win').length + ' trận','Thắng · +2 điểm','sand')}${stat('flag',history.filter(item => item.outcome === 'lose').length + ' trận','Thua · −1 điểm','peach')}${stat('users',history.filter(item => item.outcome === 'draw').length + ' trận','Hòa · 0 điểm')}</div>
            ${heading('Chọn linh vật')}<div class="grid2">${[['dog','Chó'],['horse','Ngựa'],['dolphin','Cá heo'],['octopus','Bạch tuộc'],['starfish','Sao biển'],['bee','Ong'],['butterfly','Bướm'],['ca-map','Cá mập'],['tiger','Hổ'],['crab','Cua biển'],['eagle','Đại bàng'],['sparrow','Chim sẻ'],['sprout','Mầm Sách'],['cu-meo','Cú mèo'],['fox','Cáo Nâu'],['voi','Voi'],['rabbit','Thỏ'],['cat','Mèo'],['gau','Gấu'],['lion','Sư tử']].map(([pet,title]) => `<section class="card card-pad pet-option">${art(pet,title)}<div><h3>${title}</h3>${pet === state.mascot ? badge('Đang chọn','sage') : button('Chọn ' + title,'choose-' + pet,'outline')}</div></section>`).join('')}</div>`;
        },

        rank() { return liveRank(); },

        profile() {
            if(live)return liveProfile();
            const academicGrade = state.birthYear ? content.gradeFor(state.birthYear) : null;
            const invitation = browser ? new URL('./?invite=' + state.inviteCode,document.baseURI).href : '';
            return `${intro('Tài khoản & quyền học','Mỗi tài khoản tương ứng một học sinh.',badge('Tài khoản trải nghiệm','peach'))}${themeSettings()}<div class="grid2"><section class="card card-pad profile-card"><div class="split"><span class="rank-avatar">${escape(initials())}</span>${badge('Thường','sage')}</div><h2>${escape(name())}</h2><p>${academicGrade ? academicGrade >= 1 && academicGrade <= 5 ? 'Khối ' + academicGrade : 'Đã ngoài khối tiểu học · Ôn tập khối ' + grade() : 'Khối 5 minh họa · Chưa nhập năm sinh'}</p>
            ${state.birthYear ? `<label class="field"><span>Năm sinh đã đăng ký</span><input value="${state.birthYear}" readonly aria-readonly="true"></label><p class="learning-notice">Năm sinh cố định sau đăng ký. Liên hệ hỗ trợ nếu cần điều chỉnh khối học.</p>` : `<form id="learning-birth-form"><label class="field"><span>Năm sinh</span><input name="birthYear" type="number" required></label><button class="btn dark" type="submit">Lưu năm sinh</button></form>`}
            ${button('Đổi tên hiển thị','rename','outline')}${button('Thoát tài khoản mẫu','logout','outline')}</section>
            <section class="card card-pad"><h2>Mời bạn học cùng</h2><p>Người mời nhận một tháng VIP khi bạn được mời nâng cấp VIP lần đầu.</p><label class="field"><span>Mã giới thiệu của em</span><input readonly value="${escape(state.inviteCode)}"></label><div class="actions">${button('Sao chép mã','copy-invite','dark','copy')}${button('Sao chép liên kết','copy-invite-link','outline','copy')}</div><label class="field"><span>Liên kết giới thiệu</span><input readonly value="${escape(invitation)}"></label>${state.invitedBy ? '<p>Mã người giới thiệu đã ghi nhận ' + escape(state.invitedBy) + '.</p>' : ''}<p class="learning-notice">Mã và liên kết dùng thử lưu trên thiết bị này. Ghi nhận thanh toán và thưởng VIP đang chờ kết nối tài khoản thật.</p></section></div>
            ${accountRecordsSection('notifications')}${accountRecordsSection('referrals')}
            ${heading('Quyền học')}<div class="grid3">${[['video','Nội bộ','Đầy đủ chức năng trong thời gian theo học lớp Zoom.','sage'],['spark','VIP','Đầy đủ chức năng trong thời hạn gói. Hết hạn chuyển về Thường.','sand'],['leaf','Thường','Truy cập học liệu và chức năng miễn phí được mở.','peach']].map(([symbol,title,copy,color]) => `<section class="card card-pad">${tile(symbol,color)}<h3>${title}</h3><p>${copy}</p></section>`).join('')}</div>`;
        },

        zoomRegistration() { return intro('Đăng ký học Zoom','Cùng thầy cô xây nền tảng Toán và phát triển tư duy.')+'<div class="zoom-svip-plan">'+svipPlan(true)+'</div>'; },
        classroom() { return liveClassroom(); },
        upgrade() { return upgradeView(); },
        payment() { return intro('Thanh toán','Kiểm tra thông tin trước khi chuyển khoản.')+'<section class="card card-pad" id="payment-content" role="status">Đang chuẩn bị thông tin…</section>'; },
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
    function accountPagination(kind,record){
        const pages=Math.max(1,Math.ceil(record.total/5)),label=kind==='notifications'?'thông báo':'lượt giới thiệu';
        return record.total?`<nav class="account-pagination" aria-label="Trang ${label}"><span>${record.total} ${label} · Trang ${record.page} / ${pages}</span><div class="actions"><button type="button" class="btn outline" data-account-page="${kind}" data-page="${record.page-1}" ${record.page<=1||record.loading?'disabled':''}>Trang trước</button><button type="button" class="btn outline" data-account-page="${kind}" data-page="${record.page+1}" ${record.page>=pages||record.loading?'disabled':''}>Trang sau</button></div></nav>`:'';
    }
    function accountRecordsMarkup(kind){
        const record=accountPages[kind],rows=record.rows||[];
        const title=kind==='notifications'?'Thông báo tài khoản':'Lịch sử giới thiệu';
        let body;
        if(kind==='notifications')body=rows.map(item=>`<article class="account-notification ${item.read_at?'is-read':'is-unread'}" data-notification-row="${Number(item.id)}"><div class="account-notification-copy"><div class="account-notification-state">${item.read_at?'Đã đọc':'Chưa đọc'}<time datetime="${escape(item.created_at)}">${escape(accountDate(item.created_at))}</time></div><h3>${escape(notificationTitle(item))}</h3><p class="account-notification-sender"><span>Người gửi</span><strong>${escape(notificationSender(item))}</strong></p></div><button class="btn ${item.read_at?'outline':'dark'}" type="button" data-notification="${Number(item.id)}" aria-label="Xem thông báo: ${escape(notificationTitle(item))}" ${notificationPending===item.id?'disabled':''}>${notificationPending===item.id?'Đang mở…':'Xem'}</button></article>`).join('');
        else body=rows.map(item=>{
            const supported=Boolean(item.support_confirmed_at),granted=item.reward_status==='granted',support=item.reward_status==='customer_service';
            const label=supported||granted?'Đã nhận thưởng':support?'Cần hỗ trợ nhận thưởng':'Chờ nâng cấp VIP';
            return `<article class="account-referral" data-referral-row="${Number(item.id)}"><header><h3>${escape(displayName(item.full_name))}</h3><span class="referral-status ${supported||granted?'is-granted':support?'needs-support':'is-pending'}">${label}</span></header><dl class="referral-dates"><div><dt>Ngày đăng ký</dt><dd>${escape(accountDate(item.registered_at))}</dd></div><div><dt>Nâng cấp VIP lần đầu</dt><dd>${escape(accountDate(item.first_vip_upgraded_at))}</dd></div></dl><div class="referral-reward ${supported||granted?'is-granted':support?'needs-support':''}">${supported?`<strong>Đã được hỗ trợ nhận thưởng</strong><span>Ngày xác nhận hỗ trợ: ${escape(accountDate(item.support_confirmed_at))}</span>`:granted?`<strong>Đã cộng 1 tháng VIP</strong><span>Ngày cộng thưởng: ${escape(accountDate(item.reward_granted_at))}</span><b>VIP sau cộng thưởng đến: ${item.reward_vip_expires_at?escape(accountDate(item.reward_vip_expires_at)):'Chờ cập nhật thời hạn'}</b>`:support?'<strong>Liên hệ chăm sóc khách hàng</strong><span>Đội ngũ 5BMath sẽ hỗ trợ tài khoản nội bộ nhận thưởng.</span>':'<strong>Chưa phát sinh thưởng</strong><span>Thưởng được ghi nhận khi bạn nâng cấp VIP lần đầu.</span>'}</div></article>`;
        }).join('');
        const empty=kind==='notifications'?'Em chưa có thông báo.':'Chưa có tài khoản đăng ký qua mã của em.';
        return `<div class="account-records-head"><h2 data-account-heading tabindex="-1">${title}</h2>${kind==='notifications'?`<span class="account-record-count">${unreadNotificationCount()} chưa đọc</span>`:''}</div><div class="account-records-list">${body||`<p class="account-records-empty">${empty}</p>`}</div><p class="account-records-feedback" id="${kind}-feedback" role="alert" ${record.error?'':'hidden'}>${escape(record.error)}</p>${record.loading?'<p class="account-records-loading" role="status">Đang tải…</p>':''}${accountPagination(kind,record)}`;
    }
    function accountRecordsSection(kind){return `<section class="card card-pad account-records" id="account-${kind}" aria-label="${kind==='notifications'?'Thông báo tài khoản':'Lịch sử giới thiệu'}">${accountRecordsMarkup(kind)}</section>`;}
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
    async function loadAccountPage(kind,page=accountPages[kind].page,{quiet=false}={}){
        if(!live||!PlatformAPI.snapshot.authenticated)return;
        const record=accountPages[kind],owner=accountPageOwner,ticket=++record.request;
        record.loading=!quiet;record.error='';if(!quiet)updateAccountSection(kind);
        try{
            let result=await PlatformAPI.request(kind+'?page='+Math.max(1,page));
            const last=Math.max(1,Math.ceil(result.total/5));
            if(result.page>last)result=await PlatformAPI.request(kind+'?page='+last);
            if(owner!==accountPageOwner||ticket!==record.request)return;
            Object.assign(record,{page:result.page,rows:result.rows,total:result.total,error:''});
            if(kind==='notifications')adoptNotificationSummary(result);
            else if(result.page===1){PlatformAPI.snapshot.account.referrals=result.rows;PlatformAPI.snapshot.account.referralTotal=result.total;}
        }catch(error){if(owner===accountPageOwner&&ticket===record.request){record.error='Chưa tải được '+(kind==='notifications'?'thông báo':'lịch sử giới thiệu')+'. '+error.message;}}
        finally{if(owner===accountPageOwner&&ticket===record.request){record.loading=false;updateAccountSection(kind);}}
    }
    function stopNotificationPolling(){
        notificationPolling=false;notificationLifecycle++;clearTimeout(notificationPollTimer);notificationPollTimer=null;
    }
    function scheduleNotificationPolling(){
        clearTimeout(notificationPollTimer);notificationPollTimer=null;
        if(notificationPolling&&!document.hidden&&navigator.onLine!==false&&PlatformAPI.snapshot.authenticated)notificationPollTimer=setTimeout(()=>refreshNotificationSummary(),30000);
    }
    async function refreshNotificationSummary({focus=false}={}){
        if(!notificationPolling||document.hidden||navigator.onLine===false||!PlatformAPI.snapshot.authenticated)return;
        if(notificationPollBusy||notificationPending!==null||Date.now()-notificationLastRefresh<(focus?3000:15000)){scheduleNotificationPolling();return;}
        const lifecycle=notificationLifecycle,owner=accountPageOwner,version=notificationVersion,classVersion=classUnreadVersion;
        const sessionCsrf=PlatformAPI.snapshot.csrf;
        const knownEntitlementNotices=new Set((PlatformAPI.snapshot.account?.notifications||[]).filter(item=>entitlementNoticeKinds.has(item.kind)).map(item=>item.id));
        const referralPage=accountPages.referrals.page,referralRequest=accountPages.referrals.request;
        notificationPollBusy=true;
        try{
            const [result,classResult,referralResult]=await Promise.all([PlatformAPI.request('notifications?page=1'),isInternal()?PlatformAPI.request('classes/unread').catch(()=>null):Promise.resolve(null),currentRoute==='profile'&&!accountPages.referrals.loading?PlatformAPI.request('referrals?page='+referralPage).catch(()=>null):Promise.resolve(null)]);
            if(!notificationPolling||lifecycle!==notificationLifecycle||owner!==accountPageOwner||version!==notificationVersion||notificationPending!==null)return;
            if(result.rows.some(item=>entitlementNoticeKinds.has(item.kind)&&!knownEntitlementNotices.has(item.id)))entitlementRefreshPending=true;
            notificationLastRefresh=Date.now();adoptNotificationSummary(result);
            if(classResult&&!classReadBusy&&classVersion===classUnreadVersion)adoptClassUnread(classResult.classroomUnread);
            if(currentRoute==='profile'&&accountPages.notifications.page===1&&!document.querySelector('#modal')?.open)updateAccountSection('notifications');
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
        if(!live||!PlatformAPI.snapshot.authenticated)return;
        notificationPolling=true;updateUnreadBadge();updateClassUnread();refreshNotificationSummary();scheduleNotificationPolling();
    }
    function updateMembershipViews(){
        const account=PlatformAPI.snapshot.account;
        if(!account)return;
        for(const label of document.querySelectorAll('.top-right > .tag,[data-account-membership]'))label.textContent=account.membership;
        for(const expiry of document.querySelectorAll('[data-vip-expiry]'))expiry.textContent=accountDate(account.vipExpiresAt);
    }
    async function readNotification(control){
        if(notificationPending!==null)return;
        const identity=Number(control.dataset.notification),owner=accountPageOwner,lifecycle=notificationLifecycle;
        const selected=accountPages.notifications.rows?.find(item=>item.id===identity);
        notificationPending=identity;notificationVersion++;control.disabled=true;control.textContent='Đang mở…';
        try{
            const result=await PlatformAPI.request('notifications/'+identity+'/read',{});
            if(owner!==accountPageOwner)return;
            syncAccountPages(result);updateUnreadBadge();
            const detail=result.notification||selected;
            await loadAccountPage('notifications',accountPages.notifications.page,{quiet:true});
            if(currentRoute!=='profile'||lifecycle!==notificationLifecycle||!detail)return;
            const dialog=document.querySelector('#modal'),oldLabel=dialog.getAttribute('aria-labelledby');
            host.showModal(`<article class="account-notification-detail"><p class="account-detail-kicker">Thông báo tài khoản</p><h2 class="modal-title" id="account-notification-title">${escape(notificationTitle(detail))}</h2><dl class="notification-detail-meta"><div><dt>Người gửi</dt><dd>${escape(notificationSender(detail))}</dd></div><div><dt>Ngày gửi</dt><dd>${escape(accountDate(detail.created_at))}</dd></div></dl><div class="notification-detail-body">${escape(detail.body||'')}</div><div class="actions"><button class="btn dark" type="button" id="close-notification-detail">Đóng thông báo</button></div></article>`);
            dialog.setAttribute('aria-labelledby','account-notification-title');
            document.querySelector('#close-notification-detail').onclick=()=>dialog.close();
            dialog.addEventListener('close',()=>{if(oldLabel===null)dialog.removeAttribute('aria-labelledby');else dialog.setAttribute('aria-labelledby',oldLabel);const next=document.querySelector(`[data-notification="${identity}"]`)||document.querySelector('#account-notifications [data-account-heading]');next?.focus({preventScroll:true});},{once:true});
            document.querySelector('#close-notification-detail').focus();
        }catch(error){
            accountPages.notifications.error='Chưa mở được thông báo. '+error.message;updateAccountSection('notifications');host.toast(error.message);
        }finally{notificationPending=null;const next=document.querySelector(`[data-notification="${identity}"]`);if(next){next.disabled=false;next.textContent='Xem';}scheduleNotificationPolling();}
    }

    function liveProfile() {
        const account=PlatformAPI.snapshot.account;
        const date=value=>value?new Date(value).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'}):'Chưa phát sinh';
        const invitation=new URL('./?invite='+state.inviteCode,document.baseURI).href;
        return `${intro('Tài khoản & quyền học','Thông tin được lưu tại máy chủ.',badge(account.membership,'sage').replace('<span','<span data-account-membership'))}${themeSettings()}<div class="grid2"><section class="card card-pad"><h2>${escape(name())}</h2><p>Tên đăng nhập: ${escape(account.login)} · Khối ${grade()}</p><label class="field"><span>Năm sinh đã đăng ký</span><input readonly value="${state.birthYear}" aria-readonly="true"></label><p>Năm sinh cố định sau đăng ký. Liên hệ hỗ trợ nếu cần điều chỉnh khối học.</p><p>VIP đến: <span data-vip-expiry>${escape(date(account.vipExpiresAt))}</span></p><div class="actions">${button('Đổi tên hiển thị','rename')}${button('Đăng xuất','logout')}${button('Cập nhật thông báo','refresh-account')}</div></section><section class="card card-pad"><h2>Mời bạn học cùng</h2><p>Nhận một tháng lịch VIP khi tài khoản được mời nâng cấp VIP lần đầu. Thời hạn được cộng dồn; mỗi cặp chỉ nhận thưởng một lần.</p><label class="field"><span>Mã giới thiệu</span><input readonly value="${escape(state.inviteCode)}"></label><label class="field"><span>Liên kết giới thiệu</span><input readonly value="${escape(invitation)}"></label><div class="actions">${button('Sao chép mã','copy-invite','dark','copy')}${button('Sao chép liên kết','copy-invite-link')}</div>${state.invitedBy?'<p>Đăng ký qua mã '+escape(state.invitedBy)+'</p>':''}</section></div>${accountRecordsSection('notifications')}${accountRecordsSection('referrals')}`;
    }

    let rankScope='all';
    function liveRank() {
        return `${intro('Bảng xếp hạng','Cùng học, cùng tiến bộ trên 5BMath.')}<div class="toolbar rank-tools"><div class="tabs">${[['battle','Linh vật'],['activity','Chăm chỉ']].map(([type,title])=>`<button type="button" data-rank="${type}" class="${rankType===type?'selected':''}" aria-pressed="${rankType===type}">${title}</button>`).join('')}</div><div class="actions">${field('Phạm vi','rank-scope',[['all','Tất cả'],['grade','Lớp '+grade()],...(isInternal()?[['class','Lớp Zoom']]:[])],rankScope)}${field('Thời gian','rank-period',[['all','Tất cả'],['day','Hôm nay'],['week','Tuần này'],['month','Tháng này']],rankPeriod)}</div></div><div class="card leaderboard" id="live-rank" role="status">Đang tải bảng xếp hạng…</div>`;
    }
    const medal=n=>n&&n<=3?`<span class="medal medal-${n}" aria-label="Hạng ${n}">${n}</span>`:escape(n??'—');
    async function loadRank() {
        const container=document.querySelector('#live-rank');if(!container)return;
        try{
            const result=live?await PlatformAPI.request('leaderboard?'+new URLSearchParams({kind:rankType,period:rankPeriod,scope:rankScope})):{rows:[]};
            if(!container.isConnected)return;
            container.innerHTML=result.rows.length?`<table><thead><tr><th>Hạng</th>${rankType==='battle'?'<th>Linh vật</th>':''}<th>Học sinh</th><th>Lớp</th><th>${rankType==='activity'?'Giờ học':'Kinh nghiệm'}</th></tr></thead><tbody>${result.rows.map(row=>`<tr class="${row.mine?'mine':''}"><td>${medal(row.rank)}</td>${rankType==='battle'?'<td>'+art(row.mascot)+'</td>':''}<td><strong>${escape(displayName(row.name))}</strong> ${rankType==='battle'?'<small>'+escape(petRank(row.level))+' · Level '+row.level+'</small>':''}</td><td>${escape(row.class)}</td><td><strong>${escape(row.value)}</strong>${rankType==='battle'?'<small>'+row.wins+' thắng / '+row.losses+' thua</small>':''}</td></tr>`).join('')}</tbody></table>`:'<p class="card-pad">Chưa có dữ liệu trong phạm vi này.</p>';
        }catch(error){container.textContent=error.message;}
    }
    let classTab='sessions',classData=null,classFrom='',classTo='',classLoadTicket=0,classUnreadVersion=0,classReadBusy=0,classReadQueue=Promise.resolve();
    function liveClassroom() {
        if(!isInternal())return intro('Lớp Zoom','Lớp học dành cho tài khoản SVip.')+link('Đăng ký học Zoom','zoomRegistration');
        const classes=PlatformAPI.snapshot.account.classes;
        return `${intro('Lớp Zoom','Lịch học và kết quả của lớp em.')}${classes.length?field('Lớp đang học','class-select',classes.map(c=>[c.id,c.name]),query('class')||classes[0].id):''}<section class="card card-pad" id="class-info">${classes.length?'Đang tải lớp học…':'Chưa có lớp được gán. Liên hệ chăm sóc khách hàng để được xếp lớp.'}</section><div class="tabs class-tabs">${[['sessions','Buổi học'],['assignments','Bài tập'],['summary','Tổng kết'],['fees','Học phí']].map(([key,label])=>`<button type="button" data-class-tab="${key}" aria-pressed="${classTab===key}" class="${classTab===key?'selected':''}">${label}${['assignments','fees'].includes(key)?classUnreadBadge(0,key):''}</button>`).join('')}</div><p id="class-read-feedback" class="class-read-feedback" role="status" hidden></p><div id="class-body"></div>`;
    }

    const member=()=>live?PlatformAPI.snapshot.account?.membership||'Free':'Free';
    const isInternal=()=>member()==='SVip';
    const isPaid=()=>member()!=='Free';
    const petRank=n=>n>=10?'Đại thụ':n>=5?'Chồi xanh':'Hạt mầm';
    const emotes=[['👋','Chào bạn!'],['🌟','Bạn giỏi quá!'],['💪','Cố lên nào!'],['👏','Tuyệt vời!'],['🤝','Cùng cố gắng!'],['😊','Vui quá!'],['🤔','Để mình nghĩ!'],['🔥','Hết mình nhé!'],['🍀','Chúc may mắn!'],['❤️','Không bỏ cuộc!']];
    const audioButton=()=>button(typeof ArenaAudio!=='undefined'&&ArenaAudio.muted?'🔇 Nhạc: Tắt':'🎵 Nhạc: Bật','toggle-music','outline');
    const lessonRow=l=>`<a class="list-row" href="${href('lesson',{id:l.id})}">${tile(state.completed[l.id]?'check':'book')}<div><strong>Tuần ${l.week}: ${escape(l.title)}</strong><small>Bài đọc có ví dụ</small></div>${badge(state.completed[l.id]?'Đã học':'Chưa học',state.completed[l.id]?'sage':'')}${icon('chevron',17)}</a>`;
    function quota(category) {
        if(live)return PlatformAPI.snapshot.account?.usage?.[category]||{used:0,limit:1};
        const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Ho_Chi_Minh'}).format(new Date());
        const used=(state.usage||{})[day+'-'+category]||0;
        return {used,limit:{content:1,combined:1,human:3,bot:5}[category]};
    }
    const canUse=category=>isPaid()||quota(category).limit===null||quota(category).used<quota(category).limit;
    const arenaScopeLabel=value=>value==='all'?'Kiến Thức Tổng Hợp':'Chương trình trên lớp';
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
            control.disabled=control.dataset.humanPending==='true'||seconds>0||(control.dataset.humanQuota==='true'&&!canUse('human'));
            if(seconds)control.setAttribute('aria-describedby','arena-discipline');else control.removeAttribute('aria-describedby');
        });
    }
    function receiveArenaDiscipline(result) {
        if(result?.serverNow)serverOffset=result.serverNow-Date.now();
        if(result?.arenaDiscipline)setArenaDiscipline(result.arenaDiscipline,result.serverNow);
        updateArenaDiscipline();
    }
    function requireHumanPlay() {
        if(disciplineSeconds()>0)throw new Error('Em đang tạm nghỉ đấu với người. Có thể đấu lại sau '+timeText(disciplineSeconds())+'.');
    }
    function setArenaScope(value) {
        if(!['weekly','all'].includes(value))return;
        arenaScope=value;try{sessionStorage.setItem('5bmath-arena-scope',value);}catch{}
        const input=document.querySelector('#battle-scope');if(input)input.value=value;
    }
    function openArenaPreflight(kind,settings={},trigger=document.activeElement) {
        const human=kind!=='bot';
        if(human){if(sessionStorage.getItem('5bmath-room')){go('room');return;}requireHumanPlay();}
        if(!canUse(human?'human':'bot'))throw new Error('Em đã hết lượt hôm nay. Hãy vào Nâng cấp gói.');
        if(arenaPreflight)return;
        const dialog=document.querySelector('#modal'),scroll={x:scrollX,y:scrollY},oldLabel=dialog.getAttribute('aria-labelledby'),oldDescription=dialog.getAttribute('aria-describedby');
        const context={dialog,trigger,kind,busy:false,draft:'weekly',botLevel:Math.max(0,Math.min(2,Number(settings.botLevel)||0))};
        const label=kind==='create'?'tạo phòng':kind==='bot'?'luyện với máy':'tìm đối thủ';
        const cleanup=(restoreFocus=true)=>{
            if(arenaPreflight!==context)return;
            arenaPreflight=null;dialog.classList.remove('arena-preflight-modal');document.body.classList.remove('arena-preflight-open');
            dialog.removeEventListener('close',onClose);dialog.removeEventListener('cancel',onCancel);dialog.removeEventListener('keydown',trap);dialog.removeEventListener('click',blockBackdrop,true);
            for(const [attribute,value]of [['aria-labelledby',oldLabel],['aria-describedby',oldDescription]]){if(value===null)dialog.removeAttribute(attribute);else dialog.setAttribute(attribute,value);}
            document.querySelector('#close-modal').disabled=false;
            if(restoreFocus&&trigger?.isConnected){trigger.focus({preventScroll:true});window.scrollTo({left:scroll.x,top:scroll.y,behavior:'instant'});}
        };
        const close=(restoreFocus=true)=>{if(dialog.open)dialog.close();cleanup(restoreFocus);};
        const onClose=()=>cleanup();
        const onCancel=event=>{if(context.busy)event.preventDefault();};
        const blockBackdrop=event=>{if(context.busy&&event.target===dialog){event.preventDefault();event.stopImmediatePropagation();}};
        const trap=event=>{
            if(event.key!=='Tab')return;
            const controls=[...dialog.querySelectorAll('button:not(:disabled),input:not(:disabled),a[href]')].filter(node=>node.getClientRects().length),index=controls.indexOf(document.activeElement);
            if(event.shiftKey&&index<=0){event.preventDefault();controls.at(-1)?.focus();}
            else if(!event.shiftKey&&index===controls.length-1){event.preventDefault();controls[0]?.focus();}
        };
        context.close=close;arenaPreflight=context;
        dialog.classList.add('arena-preflight-modal');document.body.classList.add('arena-preflight-open');
        host.showModal(`<section id="arena-preflight"><div class="arena-preflight-handle" aria-hidden="true"></div><p class="arena-preflight-kicker">Trước khi ${label}</p><div class="arena-preflight-icon">${icon('grid',28)}</div><h2 class="modal-title" id="arena-preflight-title">Sẵn sàng đấu trí?</h2><p id="arena-preflight-copy">Chọn nội dung em muốn thử sức trong trận này.</p><input type="hidden" id="battle-scope" value="${context.draft}"><fieldset class="arena-preflight-scopes"><legend>Chọn nội dung thi đấu</legend><div role="group" aria-label="Chọn nội dung thi đấu">${[['weekly','Chương trình trên lớp'],['all','Kiến Thức Tổng Hợp']].map(([value,title])=>`<button type="button" data-preflight-scope="${value}" aria-pressed="${context.draft===value}"><span aria-hidden="true" class="arena-preflight-dot"></span><span>${title}</span></button>`).join('')}</div></fieldset>${kind==='create'?'<fieldset class="arena-preflight-visibility"><legend>Ai có thể vào phòng?</legend><label><input type="radio" name="arena-visibility" value="private" checked><span>Bạn bè có mã</span></label><label><input type="radio" name="arena-visibility" value="public"><span>Tất cả</span></label></fieldset>':''}<p class="arena-preflight-context"><b>Khối ${grade()}</b> · Tối đa 20 câu${kind==='bot'?' · '+['Máy dễ','Máy trung bình','Máy khó'][context.botLevel]:''}<small>${grade()<=2?'1 phút/câu':grade()<=4?'2 phút/câu':'3 phút/câu · Riêng câu khó: 4 phút'}</small></p><p id="arena-preflight-error" role="alert" hidden></p><button type="button" class="btn dark" id="arena-preflight-confirm" ${human?'data-human-play data-human-quota="true"':''}>Xác nhận & ${label} ${icon('arrow',19)}</button><button type="button" id="arena-preflight-back">Quay lại chọn cách chơi</button></section>`);
        dialog.setAttribute('aria-labelledby','arena-preflight-title');dialog.setAttribute('aria-describedby','arena-preflight-copy');
        dialog.addEventListener('close',onClose);dialog.addEventListener('cancel',onCancel);dialog.addEventListener('keydown',trap);dialog.addEventListener('click',blockBackdrop,true);
        dialog.querySelectorAll('[data-preflight-scope]').forEach(control=>control.onclick=()=>{
            context.draft=control.dataset.preflightScope;dialog.querySelector('#battle-scope').value=context.draft;
            dialog.querySelectorAll('[data-preflight-scope]').forEach(button=>button.setAttribute('aria-pressed',String(button===control)));
        });
        dialog.querySelector('#arena-preflight-back').onclick=()=>close();
        dialog.querySelector('#arena-preflight-confirm').onclick=async event=>{
            if(context.busy)return;
            const confirm=event.currentTarget,errorNode=dialog.querySelector('#arena-preflight-error');
            try{
                if(human)requireHumanPlay();
                if(!canUse(human?'human':'bot'))throw new Error('Em đã hết lượt hôm nay. Hãy vào Nâng cấp gói.');
                context.busy=true;confirm.dataset.humanPending='true';
                dialog.querySelectorAll('button,input').forEach(control=>control.disabled=true);errorNode.hidden=true;
                setArenaScope(context.draft);
                if(kind==='bot')await startBot({scope:context.draft,botLevel:context.botLevel});
                else await enterRoom(kind==='create'?'create':'quick',{...roomSettings(),scope:context.draft,...(kind==='create'?{public:dialog.querySelector('[name="arena-visibility"]:checked').value==='public'}:{})});
                close(false);
            }catch(error){if(arenaPreflight===context){errorNode.textContent=error.message;errorNode.hidden=false;}}
            finally{context.busy=false;delete confirm.dataset.humanPending;if(arenaPreflight===context){dialog.querySelectorAll('button,input').forEach(control=>control.disabled=false);updateArenaDiscipline();}}
        };
        updateArenaDiscipline();dialog.querySelector('[data-preflight-scope="'+context.draft+'"]').focus();
    }
    const usagePanel=category=>{const q=quota(category);return `<p class="usage-note">${q.limit===null?'✦ Không giới hạn':q.used+' / '+q.limit+' lượt hôm nay'+(canUse(category)?'':' · Đã đạt giới hạn')}</p>${!canUse(category)?link('Nâng cấp gói','upgrade','outline','spark'):''}`;};
    function consumeLocal(category) {
        if(!canUse(category))throw new Error('Em đã hết lượt hôm nay. Hãy vào Nâng cấp gói.');
        const day=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Ho_Chi_Minh'}).format(new Date());
        state.usage ||= {};state.usage[day+'-'+category]=(state.usage[day+'-'+category]||0)+1;save();
    }
    function examOptions(scope,search='') {
        const lessons=lessonList(),options=scope==='weekly'?[['','Tổng hợp đến hiện tại'],...Array.from({length:week()},(_,i)=>{
            const list=lessons.filter(l=>l.week===i+1);return ['week-'+(i+1),'Tuần '+(i+1)+' : '+(list.map(l=>l.title).join(' · ')||'Đang biên soạn'),!list.length];
        })]:[...new Map(lessons.map(l=>[l.topic,[l.topic,l.title.replace(/^Ôn tập: /,'')]])).values()];
        return options.filter(([,label])=>!search||label.toLocaleLowerCase('vi').includes(search.toLocaleLowerCase('vi'))).map(([value,label,disabled])=>`<option value="${escape(value)}" ${disabled?'disabled':''}>${escape(label)}</option>`).join('');
    }
    function svipPlan(registration=false) {
        const features=['🌱 Không giới hạn chức năng trên 5bmath.vn','👩‍🏫 Lớp sĩ số nhỏ, giáo viên sát sao','💬 Review từng học sinh sau mỗi buổi học','📝 Mini test mỗi buổi học','🏆 Big test mỗi tháng'];
        return `<section class="card card-pad plan gold">${badge('👑 SVip','gold')}<h2>${registration?'Học Zoom online':'SVip / Học Zoom online'}</h2><strong class="plan-price">${registration?'Học phí: 100k/buổi':'100k/Buổi'}</strong><ul>${features.map(text=>`<li class="plan-highlight">${text}</li>`).join('')}</ul><p class="free-highlight"><mark>MIỄN PHÍ</mark> 1 buổi trao đổi 1-1 với giáo viên mỗi tháng</p>${registration?'<div class="actions"><a class="btn dark" href="dang-ky-kiem-tra-dau-vao/">Đăng ký kiểm tra đầu vào</a><a class="btn outline" href="https://zalo.me/0984763971" target="_blank" rel="noopener noreferrer">Đăng ký tư vấn · Zalo</a><a class="btn outline" href="https://www.facebook.com/5bmath" target="_blank" rel="noopener noreferrer">Đăng ký tư vấn · Facebook</a></div>':'<a class="btn dark" href="https://zalo.me/0984763971" target="_blank" rel="noopener noreferrer">Đăng ký tư vấn</a>'}</section>`;
    }
    function upgradeView() {
        if(isInternal())return intro('Quyền học SVip','Em đang có đầy đủ quyền học trong thời gian theo học.')+link('Về lớp Zoom','classroom');
        const free=['🧩 Ôn theo nội dung hoặc chuyên đề: 1 lần/ngày','📝 Luyện đề tổng hợp: 1 lần/ngày','🎮 Game Đấu trí: 3 trận với người/ngày','🤖 Luyện với máy: 5 trận/ngày','🔒 Luyện đề theo trường: Không','🔒 Tải tài liệu: Không'];
        const vip=['🧩 Ôn nội dung hoặc chuyên đề: Không giới hạn','📝 Luyện đề tổng hợp: Không giới hạn','🎮 Game Đấu trí: Không giới hạn','🏫 Luyện đề theo trường: Không giới hạn','📥 Tải tài liệu: Có'];
        return `${intro('Nâng cấp gói','Chọn cách học phù hợp với em.')}<div class="upgrade-brand"><img src="5bmath-logo.svg" alt="5BMath Gieo Mầm Toán" width="314" height="84"><h2>Hệ thống toán học online 5BMath</h2><p>Ươm mầm tư duy - Khơi nguồn tri thức.</p></div><div class="grid3 plans">${[['Free','Miễn phí','bronze',free],['Vip','100k/tháng','silver',vip]].map(([title,price,style,features])=>`<section class="card card-pad plan ${style}">${badge(style==='silver'?'✦ VIP':'🌱 Free',style)}<h2>${title}</h2><strong class="plan-price">${price}</strong><ul>${features.map(text=>`<li class="${style==='bronze'?'':'plan-highlight'}">${text}</li>`).join('')}</ul>${style==='silver'?link('Nâng cấp','payment','dark','spark'):badge(member()==='Free'?'Gói hiện tại':'Gói miễn phí')}</section>`).join('')}${svipPlan()}</div><section class="card card-pad consultation"><h2>Kiểm tra đầu vào & tư vấn lớp Zoom</h2><p>Đăng ký kiểm tra đầu vào để thầy cô tư vấn lộ trình học phù hợp.</p><div class="actions"><a class="btn dark" href="dang-ky-kiem-tra-dau-vao/">Đăng ký kiểm tra đầu vào</a><a class="btn outline" href="https://www.facebook.com/5bmath" target="_blank" rel="noopener noreferrer">Đăng ký tư vấn · Facebook</a><a class="btn outline" href="https://zalo.me/0984763971" target="_blank" rel="noopener noreferrer">Zalo 0984763971</a></div></section>`;
    }
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
    function trendChart(months) {
        if(!months.length)return '<p>Biểu đồ sẽ xuất hiện khi bài tập được chấm điểm.</p>';
        const x=i=>55+i*(500/Math.max(1,months.length-1)),y=v=>215-v*18;
        return `<figure class="trend-chart"><svg viewBox="0 0 620 270" role="img" aria-label="Điểm trung bình theo tháng"><path d="M40 25V215H590" fill="none" stroke="currentColor"/>${[0,5,10].map(v=>`<text x="10" y="${y(v)+5}">${v}</text><path d="M40 ${y(v)}H590" stroke="#e4e8d8"/>`).join('')}<polyline points="${months.map((m,i)=>x(i)+','+y(m.average)).join(' ')}" fill="none" stroke="var(--green)" stroke-width="4"/>${months.map((m,i)=>`<circle cx="${x(i)}" cy="${y(m.average)}" r="6" fill="var(--orange)"/><text x="${x(i)}" y="${y(m.average)-14}" text-anchor="middle">${m.average}</text><text x="${x(i)}" y="245" text-anchor="middle">${escape(m.month)}</text>`).join('')}</svg><figcaption>Điểm trung bình các bài đã chấm (thang 10)</figcaption></figure>`;
    }
    async function loadClass() {
        const select=document.querySelector('#class-select'),info=document.querySelector('#class-info');
        if(!live||!select||!info)return;
        const identity=select.value,ticket=++classLoadTicket,owner=accountPageOwner;
        if(String(classData?.class.id)!==identity){classData=null;const body=document.querySelector('#class-body');if(body)body.innerHTML='';}
        updateClassUnread();
        try{
            const data=await PlatformAPI.request('classes/'+identity+'?'+new URLSearchParams({from:classFrom,to:classTo}));
            if(!info.isConnected||ticket!==classLoadTicket||owner!==accountPageOwner)return;classData=data;
            info.innerHTML=`<h2>${escape(data.class.name)}</h2><div class="grid2"><p>Học sinh: <strong>${escape(name())}</strong><br>Giáo viên: ${escape(data.class.teacher)}</p><p>Lịch học: ${escape(data.class.schedule||'Chờ cập nhật')}<br>Chương trình: ${escape(data.class.curriculum||'Chờ cập nhật')}</p></div>${safeUrl(data.class.meeting_ref)?`<a class="btn dark" href="${safeUrl(data.class.meeting_ref)}" target="_blank" rel="noopener noreferrer">Vào lớp Zoom</a>`:''}`;
            renderClassBody();
            return data;
        }catch(e){if(info.isConnected&&ticket===classLoadTicket){info.textContent=e.message;classData=null;}}
    }
    async function readClassSection(data,section){
        if(!data||!['assignments','fees'].includes(section))return;
        const through=Number(data.readThrough?.[section])||0;
        if(!through)return;
        const owner=accountPageOwner,feedback=document.querySelector('#class-read-feedback');
        classUnreadVersion++;classReadBusy++;
        if(feedback)feedback.hidden=true;
        const perform=async()=>{
            if(owner!==accountPageOwner)return;
            try{
                const result=await PlatformAPI.request('classes/'+data.class.id+'/read',{section,through});
                if(owner===accountPageOwner)adoptClassUnread(result.classroomUnread);
            }catch(error){
                if(owner===accountPageOwner&&feedback?.isConnected){feedback.textContent='Chưa đánh dấu đã đọc. Em có thể bấm lại mục này. '+error.message;feedback.hidden=false;}
            }
        };
        const operation=classReadQueue.then(perform,perform);classReadQueue=operation;
        try{await operation;}finally{classReadBusy--;classUnreadVersion++;}
    }
    const classFileUrl=value=>/^\/api\/v1\/class-submissions\/\d+\/file$/.test(value||'')?escape(value):'';
    const submissionMarkup=submission=>submission&&classFileUrl(submission.url)?`<a href="${classFileUrl(submission.url)}" target="_blank" rel="noopener noreferrer">Xem bài đã nộp: ${escape(submission.filename)}</a><small>Nộp lúc ${escape(accountDate(submission.submitted_at))}</small>`:'<span>Em chưa nộp bài này.</span>';
    function classAssignmentMarkup(a){
        return `<article class="assignment-row class-assignment" data-assignment="${a.id}"><div class="class-assignment-heading"><div><h3>${escape(a.title)}</h3><small>${escape(a.kind)}</small>${safeUrl(a.document_url)?`<a href="${safeUrl(a.document_url)}" target="_blank" rel="noopener noreferrer">Mở đề bài</a>`:''}</div>${badge(a.score==null?'Chưa có điểm':a.score+'/10','sage')}<button class="btn outline" type="button" data-class-ranking="assignment" data-value="${a.id}">Bảng điểm</button></div><p class="class-personal-comment"><strong>Nhận xét bài làm:</strong> ${escape(a.comment||'Thầy cô chưa nhận xét bài này.')}</p><div class="class-submission-current">${submissionMarkup(a.submission)}</div><form data-class-submit="${a.id}" class="class-submission-form"><label class="field"><span>${a.submission?'Chọn tệp để nộp lại':'Chọn bài làm để nộp'}</span><input name="file" type="file" accept=".jpg,.jpeg,.png,.webp,.pdf" required aria-label="Bài làm ${escape(a.title)}"></label><p>Ảnh JPG, PNG, WebP hoặc PDF, tối đa 10 MB.${a.submission&&a.score!=null?' Nộp lại vẫn giữ điểm và nhận xét hiện tại để thầy cô xem lại.':''}</p><button class="btn dark" type="submit">${a.submission?'Nộp lại bài':'Nộp bài'}</button><p class="class-submit-status" role="status" hidden></p></form></article>`;
    }
    async function submitClassAssignment(form){
        if(form.dataset.pending)return;
        const data=classData,identity=Number(form.dataset.classSubmit),assignment=data?.sessions.flatMap(s=>s.assignments).find(a=>a.id===identity),owner=accountPageOwner;
        if(!assignment)return;
        const control=form.querySelector('button[type="submit"]'),input=form.querySelector('input[type="file"]'),status=form.querySelector('[role="status"]'),file=input.files[0];
        status.hidden=false;
        if(!file){status.textContent='Em hãy chọn bài làm trước khi nộp.';return;}
        const mime=file.type||({'jpg':'image/jpeg','jpeg':'image/jpeg','png':'image/png','webp':'image/webp','pdf':'application/pdf'}[file.name.split('.').pop().toLowerCase()]);
        if(!['image/jpeg','image/png','image/webp','application/pdf'].includes(mime)||!file.size||file.size>10*1024*1024){status.textContent='Chọn ảnh JPG, PNG, WebP hoặc PDF từ 1 byte đến 10 MB.';return;}
        form.dataset.pending='true';control.disabled=true;input.disabled=true;status.textContent='Đang gửi bài đến thầy cô…';
        try{
            const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(String(reader.result).split(',')[1]);reader.onerror=()=>reject(new Error('Chưa đọc được tệp. Em hãy chọn lại.'));reader.readAsDataURL(file);});
            if(owner!==accountPageOwner||!form.isConnected)return;
            const result=await PlatformAPI.request('classes/'+data.class.id+'/assignments/'+identity+'/submissions',{filename:file.name,mimeType:mime,data:encoded});
            if(owner!==accountPageOwner||!form.isConnected)return;
            assignment.submission=result.submission;
            form.closest('[data-assignment]').querySelector('.class-submission-current').innerHTML=submissionMarkup(result.submission);
            input.value='';control.textContent='Nộp lại bài';status.textContent='Đã gửi bài đến thầy cô.';
        }catch(error){if(form.isConnected)status.textContent='Chưa gửi được bài. '+error.message;}
        finally{delete form.dataset.pending;if(form.isConnected){control.disabled=false;input.disabled=false;}}
    }
    function renderClassBody() {
        const body=document.querySelector('#class-body');if(!body||!classData)return;
        const d=classData;
        if(classTab==='sessions'||classTab==='assignments'){
            body.innerHTML=`<form id="class-filter" class="actions"><label class="field"><span>Từ ngày</span><input name="from" type="date" value="${escape(classFrom)}"></label><label class="field"><span>Đến ngày</span><input name="to" type="date" value="${escape(classTo)}"></label><button class="btn dark" type="submit">Tìm kiếm</button></form><div class="solution-list">${d.sessions.map(s=>`<details class="card card-pad class-session"><summary><strong>${escape(s.title)}</strong><span>${new Date(s.starts_at).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'})}</span>${classTab==='assignments'?badge(s.complete?'Đã chấm đủ':'Chưa chấm đủ',s.complete?'sage':'peach'):''}</summary>${classTab==='sessions'?`<h3>Nhận xét dành cho em</h3><p class="class-personal-comment">${escape(s.personal_comment||'Thầy cô chưa có nhận xét riêng sau buổi học này.')}</p><p>Điểm danh: <strong>${{charged:'Có học · tính phí',free:'Có học · miễn phí',absent:'Vắng'}[s.attendance_status]||'Chưa điểm danh'}</strong></p><h3>Nội dung buổi học</h3><p class="class-personal-comment">${escape(s.teacher_comment||'Chưa có nội dung tổng kết chung.')}</p>${safeUrl(s.video_url)?`<video controls preload="none" src="${safeUrl(s.video_url)}" aria-label="Video bài giảng"></video><a href="${safeUrl(s.video_url)}" target="_blank" rel="noopener noreferrer">Mở video bài giảng</a>`:'<p>Video bài giảng chưa được cập nhật.</p>'}`:s.assignments.map(classAssignmentMarkup).join('')||'<p>Chưa giao bài tập cho buổi học này.</p>'}</details>`).join('')||'<p class="card card-pad">Chưa có buổi học trong khoảng ngày này.</p>'}</div>`;
            body.querySelector('#class-filter').onsubmit=e=>{e.preventDefault();const f=new FormData(e.currentTarget);classFrom=f.get('from');classTo=f.get('to');loadClass();};
            body.querySelectorAll('[data-class-submit]').forEach(form=>form.onsubmit=event=>{event.preventDefault();submitClassAssignment(form);});
            if(classTab==='assignments'&&grade()===5)body.insertAdjacentHTML('beforeend',homeworkPanel());
        }else if(classTab==='summary')body.innerHTML=`<section class="card card-pad"><h2>Kết quả học tập theo tháng</h2>${trendChart(d.months)}</section><section class="card card-pad"><h2>Chu kỳ học · mỗi 2 tuần</h2>${d.cycles.map(c=>`<div class="list-row"><div><strong>${c.from} ~ ${c.to}</strong><small>Trung bình: ${c.average??'Chưa có điểm'}</small></div><button type="button" class="btn outline" data-class-ranking="cycle" data-value="${c.index}">Xếp hạng</button></div>`).join('')||'<p>Chưa có chu kỳ học.</p>'}</section>`;
        else body.innerHTML=`<section class="card card-pad"><h2>Học phí theo tháng</h2><div class="table-scroll"><table><thead><tr><th>Tháng</th><th>Số buổi tính phí</th><th>Học phí</th><th>Trạng thái</th></tr></thead><tbody>${d.fees.map(f=>`<tr><td><button type="button" class="btn outline" data-fee="${f.id}">${escape(f.month)}</button><small class="tuition-source-label">${f.source==='calculated'?'Theo điểm danh đã lưu':'Nhập thủ công'}</small></td><td>${f.charged_count??f.count}<small>${f.source==='calculated'?'Đơn giá: '+content.format(f.session_fee)+'đ/buổi':'Điểm danh hiện tại'}</small></td><td><strong>${content.format(f.amount)}đ</strong></td><td>${badge(feePaidLabel(f),f.paid_at||f.amount===0?'sage':'peach')}</td></tr>`).join('')}</tbody></table></div>${d.fees.length?'':'<p>Chưa có học phí được cập nhật.</p>'}</section>`;
    }
    async function showClassRanking(kind,value) {
        const result=await PlatformAPI.request('classes/'+classData.class.id+'/ranking?'+new URLSearchParams({[kind]:value}));
        host.showModal(`<h2 class="modal-title">${kind==='cycle'?'Xếp hạng chu kỳ':'Bảng điểm bài tập'}</h2><div class="table-scroll"><table><thead><tr><th>Hạng</th><th>Học sinh</th><th>Điểm</th></tr></thead><tbody>${result.rows.map(r=>`<tr class="${r.mine?'mine':''}"><td>${medal(r.rank)}</td><td>${escape(displayName(r.name))}</td><td>${r.value??'Chưa chấm'}</td></tr>`).join('')}</tbody></table></div>`);
    }
    async function showFee(id) {
        stopPaymentWatch();
        const f=classData.fees.find(f=>f.id===Number(id));if(!f)return;
        const calculated=f.source==='calculated',sessions=[...(f.sessions||[])].sort((a,b)=>String(feeSessionTime(a)).localeCompare(String(feeSessionTime(b)))||a.id-b.id),charged=f.charged_count??f.count??0;
        const source=calculated?'Tính theo điểm danh đã lưu':'Học phí nhập thủ công';
        const formula=calculated?`<div class="tuition-formula" aria-label="Đơn giá đã lưu nhân số buổi tính phí"><span><b>${content.format(f.session_fee)}đ</b><small>Đơn giá / buổi</small></span><i aria-hidden="true">×</i><span><b>${charged} buổi</b><small>Có học · tính phí</small></span></div>`:'<p class="tuition-manual-note">Số tiền do thầy cô cập nhật. Điểm danh bên dưới là thông tin hiện tại để tham khảo.</p>';
        host.showModal(`<article class="tuition-detail" data-fee-detail="${f.id}"><p class="tuition-kicker">${source}</p><h2 class="modal-title" id="fee-detail-title">Học phí tháng ${escape(f.month)}</h2><section class="tuition-bill-summary" aria-label="Thông tin học phí">${formula}<div class="tuition-total"><span>Tổng học phí</span><strong data-fee-amount>${content.format(f.amount)}đ</strong>${badge(feePaidLabel(f),f.paid_at||f.amount===0?'sage':'peach')}</div></section>${calculated?`<p class="tuition-snapshot-note">Bảng kê đã lưu${f.calculated_at?' lúc '+escape(accountDate(f.calculated_at)):''}. Đơn giá và điểm danh dưới đây thuộc lần lập học phí này.</p>`:''}${calendarHtml(f.month,sessions)}<section class="tuition-session-section" aria-labelledby="fee-session-heading"><h3 id="fee-session-heading">Chi tiết từng buổi${calculated?' đã lưu':''}</h3><ol class="tuition-session-list">${sessions.map(session=>`<li data-fee-session="${session.id}"><div><time datetime="${escape(feeSessionTime(session)||session.date||'')}">${escape(feeSessionTime(session)?accountDate(feeSessionTime(session)):session.date||'Chưa có thời gian')}</time><strong>${escape(session.title)}</strong></div><span class="tuition-attendance attendance-${feeStatus(session)}">${feeStatuses[feeStatus(session)]}</span></li>`).join('')||'<li>Chưa có buổi học trong tháng này.</li>'}</ol></section><div id="fee-payment" class="tuition-payment" aria-live="polite">${f.amount===0?'<p>Tháng này không phát sinh học phí. Em không cần tạo giao dịch thanh toán.</p>':f.paid_at?'<p>Học phí đã được thầy cô ghi nhận thanh toán.</p>':'<p>Đang chuẩn bị thông tin thanh toán…</p>'}</div><div class="actions tuition-close"><button class="btn outline" type="button" id="close-fee-detail">Đóng chi tiết</button></div></article>`);
        const dialog=document.querySelector('#modal'),article=document.querySelector('[data-fee-detail]'),oldLabel=dialog.getAttribute('aria-labelledby');
        dialog.setAttribute('aria-labelledby','fee-detail-title');dialog.scrollTop=0;
        const trap=event=>{
            if(event.key!=='Tab')return;
            const controls=[...dialog.querySelectorAll('a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])')].filter(node=>node.getClientRects().length),index=controls.indexOf(document.activeElement);
            if(!controls.length)return;
            if(event.shiftKey&&index<=0){event.preventDefault();controls.at(-1).focus();}
            else if(!event.shiftKey&&(index<0||index===controls.length-1)){event.preventDefault();controls[0].focus();}
        };
        dialog.addEventListener('keydown',trap);
        document.querySelector('#close-fee-detail').onclick=()=>dialog.close();
        dialog.addEventListener('close',()=>{if(paymentWatch?.target.closest('[data-fee-detail]')===article)stopPaymentWatch();dialog.removeEventListener('keydown',trap);if(oldLabel===null)dialog.removeAttribute('aria-labelledby');else dialog.setAttribute('aria-labelledby',oldLabel);document.querySelector(`[data-fee="${f.id}"]`)?.focus({preventScroll:true});},{once:true});
        if(!f.paid_at&&f.amount>0){
            await startPaymentView(article.querySelector('#fee-payment'),{feeId:f.id},{dialog,classId:classData.class.id});
        }
    }
    function paymentMarkup(o) {
        const paid=o.status==='paid',cancelled=o.status==='cancelled',pending=o.status==='pending';
        const label=paid?'Đã hoàn thành':cancelled?'Đã hủy':'Chờ xác nhận thanh toán';
        const status=paid?(o.fee_id?'Học phí đã được ghi nhận thanh toán.':'Thanh toán thành công. Quyền VIP đã được ghi nhận cho tài khoản của em.'):cancelled?'Đơn này đã hủy. Em hãy liên hệ 5BMath để kiểm tra trước khi chuyển tiền.':o.automationEnabled?'Trang sẽ tự cập nhật khi giao dịch chuyển khoản được xác nhận.':'Quyền học được cập nhật sau khi 5BMath xác nhận khoản tiền đã nhận.';
        return `<div class="payment-order" data-payment-order="${Number(o.id)}" data-payment-status="${escape(o.status)}"><div class="payment-heading"><h3>${o.fee_id?'Thanh toán học phí':'Nâng cấp VIP · '+Number(o.vip_months||1)+' tháng'}</h3>${badge(label,paid?'sage':'peach')}</div><dl class="payment-details"><div><dt>Số tiền</dt><dd><strong>${content.format(o.amount)}đ</strong></dd></div><div><dt>Mã thanh toán</dt><dd><strong>${escape(o.reference)}</strong></dd></div>${o.bankAccount?`<div><dt>Tài khoản nhận</dt><dd>${escape(o.bank)} · ${escape(o.bankAccount)}<br>${escape(o.bankName)}</dd></div>`:''}</dl>${pending?(o.qrUrl?`<img class="payment-qr" src="${escape(o.qrUrl)}" alt="QR chuyển khoản ${escape(o.reference)}" width="320" height="420"><p class="payment-transfer-note">Giữ nguyên số tiền và mã thanh toán khi chuyển khoản.</p>`:'<p class="learning-notice">Thông tin ngân hàng đang chờ cấu hình. Liên hệ 5BMath để được hướng dẫn thanh toán.</p>'):''}<p class="payment-confirmation ${paid?'is-paid':''}" role="status">${escape(status)}${paid&&o.paid_at?' Xác nhận lúc '+escape(accountDate(o.paid_at))+'.':''}</p><p class="payment-feedback" data-payment-feedback role="status" hidden></p><div class="actions payment-actions">${pending?'<button class="btn dark" type="button" data-payment-retry>Kiểm tra thanh toán</button>':''}<a class="btn outline" href="https://zalo.me/0984763971" target="_blank" rel="noopener noreferrer">Liên hệ Zalo</a>${paid&&!o.fee_id?link('Xem tài khoản','profile','outline'):''}</div></div>`;
    }
    function stopPaymentWatch(){
        paymentGeneration++;
        if(paymentWatch){clearTimeout(paymentWatch.timer);paymentWatch.controller.abort();}
        paymentWatch=null;
    }
    function paymentViewActive(context){
        return paymentWatch===context&&context.generation===paymentGeneration&&context.owner===accountPageOwner&&PlatformAPI.snapshot.authenticated&&PlatformAPI.snapshot.account?.id===context.owner&&PlatformAPI.snapshot.csrf===context.csrf&&context.target.isConnected&&(context.dialog?currentRoute==='classroom'&&context.dialog.open:currentRoute==='payment');
    }
    function paymentAvailable(context){return paymentViewActive(context)&&!document.hidden&&navigator.onLine!==false;}
    function schedulePaymentCheck(context){
        clearTimeout(context.timer);context.timer=null;
        if(paymentAvailable(context)&&context.order?.status==='pending')context.timer=setTimeout(()=>checkPayment(context),Math.min(30000,5000*Math.max(1,context.failures)));
    }
    function paymentFeedback(context,message,error=false){
        if(!paymentViewActive(context))return;
        const feedback=context.target.querySelector('[data-payment-feedback]');
        if(feedback){feedback.textContent=message;feedback.hidden=!message;feedback.classList.toggle('is-error',error);}
    }
    function renderPaymentOrder(context,order){
        if(!paymentViewActive(context)||Number(order.account_id)!==Number(context.owner))return false;
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
        return true;
    }
    async function syncPaidPayment(context){
        if(context.synced||!paymentAvailable(context))return;
        const snapshot=await PlatformAPI.request('session',undefined,{signal:context.controller.signal,owner:context.owner});
        if(!paymentViewActive(context))return;
        applySnapshot(snapshot);entitlementRefreshPending=false;updateMembershipViews();updateUnreadBadge();updateClassUnread();
        if(context.order.fee_id){
            const targetClass=Number(context.classId),selectedClass=Number(document.querySelector('#class-select')?.value);
            if(classData&&Number(classData.class.id)===targetClass){
                const fee=classData.fees.find(item=>Number(item.id)===Number(context.order.fee_id));
                if(fee){fee.paid_at=context.order.paid_at;const label=context.target.closest('[data-fee-detail]')?.querySelector('.tuition-total .tag');if(label){label.textContent='Đã hoàn thành';label.classList.remove('peach');label.classList.add('sage');}}
            }
            if(selectedClass===targetClass){
                const position={x:scrollX,y:scrollY},dialogScroll=context.dialog?.scrollTop;
                await loadClass();
                if(!paymentViewActive(context))return;
                window.scrollTo({left:position.x,top:position.y,behavior:'instant'});
                if(context.dialog)context.dialog.scrollTop=dialogScroll;
            }
        }
        if(paymentViewActive(context)){context.synced=true;paymentFeedback(context,'');context.target.querySelector('[data-payment-retry]')?.remove();}
    }
    async function checkPayment(context,manual=false){
        if(!paymentAvailable(context)||context.busy||!context.order)return;
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
            if(paymentViewActive(context)&&context.order.status==='pending')paymentFeedback(context,manual?'Chưa có xác nhận thanh toán. Trang vẫn đang tự kiểm tra.':'');
        }catch(error){
            if(error.name!=='AbortError'&&paymentViewActive(context)){
                if([401,403,404].includes(error.status)){
                    context.target.innerHTML='<p class="payment-feedback is-error" role="alert">Chưa thể đọc đơn thanh toán của tài khoản này. Em hãy đăng nhập lại hoặc liên hệ 5BMath để kiểm tra.</p>';
                    stopPaymentWatch();return;
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
            if(paymentViewActive(context)){const control=context.target.querySelector('[data-payment-retry]');if(control)control.disabled=false;if(context.resumeRequested){context.resumeRequested=false;resumePaymentCheck();}else schedulePaymentCheck(context);}
        }
    }
    async function createPayment(context){
        if(!paymentAvailable(context)||context.busy)return;
        context.busy=true;context.target.innerHTML='<p role="status">Đang chuẩn bị thông tin thanh toán…</p>';
        try{
            const result=await PlatformAPI.request(context.resumeOrderId?'payments/'+context.resumeOrderId:'payments',context.resumeOrderId?undefined:context.body,{signal:context.controller.signal,owner:context.owner});
            if(!renderPaymentOrder(context,result.order))return;
        }catch(error){
            if(paymentViewActive(context)&&error.name!=='AbortError'){
                context.target.innerHTML=`<p class="payment-feedback is-error" role="alert">Chưa tải được thông tin thanh toán. ${escape(error.message)}</p><div class="actions payment-actions"><button class="btn outline" type="button" data-payment-retry>Thử lại</button>${context.resumeOrderId&&error.status===404?link('Tạo đơn mua VIP','payment','outline'):''}</div>`;
                context.target.querySelector('[data-payment-retry]').onclick=()=>createPayment(context);
            }
        }finally{context.busy=false;if(paymentViewActive(context)){if(context.resumeRequested){context.resumeRequested=false;resumePaymentCheck();}else if(context.order?.status==='paid')checkPayment(context);else schedulePaymentCheck(context);}}
    }
    async function startPaymentView(target,body,options={}){
        stopPaymentWatch();
        if(!target||!PlatformAPI.snapshot.authenticated)return;
        const context={target,body,...options,owner:accountPageOwner,csrf:PlatformAPI.snapshot.csrf,generation:paymentGeneration,controller:new AbortController(),timer:null,busy:false,order:null,markup:'',failures:0,synced:false,lastCheck:0};
        paymentWatch=context;
        if(!paymentAvailable(context)){target.innerHTML='<p class="payment-feedback" role="status">Kết nối mạng để tải thông tin thanh toán.</p>';return;}
        await createPayment(context);
    }
    function pausePaymentCheck(){
        if(!paymentWatch)return;
        clearTimeout(paymentWatch.timer);paymentWatch.timer=null;paymentWatch.controller.abort();paymentWatch.controller=new AbortController();
    }
    function resumePaymentCheck(){
        const context=paymentWatch;if(!context||!paymentAvailable(context))return;
        if(context.busy){context.resumeRequested=true;return;}
        if(!context.order){createPayment(context);return;}
        if(Date.now()-context.lastCheck>1500)checkPayment(context);else schedulePaymentCheck(context);
    }
    async function loadPayment() {
        const container=document.querySelector('#payment-content');if(!container)return;
        if(!live){container.textContent='Đăng nhập trên máy chủ để thanh toán theo tài khoản.';return;}
        const identity=query('order');
        if(identity!==null&&!/^[1-9][0-9]{0,14}$/.test(identity)){container.innerHTML='<p class="payment-feedback is-error" role="alert">Mã đơn thanh toán không hợp lệ.</p>'+link('Tạo đơn mua VIP','payment','outline');return;}
        await startPaymentView(container,{},{resumeOrderId:identity===null?null:Number(identity)});
    }

    function initials() {
        return name().trim().split(/\s+/).slice(-2).map(part => part[0]).join('').toLocaleUpperCase('vi');
    }

    function getExam() {
        return state.exams[query('id') || state.activeExam];
    }

    function timeText(seconds) {
        const value = Math.max(0,Math.ceil(seconds));
        return String(Math.floor(value / 60)).padStart(2,'0') + ':' + String(value % 60).padStart(2,'0');
    }

    function timeLeft(deadline) {
        return timeText((deadline - Date.now()) / 1000);
    }

    function battleTime(battle) {
        const duration=content.battleSeconds(battle.grade,battle.questions[battle.index].difficulty);
        const now=battle.mode==='bot'?Date.now():arenaNow();
        const remaining=Math.min(duration,Math.max(0,Math.ceil((battle.deadline-now)/1000)));
        return {duration,remaining,percent:remaining/duration*100};
    }

    function updateBattleTimer(battle) {
        const time=battleTime(battle),label=timeText(time.remaining);
        const timer=document.querySelector('#learning-battle-timer');
        if(timer)timer.textContent=label;
        const meter=document.querySelector('#learning-battle-time-meter');
        if(meter){
            meter.setAttribute('aria-valuemax',time.duration);
            meter.setAttribute('aria-valuenow',time.remaining);
            meter.setAttribute('aria-valuetext',label+' còn lại');
            meter.firstElementChild.style.setProperty('--value',time.percent+'%');
        }
    }

    function updateBattleRound(battle) {
        const panel=document.querySelector('.battle-round-status');
        const question=document.querySelector('.battle-question-content');
        if(!panel||!question)return;
        const now=battle.mode==='bot'?Date.now():arenaNow();
        const expired=now>=battle.deadline;
        // The fallback also supports bot rounds saved before roundOutcome existed.
        let outcome=battle.roundOutcome;
        if(!outcome||outcome==='waiting'){
            outcome=battle.answer!==null
                ? battle.mode==='bot'
                    ? isCorrect(battle.questions[battle.index],battle.answer)?'correct':'wrong'
                    : battle.feedback?.includes('chưa đúng')?'wrong':'correct'
                : battle.resolved&&battle.feedback?.includes('trả lời đúng')?'opponent'
                : expired?'timeout':'waiting';
        }
        const shown=outcome!=='waiting';
        if(panel.hidden===shown)panel.hidden=!shown;
        question.classList.toggle('round-hidden',shown);
        if(question.inert!==shown)question.inert=shown;
        if(question.getAttribute('aria-hidden')!==String(shown))question.setAttribute('aria-hidden',String(shown));
        if(!shown)return;
        if(panel.dataset.outcome!==outcome)panel.dataset.outcome=outcome;
        const titles={correct:'Em trả lời đúng!',wrong:'Em trả lời sai',opponent:'Bạn trả lời nhanh hơn',timeout:'Hết giờ!'};
        const symbols={correct:'check',wrong:'flag',opponent:'zap',timeout:'clock'};
        const setText=(selector,text)=>{const node=panel.querySelector(selector);if(node.textContent!==text)node.textContent=text;};
        setText('#battle-round-title',titles[outcome]);
        const symbol=panel.querySelector('.battle-round-symbol');
        if(symbol.dataset.symbol!==symbols[outcome]){symbol.innerHTML=icon(symbols[outcome],28);symbol.dataset.symbol=symbols[outcome];}
        let detail=outcome==='correct'?'Em gây 20 sát thương.':outcome==='opponent'?'Bạn trả lời đúng trước. Em bị trừ 20 máu.':'Chưa có đáp án đúng. Hai bên giữ nguyên máu.';
        if(outcome==='wrong')detail=!battle.resolved?'Em hãy chờ bạn trả lời hoặc hết thời gian câu này.':battle.roundReason==='correct'?'Bạn trả lời đúng. Em bị trừ 20 máu.':'Câu này chưa có đáp án đúng. Hai bên giữ nguyên máu.';
        if(outcome==='timeout'&&!battle.resolved)detail='Đang nhận kết quả câu này…';
        setText('#battle-round-detail',detail);
        const final=battle.hp===0||battle.opponentHp===0||battle.index>=battle.questions.length-1;
        setText('#battle-round-next',final?'Hãy xem kết quả trận đấu':'Hãy chuẩn bị cho câu '+(battle.index+2));
        const seconds=Math.max(0,Math.ceil(((battle.nextAt||now)-now)/1000));
        const countdown=panel.querySelector('.battle-round-countdown'),hideCount=!battle.resolved||seconds===0;
        if(countdown.hidden!==hideCount)countdown.hidden=hideCount;
        setText('#next-round-count',String(seconds));
        setText('#battle-round-wait',battle.resolved?(seconds===0?'Đang chuyển…':''):expired?'Đang đồng bộ câu tiếp theo…':'Câu này còn '+timeText((battle.deadline-now)/1000));
    }

    function resumeArena() {
        if(document.hidden||!currentRoute||!host.progress?.name||live&&!PlatformAPI.snapshot.authenticated)return;
        if(sessionStorage.getItem('5bmath-room'))pollRoom();
        else if(currentRoute==='battle'&&currentBattle?.mode==='bot'){
            tickBot();
            if(currentBattle){updateBattleTimer(currentBattle);updateBattleVisuals();}
        }
    }

    function emoteSeconds(battle) {
        const now=battle.mode==='bot'?Date.now():arenaNow();
        const until=Math.max(battle.emoteAvailableAt||0,emoteLock.id===battle.id?emoteLock.until:0);
        return Math.max(0,Math.ceil((until-now)/1000));
    }

    function updateEmoteControls(battle) {
        if(battle.mode==='bot'&&battle.myEmote!=null&&Date.now()>=(battle.myEmoteUntil||0)){
            battle.myEmote=null;persistBot();
        }
        if(battle.mode==='bot'){
            const bubble=document.querySelector('#my-emote'),text=emotes[battle.myEmote]?.join(' ')||'';
            if(bubble&&bubble.textContent!==text)bubble.textContent=text;
        }
        const seconds=emoteSeconds(battle),pending=emoteLock.id===battle.id&&emoteLock.pending;
        battle.emoteUsed=seconds>0;
        document.querySelectorAll('[data-emote]').forEach(control=>{const disabled=seconds>0||pending;if(control.disabled!==disabled)control.disabled=disabled;});
        const bar=document.querySelector('.emote-bar'),disabled=seconds>0||pending;
        if(bar){
            bar.classList.toggle('is-cooling',disabled);
            if(bar.getAttribute('aria-disabled')!==String(disabled))bar.setAttribute('aria-disabled',String(disabled));
        }
    }

    async function sendEmote(index) {
        const battle=currentBattle;
        if(!battle||emoteSeconds(battle)>0||emoteLock.id===battle.id&&emoteLock.pending)return;
        const now=battle.mode==='bot'?Date.now():arenaNow();
        emoteLock={id:battle.id,until:now+5000,pending:true};
        updateEmoteControls(battle);
        try{
            if(battle.mode==='bot'){
                battle.emoteAvailableAt=now+5000;battle.myEmoteUntil=now+4000;battle.myEmote=index;
                persistBot();updateBattleVisuals();
            }else{
                const result=await arenaRequest('emote',{emote:index});
                if(result.battle?.id===battle.id){
                    if(emoteLock.id===battle.id)emoteLock.until=result.battle.emoteAvailableAt||0;
                    if(currentBattle?.id===battle.id){
                        currentBattle.emoteAvailableAt=result.battle.emoteAvailableAt;
                        currentBattle.myEmote=result.battle.myEmote;
                        updateBattleVisuals();
                    }
                }
                await pollRoom();
            }
        }catch(error){if(emoteLock.id===battle.id)emoteLock.until=0;throw error;}
        finally{if(emoteLock.id===battle.id)emoteLock.pending=false;if(currentBattle?.id===battle.id)updateEmoteControls(currentBattle);}
    }

    function isCorrect(question, answer) {
        if (answer === undefined || answer === null || answer === '') return false;
        return typeof question.answer === 'number'
            ? Math.abs(Number(answer) - question.answer) < 1e-9
            : String(question.answer) === String(answer);
    }

    function go(route, parameters = {}) {
        location.assign(href(route,parameters));
    }

    function refresh() {
        host.redraw();
    }

    async function createExam({topic = '', count = 10, difficulty = 0, maxWeek, week:exactWeek, category, school} = {}) {
        if(live){
            const {exam}=await PlatformAPI.request('exams',{topic,count,difficulty,maxWeek,week:exactWeek,category:category||(topic||maxWeek!==undefined?'content':'combined'),school,requestKey:uid()});
            state.exams[exam.id]=exam;state.activeExam=exam.id;
            go('testing',{id:exam.id});return;
        }
        consumeLocal(category||(topic||maxWeek!==undefined?'content':'combined'));
        maxWeek = maxWeek ?? 35;
        const previous = Object.values(state.exams).at(-1);
        const questions = content.generate({grade:grade(),topic,count,difficulty,maxWeek},previous?.questions.map(question => question.id));
        const id = uid();
        const startedAt = Date.now();
        const exam = {
            id, code:'5B-' + id.replaceAll('-','').slice(0,8).toUpperCase(),
            title: topic ? 'Ôn luyện · ' + questions[0].topicTitle : 'Thi thử tổng hợp',
            grade:grade(), questions, answers:{}, index:0, startedAt,
            expiresAt:startedAt + (count === 3 ? 10 : 30) * 60000,
        };
        state.exams[id] = exam;
        state.activeExam = id;
        save();
        go('testing',{id});
    }

    let submitting = false;
    async function finishExam(exam) {
        if(live){
            if(submitting)return;
            submitting=true;
            try {
                const result=await PlatformAPI.request('exams/'+exam.id+'/submit',{});
                state.exams[exam.id]=result.exam;
                go('results',{id:exam.id});
            }catch(error){host.toast(error.message);}finally{submitting=false;}
            return;
        }
        load();
        const saved = state.exams[exam.id];
        if (!saved || saved.submittedAt) {
            if (saved) go('results',{id:saved.id});
            return;
        }
        saved.correct = saved.questions.filter(question => isCorrect(question,saved.answers[question.id])).length;
        saved.score = Math.round(saved.correct / saved.questions.length * 100) / 10;
        saved.duration = Math.floor((Math.min(Date.now(),saved.expiresAt) - saved.startedAt) / 1000);
        saved.submittedAt = new Date().toISOString();
        save();
        go('results',{id:saved.id});
    }

    function requestSubmit() {
        const exam = getExam();
        if (!exam || exam.submittedAt) return;
        const missing = exam.questions.filter(question => !exam.answers[question.id]).length;
        host.showModal(`<h2 class="modal-title">Nộp bài thi thử?</h2><p>${missing ? 'Em còn ' + missing + ' câu chưa trả lời. Câu trống được tính 0 điểm.' : 'Em đã trả lời toàn bộ câu hỏi.'}</p><div class="actions"><button class="btn outline" id="learning-continue" type="button">Làm tiếp</button><button class="btn dark" id="learning-confirm-submit" type="button">Nộp bài</button></div>`);
        document.querySelector('#learning-continue').onclick = () => document.querySelector('#modal').close();
        document.querySelector('#learning-confirm-submit').onclick = () => {
            document.querySelector('#modal').close();
            finishExam(exam);
        };
    }

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

    async function startBot(settings={}) {
        if(live)await PlatformAPI.request('bot/start',{requestKey:uid()});else consumeLocal('bot');
        const difficulty = 0;
        const botLevel = Number(settings.botLevel??document.querySelector('#bot-level')?.value??0);
        const scope = settings.scope||arenaScope;
        const questions = content.generate({grade:grade(),difficulty,count:20,maxWeek:scope === 'weekly' ? week() : 35});
        const harderCount = difficulty < 3 ? 6 : 0;
        for (let index = 0; index < harderCount; index++) {
            questions[index] = content.problem(grade(),questions[index].topic,index,difficulty + 1);
        }
        currentBattle = {
            id:uid(), mode:'bot', grade:grade(), questions, index:0,
            hp:100, opponentHp:100, opponent:['Bot Dễ','Bot Trung bình','Bot Khó'][botLevel],
            botLevel, readyAt:Date.now()+5000,
            answer:null, resolved:false, correct:0, feedback:'', review:[],
        };
        setBotRoundTiming(currentBattle,currentBattle.readyAt);
        sessionStorage.setItem('5bmath-bot-battle',JSON.stringify(currentBattle));
        go('battle');
    }

    function setBotRoundTiming(battle,startedAt) {
        const duration=content.battleSeconds(battle.grade,battle.questions[battle.index].difficulty)*1000;
        battle.deadline=startedAt+duration;
        // Leave one polling interval before expiry so a scheduled bot answer
        // is processed while the question is still open.
        battle.botAt=startedAt+duration*0.7+Math.random()*(duration*0.3-1000);
    }

    function persistBot() {
        sessionStorage.setItem('5bmath-bot-battle',JSON.stringify(currentBattle));
    }

    function answerBot(answer) {
        const battle = currentBattle;
        if (!battle || battle.resolved || battle.answer !== null || Date.now() >= battle.deadline || Date.now() < (battle.readyAt||0)) return;
        battle.answer = answer;
        const question = battle.questions[battle.index];
        if (isCorrect(question,answer)) {
            battle.correct++;
            recordBotAttack(battle,'me');
            battle.opponentHp = Math.max(0,battle.opponentHp - 20);
            battle.resolved = true;
            battle.feedback = 'Đúng rồi! Linh vật của em gây 20 sát thương.';
            battle.roundOutcome='correct';battle.roundReason='correct';
        } else {
            battle.feedback = 'Câu trả lời chưa đúng. Đang chờ lượt trả lời của bot.';
            battle.roundOutcome='wrong';battle.roundReason=null;
            ArenaAudio.effect('wrong');
        }
        if(battle.resolved)battle.nextAt=Date.now()+3000;
        persistBot();
        updateBattleVisuals();
    }

    function tickBot() {
        const battle = currentBattle;
        if (!battle || battle.mode !== 'bot') return;
        if(Date.now()<(battle.readyAt||0))return;
        if(battle.resolved){if(Date.now()>=battle.nextAt)nextBot();return;}
        const question = battle.questions[battle.index];
        const botCanAnswer = question.difficulty <= battle.botLevel;
        if (Date.now() >= battle.deadline) {
            battle.resolved = true;
            battle.feedback = 'Hết thời gian câu này. Hai bên giữ nguyên máu.';
            battle.roundOutcome=battle.answer!==null?'wrong':'timeout';battle.roundReason='timeout';
        } else if (Date.now() >= battle.botAt && botCanAnswer) {
            recordBotAttack(battle,'opponent');
            battle.hp = Math.max(0,battle.hp - 20);
            battle.feedback = 'Bot trả lời đúng. Linh vật của em còn ' + battle.hp + ' máu.';
            battle.roundOutcome=battle.answer!==null?'wrong':'opponent';battle.roundReason='correct';
            battle.resolved = true;
        } else return;
        battle.nextAt=Date.now()+3000;persistBot();updateBattleVisuals();
    }

    function nextBot() {
        const battle = currentBattle;
        if (!battle?.resolved) return;
        if(battle.review.length===battle.index)battle.review.push({...battle.questions[battle.index],myAnswer:battle.answer,correct:isCorrect(battle.questions[battle.index],battle.answer)});
        if (battle.hp === 0 || battle.opponentHp === 0 || battle.index === battle.questions.length - 1) {
            const outcome = battle.hp === 0 ? 'lose' : battle.opponentHp === 0 ? 'win' : 'draw';
            finishBattle({...battle,outcome,rounds:battle.index + 1,points:0});
            return;
        }
        battle.index++;
        setTimeout(()=>ArenaAudio.effect('next'),100);
        battle.answer = null;
        battle.resolved = false;
        battle.feedback = '';battle.nextAt=null;
        battle.roundOutcome='waiting';battle.roundReason=null;
        setBotRoundTiming(battle,Date.now());
        persistBot();
        refresh();
    }

    function finishBattle(result) {
        const horsePending=browser?window.HorseAnimation?.pendingUntil?.()||0:0;
        if(result.outcome!=='left'&&currentRoute==='battle'&&Date.now()<horsePending){
            if(!catFinishTimer)catFinishTimer=setTimeout(()=>{catFinishTimer=null;if(currentBattle?.id===result.id&&currentRoute==='battle')finishBattle(result);},Math.max(40,horsePending-Date.now()+40));
            return;
        }
        if(result.outcome!=='left'&&currentRoute==='battle'&&Date.now()<octopusFinaleUntil){
            if(!octopusFinishTimer)octopusFinishTimer=setTimeout(()=>{octopusFinishTimer=null;if(currentBattle?.id===result.id&&currentRoute==='battle')finishBattle(result);},octopusFinaleUntil-Date.now()+40);
            return;
        }
        // Visual completion only; authoritative damage, score and deadlines stay unchanged.
        if(result.outcome!=='left'&&currentRoute==='battle'&&Date.now()<owlFinaleUntil){
            if(!owlFinishTimer)owlFinishTimer=setTimeout(()=>{owlFinishTimer=null;if(currentBattle?.id===result.id&&currentRoute==='battle')finishBattle(result);},owlFinaleUntil-Date.now()+30);
            return;
        }
        // Let an already resolved visual finish; server HP/score/deadlines stay authoritative.
        if(result.outcome!=='left'&&currentRoute==='battle'&&Date.now()<catFinaleUntil){
            if(!catFinishTimer)catFinishTimer=setTimeout(()=>{catFinishTimer=null;if(currentBattle?.id===result.id&&currentRoute==='battle')finishBattle(result);},catFinaleUntil-Date.now()+40);
            return;
        }
        load();
        if (!state.battles[result.id]) {
            state.battles[result.id] = {
                id:result.id, mode:result.mode, grade:result.grade, outcome:result.outcome,
                correct:result.correct, rounds:result.rounds, points:result.points,
                completed:result.completed,reason:result.reason,penalty:result.penalty,quotaRefunded:result.quotaRefunded,
                review:result.review || [], date:new Date().toISOString(),
            };
            state.points = Math.max(1000,state.points + result.points);
            save();
        }
        sessionStorage.removeItem('5bmath-bot-battle');
        sessionStorage.removeItem('5bmath-room');
        if(document.querySelector('#modal .arena-leave-confirm'))document.querySelector('#modal').close();
        currentBattle = null;
        sessionStorage.setItem('5bmath-last-battle',JSON.stringify(state.battles[result.id]||result));
        go('battleResult',{id:result.id});
    }

    async function arenaRequest(action, values = {}) {
        const session = JSON.parse(sessionStorage.getItem('5bmath-room') || 'null') || {};
        if(live){
            try{const result=await PlatformAPI.request('arena',{action,...session,...values});receiveArenaDiscipline(result);return result;}
            catch(error){
                if(error.details?.arenaDiscipline)receiveArenaDiscipline(error.details);
                else if(error.status===429)try{applySnapshot(await PlatformAPI.refresh());updateArenaDiscipline();}catch{}
                throw error;
            }
        }
        const response = await fetch('/api/arena',{
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({action,...session,...values}), signal:AbortSignal.timeout(8000),
        });
        const result = await response.json().catch(() => ({}));
        receiveArenaDiscipline(result);
        if (!response.ok) throw new Error(result.error || 'Máy chủ đấu trí chưa sẵn sàng. Em có thể luyện với bot.');
        return result;
    }

    function roomSettings() {
        const difficulty = 0;
        const scope = arenaScope;
        return {name:name(),grade:grade(),difficulty,scope,mascot:state.mascot};
    }

    async function enterRoom(action, values = {}) {
        if(sessionStorage.getItem('5bmath-room')){go('room');return;}
        requireHumanPlay();
        const result = await arenaRequest(action,{...roomSettings(),...values});
        sessionStorage.removeItem('5bmath-bot-battle');
        sessionStorage.setItem('5bmath-room',JSON.stringify({code:result.code,token:result.token}));
        go('room',{code:result.code});
    }

    let polling=false,publicRefresh=0,serverOffset=0,lastCount=null;
    const arenaNow=()=>Date.now()+serverOffset;
    function overlay(html) {
        if(html)setMobileMenu(false,false);
        let node=document.querySelector('#arena-overlay');
        if(!html){node?.remove();return;}
        if(!node){node=document.createElement('div');node.id='arena-overlay';node.className='arena-overlay';document.body.append(node);}
        node.innerHTML=html;
        node.querySelector('[data-cancel-challenge]')?.addEventListener('click',()=>actions['leave-room']().catch(e=>host.toast(e.message)));
        node.querySelector('[data-accept-challenge]')?.addEventListener('click',async e=>{const control=e.currentTarget;control.dataset.humanPending='true';control.disabled=true;try{requireHumanPlay();await arenaRequest('accept');await pollRoom();}catch(error){host.toast(error.message);}finally{if(control.isConnected){delete control.dataset.humanPending;control.disabled=false;}updateArenaDiscipline();}});
        updateArenaDiscipline();
    }
    function countdown(until,clock=arenaNow()) {
        const seconds=Math.max(0,Math.ceil((until-clock)/1000));
        if(seconds===lastCount&&document.querySelector('.prepare-count'))return;
        if(seconds!==lastCount){lastCount=seconds;if(typeof ArenaAudio!=='undefined')ArenaAudio.effect(seconds?'count':'go');}
        overlay(`<div class="prepare-count" role="status"><strong>${seconds||'BẮT ĐẦU!'}</strong><span>Sẵn sàng cùng linh vật!</span></div>`);
    }
    async function loadPublicRooms() {
        const target=document.querySelector('#public-rooms');if(!target||document.querySelector('#arena-panel-quick')?.hidden)return;
        try{
            const result=await arenaRequest('list');if(!target.isConnected)return;
            target.innerHTML=result.rooms.length?result.rooms.map(r=>`<article class="public-room">${art(r.mascot||'sprout')}<div><strong>${escape(displayName(r.name))}</strong><p>${arenaScopeLabel(r.scope)} · Lớp ${r.grade}</p><small>${petRank(r.level||1)} · Level ${r.level||1} · ${r.xp||1000} XP · ${r.wins||0} thắng / ${r.losses||0} thua</small></div><button type="button" class="btn dark" data-human-play data-human-quota="true" data-challenge="${r.code}">Thách Đấu</button></article>`).join(''):'<p>Chưa có phòng phù hợp. Bấm Tìm đối thủ để mở phòng công khai.</p>';
            updateArenaDiscipline();
        }catch(e){target.textContent=e.message;}
    }
    function roomPopup(code) {
        let node=document.querySelector('#waiting-popup');
        if(!node){node=document.createElement('aside');node.id='waiting-popup';node.className='waiting-popup';document.body.append(node);}
        node.innerHTML=`${art(state.mascot)}<a href="${href('room')}">Đang chờ bạn vào phòng <strong>${escape(code)}</strong></a><button type="button" aria-label="Đóng và rời phòng">×</button>`;
        node.querySelector('button').onclick=()=>actions['leave-room']().catch(e=>host.toast(e.message));
    }
    async function pollRoom() {
        if(polling||!sessionStorage.getItem('5bmath-room'))return;polling=true;
        try{
            const result=await arenaRequest('state');serverOffset=(result.serverNow||Date.now())-Date.now();
            if(result.status==='cancelled'){
                overlay('');sessionStorage.removeItem('5bmath-room');document.querySelector('#waiting-popup')?.remove();host.toast('Phòng đã hủy hoặc hết thời gian chờ.');go('arena');
            }else if(result.status==='finished'){
                if(currentBattle&&Number.isFinite(result.result.hp)&&currentRoute==='battle'){
                    currentBattle.hp=result.result.hp;currentBattle.opponentHp=result.result.opponentHp;
                    currentBattle.lastAttack=result.result.lastAttack;
                    updateBattleVisuals();
                }
                overlay('');finishBattle(result.result);
            }else if(result.status==='challenged'){
                document.querySelector('#waiting-popup')?.remove();
                const seconds=Math.max(0,Math.ceil((result.challengeUntil-arenaNow())/1000));
                if(document.querySelector('.challenge-dialog'))document.querySelector('.challenge-time').textContent=seconds+'s';
                else {overlay(`<section class="challenge-dialog" role="dialog" aria-modal="true" aria-label="Lời thách đấu"><h2>${result.host?'Có lời thách đấu!':'Đã gửi lời thách đấu'}</h2><p>${escape(displayName(result.opponent))}</p><strong class="challenge-time">${seconds}s</strong><div class="actions">${result.host?'<button class="btn dark" type="button" data-human-play data-accept-challenge>Chấp Nhận</button>':''}<button class="btn outline" type="button" data-cancel-challenge>Hủy Trận</button></div></section>`);document.querySelector('[data-accept-challenge],[data-cancel-challenge]')?.focus();}
            }else if(result.status==='preparing'){
                document.querySelector('#waiting-popup')?.remove();countdown(result.readyAt);
            }else if(result.status==='playing'){
                overlay('');document.querySelector('#waiting-popup')?.remove();
                const changed=!currentBattle||result.battle.index!==currentBattle.index;
                const refreshHp=changed&&currentRoute==='battle'&&currentBattle?.id===result.battle.id?visualHp?.slice():null;
                currentBattle=result.battle;
                if(currentRoute!=='battle')go('battle');else if(changed){refresh();setTimeout(()=>ArenaAudio.effect('next'),100);}else updateBattleVisuals();
                if(refreshHp&&currentRoute==='battle'){visualHp=refreshHp;updateBattleVisuals();}
            }else {
                overlay('');
                if(currentRoute==='room'){
                    document.querySelector('#waiting-popup')?.remove();
                    const status=document.querySelector('#learning-room-status'),container=document.querySelector('#learning-room-content');
                    if(status)status.textContent=`${result.public?'Phòng công khai':'Phòng bạn bè'} · Tự đóng sau ${timeText((result.expiresAt-arenaNow())/1000)}`;
                    if(container&&!container.children.length)container.innerHTML=`<div class="room-code"><small>Mã phòng</small><strong>${escape(result.code)}</strong><div class="actions">${button('Sao chép mã','copy-room','outline','copy')}${button('Sao chép liên kết','copy-room-link','outline','copy')}</div></div><p>${result.players.map(value=>escape(displayName(value))).join(' · ')} · Đang chờ đối thủ</p>`;
                }else roomPopup(result.code);
            }
        }catch(e){host.toast(e.message);if(/hết hạn|không thuộc|không hợp lệ/.test(e.message)){sessionStorage.removeItem('5bmath-room');overlay('');document.querySelector('#waiting-popup')?.remove();currentBattle=null;if(currentRoute==='battle'||currentRoute==='room')go('arena');}}
        finally{polling=false;}
    }
    let visualHp=null,catFinaleUntil=0,catFinishTimer=null;
    let owlFinaleUntil=0,owlFinishTimer=null;
    const attackSpells=[['rock','Đá rơi'],['vine','Dây leo trói'],['lightning','Sét đánh']];
    const activeHitSpells=new Set(),shownHitSpells=new Set(),hitSpellImages=[];
    let hitSpellBattle=null;
    function recordBotAttack(battle,attacker) {
        battle.lastAttack={id:battle.id+':'+battle.index,spell:attackSpells[Math.floor(Math.random()*attackSpells.length)][0],index:battle.index,attacker};
    }
    function attackSpell(attacker) {
        const battle=currentBattle,event=battle?.lastAttack,side=attacker==='#fighter-me'?'me':'opponent';
        const chosen=event?.attacker===side&&attackSpells.find(([key])=>key===event.spell);
        // Compatibility for a bot session saved before lastAttack existed.
        return chosen||attackSpells[artSeed((battle?.id||'')+':'+(battle?.index||0))%attackSpells.length];
    }
    function clearHitSpells() {
        for(const effect of activeHitSpells){effect.timers.forEach(clearTimeout);effect.node?.remove();}
        activeHitSpells.clear();
    }
    function playHitSpell(target,attacker,spell,final) {
        const battle=currentBattle,stage=document.querySelector('#battle-stage');
        if(!battle||!stage)return;
        if(hitSpellBattle!==battle.id){shownHitSpells.clear();hitSpellBattle=battle.id;}
        const side=attacker==='#fighter-me'?'me':'opponent';
        const eventId=battle.lastAttack?.attacker===side?battle.lastAttack.id:battle.id+':'+battle.index+':'+side;
        if(shownHitSpells.has(eventId))return;
        shownHitSpells.add(eventId);
        stage.dataset.randomSpells='true';
        const effect={node:null,timers:[]};activeHitSpells.add(effect);
        const show=()=>{
            const body=document.querySelector(target+' .pet-body');
            if(!stage.isConnected||!body||currentBattle?.id!==battle.id){activeHitSpells.delete(effect);return;}
            const arena=stage.getBoundingClientRect(),pet=body.getBoundingClientRect();
            const width=stage.clientWidth,height=stage.clientHeight,padding=6;
            const size=Math.max(1,Math.min(pet.width*1.55,pet.height*1.55,width-padding*2,height-padding*2));
            const left=Math.max(padding,Math.min(width-size-padding,pet.left-arena.left-stage.clientLeft+pet.width/2-size/2));
            const top=Math.max(padding,Math.min(height-size-padding,pet.top-arena.top-stage.clientTop+pet.height/2-size*.6));
            const node=document.createElement('span');effect.node=node;
            node.className='random-hit-spell';node.dataset.spell=spell[0];node.dataset.attackId=eventId;node.setAttribute('aria-hidden','true');
            node.style.cssText=`left:${left}px;top:${top}px;width:${size}px;height:${size}px;--hit-duration:${final?1000:1500}ms`;
            stage.append(node);
            effect.timers.push(setTimeout(()=>{node.remove();activeHitSpells.delete(effect);},final?1000:1500));
        };
        // Keep the added impact inside the existing three-second finale.
        if(final)effect.timers.push(setTimeout(show,1750));else show();
    }
    function animateHit(target,attacker,final,spell) {
        if(window.ArenaCrabAnimation?.hit({source:document.querySelector(attacker),victim:document.querySelector(target),final})){
            if(final)catFinaleUntil=Math.max(catFinaleUntil,Date.now()+3100);
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(final&&document.querySelector(target)?.querySelector('.battle-pet.octopus'))octopusFinaleUntil=Date.now()+4100;
        if(final){const pet=document.querySelector(target)?.querySelector('.battle-pet.ca-map');if(pet){window.SharkAnimation?.markDefeated(pet);catFinaleUntil=Math.max(catFinaleUntil,Date.now()+3100);}}
        const mamSource=document.querySelector(attacker),mamVictim=document.querySelector(target);
        const mamSourcePet=mamSource?.querySelector('.battle-pet.sprout');
        if(mamSourcePet&&window.MamSachAnimation){
            if(final)catFinaleUntil=Math.max(catFinaleUntil,Date.now()+3100);
            const mamVictimPet=mamVictim?.querySelector('.battle-pet'),label=document.querySelector('#spell-announcement');
            if(label)label.textContent='';
            if(mamVictim)mamVictim.dataset.spell='mam-sach';
            const impact=()=>{
                if(!mamVictim?.isConnected||!mamVictimPet)return;
                mamVictimPet.dataset.mood=final?'lose':'hit';mamVictim.classList.add('taking-hit');
                if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(mamVictimPet,final?'lose':'hit');
            };
            mamSource.classList.add('attacking');window.MamSachAnimation.hit({source:mamSource,victim:mamVictim,final});
            if(final)setTimeout(impact,1750);else impact();
            ArenaAudio.effect(final?'beam':spell[0]);
            setTimeout(()=>{
                mamSource?.classList.remove('attacking');mamVictim?.classList.remove('taking-hit');
                if(mamSourcePet.isConnected)mamSourcePet.dataset.mood=final?'win':'idle';
                if(mamVictimPet?.isConnected){mamVictimPet.dataset.mood=final?'lose':'idle';if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(mamVictimPet,final?'lose':'idle');}
                if(label?.isConnected&&label.dataset.mamSach==='true')label.textContent='';
            },final?3000:1100);
            return;
        }
        const owlSource=document.querySelector(attacker),owlVictim=document.querySelector(target);
        if(typeof OwlAnimation!=='undefined'&&OwlAnimation.hit({source:owlSource,victim:owlVictim,final})){
            if(final)owlFinaleUntil=Date.now()+3100;
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(window.HorseAnimation?.hit({source:document.querySelector(attacker),victim:document.querySelector(target),final})){
            if(final)catFinaleUntil=Math.max(catFinaleUntil,Date.now()+3100);
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(typeof ArenaStarfish!=='undefined' && ArenaStarfish.animate(target,attacker,final)){
            if(final)catFinaleUntil=Math.max(catFinaleUntil,Date.now()+3100);
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(window.ArenaDolphin?.hit({source:document.querySelector(attacker),victim:document.querySelector(target),final})){
            if(final)catFinaleUntil=Math.max(catFinaleUntil,Date.now()+3100);
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(browser&&window.SharkAnimation?.animate(target,attacker,final)){
            if(final)catFinaleUntil=Date.now()+3100;
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(window.ButterflyAnimation?.hit({source:document.querySelector(attacker),victim:document.querySelector(target),final})){
            if(final)catFinaleUntil=Math.max(catFinaleUntil,Date.now()+3100);
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(typeof TigerAnimation!=='undefined' && TigerAnimation.hit({source:document.querySelector(attacker),victim:document.querySelector(target),final})){
            if(final&&TigerAnimation.remaining()>0)catFinaleUntil=Math.max(catFinaleUntil,Date.now()+3100);
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(typeof ArenaVoi!=='undefined' && ArenaVoi.animate(target,attacker,final)){
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(typeof ArenaLion!=='undefined' && ArenaLion.animate(target,attacker,final)){
            if(final)catFinaleUntil=Date.now()+3100;
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        const stage=document.querySelector('#battle-stage'),victim=document.querySelector(target),source=document.querySelector(attacker);
        const sourcePet=source?.querySelector('.battle-pet'),victimPet=victim?.querySelector('.battle-pet');
        if(sourcePet?.classList.contains('fox')&&window.FoxAnimation){
            if(final)catFinaleUntil=Date.now()+3100;
            if(victim)victim.dataset.spell='fox';
            const impact=()=>{if(!victim?.isConnected||!victimPet)return;victimPet.dataset.mood=final?'lose':'hit';victim.classList.add('taking-hit');};
            const show=()=>{
                if(!stage?.isConnected||!sourcePet.isConnected)return;
                if(final)catFinaleUntil=Date.now()+3100;
                if(final)setTimeout(impact,1750);else impact();
                source.classList.add('attacking');window.FoxAnimation.hit({source,victim,final});
                const label=document.querySelector('#spell-announcement');if(label)label.textContent='';
                ArenaAudio.effect(final?'beam':spell[0]);
                setTimeout(()=>{victim?.classList.remove('taking-hit');source?.classList.remove('attacking');if(victimPet?.isConnected&&!final)victimPet.dataset.mood='idle';if(sourcePet.isConnected)window.FoxAnimation.play(sourcePet,final?'win':'idle');},final?3000:1100);
            };
            // Start the impact and result delay with the decoded images on a cold load.
            window.FoxAnimation.ready().then(show).catch(()=>{
                if(!sourcePet.isConnected)return;
                sourcePet.dataset.mood='attack';impact();
                setTimeout(()=>{victim?.classList.remove('taking-hit');if(victimPet?.isConnected&&!final)victimPet.dataset.mood='idle';if(sourcePet.isConnected)sourcePet.dataset.mood='idle';},1100);
            });
            return;
        }
        if(sourcePet?.classList.contains('eagle')&&window.EagleAnimation){
            if(final)catFinaleUntil=Date.now()+3100;
            if(victim)victim.dataset.spell='eagle';
            const impact=()=>{if(!victim?.isConnected)return;victimPet.dataset.mood=final?'lose':'hit';victim.classList.add('taking-hit');};
            if(final)setTimeout(impact,1750);else impact();
            source.classList.add('attacking');window.EagleAnimation.hit({source,victim,final});
            const label=document.querySelector('#spell-announcement');if(label)label.textContent='';
            ArenaAudio.effect(final?'beam':spell[0]);
            setTimeout(()=>{victim?.classList.remove('taking-hit');source?.classList.remove('attacking');if(sourcePet.isConnected)window.EagleAnimation.play(sourcePet,final?'win':'idle');},final?3000:1100);
            return;
        }
        if(sourcePet?.classList.contains('octopus')&&typeof OctopusAnimation!=='undefined'){
            if(final)octopusFinaleUntil=Math.max(octopusFinaleUntil,Date.now()+3100);
            sourcePet.dataset.mood=final?'ultimate':'attack';source?.classList.add('attacking');
            const label=document.querySelector('#spell-announcement');if(label)label.textContent=final?'':'✦ Sóng tay Bạch tuộc';
            const impact=()=>{if(!victim?.isConnected||!victimPet)return;victim.dataset.spell='ink';victimPet.dataset.mood=final?'lose':'hit';victim.classList.add('taking-hit');};
            if(final)setTimeout(impact,1750);else impact();
            ArenaAudio.effect(final?'beam':spell[0]);
            setTimeout(()=>{
                source?.classList.remove('attacking');victim?.classList.remove('taking-hit');
                if(sourcePet.isConnected)sourcePet.dataset.mood='idle';
                if(victimPet?.isConnected&&!final)victimPet.dataset.mood='idle';
                if(label?.isConnected)label.textContent='';
            },final?3000:1200);
            return;
        }
        const rabbitUltimate=final&&sourcePet?.classList.contains('rabbit')&&typeof RabbitAnimation!=='undefined';
        if(rabbitUltimate)catFinaleUntil=Math.max(catFinaleUntil,Date.now()+3100);
        const bearUltimate=final&&sourcePet?.classList.contains('gau')&&typeof BearAnimation!=='undefined';
        if(bearUltimate){catFinaleUntil=Math.max(catFinaleUntil,Date.now()+3100);stage?.classList.add('bear-ultimate');setTimeout(()=>stage?.classList.remove('bear-ultimate'),3000);}
        const playBear=(pet,mode,onFinish)=>{const canvas=pet?.querySelector('canvas[data-bear]');if(canvas&&typeof BearAnimation!=='undefined')BearAnimation.play(canvas,mode,{onFinish});};
        const beeAttack=sourcePet?.classList.contains('bee')&&Boolean(window.ArenaBeeAnimation);
        const beeUltimate=final&&beeAttack;
        if(beeUltimate)catFinaleUntil=Date.now()+3100;
        const catAttack=sourcePet?.classList.contains('cat')&&Boolean(window.ArenaCatAnimation);
        const catUltimate=final&&catAttack;
        const sparrowAttack=sourcePet?.classList.contains('sparrow')&&Boolean(window.ArenaSparrowAnimation);
        const sparrowUltimate=final&&sparrowAttack;
        if(sparrowUltimate)catFinaleUntil=Date.now()+3100;
        if(catUltimate)catFinaleUntil=Date.now()+3100;
        victim?.classList.remove('taking-hit');source?.classList.remove('attacking');if(victim)void victim.offsetWidth;
        const hit=()=>{if(!victim?.isConnected||!victimPet)return;victim.dataset.spell=beeAttack?'bee':catAttack?'cat':rabbitUltimate?'moon':bearUltimate?'bear':spell[0];victimPet.dataset.mood=final&&!victimPet.classList.contains('gau')?'lose':'hit';victim.classList.add('taking-hit');playBear(victimPet,'hit',()=>{if(final&&victimPet.isConnected){victimPet.dataset.mood='lose';playBear(victimPet,'defeat');}});};
        if(beeUltimate||rabbitUltimate||catUltimate||bearUltimate||sparrowUltimate)setTimeout(hit,1750);else hit();
        if(sourcePet)sourcePet.dataset.mood=beeUltimate||rabbitUltimate||catUltimate||bearUltimate||sparrowUltimate?'ultimate':'attack';
        if(sparrowUltimate)window.ArenaSparrowAnimation.ultimate({source,victim});
        if(beeAttack)window.ArenaBeeAnimation.hit({source,victim,final,animateVictim:false});
        window.ArenaCatAnimation?.hit({source,victim,final});
        source?.classList.add('attacking');
        if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(sourcePet,rabbitUltimate?'ultimate':'attack');
        playBear(sourcePet,bearUltimate?'ultimate':'attack');
        const announcement=document.querySelector('#spell-announcement');
        if(announcement)announcement.textContent=beeAttack||rabbitUltimate||catAttack||bearUltimate||sparrowAttack?'':'✦ '+spell[1];
        if(final){if(!beeUltimate&&!rabbitUltimate&&!catUltimate&&!bearUltimate&&!sparrowUltimate)stage?.classList.add(attacker==='#fighter-me'?'ultimate-right':'ultimate-left');ArenaAudio.effect('beam');}else ArenaAudio.effect(spell[0]);
        setTimeout(()=>{
            victim?.classList.remove('taking-hit');source?.classList.remove('attacking');
            for(const node of [victim,source])if(node?.isConnected){const pet=node.querySelector('.battle-pet');const mood=final&&node===victim?'lose':'idle';pet.dataset.mood=mood;if(pet!==victimPet&&typeof RabbitAnimation!=='undefined')RabbitAnimation.play(pet,mood);const bearMode=final?(node===victim?'defeat':'win'):'idle';playBear(pet,bearMode);if(pet?.classList.contains('gau'))pet.dataset.mood=bearMode==='defeat'?'lose':bearMode;}
            if(announcement?.isConnected)announcement.textContent='';
        },beeUltimate||rabbitUltimate||catUltimate||bearUltimate||sparrowUltimate?3000:1600);
    }
    function dispatchBattleHit(target,attacker,final) {
        const spell=attackSpell(attacker);
        playHitSpell(target,attacker,spell,final);
        if(final&&[target,attacker].some(selector=>document.querySelector(selector)?.querySelector('.battle-pet.cu-meo')))owlFinaleUntil=Math.max(owlFinaleUntil,Date.now()+3100);
        window.HorseAnimation?.notifyVictim(target,attacker,final);
        if(typeof RabbitAnimation!=='undefined')RabbitAnimation.notifyVictim(target,attacker,final);
        if(typeof ArenaVoi!=='undefined')ArenaVoi.notifyVictim(target,attacker,final);
        animateHit(target,attacker,final,spell);
    }
    function updateBattleVisuals() {
        const b=currentBattle;if(!b||currentRoute!=='battle')return;
        const current=[b.hp,b.opponentHp],before=visualHp;
        if(before){if(b.hp<before[0])dispatchBattleHit('#fighter-me','#fighter-opponent',b.hp===0);if(b.opponentHp<before[1])dispatchBattleHit('#fighter-opponent','#fighter-me',b.opponentHp===0);}
        visualHp=current;
        for(const [id,hp]of [['#fighter-me',b.hp],['#fighter-opponent',b.opponentHp]]){
            const node=document.querySelector(id);if(!node)continue;
            node.querySelector('.split b:last-child').textContent=hp+' / 100 ♥';
            const m=node.querySelector('.meter');m.setAttribute('aria-valuenow',hp);m.querySelector('span').style.setProperty('--value',hp+'%');
        }
        const now=b.mode==='bot'?Date.now():arenaNow();
        document.querySelectorAll('[data-battle-answer]').forEach(el=>el.disabled=b.answer!==null||b.resolved||now>=b.deadline||now<(b.readyAt||0));
        updateBattleRound(b);
        const feedback=document.querySelector('#learning-battle-feedback');if(feedback){feedback.textContent=b.feedback||'Em hãy chọn một đáp án.';feedback.classList.toggle('wrong',Boolean(b.feedback?.includes('chưa đúng')));}
        for(const [id,value]of [['#my-emote',b.myEmote],['#opponent-emote',b.opponentEmote]]){
            const node=document.querySelector(id);if(node)node.textContent=value===null||value===undefined?'':emotes[value].join(' ');
        }
        updateEmoteControls(b);
    }

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
        setMobileMenu(false,false);
        const toggle=document.querySelector('#learning-menu-toggle');if(!toggle)return;
        toggle.onclick=()=>setMobileMenu(toggle.getAttribute('aria-expanded')!=='true');
        document.querySelector('#learning-menu-close').onclick=()=>setMobileMenu(false);
        document.querySelector('#learning-menu-backdrop').onclick=()=>setMobileMenu(false);
        document.querySelector('#learning-navigation').onclick=event=>{if(event.target.closest('a'))setMobileMenu(false,false);};
    }
    function setArenaMode(mode) {
        if(!['quick','friends','bot'].includes(mode))return;
        arenaMode=mode;try{sessionStorage.setItem('5bmath-arena-mode',mode);}catch{}
        document.querySelectorAll('[data-arena-mode]').forEach(button=>{
            const selected=button.dataset.arenaMode===mode;
            button.setAttribute('aria-selected',String(selected));button.tabIndex=selected?0:-1;button.classList.toggle('selected',selected);
        });
        for(const key of ['quick','friends','bot']){const panel=document.querySelector('#arena-panel-'+key);if(panel)panel.hidden=key!==mode;}
        const usage=document.querySelector('#arena-mode-usage');if(usage)usage.innerHTML=usagePanel(mode==='bot'?'bot':'human');
        updateArenaDiscipline();
        if(mode==='quick')loadPublicRooms();
    }
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
        currentRoute = route;
        const title = routes[route][1];
        const selected = sections[route] || route;
        let body;
        const featureKey={weekly:'learning_open',topics:'learning_open',lesson:'learning_open',advanced:'learning_open',
            exams:'practice_open',arena:'arena_open',rank:'leaderboard_open'}[route];
        if(live && featureKey && PlatformAPI.snapshot.features?.[featureKey]===false) body=intro(title,'Chức năng đang được tạm dừng. Em có thể chọn hoạt động khác.')+link('Về tổng quan','dashboard');
        else if (browser && !host.progress?.name && !['zoomRegistration','classroom'].includes(route)) body = accountGate();
        else body = route === 'advanced' ? views.lesson(true) : views[route]();
        return `<div id="learning-app"><button type="button" class="learning-menu-backdrop" id="learning-menu-backdrop" tabindex="-1" aria-label="Đóng menu" hidden></button><aside class="sidebar" id="learning-navigation" aria-label="Menu Góc học tập"><div class="learning-drawer-head"><strong>Góc Học Tập</strong><button type="button" id="learning-menu-close" aria-label="Đóng menu">×</button></div><a class="app-logo" href="${browser && location.protocol === 'file:' ? '#home' : './'}"><img src="5bmath-logo.svg" alt="5BMath Gieo Mầm Toán" width="628" height="168"></a><nav class="navigation" aria-label="Góc Học Tập">${navigation.filter(([id])=>id==='classroom'?isInternal():['upgrade','zoomRegistration'].includes(id)?!isInternal():true).map(([id,label,symbol]) => `<a href="${href(id)}" ${id==='profile'?'data-account-nav aria-label="Tài khoản'+(unreadNotificationCount()?', '+unreadNotificationCount()+' thông báo chưa đọc':'')+'"':''} ${id==='classroom'?'data-classroom-nav aria-label="Lớp Zoom"':''} ${selected === id ? 'aria-current="page"' : ''}>${icon(symbol,19)}<span>${label}</span>${id==='profile'?unreadBadge():id==='classroom'?classUnreadBadge(classUnreadCount(classroomUnread().total)):''}</a>`).join('')}</nav><a class="sidebar-pet" href="${href('mascot')}">${art(state.mascot)}<div><b>${escape(petName())}</b><small>Cấp ${level()} · ${content.format(state.points)} điểm</small></div>${icon('chevron',15)}</a></aside>
        <div class="app-main"><header class="topbar"><button type="button" class="learning-menu-toggle" id="learning-menu-toggle" aria-label="Mở menu học tập" aria-expanded="false" aria-controls="learning-navigation"><svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16"/></svg></button><a class="mobile-logo" href="${browser && location.protocol === 'file:' ? '#home' : './'}"><img src="5bmath-logo.svg" alt="5BMath Gieo Mầm Toán" width="628" height="168"></a><span class="top-title">Góc Học Tập ${icon('chevron',14)} <b>${title}</b></span><div class="top-right">${isInternal()?'<span class="svip-badge">👑 SVip</span>':badge(member(),'sage')}<a class="profile" href="${href('profile')}">${avatar()}<span><b>${escape(name())}</b><small>Khối ${grade()}</small></span>${icon('down',14)}</a></div></header><div class="content">${body}</div></div></div>`;
    }

    const actions = {
        async complete() {
            const lesson = selectedLesson();
            if(live){await mutate('lessons/'+lesson.id+'/complete');refresh();return;}
            if (!state.completed[lesson.id]) {
                state.completed[lesson.id] = {date:new Date().toISOString(),grade:grade()};
                if (grade() === 5 && ['decimal','percent'].includes(lesson.topic) && !host.progress.completed.includes(lesson.topic)) {
                    host.progress.completed.push(lesson.topic);
                    host.saveProgress();
                }
                save();
            }
            refresh();
        },
        practice:() => createExam({topic:selectedLesson().topic,count:3}),
        video:() => host.showModal('<h2 class="modal-title">Video bài giảng</h2>'+lessonVideo(selectedLesson())),
        'create-exam':() => createExam({difficulty:Number(document.querySelector('#exam-difficulty').value)}),
        'create-topic':()=>{const value=document.querySelector('#exam-topic').value;return createExam(document.querySelector('#exam-scope').value==='weekly'?{maxWeek:week(),week:value?Number(value.replace('week-','')):undefined,category:'content'}:{topic:value,category:'content'});},
        'create-school':()=>createExam({category:'school',school:document.querySelector('#exam-school').value}),
        previous() { const exam = getExam(); exam.index = Math.max(0,exam.index - 1); save(); refresh(); },
        next() { const exam = getExam(); exam.index = Math.min(exam.questions.length - 1,exam.index + 1); save(); refresh(); },
        'submit-exam':requestSubmit,
        'start-bot':trigger=>openArenaPreflight('bot',{botLevel:Number(document.querySelector('#bot-level')?.value)||0},trigger),
        'next-battle':() => currentBattle.mode === 'bot' ? nextBot() : arenaRequest('next',{index:currentBattle.index}).then(pollRoom),
        'create-room':trigger=>openArenaPreflight('create',{},trigger),
        'minimize-room':()=>{sessionStorage.setItem('5bmath-room-mini','1');go('arena');},
        'toggle-music':()=>{ArenaAudio.toggle();document.querySelectorAll('[data-learning=toggle-music]').forEach(b=>b.textContent=ArenaAudio.muted?'🔇 Nhạc: Tắt':'🎵 Nhạc: Bật');},
        'download-material':async()=>{if(!live){host.toast('Tài liệu cần tài khoản VIP trên máy chủ.');return;}const r=await PlatformAPI.request('materials');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([r.text],{type:'text/plain;charset=utf-8'}));a.download='5bmath-phieu-luyen-tap.txt';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),5000);},
        'quick-match':trigger=>openArenaPreflight('quick',{},trigger),
        'copy-room':() => copyText(JSON.parse(sessionStorage.getItem('5bmath-room')).code),
        'copy-room-link':() => copyText(new URL(href('room',{code:JSON.parse(sessionStorage.getItem('5bmath-room')).code}),document.baseURI).href),
        async 'leave-room'() {
            if (sessionStorage.getItem('5bmath-room')) await arenaRequest('leave');
            sessionStorage.removeItem('5bmath-room');
            overlay('');document.querySelector('#waiting-popup')?.remove();go('arena');
        },
        async 'leave-battle'() {
            if(!currentBattle)return;
            if (currentBattle.mode === 'bot') {
                finishBattle({...currentBattle,outcome:'left',rounds:currentBattle.index,points:0});
            } else {
                if(currentBattle.hp<=0||currentBattle.opponentHp<=0||currentBattle.resolved&&currentBattle.index>=currentBattle.questions.length-1){await pollRoom();return;}
                const battleId=currentBattle.id;
                host.showModal('<div class="arena-leave-confirm"><h2 class="modal-title">Em muốn rời trận?</h2><p class="modal-copy">Rời trận bây giờ sẽ tính là thua và trừ 1 kinh nghiệm. Đối thủ không nhận kinh nghiệm từ trận bỏ dở. Trận này không cộng vào số trận thắng/thua.</p><p class="modal-copy">Bỏ trận nhiều lần sẽ phải tạm nghỉ đấu với người.</p><div class="actions"><button type="button" class="btn dark" id="arena-continue-playing">Tiếp tục chơi</button><button type="button" class="btn outline" id="arena-confirm-leave">Rời trận</button></div></div>');
                document.querySelector('#arena-continue-playing').onclick=()=>document.querySelector('#modal').close();
                document.querySelector('#arena-confirm-leave').onclick=async event=>{
                    const control=event.currentTarget;control.disabled=true;
                    try{if(currentBattle?.id===battleId){const result=await arenaRequest('leave');document.querySelector('#modal').close();if(result.status==='finished')finishBattle(result.result);else await pollRoom();}}
                    catch(error){host.toast(error.message);}
                    finally{if(control.isConnected)control.disabled=false;}
                };
                const dialog=document.querySelector('#modal'),trap=event=>{
                    if(event.key!=='Tab')return;
                    const controls=[...dialog.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled)')].filter(node=>node.getClientRects().length),index=controls.indexOf(document.activeElement);
                    if(event.shiftKey&&index<=0){event.preventDefault();controls.at(-1)?.focus();}
                    else if(!event.shiftKey&&index===controls.length-1){event.preventDefault();controls[0]?.focus();}
                };
                dialog.addEventListener('keydown',trap);dialog.addEventListener('close',()=>dialog.removeEventListener('keydown',trap),{once:true});
                document.querySelector('#arena-continue-playing').focus();
            }
        },
        'choose-sparrow':async () => { if(live)await mutate('mascot',{mascot:'sparrow'});else {state.mascot = 'sparrow';save();}refresh(); },
        'choose-butterfly':async () => { if(live)await mutate('mascot',{mascot:'butterfly'});else {state.mascot = 'butterfly';save();}refresh(); },
        'choose-dolphin':async () => { if(live)await mutate('mascot',{mascot:'dolphin'});else {state.mascot = 'dolphin';save();}refresh(); },
        'choose-cu-meo':async () => { if(live)await mutate('mascot',{mascot:'cu-meo'});else {state.mascot = 'cu-meo';save();}refresh(); },
        'choose-sprout':async () => { if(live)await mutate('mascot',{mascot:'sprout'});else {state.mascot = 'sprout';save();}refresh(); },
        'choose-voi':async () => { if(live)await mutate('mascot',{mascot:'voi'});else {state.mascot = 'voi';save();}refresh(); },
        'choose-lion':async () => { if(live)await mutate('mascot',{mascot:'lion'});else {state.mascot = 'lion';save();}refresh(); },
        'choose-starfish':async () => { if(live)await mutate('mascot',{mascot:'starfish'});else {state.mascot = 'starfish';save();}refresh(); },
        'choose-fox':async () => { if(live)await mutate('mascot',{mascot:'fox'});else {state.mascot = 'fox';save();}refresh(); },
        'choose-tiger':async () => { if(live)await mutate('mascot',{mascot:'tiger'});else {state.mascot = 'tiger';save();}refresh(); },
        'choose-eagle':async () => { if(live)await mutate('mascot',{mascot:'eagle'});else {state.mascot = 'eagle';save();}refresh(); },
        'choose-ca-map':async () => { if(live)await mutate('mascot',{mascot:'ca-map'});else {state.mascot = 'ca-map';save();}refresh(); },
        'choose-bee':async () => { if(live)await mutate('mascot',{mascot:'bee'});else {state.mascot = 'bee';save();}refresh(); },
        'choose-octopus':async () => { if(live)await mutate('mascot',{mascot:'octopus'});else {state.mascot = 'octopus';save();}refresh(); },
        'choose-rabbit':async () => { if(live)await mutate('mascot',{mascot:'rabbit'});else {state.mascot = 'rabbit';save();}refresh(); },
        'choose-crab':async () => { if(live)await mutate('mascot',{mascot:'crab'});else {state.mascot = 'crab';save();}refresh(); },
        'choose-gau':async () => { if(live)await mutate('mascot',{mascot:'gau'});else {state.mascot = 'gau';save();}refresh(); },
        'choose-dog':async () => { if(live)await mutate('mascot',{mascot:'dog'});else {state.mascot = 'dog';save();}refresh(); },
        'choose-cat':async () => { if(live)await mutate('mascot',{mascot:'cat'});else {state.mascot = 'cat';save();}refresh(); },
        'choose-horse':async () => { if(live)await mutate('mascot',{mascot:'horse'});else {state.mascot = 'horse';save();}refresh(); },
        'refresh-account':async () => {applySnapshot(await PlatformAPI.refresh());refresh();},
        'review-upgrade':async () => {await mutate('dev/upgrade',{requestKey:uid()});refresh();host.toast('Đã mô phỏng nâng cấp VIP để kiểm tra luồng giới thiệu.');},
        'copy-invite':() => copyText(state.inviteCode),
        'copy-invite-link':() => copyText(new URL('./?invite=' + state.inviteCode,document.baseURI).href),
        'class-preview':() => document.querySelector('#live-class')?.click() || host.showModal('<h2 class="modal-title">Buổi học mẫu 45 phút</h2><ol><li>5 phút khởi động.</li><li>10 phút giải thích bằng ví dụ.</li><li>15 phút học sinh tự làm.</li><li>10 phút chữa bài.</li><li>5 phút củng cố.</li></ol><p>Lịch học và phòng Zoom đang chờ thiết lập.</p>'),
        rename() {
            host.showModal(`<h2 class="modal-title">Đổi biệt danh</h2><form id="learning-name-form"><label class="field"><span>Biệt danh của em</span><input name="name" value="${escape(name())}" minlength="2" maxlength="40" autocomplete="nickname" aria-describedby="nickname-help nickname-error" required></label><p class="modal-copy" id="nickname-help">${escape(nicknames.help)}</p><p id="nickname-error" role="alert"></p><button class="btn dark" type="submit">Lưu tên</button></form>`);
            const nameInput = document.querySelector('#learning-name-form [name=name]');
            nameInput.oninput = () => {nameInput.removeAttribute('aria-invalid');document.querySelector('#nickname-error').textContent='';};
            document.querySelector('#learning-name-form').onsubmit = async event => {
                event.preventDefault();
                const error = nicknames.error(nameInput.value);
                if (error) {document.querySelector('#nickname-error').textContent=error;nameInput.setAttribute('aria-invalid','true');nameInput.focus();return;}
                const value = nicknames.normalize(nameInput.value);
                if(live){
                    try{await mutate('profile',{name:value});document.querySelector('#modal').close();refresh();}
                    catch(error){document.querySelector('#nickname-error').textContent=error.message;}
                    return;
                }
                host.progress.name = value;
                host.saveProgress();
                document.querySelector('#modal').close();
                refresh();
            };
        },
        async logout() { if(live){await PlatformAPI.logout();sessionStorage.removeItem('5bmath-room');sessionStorage.removeItem('5bmath-bot-battle');}host.progress.name = ''; host.saveProgress(); location.assign(new URL(location.protocol==='file:'?'index.html#home':'./',document.baseURI)); },
    };

    function mount(route) {
        stopPaymentWatch();
        clearInterval(interval);
        if (!host.progress?.name){mountNavigation();return;}
        if(route==='profile') {
            if(typeof ThemeManager !== 'undefined') ThemeManager.mountSettings();
            if(live){loadAccountPage('notifications');loadAccountPage('referrals');}
        }
        startNotificationPolling();
        if(route==='rank')loadRank();
        if(route==='classroom')loadClass();
        if(route==='payment')loadPayment();
        if(route==='arena')loadPublicRooms();
            if(route==='battleResult'){ArenaAudio.setActive(true);const victory=document.querySelector('.victory');setTimeout(()=>ArenaAudio.effect(victory?'win':'lose'),100);setTimeout(()=>document.querySelector('.confetti')?.remove(),3000);}
        ArenaAudio.setActive((sections[route]||route)==='arena');
        if(live && !document.hidden)PlatformAPI.request('heartbeat',{}).catch(()=>{});
        if (!document.hidden) activityStarted = Date.now();
        if (['lesson','advanced'].includes(route)) {
            state.lastLesson = selectedLesson().id;
            if(live)PlatformAPI.request('lessons/'+state.lastLesson+'/open',{}).catch(error=>host.toast(error.message));
            save();
        }
        if (route === 'battle') {
            if(!hitSpellImages.length)for(const [key]of attackSpells){const image=new Image();image.src='arena-art/'+key+'-spell.webp';hitSpellImages.push(image);}
            try {
                if (!sessionStorage.getItem('5bmath-room')) currentBattle = JSON.parse(sessionStorage.getItem('5bmath-bot-battle') || 'null');
            }
            catch { currentBattle = null; }
            if (currentBattle) {
                document.querySelector('#app').innerHTML = render(route);visualHp=[currentBattle.hp,currentBattle.opponentHp];
                updateBattleRound(currentBattle);
                updateEmoteControls(currentBattle);
            }
        }
        if(typeof RuntimeAssets==='undefined'||!RuntimeAssets.managed){
            if(typeof ArenaLion!=='undefined')ArenaLion.mount();
            if(browser)window.ArenaBeeAnimation?.sync();
        }
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
            const action = event.target.closest('[data-learning]');
            const questionButton = event.target.closest('[data-question]');
            const answer = event.target.closest('[data-battle-answer]');
            const rankButton = event.target.closest('[data-rank]');
            const challenge=event.target.closest('[data-challenge]'),emote=event.target.closest('[data-emote]'),classButton=event.target.closest('[data-class-tab]'),classRanking=event.target.closest('[data-class-ranking]'),fee=event.target.closest('[data-fee]');
            const mode=event.target.closest('[data-arena-mode]');
            const notification = event.target.closest('[data-notification]');
            const accountPage=event.target.closest('[data-account-page]');
            try {
                if(mode){setArenaMode(mode.dataset.arenaMode);}
                else if(challenge){if(challenge.disabled)return;challenge.dataset.humanPending='true';challenge.disabled=true;try{await enterRoom('join',{code:challenge.dataset.challenge});}finally{delete challenge.dataset.humanPending;updateArenaDiscipline();}}
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
                    action.disabled = true;
                    if(action.dataset.botLevel!==undefined)document.querySelector('#bot-level').value=action.dataset.botLevel;
                    await actions[action.dataset.learning](action);
                }
            } catch (error) { host.toast(error.message); }
            finally { if (action?.isConnected) {delete action.dataset.humanPending;action.disabled = false;}updateArenaDiscipline(); }
        };
        document.querySelector('#learning-app').onchange = async event => {
            const target = event.target;
            if(target.id==='review-incorrect'){document.querySelectorAll('[data-review-correct]').forEach(el=>el.hidden=target.checked&&el.dataset.reviewCorrect==='true');return;}
            if(target.id==='class-select'){stopPaymentWatch();document.querySelector('#modal')?.close();loadClass();return;}
            if(target.id==='exam-scope'){document.querySelector('#exam-content-search').value='';document.querySelector('#exam-topic').innerHTML=examOptions(target.value);return;}
            if (target.name === 'learning-answer') {
                const exam = getExam();
                if (Date.now() >= exam.expiresAt) { finishExam(exam); return; }
                if(live){
                    const controls=[...document.querySelectorAll('[name=learning-answer], [data-learning=submit-exam], [data-learning=next], [data-learning=previous], [data-question]')];
                    controls.forEach(control=>control.disabled=true);
                    try{
                        const result=await PlatformAPI.request('exams/'+exam.id+'/answers',{position:exam.index+1,answer:target.value});
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
            button.dataset.humanPending='true';
            button.disabled = true;
            try { const raw=document.querySelector('#learning-room-code').value.trim();let code=raw;try{code=new URL(raw).searchParams.get('code')||'';}catch{}if(!/^[a-z0-9]{6}$/i.test(code))throw new Error('Nhập mã gồm 6 ký tự hoặc liên kết phòng hợp lệ.');await enterRoom('join',{code:code.toUpperCase()}); }
            catch (error) { host.toast(error.message); }
            finally { delete button.dataset.humanPending;button.disabled = false;updateArenaDiscipline(); }
        };
        const birthForm = document.querySelector('#learning-birth-form');
        if (birthForm) birthForm.onsubmit = event => {
            event.preventDefault();
            try { setBirthYear(new FormData(birthForm).get('birthYear')); refresh(); }
            catch (error) { host.toast(error.message); }
        };
        if(sessionStorage.getItem('5bmath-room'))pollRoom();
        else if(route==='room'&&query('code'))enterRoom('join',{code:query('code').toUpperCase()}).catch(e=>host.toast(e.message));
        interval = setInterval(() => {
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
            if(document.hidden)pausePaymentCheck();else resumePaymentCheck();
            if (document.hidden) {recordActivity();clearTimeout(notificationPollTimer);notificationPollTimer=null;}
            else if (document.body.classList.contains('learning-mode') && host.progress?.name) {activityStarted = Date.now();resumeArena();refreshNotificationSummary({focus:true});}
        });
        window.addEventListener('pagehide',recordActivity);
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

    return {routes,configure,render,mount,unmount,setBirthYear,avatar};
})();

if (typeof module !== 'undefined' && module.exports) module.exports = LearningApp;
