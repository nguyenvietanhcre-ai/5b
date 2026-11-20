'use strict';
// Form controls shared by the two lesson libraries in the existing admin area.
const LessonEditor = (() => {
    const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
    const clone = value => JSON.parse(JSON.stringify(value));
    const lines = value => String(value || '').split(/\r?\n/).map(line => line.trim()).filter(Boolean);
    const field = (label,name,value='',extra='') => `<label class="staff-field"><span>${esc(label)}</span><input name="${name}" value="${esc(value)}" ${extra}></label>`;
    const area = (label,name,value='',extra='') => `<label class="staff-field"><span>${esc(label)}</span><textarea name="${name}" rows="3" ${extra}>${esc(value)}</textarea></label>`;
    const select = (label,name,options,value) => `<label class="staff-field"><span>${esc(label)}</span><select name="${name}">${options.map(([key,title]) => `<option value="${esc(key)}" ${String(key)===String(value)?'selected':''}>${esc(title)}</option>`).join('')}</select></label>`;
    const section = (title,body) => `<fieldset class="lesson-editor-section"><legend>${esc(title)}</legend>${body}</fieldset>`;
    function safeUrl(value) {
        if (typeof value !== 'string' || value.length > 2000 || /[\u0000-\u0020\u007f\\]/.test(value)) return '';
        if (value.startsWith('/') && !value.startsWith('//')) return value;
        try {const url=new URL(value);return url.protocol==='https:' && !url.username && !url.password ? value : '';} catch {return '';}
    }
    function videoPreview(value) {
        const href=safeUrl(value);
        if(!href) return '<p class="staff-note">Chưa có liên kết video hợp lệ để xem trước.</p>';
        const url=new URL(href,'https://5bmath.vn'),host=url.hostname.toLowerCase();let embed='';
        if(['youtube.com','www.youtube.com','m.youtube.com','youtu.be','www.youtube-nocookie.com'].includes(host)) {
            const id=host==='youtu.be'?url.pathname.slice(1):url.pathname.startsWith('/embed/')?url.pathname.split('/')[2]:url.searchParams.get('v');
            if(/^[A-Za-z0-9_-]{11}$/.test(id||''))embed='https://www.youtube-nocookie.com/embed/'+id;
        } else if(['vimeo.com','www.vimeo.com','player.vimeo.com'].includes(host)) {
            const id=url.pathname.split('/').filter(Boolean).pop();if(/^\d{1,12}$/.test(id||''))embed='https://player.vimeo.com/video/'+id;
        }
        const link=`<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">Mở video trong thẻ mới ↗</a>`;
        if(embed)return `<iframe title="Xem trước video bài học" src="${esc(embed)}" loading="lazy" referrerpolicy="strict-origin-when-cross-origin" allow="fullscreen" allowfullscreen></iframe>${link}`;
        if(/\.(mp4|webm|ogv)$/i.test(url.pathname))return `<video controls preload="none" src="${esc(href)}"></video>${link}`;
        return `<p class="staff-note">Liên kết này được mở tại trang video.</p>${link}`;
    }
    function resources(row={},options={}) {
        const video=row.videoUrl??row.videoRef??row.video_ref??'';
        const source=select('Nguồn video','videoSource',[['url','Liên kết có sẵn'],['bunny','Tải video từ máy · Bunny Stream']],row.bunnyVideo?'bunny':'url');
        const urlFields=field('Liên kết video HTTPS hoặc đường dẫn trong website','videoUrl',video,'maxlength="2000" placeholder="https://…" inputmode="url"')+
            '<p class="staff-note">Để trống nếu bài chưa có video.</p><button class="btn outline" type="button" data-lesson-preview>Xem trước video</button><div class="lesson-editor-preview" data-lesson-preview-area aria-live="polite"></div>';
        return section('Video bài học',source+'<div data-lesson-url-video'+(row.bunnyVideo?' hidden':'')+'>'+urlFields+'</div>'+BunnyUpload.markup())+
            section('Tài liệu của bài học','<p class="staff-note">Đặt tên rõ nội dung. PDF và liên kết tài liệu được lưu cùng video khi bấm lưu bài.</p><label class="staff-field lesson-editor-upload"><span>Thêm tài liệu PDF từ máy</span><input type="file" accept="application/pdf,.pdf" multiple data-lesson-pdf><small>Tổng PDF mới tối đa 5 MB mỗi lần lưu. Chọn tệp để thêm vào danh sách bên dưới.</small></label><p class="staff-note" data-lesson-file-status role="status"></p><div data-lesson-materials></div><button class="btn outline" type="button" data-lesson-add-material>+ Thêm liên kết tài liệu</button><p class="staff-note" data-lesson-material-count></p>')+
            (options.examples?section('Câu hỏi mẫu tự học','<p class="staff-note">Thêm tối đa 10 câu do giáo viên biên soạn cho chính bài này. Đáp số và các bước giải có thể bổ sung sau.</p><div data-lesson-examples></div><button class="btn outline" type="button" data-lesson-add-example>+ Thêm câu hỏi mẫu</button><p class="staff-note" data-lesson-example-count></p>'):'');
    }
    function fixed(row) {
        const q=row.fixed,guide=q.inputGuide||{},guideObject=typeof guide==='object' && !Array.isArray(guide),guideInstruction=guideObject?guide.instruction||'':String(guide),targets=q.answerTargets||[];
        return section('Câu tự kiểm tra của bài',area('Đề bài','fixedPrompt',q.prompt,'required maxlength="10000"')+select('Hình thức trả lời','fixedMode',[['typed','Tự nhập một đáp số'],['choice','Trắc nghiệm bốn phương án']],q.responseMode)+
            '<p class="staff-note">Câu nhiều ý, nhiều đối tượng hoặc nhiều kết quả dùng một phương án chứa đủ kết quả và đơn vị. Ba phương án sai cần có lý do sai cụ thể.</p>'+
            '<div data-lesson-typed>'+field('Đáp số đúng','fixedAnswer',q.correctAnswer,'maxlength="500"')+select('Cách so đáp số','fixedKind',[['number','Số / phân số tương đương'],['auto','Số hoặc văn bản'],['text','Văn bản chính xác']],q.answerKind||'number')+'</div>'+
            '<div data-lesson-choice>'+[0,1,2,3].map(i=>`<div class="lesson-editor-choice"><label class="lesson-editor-correct"><input type="radio" name="fixedCorrect" value="${i}" ${q.options?.[i]===q.correctAnswer?'checked':''}><span>Phương án ${String.fromCharCode(65+i)} là đáp án đúng</span></label>${area('Phương án '+String.fromCharCode(65+i),'fixedOption'+i,q.options?.[i]||'','maxlength="500"')}${area('Giải thích phương án '+String.fromCharCode(65+i),'fixedRationale'+i,q.choiceRationales?.[i]||'','maxlength="2000"')}</div>`).join('')+'</div>'+
            '<div data-lesson-shape>'+select('Cấu trúc kết quả','fixedShape',[['scalar','Một đáp số'],['single','Một đáp số (bản cũ)'],['complete-choice','Một kết luận đầy đủ'],['parts','Nhiều ý (a, b…)'],['objects','Nhiều đối tượng'],['solutions','Nhiều kết quả']],q.answerShape||'scalar')+area('Nhãn các ý / đối tượng · mỗi dòng một nhãn','fixedTargets',targets.join('\n'),'maxlength="1200"')+'</div>')+
            section('Hướng dẫn nhập đáp án',area('Hướng dẫn cho học sinh','fixedGuide',guideInstruction,'maxlength="2000"')+'<div class="staff-form-grid">'+area('Nhãn ô nhập · mỗi dòng một nhãn','fixedGuideLabels',guideObject?(guide.labels||[]).join('\n'):'','maxlength="1200"')+area('Đơn vị · mỗi dòng một đơn vị','fixedGuideUnits',guideObject?(guide.units||[]).join('\n'):'','maxlength="1200"')+'</div>')+
            section('Lời giải câu tự kiểm tra',[['1. Định hướng tư duy',0],['2. Điểm mấu chốt',1],['3. Bài giải chi tiết',2]].map(([title,i])=>area(title,'fixedSolution'+i,row.solution?.[i]||'','required maxlength="20000"')).join('')+'<p class="staff-note">Học sinh xem lời giải sau khi tự kiểm tra. Hình minh họa và lịch sử phiên bản được giữ khi sửa phần chữ.</p>');
    }
    function bind(form,row={},options={}) {
        form.classList.add('lesson-editor');
        const originalMaterials=Array.isArray(row.materials)?row.materials:[];
        let materials=originalMaterials.map((value,index)=>({...value,_key:index})),nextMaterial=materials.length;
        let examples=(Array.isArray(row.examples)?row.examples:row.exampleText?[{text:row.exampleText,steps:Array.isArray(row.exampleSteps)?row.exampleSteps:lines(row.exampleSteps)}]:[]).map((value,index)=>({...value,_key:index})),nextExample=examples.length;
        const materialBox=form.querySelector('[data-lesson-materials]'),exampleBox=form.querySelector('[data-lesson-examples]');
        let busy=false,staging=false,dirty=false,closed=false,conflict=false;
        const snapshot=()=>JSON.stringify([...new FormData(form)].map(([name,value])=>[name,typeof value==='string'?value:'']));
        function materialRows() {
            materialBox.innerHTML=materials.length?materials.map((m,i)=>`<article class="lesson-editor-card" data-material-key="${m._key}"><div class="lesson-editor-card-head"><h3>Tài liệu ${i+1}</h3><button type="button" class="btn outline" data-remove-material="${m._key}" aria-label="Bỏ tài liệu ${i+1}">Bỏ tài liệu</button></div>${field('Tên tài liệu','materialTitle'+m._key,m.title,'required maxlength="180"')}${m.resourceId||m.upload?'<p class="staff-note">'+(m.upload?'PDF chờ lưu: ':'PDF đã lưu: ')+esc(m.upload?.filename||m.filename||m.title)+(m.upload?' · '+Math.ceil(m._size/1024)+' KB':'')+'</p>':field('Liên kết tài liệu HTTPS hoặc đường dẫn trong website','materialHref'+m._key,m.href,'required maxlength="2000" inputmode="url" placeholder="https://…"')}${m.resourceId||m.upload?'':`<label class="lesson-editor-check"><input type="checkbox" name="materialDownload${m._key}" ${m.download?'checked':''}><span>Hiện nhãn tải tài liệu</span></label>`}</article>`).join(''):'<p class="lesson-editor-empty">Chưa thêm tài liệu cho bài này. Học sinh sẽ không thấy nút tải tài liệu.</p>';
            form.querySelector('[data-lesson-add-material]').disabled=materials.length>=20;
            form.querySelector('[data-lesson-material-count]').textContent=materials.length+'/20 tài liệu';
        }
        function exampleRows() {
            if(!exampleBox)return;
            exampleBox.innerHTML=examples.length?examples.map((q,i)=>`<article class="lesson-editor-card" data-example-key="${q._key}"><div class="lesson-editor-card-head"><h3>Câu hỏi mẫu ${i+1}</h3><button type="button" class="btn outline" data-remove-example="${q._key}" aria-label="Bỏ câu hỏi mẫu ${i+1}">Bỏ câu</button></div>${area('Đề bài','exampleText'+q._key,q.text,'required maxlength="20000"')}${field('Đáp số · tùy chọn','exampleAnswer'+q._key,q.answer||'','maxlength="500"')}${area('Các bước giải · mỗi dòng một bước','exampleSteps'+q._key,(q.steps||[]).join('\n'),'maxlength="100000"')}</article>`).join(''):'<p class="lesson-editor-empty">Chưa có câu hỏi mẫu. Có thể lưu bài mà chưa thêm câu.</p>';
            form.querySelector('[data-lesson-add-example]').disabled=examples.length>=10;
            form.querySelector('[data-lesson-example-count]').textContent=examples.length+'/10 câu hỏi mẫu';
        }
        const value=name=>form.elements.namedItem(name)?.value||'';
        function captureRows() {
            materials=materials.map(m=>({...m,title:value('materialTitle'+m._key),href:m.resourceId||m.upload?m.href:value('materialHref'+m._key),download:!!form.elements.namedItem('materialDownload'+m._key)?.checked}));
            examples=examples.map(q=>({...q,text:value('exampleText'+q._key),answer:value('exampleAnswer'+q._key),steps:lines(value('exampleSteps'+q._key))}));
        }
        function showMode() {
            const choice=value('fixedMode')==='choice';
            form.querySelectorAll('[data-lesson-typed]').forEach(el=>el.hidden=choice);
            form.querySelectorAll('[data-lesson-choice]').forEach(el=>el.hidden=!choice);
        }
        const fixedNames=()=>[...form.querySelectorAll('[name^="fixed"]')].map(el=>el.name).filter((name,i,all)=>all.indexOf(name)===i);
        const fixedSnapshot=()=>JSON.stringify(fixedNames().map(name=>[name,value(name)]));
        materialRows();exampleRows();showMode();
        const originalFixed=options.fixed?fixedSnapshot():'',initialFixedValues=Object.fromEntries(fixedNames().map(name=>[name,value(name)])),initialSnapshot=snapshot();
        const footer=form.querySelector('.staff-form-footer');
        const notice=document.createElement('div');notice.className='lesson-editor-notice';notice.setAttribute('aria-live','polite');notice.innerHTML='<span data-lesson-save-status>Chưa có thay đổi.</span><div data-lesson-discard hidden><p>Có thay đổi chưa lưu trong bài này.</p><div class="staff-actions"><button class="btn outline" type="button" data-lesson-continue>Tiếp tục biên tập</button><button class="btn outline" type="button" data-lesson-discard-now>Đóng và bỏ thay đổi</button></div></div><div data-lesson-conflict hidden><p>Bản đang biên tập được giữ ở đây. Tải bản mới sẽ bỏ các thay đổi chưa lưu.</p><button class="btn outline" type="button" data-lesson-reload>Tải lại bản mới nhất</button></div>';
        if(footer)footer.before(notice);
        const status=notice.querySelector('[data-lesson-save-status]'),dialog=form.closest('dialog')||document.querySelector('#modal'),disabledControls=new Map();
        const active=()=>!closed&&form.isConnected&&!!dialog?.open&&(options.active?.()??true);
        const bunny=BunnyUpload.mount(form,row,{...options.bunny,active,changed:markDirty});
        function showVideoSource() {
            const managed=value('videoSource')==='bunny';
            form.querySelector('[data-lesson-url-video]').hidden=managed;
            if(managed)form.querySelector('[data-lesson-preview-area]').replaceChildren();
            bunny.setVisible(managed);
        }
        function markDirty(){dirty=snapshot()!==initialSnapshot||materials.some(m=>m.upload)||bunny.changed;status.textContent=dirty?'Có thay đổi chưa lưu.':'Chưa có thay đổi.';}
        function cancel(event){if(busy){event.preventDefault();return;}if(dirty){event.preventDefault();notice.querySelector('[data-lesson-discard]').hidden=false;notice.scrollIntoView({block:'nearest'});}}
        dialog?.addEventListener('cancel',cancel);
        function backdrop(event){if((event.target===dialog||event.target.closest?.('#close-modal'))&&(busy||dirty)){cancel(event);event.stopImmediatePropagation();}}
        dialog?.addEventListener('click',backdrop,true);
        function unload(event){if((dirty||bunny.uploading)&&!closed){event.preventDefault();event.returnValue='';}}
        window.addEventListener('beforeunload',unload);
        function cleanup(){closed=true;bunny.destroy();dialog?.removeEventListener('cancel',cancel);dialog?.removeEventListener('click',backdrop,true);window.removeEventListener('beforeunload',unload);dialog?.removeEventListener('close',cleanup);}
        dialog?.addEventListener('close',cleanup);
        showVideoSource();
        form.addEventListener('input',markDirty);
        form.addEventListener('change',event=>{if(event.target.name==='fixedMode')showMode();if(event.target.name==='videoSource')showVideoSource();markDirty();});
        form.querySelector('[data-lesson-pdf]')?.addEventListener('change',async event=>{
            const picker=event.target,files=[...picker.files],feedback=form.querySelector('[data-lesson-file-status]');
            if(busy||staging)return;staging=true;picker.disabled=true;feedback.textContent='Đang kiểm tra PDF…';
            try {
                captureRows();
                if(files.length+materials.length>20)throw Error('Mỗi bài có tối đa 20 tài liệu. Bỏ tài liệu chưa dùng trước khi thêm tệp.');
                if(files.reduce((total,f)=>total+f.size,materials.reduce((total,m)=>total+(m._size||0),0))>5*1024*1024)throw Error('Tổng PDF mới vượt 5 MB. Chọn tệp nhỏ hơn hoặc lưu từng đợt.');
                const staged=[];
                for(const file of files) {
                    if(!file.size||!file.name.toLowerCase().endsWith('.pdf')||(file.type&&file.type!=='application/pdf'))throw Error('Chỉ thêm tệp PDF có nội dung, đúng đuôi .pdf.');
                    if(file.name.length>160||file.name!==file.name.trim()||file.name.startsWith('.')||/[\u0000-\u001f\u007f/\\:<>"|?*]/.test(file.name)||/^(CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])\.pdf$/i.test(file.name))throw Error('Tên PDF cần tối đa 160 ký tự, không dùng đường dẫn, ký tự đặc biệt hoặc tên dành riêng của hệ thống.');
                    const bytes=new Uint8Array(await file.arrayBuffer());
                    if(String.fromCharCode(...bytes.slice(0,5))!=='%PDF-'||!String.fromCharCode(...bytes.slice(-1024)).includes('%%EOF'))throw Error('Tệp '+file.name+' chưa có định dạng PDF hợp lệ.');
                    let binary='';for(let offset=0;offset<bytes.length;offset+=16384)binary+=String.fromCharCode(...bytes.subarray(offset,offset+16384));
                    staged.push({_key:nextMaterial++,title:file.name.replace(/\.pdf$/i,''),_size:file.size,upload:{filename:file.name,mime:'application/pdf',base64:btoa(binary)}});
                }
                if(!form.isConnected||closed)return;
                // The teacher may have continued typing while the browser read files.
                captureRows();if(materials.length+staged.length>20)throw Error('Mỗi bài có tối đa 20 tài liệu. Bỏ tài liệu chưa dùng trước khi thêm tệp.');materials.push(...staged);materialRows();markDirty();feedback.textContent=files.length+' PDF đã thêm vào bài, chưa gửi lên máy chủ. Bấm lưu bài để hoàn tất.';
            } catch(error){feedback.textContent=error.message;}finally{staging=false;picker.disabled=false;picker.value='';}
        });
        form.addEventListener('submit',event=>{if(busy||staging||conflict){event.preventDefault();event.stopImmediatePropagation();}},true);
        form.addEventListener('click',event=>{
            const target=event.target.closest('button');if(!target)return;
            if(busy){event.preventDefault();event.stopImmediatePropagation();return;}
            if(target.matches('[data-staff="close-modal"]')&&dirty){event.preventDefault();event.stopImmediatePropagation();notice.querySelector('[data-lesson-discard]').hidden=false;notice.scrollIntoView({block:'nearest'});return;}
            if(target.matches('[data-lesson-continue]')){notice.querySelector('[data-lesson-discard]').hidden=true;return;}
            if(target.matches('[data-lesson-discard-now]')){cleanup();dialog?.close();return;}
            if(target.matches('[data-lesson-reload]')){options.reload?.();return;}
            if(target.matches('[data-lesson-preview]')){form.querySelector('[data-lesson-preview-area]').innerHTML=videoPreview(value('videoUrl').trim());return;}
            if(target.matches('[data-lesson-add-material],[data-remove-material]')){captureRows();if(target.hasAttribute('data-remove-material'))materials=materials.filter(m=>m._key!==Number(target.dataset.removeMaterial));else if(materials.length<20)materials.push({_key:nextMaterial++,title:'',href:'',download:false});materialRows();markDirty();if(target.hasAttribute('data-lesson-add-material'))materialBox.lastElementChild?.querySelector('input')?.focus();}
            if(target.matches('[data-lesson-add-example],[data-remove-example]')){captureRows();if(target.hasAttribute('data-remove-example'))examples=examples.filter(q=>q._key!==Number(target.dataset.removeExample));else if(examples.length<10)examples.push({_key:nextExample++,text:'',answer:'',steps:[]});exampleRows();markDirty();if(target.hasAttribute('data-lesson-add-example'))exampleBox.lastElementChild?.querySelector('textarea')?.focus();}
        },true);
        function read() {
            if(staging)throw Error('Đang đọc PDF. Vui lòng chờ trước khi lưu.');
            if(bunny.uploading)throw Error('Tạm dừng tải video hoặc chờ tệp tải xong trước khi lưu.');
            const source=value('videoSource'),video=source==='bunny'?'':value('videoUrl').trim();if(video&&!safeUrl(video))throw Error('Liên kết video cần dùng HTTPS hoặc đường dẫn bắt đầu bằng / trong website.');
            captureRows();
            const result={videoUrl:video,...bunny.read(source),materials:materials.map(m=>{if(!m.title.trim())throw Error('Điền tên cho từng tài liệu hoặc bỏ tài liệu chưa dùng.');if(m.resourceId)return {title:m.title.trim(),resourceId:m.resourceId};if(m.upload)return {title:m.title.trim(),upload:m.upload};if(!safeUrl(m.href.trim()))throw Error('Liên kết tài liệu cần dùng HTTPS hoặc đường dẫn bắt đầu bằng / trong website.');return {title:m.title.trim(),href:m.href.trim(),download:!!m.download};})};
            if(options.examples)result.examples=examples.map(q=>{if(!q.text.trim())throw Error('Điền đề bài cho từng câu hỏi mẫu hoặc bỏ câu chưa dùng.');if(q.steps.length>50||q.steps.some(step=>step.length>2000))throw Error('Mỗi câu hỏi mẫu có tối đa 50 bước giải, mỗi bước tối đa 2.000 ký tự.');return {text:q.text.trim(),steps:q.steps,...(q.answer.trim()?{answer:q.answer.trim()}:{})};});
            if(options.fixed && fixedSnapshot()!==originalFixed) {
                const q=clone(row.fixed),mode=value('fixedMode'),prompt=value('fixedPrompt').trim(),shape=value('fixedShape'),targets=lines(value('fixedTargets'));
                if(!prompt)throw Error('Điền đề bài cho câu tự kiểm tra.');
                const changed=name=>value(name)!==initialFixedValues[name];
                if(changed('fixedPrompt'))q.prompt=prompt;
                if(changed('fixedMode'))q.responseMode=mode;
                if(changed('fixedShape'))q.answerShape=shape;
                if(mode==='choice') {
                    const choices=[0,1,2,3].map(i=>value('fixedOption'+i).trim()),rationales=[0,1,2,3].map(i=>value('fixedRationale'+i).trim()),correct=value('fixedCorrect');
                    if(choices.some(option=>!option)||new Set(choices).size!==4)throw Error('Nhập bốn phương án khác nhau và đầy đủ.');
                    if(correct==='')throw Error('Chọn phương án đúng của câu tự kiểm tra.');
                    if(rationales.some(reason=>reason.length<12))throw Error('Giải thích cả bốn phương án (ít nhất 12 ký tự), nêu lỗi giải cụ thể cho phương án sai.');
                    if(choices.some(option=>targets.some(label=>!option.toLocaleLowerCase('vi').includes(label.toLocaleLowerCase('vi')+':'))))throw Error('Mỗi phương án cần ghi đủ nhãn kết quả theo dạng Nhãn: đáp số.');
                    if(changed('fixedMode')||changed('fixedCorrect')||[0,1,2,3].some(i=>changed('fixedOption'+i)))Object.assign(q,{correctAnswer:choices[Number(correct)],options:choices});
                    if(changed('fixedMode'))q.answerKind='text';
                    if(changed('fixedMode')||[0,1,2,3].some(i=>changed('fixedRationale'+i)))q.choiceRationales=rationales;
                    if(changed('fixedTargets'))q.answerTargets=targets;
                } else {
                    if(['parts','objects','solutions'].includes(shape)||targets.length>1)throw Error('Câu có nhiều kết quả cần dùng trắc nghiệm bốn phương án.');
                    const answer=value('fixedAnswer').trim();if(!answer)throw Error('Điền đáp số đúng của câu tự kiểm tra.');
                    if(changed('fixedAnswer')||changed('fixedMode'))q.correctAnswer=answer;
                    if(changed('fixedKind')||changed('fixedMode'))q.answerKind=value('fixedKind');
                    if(changed('fixedTargets'))q.answerTargets=targets;
                    if(changed('fixedMode')){delete q.options;delete q.choiceRationales;}
                }
                const oldGuide=row.fixed.inputGuide,guideInstruction=value('fixedGuide'),guideLabels=lines(value('fixedGuideLabels')),guideUnits=lines(value('fixedGuideUnits'));
                if(['fixedGuide','fixedGuideLabels','fixedGuideUnits'].some(changed)) {
                    if(typeof oldGuide==='string' && !guideLabels.length && !guideUnits.length)q.inputGuide=guideInstruction;
                    else q.inputGuide={...(oldGuide&&typeof oldGuide==='object'?oldGuide:{}),instruction:guideInstruction,labels:guideLabels,units:guideUnits};
                }
                const solution=[0,1,2].map(i=>value('fixedSolution'+i));if(solution.some(s=>!s.trim()))throw Error('Lời giải cần đủ ba phần: định hướng tư duy, điểm mấu chốt, bài giải chi tiết.');
                const solutionChanged=solution.some((s,i)=>s!==(row.solution?.[i]||''));
                const questionChanged=JSON.stringify(q)!==JSON.stringify(row.fixed);
                if(questionChanged)result.fixed=q;
                if(solutionChanged)result.solution=solution;
            }
            return result;
        }
        return {read,setBusy(value){busy=!!value;form.setAttribute('aria-busy',String(busy));if(busy){for(const control of form.querySelectorAll('input,select,textarea,button')){disabledControls.set(control,control.disabled);control.disabled=true;}}else{for(const [control,disabled] of disabledControls)control.disabled=disabled;disabledControls.clear();}bunny.setBusy(busy);status.textContent=busy?'Đang lưu bài, vui lòng chờ…':dirty?'Có thay đổi chưa lưu.':'Chưa có thay đổi.';},error(error){if(error.status===409&&!String(error.code||'').startsWith('bunny_')){conflict=true;notice.querySelector('[data-lesson-conflict]').hidden=false;setTimeout(()=>{if(form.isConnected)form.querySelector('[type="submit"]').disabled=true;},0);status.textContent='Bài vừa được thay đổi ở nơi khác. Cần tải bản mới trước khi lưu.';}},destroy:cleanup,get active(){return active();}};
    }
    return {resources,fixed,bind,safeUrl,videoPreview,section};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=LessonEditor;
