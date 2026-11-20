/* Administrative question rights editor. Server authorization is mandatory. */
(function (global) {
    'use strict';

    const TIERS = [['trial', 'Trải nghiệm'], ['free', 'Free'], ['vip', 'VIP'], ['vip_plus', 'VIP+']];
    const REVIEWS = [['draft', 'Chờ duyệt'], ['approved', 'Đã duyệt'], ['rejected', 'Cần sửa']];
    const PURPOSES = [['practice', 'Luyện tập'], ['arena', 'Đấu trí'], ['group-games', 'Game nhiều người'], ['premium', 'Bộ VIP+'], ['exam-sale', 'Đề bán riêng']];
    const labelOf = (list, value, fallback = 'Chưa phân loại') => (list.find(item => item[0] === value) || [null, fallback])[1];

    function node(tag, className, text) {
        const result = document.createElement(tag);
        if (className) result.className = className;
        if (text !== undefined) result.textContent = String(text);
        return result;
    }

    function promptText(value) {
        if (typeof value === 'string') return value;
        if (Array.isArray(value)) return value.map(block => typeof block === 'string' ? block : (block && (block.text || block.latex) || '')).filter(Boolean).join('\n');
        return '';
    }

    function selectField(title, entries, value, name) {
        const label = node('label', 'qa-field');
        label.append(node('span', '', title));
        const select = node('select');
        select.name = name;
        entries.forEach(([key, text]) => {
            const option = node('option', '', text);
            option.value = key;
            select.append(option);
        });
        select.value = value;
        label.append(select);
        return {label, input: select};
    }

    function mount(container, options = {}) {
        if (!container || typeof container.replaceChildren !== 'function') throw new TypeError('Cần phần tử chứa bảng phân quyền câu hỏi.');
        const host = node('section', 'question-access-admin');
        let disposed = false;
        let loading = false;
        let sequence = 0;
        let controller = null;
        let selected = null;
        let page = 1;
        let pageSize = 25;
        let total = 0;
        let csrf = options.csrf || '';
        const filters = {grade: '', tier: '', review: ''};
        const request = options.fetch || global.fetch.bind(global);
        const heading = node('h2', '', 'Phân quyền kho câu hỏi');
        const intro = node('p', 'qa-description', 'Nhóm quyền tách riêng khối, độ khó và mục đích sử dụng. Chỉ duyệt sau khi đã kiểm dữ kiện, đáp án, lời giải và phương án nhiễu.');
        const policy = node('p', 'qa-policy');
        const counts = node('div', 'qa-counts');
        const status = node('p', 'qa-status');
        status.setAttribute('role', 'status');
        status.setAttribute('aria-live', 'polite');
        const filterForm = node('form', 'qa-filters');
        const content = node('div', 'qa-content');
        const listPane = node('div', 'qa-list-pane');
        const list = node('div', 'qa-list');
        const editor = node('div', 'qa-editor');
        const pager = node('div', 'qa-pager');
        const previous = node('button', 'qa-button qa-secondary', 'Trang trước');
        const next = node('button', 'qa-button qa-secondary', 'Trang sau');
        const pageLabel = node('span');
        previous.type = next.type = 'button';
        previous.addEventListener('click', () => { if (page > 1 && !loading) { page -= 1; load(); } });
        next.addEventListener('click', () => { if (page * pageSize < total && !loading) { page += 1; load(); } });
        pager.append(previous, pageLabel, next);
        listPane.append(list, pager);
        content.append(listPane, editor);
        host.append(heading, intro, policy, counts, filterForm, status, content);
        container.replaceChildren(host);

        [['grade', 'Khối', [['', 'Tất cả khối'], ...[1, 2, 3, 4, 5].map(value => [String(value), 'Khối ' + value])]],
         ['tier', 'Nhóm quyền', [['', 'Tất cả nhóm'], ['unmapped', 'Chưa phân loại'], ...TIERS]],
         ['review', 'Duyệt phân quyền', [['', 'Tất cả trạng thái'], ...REVIEWS]]].forEach(([key, title, entries]) => {
            const field = selectField(title, entries, filters[key], key);
            field.input.addEventListener('change', () => { filters[key] = field.input.value; page = 1; load(); });
            filterForm.append(field.label);
        });
        const refresh = node('button', 'qa-button qa-secondary', 'Tải lại');
        refresh.type = 'submit';
        filterForm.append(refresh);
        filterForm.addEventListener('submit', event => { event.preventDefault(); load(); });

        function announce(message, error = false) {
            status.textContent = message;
            status.classList.toggle('qa-error', error);
        }

        async function api(path, body, signal) {
            const headers = {Accept: 'application/json'};
            if (body !== undefined) {
                headers['Content-Type'] = 'application/json';
                headers['X-CSRF-Token'] = typeof csrf === 'function' ? csrf() : csrf;
            }
            const response = await request(path, {method: body === undefined ? 'GET' : 'POST', credentials: 'same-origin', headers, body: body === undefined ? undefined : JSON.stringify(body), signal, cache: 'no-store'});
            let data;
            try { data = await response.json(); } catch (_) { throw new Error('Máy chủ chưa trả dữ liệu hợp lệ. Hãy tải lại.'); }
            if (!data || typeof data !== 'object') throw new Error('Máy chủ chưa trả dữ liệu hợp lệ. Hãy tải lại.');
            if (!response.ok) throw new Error(typeof data.error === 'string' ? data.error : (data.message || 'Không thể lưu hoặc tải phân quyền câu hỏi.'));
            return data;
        }

        function resetEditor() {
            selected = null;
            editor.replaceChildren(node('p', 'qa-empty', 'Chọn một phiên bản để xem và phân loại.'));
        }

        function showEditor(item) {
            selected = item;
            const form = node('form', 'qa-edit-form');
            const title = node('h3', '', 'Phân loại phiên bản ' + item.versionId);
            title.tabIndex = -1;
            form.append(title, node('p', 'qa-meta', item.questionCode + ' · Bản ' + (item.contentRevision ?? item.revision) + ' · Khối ' + item.grade + ' · Độ khó ' + item.difficulty));
            form.append(node('p', 'qa-meta', 'Nội dung: ' + (item.status || 'Chưa rõ trạng thái') + ' · ' + (item.topic || 'Chưa có chuyên đề') + (item.week ? ' · Tuần ' + item.week : '')));
            form.append(node('div', 'qa-prompt', promptText(item.prompt) || 'Phiên bản chưa có bản xem trước nội dung.'));
            const tier = selectField('Nhóm quyền', [['', 'Chọn nhóm quyền'], ...TIERS], item.tier || '', 'tier');
            tier.input.required = true;
            const review = selectField('Trạng thái duyệt phân quyền', REVIEWS, item.reviewStatus || 'draft', 'reviewStatus');
            form.append(tier.label, review.label);
            const purposes = node('fieldset', 'qa-purposes');
            purposes.append(node('legend', '', 'Mục đích được phép'));
            const checks = PURPOSES.map(([key, text]) => {
                const label = node('label', 'qa-check');
                const input = node('input');
                input.type = 'checkbox'; input.value = key; input.name = 'purpose';
                input.checked = Array.isArray(item.purposes) && item.purposes.includes(key);
                label.append(input, node('span', '', text));
                purposes.append(label);
                return input;
            });
            form.append(purposes, node('p', 'qa-hint', 'Game công khai cần nhóm Free và đúng mục đích đã duyệt. Nhãn Free không tự cấp quyền cho mọi game. Trải nghiệm chỉ dùng bộ mẫu được ghim riêng.'));
            const source = node('label', 'qa-field');
            source.append(node('span', '', 'Nguồn, quyền khai thác và căn cứ duyệt'));
            const note = node('textarea');
            note.name = 'sourceNote'; note.rows = 5; note.maxLength = 2000;
            note.value = item.sourceNote || '';
            note.placeholder = 'Ghi nguồn và những phần đã kiểm; ghi rõ phần còn chờ nếu chưa đủ điều kiện duyệt.';
            source.append(note);
            form.append(source);
            const attestation = node('label', 'qa-check qa-attestation');
            const checked = node('input'); checked.type = 'checkbox';
            attestation.append(checked, node('span', '', 'Tôi đã kiểm nội dung, đáp án, lời giải, nhiễu (nếu có), nguồn và quyền khai thác của đúng phiên bản này.'));
            form.append(attestation);
            const actions = node('div', 'qa-actions');
            const save = node('button', 'qa-button', 'Lưu phân quyền'); save.type = 'submit';
            const close = node('button', 'qa-button qa-secondary', 'Đóng'); close.type = 'button';
            close.addEventListener('click', resetEditor);
            actions.append(save, close); form.append(actions);
            form.addEventListener('submit', async event => {
                event.preventDefault();
                if (!form.reportValidity()) return;
                const approved = review.input.value === 'approved';
                const selectedPurposes = checks.filter(input => input.checked).map(input => input.value);
                if (approved && (!checked.checked || !note.value.trim() || !selectedPurposes.length)) {
                    announce('Để duyệt, cần chọn mục đích, ghi căn cứ và xác nhận đã kiểm đúng phiên bản.', true);
                    return;
                }
                if ((selectedPurposes.includes('arena') || selectedPurposes.includes('group-games')) && tier.input.value !== 'free') {
                    announce('Mục đích game công khai chỉ nhận câu thuộc nhóm Free.', true);
                    return;
                }
                save.disabled = true;
                close.disabled = true;
                try {
                    await api('/api/staff/question-access/versions/' + encodeURIComponent(item.versionId), {tier: tier.input.value, purposes: selectedPurposes, reviewStatus: review.input.value, sourceNote: note.value.trim(), expectedRevision: item.revision});
                    if (disposed) return;
                    announce('Đã lưu phân quyền. Bộ chọn nguồn chỉ chuyển chế độ sau khi kiểm đủ nguồn hợp lệ.');
                    await load(true);
                    if (typeof options.onSaved === 'function') options.onSaved(item.versionId);
                } catch (error) {
                    if (!disposed) announce(error.message, true);
                } finally {
                    if (!disposed) { save.disabled = false; close.disabled = false; }
                }
            });
            editor.replaceChildren(form);
            title.focus({preventScroll: true});
        }

        function render(data) {
            total = Number(data.total) || 0;
            pageSize = Number(data.pageSize) || 25;
            page = Number(data.page) || page;
            const active = data.policy || {};
            policy.textContent = (active.mode === 'classified' ? 'Nguồn đang dùng phân quyền đã duyệt.' : 'Đang giữ nguồn hiện hành bằng danh sách phiên bản đã ghim.') + (active.baseline ? ' Mốc: ' + active.baseline + '.' : '') + (active.note ? ' ' + active.note : '');
            counts.replaceChildren();
            const tierCounts = new Map();
            if (Array.isArray(data.counts)) data.counts.forEach(count => {
                if (!count || !Number.isFinite(Number(count.count))) return;
                const tier = TIERS.some(entry => entry[0] === count.tier) ? count.tier : 'unmapped';
                tierCounts.set(tier, (tierCounts.get(tier) || 0) + Number(count.count));
            });
            [['unmapped', 'Chưa phân loại'], ...TIERS].forEach(([tier, title]) => {
                if (tierCounts.has(tier)) counts.append(node('span', 'qa-count', title + ': ' + tierCounts.get(tier)));
            });
            const items = Array.isArray(data.items) ? data.items : [];
            list.replaceChildren();
            items.forEach(item => {
                const card = node('article', 'qa-item');
                const heading = node('h3', '', item.questionCode || ('Câu ' + item.versionId));
                card.append(heading, node('p', 'qa-meta', 'Khối ' + item.grade + ' · Độ khó ' + item.difficulty + ' · Bản ' + (item.contentRevision ?? item.revision) + ' · ' + (item.topic || 'Chưa có chuyên đề')));
                const tags = node('p', 'qa-tags');
                tags.append(node('span', 'qa-tag', labelOf(TIERS, item.tier)), node('span', 'qa-tag qa-review-' + (['draft', 'approved', 'rejected'].includes(item.reviewStatus) ? item.reviewStatus : 'draft'), labelOf(REVIEWS, item.reviewStatus, 'Chưa duyệt')));
                card.append(tags, node('p', 'qa-excerpt', promptText(item.prompt).slice(0, 250) || 'Chưa có bản xem trước.'));
                const edit = node('button', 'qa-button qa-secondary', 'Xem và phân loại'); edit.type = 'button';
                edit.addEventListener('click', () => showEditor(item));
                card.append(edit); list.append(card);
            });
            if (!items.length) list.append(node('p', 'qa-empty', 'Không có câu phù hợp bộ lọc này.'));
            pageLabel.textContent = 'Trang ' + page + ' · ' + total + ' phiên bản';
            previous.disabled = page <= 1;
            next.disabled = page * pageSize >= total;
            if (selected) {
                const fresh = items.find(item => item.versionId === selected.versionId);
                if (fresh) showEditor(fresh); else resetEditor();
            }
        }

        async function load(keepStatus = false) {
            const current = ++sequence;
            if (controller) controller.abort();
            controller = new AbortController();
            loading = true; host.setAttribute('aria-busy', 'true'); refresh.disabled = true;
            previous.disabled = next.disabled = true;
            if (!keepStatus) announce('Đang tải phân quyền…');
            const query = new URLSearchParams({page: String(page)});
            Object.entries(filters).forEach(([key, value]) => { if (value) query.set(key, value); });
            try {
                const data = await api('/api/staff/question-access?' + query.toString(), undefined, controller.signal);
                if (disposed || current !== sequence) return;
                render(data);
                if (!keepStatus) announce('Đã tải ' + (Array.isArray(data.items) ? data.items.length : 0) + ' phiên bản.');
            } catch (error) {
                if (!disposed && current === sequence && error.name !== 'AbortError') announce(error.message, true);
            } finally {
                if (!disposed && current === sequence) { loading = false; host.removeAttribute('aria-busy'); refresh.disabled = false; }
            }
        }

        resetEditor();
        load();
        return {reload: () => load(), setCsrf: value => { csrf = value; }, destroy: () => { disposed = true; sequence += 1; if (controller) controller.abort(); host.remove(); }};
    }

    global.QuestionAccessAdmin = Object.freeze({mount});
})(window);
