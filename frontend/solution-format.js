/* Presentation for already-authorized practice review payloads. Never fetches answers. */
(function (global) {
    'use strict';
    const view = global.SolutionView || (typeof require === 'function' ? require('./solution-view.js') : null);
    const escape = view.escape;
    const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);
    const answerPrefix = /^\s*(?:Đáp\s*số|Đáp\s*án|Kết\s*quả)\s*[:：]/iu;
    const labelPrefix = /^(\s*(?:(?:Bước|Cách)\s+\d+|Thử\s*lại|Kiểm\s*tra|Lưu\s*ý|Đáp\s*số|Đáp\s*án|Kết\s*quả)\s*[:：])/iu;
    const allowedTags = new Set(['p', 'strong', 'b', 'em', 'i', 'ol', 'ul', 'li', 'aside', 'h3', 'h4', 'figure', 'figcaption', 'div', 'span', 'br', 'table', 'thead', 'tbody', 'tr', 'th', 'td', 'caption', 'code']);
    const mathTags = new Set(['math', 'mrow', 'mfrac', 'mn', 'mo', 'mi', 'msup', 'msub', 'msqrt', 'mtext']);
    const mathNamespace = 'http://www.w3.org/1998/Math/MathML';
    const isText = node => typeof node === 'string' || typeof node === 'number' || node?.type === 'text';
    const textValue = node => typeof node === 'object' ? String(node?.text ?? '') : String(node ?? '');

    function line(value) {
        const source = String(value ?? '');
        const label = source.match(labelPrefix);
        return label ? `<strong class="study-solution-key">${escape(label[0])}</strong>${escape(source.slice(label[0].length))}` : escape(source);
    }
    function paragraphs(value) {
        // Only author-supplied line boundaries become new paragraphs; punctuation is untouched.
        return String(value ?? '').replace(/\r\n?/g, '\n').split(/\n\s*\n/).map(part =>
            `<p class="study-solution-paragraph${answerPrefix.test(part) ? ' solution-answer' : ''}">${part.split('\n').map(line).join('<br>')}</p>`
        ).join('');
    }
    function math(node) {
        const fallback = escape(node?.text ?? node?.latex ?? '');
        if (typeof DOMParser === 'undefined' || typeof document === 'undefined' || !node?.mathml) return `<span class="study-solution-math">${fallback}</span>`;
        try {
            const parsed = new DOMParser().parseFromString(node.mathml, 'application/xml');
            const root = parsed.documentElement;
            const valid = root.localName === 'math' && !parsed.querySelector('parsererror') && [...parsed.getElementsByTagName('*')].every(element =>
                element.namespaceURI === mathNamespace && mathTags.has(element.localName) && [...element.attributes].every(attribute =>
                    attribute.name === 'xmlns' || (attribute.name === 'display' && ['block', 'inline'].includes(attribute.value))));
            if (!valid) return `<span class="study-solution-math">${fallback}</span>`;
            const container = document.createElement('span');
            container.className = 'study-solution-math';
            container.append(document.importNode(root, true));
            return container.outerHTML;
        } catch { return `<span class="study-solution-math">${fallback}</span>`; }
    }
    function rich(node, options) {
        if (Array.isArray(node)) return node.map(item => rich(item, options)).join('');
        if (isText(node)) return textValue(node).replace(/\r\n?/g, '\n').split('\n').map(line).join('<br>');
        if (!node || typeof node !== 'object') return '';
        if (node.type === 'math') return math(node);
        if (node.type === 'media' || node.type === 'image') return typeof options.renderMedia === 'function' ? options.renderMedia(node) : '';
        // Rich content is a small AST, never HTML. Attributes from the payload are not copied.
        const tag = allowedTags.has(node.tag) ? node.tag : 'div';
        if (tag === 'br') return '<br>';
        const content = rich(node.children || [], options);
        const element = `<${tag}${answerPrefix.test(view.plain(node)) ? ' class="solution-answer"' : ''}>${content}</${tag}>`;
        return tag === 'table' ? `<div class="study-solution-table" tabindex="0" role="region" aria-label="Bảng trong lời giải">${element}</div>` : element;
    }
    function renderBlocks(nodes, options) {
        return typeof options.renderBlocks === 'function' ? options.renderBlocks(nodes) : rich(nodes, options);
    }
    function body(value, options) {
        const nodes = Array.isArray(value) ? value : [value];
        // Portable exam blocks have one explanatory text per step. A following formula or
        // figure belongs with that text; it is not numbered as an extra reasoning step.
        const portable = nodes.every(node => isText(node) || ['math', 'media', 'image'].includes(node?.type));
        if (!portable) return `<div class="study-solution-content">${nodes.map(node => isText(node) ? paragraphs(textValue(node)) : renderBlocks([node], options)).join('')}</div>`;
        const groups = [];
        for (const node of nodes) {
            if (isText(node) || !groups.length) groups.push([]);
            groups[groups.length - 1].push(node);
        }
        return `<ol class="study-solution-steps">${groups.map(group => `<li>${group.map(node => isText(node) ? paragraphs(textValue(node)) : `<div class="study-solution-visual">${renderBlocks([node], options)}</div>`).join('')}</li>`).join('')}</ol>`;
    }
    function render(question, options = {}) {
        const source=question && typeof question==='object'?question:{};
        const frame=global.QuestionFrame||(typeof require==='function'?require('./question-frame.js'):null);
        const item=frame?frame.review(source):source;
        const solution = Array.isArray(item.solution) && item.solution.length ? item.solution :
            (typeof item.solution === 'string' && item.solution ? [item.solution] :
                (Array.isArray(item.steps) ? item.steps : []));
        const content = solution.length ? `<p class="study-solution-label">Các bước giải</p>${body(solution, options)}` : '';
        const answer = options.includeAnswer !== false && own(item, 'answer') && item.answer !== undefined && item.answer !== null ?
            `<div class="study-solution-final">${view.answer(item.answer, 'Đáp án')}</div>` : '';
        if(item.sampleBand&&item.thinking&&item.keyPoint){
            const check=item.check?paragraphs('Thử lại: '+item.check):'';
            const extension=item.extension?paragraphs('Vận dụng: '+item.extension.prompt)+paragraphs('Đối chiếu: '+item.extension.answer):'';
            const rationales=item.choiceRationales?`<details><summary>Vì sao các phương án khác chưa đúng?</summary><ul>${Object.entries(item.choiceRationales).map(([label,reason])=>`<li><strong>${escape(label)}</strong>: ${escape(reason)}</li>`).join('')}</ul></details>`:'';
            return `<div class="study-solution" aria-label="Lời giải"><section class="pilot-lesson-section card card-pad"><h3>1. Định hướng tư duy</h3>${paragraphs(item.thinking)}</section><section class="pilot-lesson-section card card-pad"><h3>2. Điểm mấu chốt</h3>${paragraphs(item.keyPoint)}</section><section class="pilot-lesson-section card card-pad"><h3>3. Bài giải chi tiết</h3>${content}${answer}${check}${extension}${rationales}</section></div>`;
        }
        return `<div class="study-solution" aria-label="Lời giải">${content}${answer}</div>`;
    }
    const api = {render, math};
    global.StudySolution = api;
    if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
