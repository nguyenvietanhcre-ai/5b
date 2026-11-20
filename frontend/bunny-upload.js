'use strict';

// Credentials stay in the transfer instance. Storage only holds the resumable resource
// URL and local file fingerprint, scoped to the staff account and existing lesson.
const BunnyUpload = (() => {
    const endpoint='https://video.bunnycdn.com/tusupload';
    const routes='bunny-stream/uploads';
    const idPattern=/^[a-f0-9]{32}$/;
    const mimeTypes={mp4:'video/mp4',m4v:'video/mp4',mov:'video/quicktime',webm:'video/webm'};
    const labels={uploading:'Chưa tải đủ tệp',processing:'Bunny đang xử lý video',ready:'Video đã sẵn sàng',failed:'Bunny không xử lý được video này'};
    const button=(name,action)=>'<button type="button" class="btn outline" data-bunny-action="'+action+'">'+name+'</button>';

    function markup() {
        return '<div class="bunny-upload" data-bunny-upload hidden>'+
            '<p class="staff-note" data-bunny-config role="status"></p>'+
            '<p class="staff-note" data-bunny-attached hidden></p>'+
            '<div class="staff-actions" data-bunny-current hidden>'+button('Xem trước video đã gắn','preview-current')+button('Bỏ video khỏi bài','clear')+'</div>'+
            '<div data-bunny-source hidden>'+
                '<label class="staff-field lesson-editor-upload"><span>Tệp video từ máy</span>'+
                '<input type="file" accept=".mp4,.m4v,.mov,.webm,video/mp4,video/quicktime,video/webm" data-bunny-file></label>'+
                '<p class="staff-note" data-bunny-file-hint></p>'+
            '</div>'+
            '<progress data-bunny-progress max="100" value="0" aria-label="Tiến độ tải video" hidden></progress>'+
            '<p class="staff-note" data-bunny-status role="status"></p>'+
            '<div class="staff-actions" data-bunny-actions>'+
                button('Tải video','start')+button('Tạm dừng','pause')+button('Dừng tải','stop')+
                button('Kiểm tra xử lý','refresh')+button('Xem trước video mới','preview')+
                button('Dùng video này','use')+button('Chọn tệp khác','replace')+button('Kiểm tra cấu hình','config')+
            '</div>'+
            '<div class="lesson-editor-preview" data-bunny-preview></div>'+
            '</div>';
    }

    function uploadUrl(value) {
        try {
            const url=new URL(value,endpoint);
            return url.origin==='https://video.bunnycdn.com' && !url.username && !url.password &&
                !url.search && !url.hash && /^\/tusupload\/[^/].*/.test(url.pathname) ? url.href : '';
        } catch {return '';}
    }

    function embedUrl(playback) {
        if(!Number.isFinite(playback?.expiresAt)||playback.expiresAt<=Date.now()/1000)return '';
        try {
            const url=new URL(playback.embedUrl);
            if(url.origin!=='https://player.mediadelivery.net'||url.username||url.password||url.hash||
                !/^\/embed\/\d+\/[a-f0-9-]+\/?$/i.test(url.pathname))return '';
            url.searchParams.set('autoplay','false');
            url.searchParams.set('rememberPosition','false');
            url.searchParams.set('rememberSettings','false');
            return url.href;
        } catch {return '';}
    }

    // Bounded samples keep confirmation fast for large files and work on HTTP LAN
    // sessions where SubtleCrypto can be unavailable. This is not an integrity check.
    async function fingerprint(file) {
        const bytes=64*1024;
        const starts=new Set([0,Math.max(0,Math.floor((file.size-bytes)/2)),Math.max(0,file.size-bytes)]);
        let a=2166136261,b=5381;
        function digest(byte){a=Math.imul(a^byte,16777619);b=Math.imul(b,33)^byte;}
        new TextEncoder().encode(JSON.stringify([file.name,file.size,file.lastModified])).forEach(digest);
        for(const start of starts)new Uint8Array(await file.slice(start,start+bytes).arrayBuffer()).forEach(digest);
        return (a>>>0).toString(16).padStart(8,'0')+(b>>>0).toString(16).padStart(8,'0');
    }

    function message(error) {
        if(error.code==='bunny_video_limit')return 'Đã hết số video cho đợt thử nghiệm. Kiểm tra hạn mức thư viện trước khi tạo lượt tải mới.';
        if(error.status===503)return 'Bunny Stream chưa được cấu hình trên máy chủ 5BMath. Bạn vẫn có thể dùng liên kết video có sẵn.';
        if(error.status===401||error.status===403)return 'Phiên quản trị đã thay đổi hoặc hết hạn. Mở lại bài sau khi đăng nhập.';
        if(error.status===404)return 'Không tìm thấy lượt tải thuộc tài khoản và bài này. Kiểm tra lại tài khoản quản trị.';
        if(error.code==='bunny_video_not_ready')return 'Video chưa sẵn sàng. Kiểm tra lại sau khi Bunny xử lý xong.';
        if(error.code==='bunny_upload_conflict')return 'Lượt tải trước đang chờ xác nhận. Thử lại với cùng tệp để tránh tạo video trùng.';
        if(error.status===502)return '5BMath chưa kết nối được Bunny Stream. Vui lòng thử lại.';
        return error.publicMessage||'Chưa thể thực hiện thao tác với video. Vui lòng thử lại.';
    }

    function mount(form,row,options) {
        const root=form.querySelector('[data-bunny-upload]');
        const node=name=>root.querySelector('[data-bunny-'+name+']');
        const controls=Object.fromEntries([...root.querySelectorAll('[data-bunny-action]')].map(el=>[el.dataset.bunnyAction,el]));
        const picker=node('file'), progress=node('progress'), preview=node('preview');
        const current=idPattern.test(row.bunnyVideo?.uploadId||'')?row.bunnyVideo:null;
        let attached=current, candidate=null, file=null, mime='', client=null, configuration=null, settleTransfer=null, cleared=false;
        let closed=false, visible=false, busy=false, operation='', notice='', ticket=0, previewTimer, pollTimer, polls=0, percent=null;
        let aborting=Promise.resolve();
        const key=options.lessonKey&&options.staffId?'5bmath:bunny-upload:v1:'+JSON.stringify([options.staffId,options.provider,options.lessonKey]):'';
        let record=null;
        try {
            const data=key&&JSON.parse(localStorage.getItem(key));
            if(data&&/^[0-9a-f]{16}$/.test(data.fingerprint)&&idPattern.test(data.requestKey)&&
                (!data.id||idPattern.test(data.id))&&Number.isSafeInteger(data.size)&&data.size>0) {
                record={fingerprint:data.fingerprint,requestKey:data.requestKey,id:data.id||'',size:data.size,
                    url:data.url?uploadUrl(data.url):'',transferred:data.transferred===true};
            }
        } catch {}

        const live=()=>!closed&&form.isConnected&&options.active();
        const active=token=>live()&&visible&&ticket===token;
        const providerAvailable=()=>configuration?.configured===true&&!!options.lessonKey;
        const canUpload=()=>providerAvailable()&&typeof globalThis.tus?.Upload==='function';
        function persist() {
            if(!key)return;
            try {
                if(record)localStorage.setItem(key,JSON.stringify(record));
                else localStorage.removeItem(key);
            } catch {}
        }
        function clearPreview() {
            clearTimeout(previewTimer);
            preview.replaceChildren();
        }
        function render() {
            if(!live())return;
            root.hidden=!visible;
            const working=!!operation;
            const transferring=operation==='transfer';
            const uploadAllowed=canUpload();
            const status=candidate?.status;
            const pending=!!record&&!record.transferred&&!['processing','ready','failed'].includes(status);
            const show=(name,enabled)=>{
                controls[name].hidden=!enabled;
                controls[name].disabled=busy;
            };
            let hint='';
            if(!options.lessonKey)hint='Lưu bản nháp bài này trước, rồi mở lại để tải video từ máy.';
            else if(operation==='config')hint='Đang kiểm tra Bunny Stream…';
            else if(configuration?.configured===false)hint='Bunny Stream chưa được cấu hình trên máy chủ 5BMath. Nhờ quản trị viên cấu hình thư viện và khóa ở máy chủ. Bạn có thể dùng liên kết có sẵn.';
            else if(configuration?.configured&&!uploadAllowed)hint='Trình duyệt chưa tải được công cụ tải video. Tải lại trang để thử lại.';
            else if(!configuration)hint='Chưa xác nhận được trạng thái Bunny Stream.';
            node('config').textContent=hint;
            node('config').hidden=!hint;
            const fileHint=configuration?.maxUploadBytes?' Tối đa '+Math.floor(configuration.maxUploadBytes/1024/1024)+' MB.':'';
            node('file-hint').textContent=pending?'Chọn lại đúng tệp đã tải trước đó để tiếp tục.':'Định dạng MP4, M4V, MOV hoặc WebM.'+fileHint;
            node('source').hidden=!uploadAllowed||!!record&&!pending;
            picker.disabled=busy||working||!uploadAllowed;
            node('attached').hidden=!attached;
            node('attached').textContent=attached?(attached.uploadId===current?.uploadId
                ?'Bài đang dùng video Bunny Stream. '+(labels[attached.status]||'')+'.'
                :'Đã chọn video mới cho bài. Bấm lưu để gắn video.').replace(/\.\./g,'.'):'';
            node('current').hidden=!attached;
            show('preview-current',!!attached&&attached.status==='ready'&&providerAvailable()&&!working);
            show('clear',!!attached&&!working);
            show('start',uploadAllowed&&!!file&&!working&&(!record||pending));
            controls.start.textContent=record?'Tiếp tục tải':'Tải video';
            show('pause',transferring);
            show('stop',transferring);
            show('refresh',providerAvailable()&&!!record?.id&&!working&&!['ready','failed'].includes(status));
            show('preview',providerAvailable()&&status==='ready'&&!working&&attached?.uploadId!==candidate.id);
            show('use',status==='ready'&&!working&&attached?.uploadId!==candidate.id);
            show('replace',uploadAllowed&&!!record&&!working);
            controls.replace.textContent=pending?'Bỏ lượt tải này':'Chọn tệp khác';
            show('config',options.lessonKey&&configuration?.configured!==true&&!working);
            node('status').textContent=notice||(status?labels[status]||'':'');
            progress.hidden=percent===null;
            progress.value=percent??0;
        }

        function halt() {
            ticket++;
            clearTimeout(pollTimer);
            operation='';
            const transfer=client;
            client=null;
            if(transfer)aborting=transfer.abort().catch(()=>{});
            settleTransfer?.('paused');
            settleTransfer=null;
        }
        function destroy() {
            if(closed)return;
            closed=true;
            halt();
            clearPreview();
            observer.disconnect();
            window.removeEventListener('pagehide',destroy);
        }
        const observer=new MutationObserver(()=>{if(!live())destroy();});
        observer.observe(form.closest('dialog')||document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['open']});
        window.addEventListener('pagehide',destroy);

        function schedulePoll() {
            clearTimeout(pollTimer);
            if(!record?.id||!record.transferred||polls>=18||['ready','failed'].includes(candidate?.status))return;
            const token=ticket;
            pollTimer=setTimeout(()=>{if(active(token)&&!busy&&!operation){polls++;refresh();}},5000);
        }

        function applyUpload(upload) {
            if(!idPattern.test(upload?.id||'')||upload.provider!==options.provider||upload.lessonKey!==options.lessonKey||
                upload.size!==record?.size||!Object.hasOwn(labels,upload.status)||(record.id&&record.id!==upload.id))throw Error('Invalid upload response');
            record.id=upload.id;
            if(upload.status==='processing'||upload.status==='ready')record.transferred=true;
            candidate=upload;
            persist();
        }

        async function run(name,task) {
            if(!live()||!visible||busy||operation)return;
            clearTimeout(pollTimer);
            const token=++ticket;
            operation=name;
            notice='';
            render();
            try {await task(token);}
            catch(error){if(active(token))notice=message(error);}
            finally {
                if(!live())destroy();
                if(active(token)){operation='';render();schedulePoll();}
            }
        }

        const refresh=()=>run('refresh',async token=>{
            if(!record?.id)return;
            const result=await options.request(routes+'/'+record.id+'/refresh',{});
            if(active(token))applyUpload(result.upload);
        });
        const checkConfig=()=>run('config',async token=>{
            if(!options.lessonKey)return;
            try {
                const result=await options.request('bunny-stream/config');
                if(active(token))configuration=result;
            } catch(error) {
                if(active(token)&&error.status===503)configuration={configured:false};
                throw error;
            }
        }).then(()=>{
            if(providerAvailable()&&record?.id&&!candidate)refresh();
        });

        async function showPreview(uploadId) {
            clearPreview();
            await run('preview',async token=>{
                const result=await options.request(routes+'/'+uploadId+'/preview',{});
                if(!active(token))return;
                const url=embedUrl(result.playback);
                if(!url)throw Error('Invalid preview response');
                const frame=document.createElement('iframe');
                frame.src=url;
                frame.title='Xem trước video bài học trên Bunny Stream';
                frame.referrerPolicy='strict-origin-when-cross-origin';
                frame.allow='fullscreen; encrypted-media; picture-in-picture';
                frame.allowFullscreen=true;
                preview.replaceChildren(frame);
                previewTimer=setTimeout(()=>{clearPreview();if(live()&&visible){notice='Phiên xem trước đã hết hạn. Bấm xem trước để mở lại.';render();}},
                    Math.min(2147483647,Math.max(0,result.playback.expiresAt*1000-Date.now())));
            });
        }

        function transfer(file,tag,credentials,token) {
            if(credentials?.endpoint!==endpoint||!Number.isFinite(credentials.expiresAt)||!credentials.headers)throw Error('Invalid upload credentials');
            const headers={};
            for(const name of ['AuthorizationSignature','AuthorizationExpire','VideoId','LibraryId']){
                if(typeof credentials.headers[name]!=='string'||!credentials.headers[name])throw Error('Invalid upload header');
                headers[name]=credentials.headers[name];
            }
            let expired=false, denied=false;
            return new Promise(resolve=>{
                settleTransfer=resolve;
                client=new globalThis.tus.Upload(file,{
                    ...(record.url?{uploadUrl:record.url}:{endpoint}),
                    metadata:{filetype:tag,title:'5BMath '+record.id},
                    headers,chunkSize:8*1024*1024,retryDelays:[0,1000,3000],
                    storeFingerprintForResuming:false,
                    onBeforeRequest(request) {
                        if(!active(token))throw Error('Inactive transfer');
                        const url=request.getURL();
                        if(url!==(request.getMethod()==='POST'?endpoint:record.url))throw Error('Unexpected transfer URL');
                        if(Date.now()/1000>=credentials.expiresAt){expired=true;throw Error('Expired credentials');}
                    },
                    onAfterResponse(request,response) {
                        if(!active(token))return;
                        const status=response.getStatus();
                        if(status===401||status===403)denied=true;
                        if(request.getMethod()==='POST'&&status===201){
                            const location=uploadUrl(response.getHeader('Location'));
                            if(!location)throw Error('Invalid transfer location');
                            record.url=location;
                            persist();
                        }
                    },
                    onShouldRetry(error){return active(token)&&!expired&&!denied&&[0,408,409,423,429,500,502,503,504].includes(error.originalResponse?.getStatus()??0);},
                    onProgress(sent,total){
                        if(!active(token)||!total)return;
                        const next=Math.min(99,Math.floor(sent*100/total));
                        if(next!==percent){percent=next;notice='Đang tải lên Bunny Stream · '+percent+'%';render();}
                    },
                    onError(){resolve(expired||denied?'renew':'error');},
                    onSuccess(){resolve('complete');}
                });
                client.start();
            });
        }

        function start() {
            if(!file||!canUpload())return;
            return run('transfer',async token=>{
                await aborting;
                if(!active(token))return;
                const selected=file, selectedMime=mime, fingerprintValue=await fingerprint(selected);
                if(!active(token))return;
                if(record&&record.fingerprint!==fingerprintValue)throw {publicMessage:'Tệp này khác tệp đã tải trước đó. Chọn lại đúng tệp hoặc bỏ lượt tải này.'};
                if(!record) {
                    const requestKey=Array.from(crypto.getRandomValues(new Uint8Array(16)),x=>x.toString(16).padStart(2,'0')).join('');
                    record={fingerprint:fingerprintValue,requestKey,id:'',size:selected.size,url:'',transferred:false};
                    persist();
                }
                for(let attempt=0;attempt<2;attempt++) {
                    notice=attempt?'Đang làm mới quyền tải…':'Đang chuẩn bị tải video…';
                    render();
                    const response=record.id
                        ?await options.request(routes+'/'+record.id+'/renew',{})
                        :await options.request(routes,{provider:options.provider,lessonKey:options.lessonKey,requestKey:record.requestKey,size:selected.size});
                    if(!active(token))return;
                    applyUpload(response.upload);
                    if(record.transferred||candidate.status==='failed'){notice='';return;}
                    const outcome=await transfer(selected,selectedMime,response.tus,token);
                    if(!active(token))return;
                    client=null;
                    settleTransfer=null;
                    if(outcome==='complete') {
                        record.transferred=true;
                        persist();
                        percent=100;
                        notice='';
                        candidate={...candidate,status:'processing'};
                        try {
                            const result=await options.request(routes+'/'+record.id+'/refresh',{});
                            if(active(token))applyUpload(result.upload);
                        } catch(error) {
                            if(active(token))notice='Đã gửi tệp. '+message(error);
                        }
                        polls=0;
                        return;
                    }
                    if(outcome!=='renew'||attempt===1)throw {publicMessage:'Lượt tải bị gián đoạn. Bấm tiếp tục tải để thử lại với cùng tệp.'};
                }
            });
        }

        picker.addEventListener('change',()=>{
            if(!live()||busy||operation)return;
            file=picker.files[0]||null;
            mime=file?mimeTypes[file.name.split('.').pop().toLowerCase()]:'';
            notice='';
            if(file&&(!file.size||!mime||file.type&&!file.type.startsWith('video/')&&file.type!=='application/octet-stream')){
                file=null;notice='Chọn một tệp video có dữ liệu, định dạng MP4, M4V, MOV hoặc WebM.';
            } else if(file&&configuration?.maxUploadBytes&&file.size>configuration.maxUploadBytes){
                file=null;notice='Tệp lớn hơn giới hạn tải video của máy chủ.';
            }
            if(!file)picker.value='';
            render();
        });
        root.addEventListener('click',event=>{
            const action=event.target.closest('[data-bunny-action]')?.dataset.bunnyAction;
            if(!action||!live()||busy||controls[action].hidden)return;
            if(action==='config'){checkConfig();return;}
            if(action==='start'){start();return;}
            if(action==='refresh'){polls=0;refresh();return;}
            if(action==='preview'){showPreview(candidate.id);return;}
            if(action==='preview-current'){showPreview(attached.uploadId);return;}
            if(action==='pause'||action==='stop'){
                halt();
                if(action==='stop'){file=null;picker.value='';}
                notice=action==='pause'?'Đã tạm dừng. Bấm tiếp tục tải để gửi phần còn lại.':'Đã dừng tải. Có thể chọn lại cùng tệp để tiếp tục.';
                render();
                return;
            }
            if(action==='replace'){
                halt();
                clearPreview();
                const abandoned=record?.id!==attached?.uploadId;
                record=null;candidate=null;file=null;picker.value='';percent=null;
                persist();
                notice=abandoned?'Đã bỏ lượt tải khỏi trình biên tập. Video đã tạo vẫn nằm trong thư viện Bunny.':'';
            }
            if(action==='clear'){attached=null;cleared=true;clearPreview();options.changed();}
            if(action==='use'){attached={...candidate,uploadId:candidate.id};cleared=false;clearPreview();options.changed();}
            render();
        });
        return {
            get changed(){return (current?.uploadId||'')!==(attached?.uploadId||'');},
            get uploading(){return operation==='transfer';},
            setVisible(value) {
                if(value===visible)return;
                visible=value;
                if(!visible){halt();clearPreview();notice='';}
                else if(!configuration)checkConfig();
                else if(providerAvailable()&&record?.id&&!candidate)refresh();
                render();
            },
            setBusy(value){busy=value;if(busy){halt();clearPreview();}render();},
            read(mode) {
                if(mode!=='bunny'||!options.lessonKey)return current?{bunnyVideo:null}:{};
                if(!attached) {
                    if(current||cleared)return {bunnyVideo:null};
                    throw Error('Chọn video Bunny đã sẵn sàng hoặc chuyển sang Liên kết có sẵn để lưu bài.');
                }
                return this.changed?{bunnyVideo:{uploadId:attached.uploadId}}:{};
            },
            destroy
        };
    }

    return {markup,mount};
})();
