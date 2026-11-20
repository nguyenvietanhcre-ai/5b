(function (global) {
    'use strict';

    const names = {duel:'Đấu trí', capture_flag:'Cướp Cờ', animal_race:'Đua Thú'};
    const labels = {
        loading:'Đang kiểm tra lượt chơi. Em chờ một chút nhé.',
        error:'Chưa xem được số lượt chơi. Em có thể thử lại.',
        inactive:'Phiên học sinh đã thay đổi.',
    };
    const buttonStates = new WeakMap();
    const refreshInterval = 15000;

    function setDisabled(button, base) {
        if (!button) return;
        const state = buttonStates.get(button);
        if (state) state.base = Boolean(base);
        button.disabled = Boolean(base || state?.blocked);
    }

    function block(button, blocked) {
        const state = buttonStates.get(button) || {base:button.disabled};
        state.blocked = blocked;
        buttonStates.set(button, state);
        button.disabled = state.base || blocked;
    }

    function summary(game) {
        if (!Object.hasOwn(names, game)) return '';
        return `<small class="game-allowance-count" data-game-allowance="${game}" data-game-allowance-count="${game}" data-game-allowance-state="loading" role="status" aria-label="Lượt chơi ${names[game]} hôm nay">Đang tải…</small>`;
    }

    function feedback(game) {
        if (!Object.hasOwn(names, game)) return '';
        return `<div class="game-allowance-feedback" data-game-allowance-feedback="${game}" hidden>
            <p data-game-allowance-message role="status"></p><button type="button" class="btn outline" data-game-allowance-retry hidden>Thử lại</button>
        </div>`;
    }

    function identity() {
        if (typeof PlatformAPI === 'undefined') return null;
        const {enabled, snapshot, familyState, familyContext} = PlatformAPI;
        if (!enabled || !snapshot.authenticated || snapshot.familyParent || !snapshot.account?.id) return null;
        const childId = familyState?.activeProfile?.childId;
        if ((familyState || familyContext) && (familyState?.activeProfile?.type !== 'child' || familyState.scope !== 'child' || !childId)) return null;
        return {owner:snapshot.account.id, csrf:snapshot.csrf, context:familyContext, childId};
    }

    function sameIdentity(a, b) {
        return Boolean(a && b && a.owner === b.owner && a.csrf === b.csrf && a.context === b.context && a.childId === b.childId);
    }

    function read(value, childId) {
        const serverTime = Date.parse(value?.serverTime);
        const resetsAt = Date.parse(value?.resetsAt);
        if (!Number.isInteger(value?.childId) || (childId !== undefined && childId !== value.childId) ||
            !/^\d{4}-\d{2}-\d{2}$/.test(value.day) || value.timeZone !== 'Asia/Ho_Chi_Minh' ||
            !Number.isFinite(serverTime) || !Number.isFinite(resetsAt) || resetsAt <= serverTime ||
            !Array.isArray(value.games) || value.games.length !== Object.keys(names).length) throw new Error(labels.error);
        const games = new Map();
        for (const row of value.games) {
            if (!Object.hasOwn(names, row?.id) || games.has(row.id) || !Number.isInteger(row.used) || row.used < 0 ||
                (row.limit === null ? row.remaining !== null : !Number.isInteger(row.limit) || row.limit < 0 || row.remaining !== Math.max(0, row.limit - row.used))) throw new Error(labels.error);
            games.set(row.id, {limit:row.limit, remaining:row.remaining});
        }
        return {games, untilReset:resetsAt - serverTime};
    }

    function mount(game, root, onChange) {
        const owner = identity();
        const extraScopes = new Set();
        let active = Boolean(owner);
        let data = null, state = active ? 'loading' : 'inactive', pending = null, resetTimer, interval;
        let expires = 0, lastNotification = '';

        function errorMessage() {
            if (state !== 'ready') return labels[state];
            const allowance = data.games.get(game);
            if (allowance.limit === 0) return `Cha mẹ đang tạm khóa ${names[game]}. Em có thể hỏi cha mẹ để chơi lại.`;
            return allowance.remaining === 0 ? `Em đã hết lượt ${names[game]} hôm nay. Ngày mai em có thể chơi tiếp.` : '';
        }

        function sync(scope) {
            if (scope && scope !== root) extraScopes.add(scope);
            const message = errorMessage();
            for (const node of [root, ...extraScopes]) {
                if (!node.isConnected) { extraScopes.delete(node); continue; }
                for (const control of node.querySelectorAll('[data-game-admission]')) block(control, Boolean(message));
                const item = data?.games.get(game);
                const value = item ? item.remaining === null ? 'Không giới hạn' : `Còn ${item.remaining} lượt`
                    : state === 'loading' ? 'Đang tải…' : 'Chưa rõ số lượt';
                for (const count of node.querySelectorAll(`[data-game-allowance="${game}"]`)) {
                    count.dataset.gameAllowanceState = state;
                    count.dataset.exhausted = String(item?.remaining === 0);
                    if (count.textContent !== value) count.textContent = value;
                }
                for (const section of node.querySelectorAll(`[data-game-allowance-feedback="${game}"]`)) {
                    const note = section.querySelector('[data-game-allowance-message]');
                    const retry = section.querySelector('[data-game-allowance-retry]');
                    if (message && (state === 'error' || state === 'loading')) {
                        // Keep a focused retry button mounted until the read returns.
                        retry.hidden = state === 'loading' && retry.hidden;
                        retry.disabled = state === 'loading';
                    } else retry.hidden = true;
                    const detail = state === 'loading' && retry.hidden ? '' : message;
                    section.hidden = !detail;
                    if (note.textContent !== detail) note.textContent = detail;
                }
            }
        }

        function publish() {
            sync();
            const key = JSON.stringify([state, data && [...data.games]]);
            if (key === lastNotification) return;
            lastNotification = key;
            onChange?.();
        }

        function valid() {
            if (active && (!root.isConnected || !sameIdentity(owner, identity()))) unmount();
            return active;
        }

        function reset() {
            refresh({visibleOnly:true});
        }

        function pull() {
            if (!valid()) return Promise.resolve(false);
            if (pending) return pending.promise;
            const request = {controller:new AbortController(), promise:null};
            pending = request;
            request.promise = (async () => {
                try {
                    const value = await PlatformAPI.request('game-limits', undefined, {
                        owner:owner.owner, expectedFamilyContext:owner.context, expectedCsrf:owner.csrf,
                        signal:request.controller.signal,
                    });
                    if (pending !== request || !valid()) return false;
                    const result = read(value, owner.childId);
                    data = result;
                    state = 'ready';
                    expires = performance.now() + result.untilReset;
                    clearTimeout(resetTimer);
                    resetTimer = setTimeout(reset, result.untilReset);
                    publish();
                    return !errorMessage();
                } catch {
                    if (pending !== request || !valid()) return false;
                    data = null;
                    state = 'error';
                    clearTimeout(resetTimer);
                    publish();
                    return false;
                } finally {
                    if (pending === request) pending = null;
                }
            })();
            return request.promise;
        }

        async function refresh({visibleOnly=false}={}) {
            if (!valid()) return false;
            // A pre-mutation poll must not replace a post-mutation read.
            const prior = pending;
            if (prior) {
                pending = null;
                prior.controller.abort();
            }
            data = null;
            state = 'loading';
            clearTimeout(resetTimer);
            publish();
            return visibleOnly && document.hidden ? false : pull();
        }

        async function check() {
            if (!valid()) return false;
            if (pending) await pending.promise;
            return pull();
        }

        function updateVisible() {
            if (!valid() || document.hidden) return;
            if (state === 'ready' && performance.now() >= expires) reset();
            else pull();
        }

        function retry(event) {
            if (event.target.closest('[data-game-allowance-retry]')) refresh();
        }

        const visibleEvents = ['focus', 'pageshow', 'online'];
        const identityEvents = ['family-state-updated', 'family-profile-changed', 'family-access-invalidated', 'family-guest', 'family-privilege-expired'];
        function unmount() {
            if (!active) return;
            active = false;
            pending?.controller.abort();
            clearInterval(interval);
            clearTimeout(resetTimer);
            for (const event of visibleEvents) global.removeEventListener(event, updateVisible);
            for (const event of identityEvents) global.removeEventListener(event, valid);
            document.removeEventListener('visibilitychange', updateVisible);
            root.removeEventListener('click', retry);
            data = null;
            state = 'inactive';
            publish();
            extraScopes.clear();
        }

        publish();
        if (active) {
            for (const event of visibleEvents) global.addEventListener(event, updateVisible);
            for (const event of identityEvents) global.addEventListener(event, valid);
            document.addEventListener('visibilitychange', updateVisible);
            root.addEventListener('click', retry);
            interval = setInterval(updateVisible, refreshInterval);
            updateVisible();
        }
        return {sync, check, refresh, errorMessage, unmount};
    }

    const api = {summary, feedback, mount, setDisabled};
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
    else global.GameAllowance = api;
})(typeof window !== 'undefined' ? window : globalThis);
