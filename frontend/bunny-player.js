/* Bunny Player implements the Player.js postMessage protocol. */
'use strict';
window.BunnyLessonPlayer = (() => {
    const origin = 'https://player.mediadelivery.net';
    const embedPath = /^\/embed\/[1-9]\d*\/[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i;
    const saveEvery = 8000;
    const profileEvents = ['family-state-updated', 'family-profile-changed',
        'family-access-invalidated', 'family-privilege-expired', 'family-guest'];

    function currentStudent(api) {
        const {snapshot, familyState, familyContext} = api;
        if (!snapshot.authenticated || snapshot.familyParent || !snapshot.account?.id || !snapshot.csrf) return null;
        if ((familyState || familyContext) && (!familyContext || familyState?.scope !== 'child' ||
            familyState.activeProfile?.type !== 'child')) return null;
        return {owner: snapshot.account.id, expectedCsrf: snapshot.csrf, expectedFamilyContext: familyContext || ''};
    }

    function signedEmbed(playback) {
        const raw = playback?.embedUrl;
        if (typeof raw !== 'string' || raw !== raw.trim() || /[\u0000-\u001f\u007f\\]/.test(raw)) return null;
        let url;
        try { url = new URL(raw); } catch { return null; }
        const expiresAt = playback.expiresAt;
        const tokens = url.searchParams.getAll('token');
        const expiries = url.searchParams.getAll('expires');
        if (url.origin !== origin || url.username || url.password || url.hash || !embedPath.test(url.pathname) ||
            tokens.length !== 1 || !/^[a-f0-9]{64}$/i.test(tokens[0]) || expiries.length !== 1 ||
            !Number.isSafeInteger(expiresAt) || String(expiresAt) !== expiries[0] || Date.now() >= expiresAt * 1000) return null;

        // Keep the signed fields and use known player preferences on shared devices.
        url.search = new URLSearchParams({token: tokens[0], expires: expiries[0], autoplay: 'false',
            rememberPosition: 'false', rememberSettings: 'false', playsinline: 'true', lang: 'vi'}).toString();
        return url;
    }

    function playbackError(error) {
        switch (error?.status) {
            case 401:
            case 403: return 'Hồ sơ này chưa có quyền xem video. Em kiểm tra hồ sơ học sinh rồi thử lại.';
            case 404: return 'Video không còn khả dụng cho bản bài giảng này. Em mở lại bài giảng nhé.';
            case 409: return 'Video đang được chuẩn bị. Em có thể đọc bài học trong lúc chờ.';
            case 503: return 'Dịch vụ video chưa sẵn sàng. Em có thể đọc bài học và thử lại sau.';
            default: return 'Chưa thể mở video. Em kiểm tra kết nối rồi thử lại.';
        }
    }

    function mount(host, {provider, lessonKey, revision, title}, api) {
        const button = host.querySelector('[data-bunny-toggle]');
        const slot = host.querySelector('[data-bunny-frame]');
        const status = host.querySelector('[data-bunny-status]');
        const student = currentStudent(api);
        const profileMessage = 'Em hãy mở video trong hồ sơ học sinh.';
        if (!student || !['main', 'native'].includes(provider) || typeof lessonKey !== 'string' ||
            !lessonKey || !Number.isSafeInteger(revision) || revision < 1) {
            button.disabled = true;
            status.textContent = student ? 'Video chưa khả dụng cho bài giảng này.' : profileMessage;
            return () => {};
        }

        const lesson = {provider, lessonKey, revision};
        let session = null;
        let mounted = true;
        button.disabled = false;

        function sameStudent() {
            const now = currentStudent(api);
            return now && Object.keys(student).every(key => student[key] === now[key]);
        }

        function stop(message = '', label = 'Mở video') {
            const previous = session;
            session = null;
            if (previous) {
                previous.controller.abort();
                clearTimeout(previous.readyTimer);
                clearTimeout(previous.expiryTimer);
                clearTimeout(previous.saveTimer);
                const restoreFocus = previous.frame && document.activeElement === previous.frame;
                slot.replaceChildren();
                if (restoreFocus && mounted && host.isConnected) button.focus({preventScroll: true});
            }
            button.setAttribute('aria-expanded', 'false');
            button.removeAttribute('aria-busy');
            button.disabled = false;
            button.textContent = label;
            status.textContent = message;
        }

        function cleanup() {
            mounted = false;
            stop();
            button.removeEventListener('click', toggle);
            window.removeEventListener('message', receive);
            profileEvents.forEach(type => window.removeEventListener(type, profileChanged));
            window.removeEventListener('pagehide', hide);
            document.removeEventListener('visibilitychange', visibilityChanged);
            observer.disconnect();
        }

        function profileChanged(event) {
            if (event.type === 'family-state-updated' && sameStudent()) return;
            cleanup();
            button.disabled = true;
            status.textContent = profileMessage;
        }

        function hide() {
            if (session) stop('Em có thể mở lại video để xem tiếp.', 'Mở lại video');
        }

        function visibilityChanged() {
            if (document.hidden) hide();
            if (!sameStudent()) profileChanged({type: 'visibilitychange'});
        }

        function expired() {
            stop('Phiên xem video đã hết hạn. Em mở lại video để xem tiếp.', 'Mở lại video');
        }

        function active(state) {
            if (!mounted || !host.isConnected || !state || session !== state || document.hidden) return false;
            if (!sameStudent()) {
                profileChanged({type: 'session'});
                return false;
            }
            if (state.expiresAt && Date.now() >= state.expiresAt * 1000) {
                expired();
                return false;
            }
            return true;
        }

        function send(state, method, value, listener) {
            state.frame.contentWindow?.postMessage(JSON.stringify({
                context: 'player.js', version: state.protocolVersion, method, value, listener,
            }), origin);
        }

        function queueSave(state) {
            if (!active(state) || state.saving || state.saveTimer || state.position === state.saved) return;
            const wait = Math.max(0, state.lastWrite + saveEvery - Date.now());
            state.saveTimer = setTimeout(() => {
                state.saveTimer = null;
                void save(state);
            }, wait);
        }

        async function save(state) {
            if (!active(state) || state.position === state.saved) return;
            const position = state.position;
            state.saving = true;
            state.lastWrite = Date.now();
            try {
                await api.request('lesson-videos/progress', {...lesson, positionSeconds: position},
                    {...student, signal: state.controller.signal});
                if (!active(state)) return;
                state.saved = position;
                status.textContent = '';
            } catch (error) {
                if (!active(state)) return;
                if (error.name === 'AbortError' || [401, 403, 404, 409, 503].includes(error.status)) {
                    stop(playbackError(error), 'Mở lại video');
                } else {
                    status.textContent = 'Chưa lưu được vị trí xem video. Em vẫn có thể xem tiếp.';
                }
            } finally {
                state.saving = false;
                if (state.position !== position) queueSave(state);
            }
        }

        function ready(state, {value, version}) {
            if (state.ready || (value?.src && value.src !== state.frame.src)) return;
            state.ready = true;
            state.protocolVersion = typeof version === 'string' && /^\d{1,2}\.\d{1,2}\.\d{1,2}$/.test(version) ? version : '0.0.11';
            clearTimeout(state.readyTimer);
            button.removeAttribute('aria-busy');
            button.textContent = 'Đóng video';
            status.textContent = '';
            for (const event of ['play', 'pause', 'ended', 'seeked', 'timeupdate', 'error']) {
                send(state, 'addEventListener', event, 'lesson-' + event);
            }
            if (state.saved > 0 && state.saved < state.duration) send(state, 'setCurrentTime', state.saved);
            if (document.activeElement === button) state.frame.focus({preventScroll: true});
        }

        function receive(event) {
            const state = session;
            if (!state?.frame || event.source !== state.frame.contentWindow || event.origin !== origin || !active(state)) return;
            let message = event.data;
            if (typeof message === 'string') {
                try { message = JSON.parse(message); } catch { return; }
            }
            if (message?.context !== 'player.js' ||
                (message.listener && message.listener !== 'lesson-' + message.event)) return;
            if (message.event === 'error') {
                stop('Video chưa phát được. Em có thể mở lại video hoặc đọc nội dung bài học.', 'Mở lại video');
                return;
            }
            if (message.event === 'ready') ready(state, message);
            if (!state.ready) return;
            if (message.event === 'play') state.started = true;
            if (!state.started) return;
            if (message.event === 'timeupdate' || message.event === 'seeked') {
                const {seconds, duration} = message.value ?? {};
                if (!Number.isFinite(seconds) || !Number.isFinite(duration) || seconds < 0 || duration <= 0 ||
                    seconds > duration + 1 || seconds > state.duration + 1) return;
                state.position = Math.min(state.duration, Math.round(seconds));
            }
            if (['timeupdate', 'seeked', 'pause', 'ended'].includes(message.event)) queueSave(state);
        }

        async function toggle() {
            if (session) {
                stop();
                return;
            }
            const state = {controller: new AbortController(), lastWrite: 0};
            session = state;
            if (!active(state)) { if (session === state) stop(); return; }
            button.setAttribute('aria-busy', 'true');
            button.textContent = 'Hủy mở video';
            status.textContent = 'Đang mở video…';
            try {
                const {playback} = await api.request('lesson-videos/playback', lesson,
                    {...student, signal: state.controller.signal});
                if (!active(state)) return;
                const url = signedEmbed(playback);
                const duration = playback?.durationSeconds;
                const position = playback?.positionSeconds;
                if (!url || !Number.isFinite(duration) || duration <= 0 ||
                    !Number.isFinite(position) || position < 0 || position > duration) {
                    stop('Phiên xem video không khả dụng. Em thử mở lại video nhé.', 'Mở lại video');
                    return;
                }
                state.duration = duration;
                state.saved = state.position = position;
                state.expiresAt = playback.expiresAt;
                state.expiryTimer = setTimeout(expired, state.expiresAt * 1000 - Date.now());
                const frame = document.createElement('iframe');
                state.frame = frame;
                frame.title = title ? 'Video bài giảng ' + title : 'Video bài giảng';
                frame.allow = 'encrypted-media; fullscreen';
                frame.allowFullscreen = true;
                frame.referrerPolicy = 'strict-origin-when-cross-origin';
                const failed = () => { if (active(state)) stop('Chưa tải được video. Em thử mở lại nhé.', 'Mở lại video'); };
                let loaded = false;
                frame.addEventListener('load', () => { if (loaded) failed(); loaded = true; });
                frame.addEventListener('error', failed);
                state.readyTimer = setTimeout(failed, 15000);
                frame.src = url.href;
                button.setAttribute('aria-expanded', 'true');
                slot.append(frame);
            } catch (error) {
                if (active(state)) stop(playbackError(error), 'Mở lại video');
            }
        }

        const observer = new MutationObserver(() => {
            if (!host.isConnected) cleanup();
            else if (session?.frame && !slot.contains(session.frame)) stop();
        });
        observer.observe(document.body, {childList: true, subtree: true});
        button.addEventListener('click', toggle);
        window.addEventListener('message', receive);
        profileEvents.forEach(type => window.addEventListener(type, profileChanged));
        window.addEventListener('pagehide', hide);
        document.addEventListener('visibilitychange', visibilityChanged);
        return cleanup;
    }

    return {mount};
})();
