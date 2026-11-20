'use strict';

// Run before stylesheets so a saved appearance is present at first paint.
const ThemeManager = (() => {
    const defaultTheme = 'clay-sprout';
    const options = Object.freeze([
        {id:'morning-garden',number:'01',name:'Vườn Sương Mai',description:'Thoáng nhẹ, màu dịu và khung thanh mảnh.'},
        {id:'crayon-workshop',number:'02',name:'Xưởng Bút Sáp',description:'Giấy ấm, viền sáp và nét nhấn vui tươi.'},
        {id:'clay-sprout',number:'03',name:'Mầm Sách 3D',description:'Khung nổi mềm, nút bấm như đất sét.'},
        {id:'garden-adventure',number:'04',name:'Vườn Khám Phá',description:'Viền xanh rõ nét, lá non và sắc cam ấm.'},
        {id:'garden-notebook',number:'05',name:'Sổ Tay Vườn Toán',description:'Trang ô ly nhẹ, thẻ giấy và bút đánh dấu.'},
    ].map(Object.freeze));
    const valid = value => options.some(option => option.id === value);
    const normalize = value => valid(value) ? value : defaultTheme;
    const label = value => options.find(option => option.id === value)?.name || options.find(option => option.id === defaultTheme).name;
    const accountKey = '5bmath-appearance-v1', guestKey = '5bmath-guest-theme-v1';
    let owner = null, savedTheme = defaultTheme, theme = defaultTheme, binding = null;
    const browser = typeof document !== 'undefined';
    function read(key) { try { return JSON.parse(localStorage.getItem(key)); } catch { return null; } }
    function write(key,value) { try { localStorage.setItem(key,JSON.stringify(value)); return true; } catch { return false; } }
    function guestTheme() { return normalize(read(guestKey)); }
    function remember() {
        if(owner !== null) write(accountKey,{owner,theme:savedTheme});
        else try { localStorage.removeItem(accountKey); } catch {}
    }
    function apply(value) {
        theme = normalize(value);
        if(!browser) return theme;
        document.documentElement.dataset.theme = theme;
        if(typeof CustomEvent === 'function') document.dispatchEvent(new CustomEvent('5bmath:themechange',{detail:{theme}}));
        return theme;
    }
    function sync(snapshot) {
        if(!snapshot || typeof snapshot.authenticated !== 'boolean') return;
        const nextOwner = snapshot.authenticated && snapshot.account?.id ? String(snapshot.account.id) : null;
        const nextTheme = nextOwner === null ? guestTheme() : normalize(snapshot.state?.theme);
        if(nextOwner !== owner) unmountSettings();
        const wasDirty = binding && binding.draft !== savedTheme;
        owner = nextOwner;
        savedTheme = nextTheme;
        remember();
        if(!binding || !wasDirty) {
            if(binding) binding.draft = savedTheme;
            apply(savedTheme);
        }
        if(binding) updateSettings();
    }
    function renderSettings() {
        return `<section class="card card-pad theme-settings theme-settings-compact" id="appearance" aria-labelledby="appearance-title"><h2 id="appearance-title">Giao diện của em</h2><p id="appearance-help">Chọn một nét riêng cho góc học, rồi bấm Áp dụng.</p><form id="appearance-form"><fieldset class="theme-fieldset" aria-describedby="appearance-help"><legend>Chọn giao diện</legend><div class="theme-options">${options.map(option=>`<label class="theme-option"><input type="radio" name="appearance-theme" value="${option.id}" ${savedTheme===option.id?'checked':''}><span class="theme-preview" data-preview-theme="${option.id}" aria-hidden="true"><span class="theme-sample">✿</span></span><span class="theme-option-copy"><strong>${option.name}</strong><span>${option.description}</span></span><span class="theme-option-check" aria-hidden="true"></span></label>`).join('')}</div></fieldset><p id="appearance-status" class="theme-settings-status" role="status" aria-live="polite">Đang dùng ${label(savedTheme)}.</p><button class="btn dark" type="submit" disabled>Áp dụng</button><p class="learning-notice">${owner===null?'Lưu trong trình duyệt này.':'Giao diện được lưu riêng theo hồ sơ của em để dùng trên thiết bị khác.'}</p></form></section>`;
    }
    function updateSettings(message) {
        const context = binding;
        if(!context?.form.isConnected) return;
        const dirty = context.draft !== savedTheme;
        context.form.querySelectorAll('[name="appearance-theme"]').forEach(input => {
            input.checked = input.value === context.draft;
            input.disabled = context.busy;
        });
        context.form.querySelector('[type="submit"]').disabled = context.busy || !dirty;
        context.form.setAttribute('aria-busy',String(context.busy));
        const status = context.form.querySelector('#appearance-status');
        status.textContent = message || (context.busy ? 'Đang lưu giao diện…' : dirty ? `Đang xem trước ${label(context.draft)}. Bấm Áp dụng để lưu.` : `Đang dùng ${label(savedTheme)}.`);
        status.classList.remove('is-error');
    }
    function preview(value) {
        if(!valid(value) || binding?.busy) return;
        if(binding) binding.draft = value;
        apply(value);
        updateSettings();
    }
    function cancelPreview() {
        if(binding?.busy) return;
        if(binding) binding.draft = savedTheme;
        apply(savedTheme);
        updateSettings();
    }
    function mountSettings() {
        unmountSettings();
        const form = document.querySelector('#appearance-form');
        if(!form) return;
        const context = {form,owner,draft:savedTheme,busy:false,controller:null};
        binding = context;
        context.change = event => {
            if(event.target.name === 'appearance-theme') preview(event.target.value);
        };
        context.cancel = () => cancelPreview();
        context.reset = () => preview(defaultTheme);
        context.submit = async event => {
            event.preventDefault();
            if(context !== binding || context.busy || context.draft === savedTheme) return;
            context.busy = true;
            const chosen = context.draft;
            context.controller = new AbortController();
            updateSettings();
            try {
                if(context.owner !== null) {
                    if(typeof PlatformAPI === 'undefined' || !PlatformAPI.snapshot.authenticated || String(PlatformAPI.snapshot.account?.id) !== context.owner) throw new Error('Tài khoản đã thay đổi. Em hãy tải lại trang.');
                    const result = await PlatformAPI.request('preferences',{theme:chosen},{owner:PlatformAPI.snapshot.account.id,signal:context.controller.signal});
                    if(context !== binding || context.owner !== owner || !form.isConnected) return;
                    if(String(result.account?.id) !== context.owner) throw new Error('Tài khoản đã thay đổi. Em hãy tải lại trang.');
                    savedTheme = normalize(result.state?.theme);
                    remember();
                } else {
                    if(!write(guestKey,chosen)) throw new Error('Trình duyệt chưa cho phép lưu. Em hãy bật bộ nhớ trình duyệt rồi thử lại.');
                    savedTheme = chosen;
                }
                if(context !== binding || context.owner !== owner || !form.isConnected) return;
                context.draft = savedTheme;
                context.busy = false;
                apply(savedTheme);
                updateSettings(`Đã lưu ${label(savedTheme)}. Em có thể tiếp tục học nhé!`);
            } catch(error) {
                if(context !== binding || !form.isConnected) return;
                context.busy = false;
                updateSettings('Chưa lưu giao diện. '+error.message);
                form.querySelector('#appearance-status').classList.add('is-error');
            } finally {
                if(context === binding && context.busy) { context.busy = false; updateSettings(); }
            }
        };
        form.addEventListener('change',context.change);
        form.addEventListener('submit',context.submit);
        updateSettings();
    }
    function unmountSettings() {
        if(binding) {
            const {form,change,submit,cancel,reset,controller} = binding;
            binding = null;
            controller?.abort();
            form.removeEventListener('change',change);
            form.removeEventListener('submit',submit);
            form.querySelector('#appearance-cancel')?.removeEventListener('click',cancel);
            form.querySelector('#appearance-default')?.removeEventListener('click',reset);
        }
        apply(savedTheme);
    }
    if(browser) {
        const cache = read(accountKey);
        if(document.documentElement.dataset.backend === 'database' && cache && typeof cache.owner === 'string' && /^\d+$/.test(cache.owner) && valid(cache.theme)) {
            owner = cache.owner;
            savedTheme = cache.theme;
        } else savedTheme = guestTheme();
        apply(savedTheme);
        window.addEventListener('storage',event => {
            if(event.key === guestKey && owner === null) {
                const dirty = binding && binding.draft !== savedTheme;
                savedTheme = guestTheme();
                if(!dirty) { if(binding) binding.draft = savedTheme; apply(savedTheme); }
                updateSettings();
            } else if(event.key === accountKey && owner !== null) {
                const incoming = read(accountKey);
                if(incoming?.owner !== owner || !valid(incoming.theme)) return;
                const dirty = binding && binding.draft !== savedTheme;
                savedTheme = incoming.theme;
                if(!dirty) { if(binding) binding.draft = savedTheme; apply(savedTheme); }
                updateSettings();
            }
        });
    }
    return {defaultTheme,options,normalize,preview,cancelPreview,sync,renderSettings,mountSettings,unmountSettings,
        get theme(){return theme;},get savedTheme(){return savedTheme;},get owner(){return owner;}};
})();

if(typeof window !== 'undefined') window.ThemeManager = ThemeManager;
if(typeof module !== 'undefined' && module.exports) module.exports = ThemeManager;
