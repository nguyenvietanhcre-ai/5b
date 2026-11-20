/* Shared button primitives. Callers own events, permissions and request state. */
(function (global) {
    'use strict';
    const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    function markup(label, {kind = 'outline', actionAttribute, action, icon = '', extra = ''} = {}) {
        if (!/^data-[a-z-]+$/.test(actionAttribute)) throw new TypeError('Button action attribute required');
        // icon/extra are trusted application markup, never question or account text.
        return `<button class="btn ${escape(kind)}" type="button" ${actionAttribute}="${escape(action)}" ${extra}>${icon}${escape(label)}</button>`;
    }
    function create(document, label, {className = '', type = 'button', onClick} = {}) {
        const button = document.createElement('button');
        button.className = ['btn', className].filter(Boolean).join(' ');
        button.type = type;
        button.textContent = String(label ?? '');
        if (onClick) button.addEventListener('click', onClick);
        return button;
    }
    const api = {markup, create};
    global.UIControls = api;
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
