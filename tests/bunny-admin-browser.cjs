'use strict';
// Real Chrome and the vendored TUS client. All API and Bunny traffic is intercepted.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require(process.env.BUNNY_TEST_PLAYWRIGHT||'playwright');
const source=path.resolve(__dirname,'..','frontend');
const out=process.env.BUNNY_TEST_ARTIFACTS||path.resolve(__dirname,'..','..','artifacts','admin-browser');
const origin='https://bunny-admin.test';
const bunnyOrigin='https://video.bunnycdn.com';
const playerOrigin='https://player.mediadelivery.net';
const secret='fixture-signature-that-must-not-be-persisted';
const id='a'.repeat(32);
const guid='12345678-1234-1234-1234-123456789012';
const resource='/tusupload/demo-fixture';
const ordinary={id:55,client_key:'ordinary-qa',revision:3,grade_id:4,topic_id:7,kind:'weekly',week_no:8,title:'Tổng và hiệu',intro:'Tìm hai số khi biết tổng và hiệu.',publication_status:'published',videoUrl:'',materials:[],examples:[{text:'Tổng 18, hiệu 4. Tìm số bé.',steps:['(18 − 4) : 2 = 7'],answer:'7'}]};
const native={lessonKey:'native-qa',title:'Đổi đơn vị',publishedRevision:4,draftRevision:2,archived:false,sections:['Nội dung 1','Nội dung 2','Nội dung 3'],sectionTitles:['Kiến thức','Ví dụ','Tự kiểm tra'],fixed:{questionKey:'fixed-qa',revision:2,source:{name:'Tự biên soạn'},prompt:'Chọn kết luận đúng.',correctAnswer:'1 m',options:['1 m','2 m','3 m','4 m'],choiceRationales:['Lí do đúng của câu A','Lí do sai của câu B','Lí do sai của câu C','Lí do sai của câu D'],answerShape:'complete-choice',responseMode:'choice',inputGuide:{instruction:'Chọn đáp án',labels:[],units:[],separator:';'}},solution:['Định hướng','Điểm mấu chốt','Bài giải'],videoRef:'',materials:[]};
const attachment={uploadId:id,durationSeconds:46,status:'ready'};
const html='<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/styles.css"><link rel="stylesheet" href="/staff.css"><link rel="stylesheet" href="/staff-catalogue.css"><body class="staff-mode"><main id="app"></main><dialog id="modal"><button id="close-modal" type="button" aria-label="Đóng">×</button><div id="modal-body"></div></dialog><div id="toast"></div>'+
    ['vendor/tus.min.js','bunny-upload.js','lesson-editor.js','staff-catalogue.js','staff.js'].map(name=>'<script src="/'+name+'"></script>').join('')+
    '<script>const modal=document.querySelector("#modal");document.querySelector("#close-modal").onclick=()=>modal.close();StaffApp.mount("admin",{showModal:html=>{document.querySelector("#modal-body").innerHTML=html;if(!modal.open)modal.showModal();},toast:value=>document.querySelector("#toast").textContent=value,passwordFields:()=>{}});</script></body></html>';
const report={scope:'Actual Chrome + official TUS vendor + intercepted API/provider fixtures',checks:[],viewports:[],errors:[]};
const pause=x=>new Promise(resolve=>setTimeout(resolve,x));
const action=(page,name)=>page.locator('[data-bunny-action="'+name+'"]');
const status=(page,text)=>page.locator('[data-bunny-status]').filter({hasText:text}).waitFor();
const uploadFile={name:'video-PRIVATE-FILENAME.mp4',mimeType:'video/mp4',buffer:Buffer.alloc(64*1024,1)};
const pdf={name:'Tai-lieu.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4\n%%EOF')};

async function suite(){
    fs.mkdirSync(out,{recursive:true});
    const onDisk=path.join(out,uploadFile.name);
    fs.writeFileSync(onDisk,uploadFile.buffer);
    const browser=await chromium.launch({headless:true,executablePath:process.env.BUNNY_TEST_CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
    const page=await browser.newPage({viewport:{width:390,height:844}});
    page.setDefaultTimeout(8000);
    page.on('pageerror',error=>report.errors.push(error.message));
    let state,navigation=0;
    const upload=(payload={})=>({id,provider:state.provider,lessonKey:state.row.client_key||state.row.lessonKey,status:state.status,size:state.size,durationSeconds:46,...payload});
    const credentials=version=>({endpoint:bunnyOrigin+'/tusupload',expiresAt:Math.floor(Date.now()/1000)+1800,headers:{AuthorizationSignature:secret+'-'+version,AuthorizationExpire:String(Math.floor(Date.now()/1000)+1800),VideoId:guid,LibraryId:'19'}});
    function fresh(provider='main',options={}){
        state={provider,row:structuredClone(provider==='native'?native:ordinary),owner:navigation+1,configured:true,creates:[],renews:0,offset:0,size:0,
            status:'uploading',tus:[],saves:[],previews:0,refreshes:0,...options};
    }
    async function edit(provider=state.provider){
        await page.locator(provider==='native'?'[data-staff=catalog-native-edit]':'[data-staff=edit-content]').first().click();
        await page.locator('form.lesson-editor').waitFor();
    }
    async function open(provider='main',options={}){
        fresh(provider,options);
        await page.goto(origin+'/quan-tri/?fixture='+(++navigation)+'#'+(provider==='native'?'nativeLessons':'content'));
        await edit(provider);
    }
    async function chooseBunny(){
        await page.locator('[name=videoSource]').selectOption('bunny');
    }
    async function file(value=onDisk){
        await page.locator('[data-bunny-file]').setInputFiles(value);
    }
    async function close(){
        await page.locator('[data-staff=close-modal]').click();
        if(await page.locator('[data-lesson-discard]').isVisible())await page.locator('[data-lesson-discard-now]').click();
        await page.locator('#modal').waitFor({state:'hidden'});
    }
    async function save(){
        await page.locator('#staff-modal-form button[type=submit]').click();
    }
    async function check(name,fn){
        await fn();
        report.checks.push(name);
        console.log('PASS '+name);
    }
    async function layout(provider){
        for(const [width,height] of [[320,720],[390,844],[844,390],[768,1024],[1024,768],[1440,900]]){
            await page.setViewportSize({width,height});
            await page.locator('[data-bunny-file]').scrollIntoViewIfNeeded();
            const geom=await page.evaluate(()=>{
                const modal=document.querySelector('#modal');
                return {document:document.documentElement.scrollWidth,modal:modal.clientWidth,scroll:modal.scrollWidth,
                    buttons:[...modal.querySelectorAll('[data-bunny-action]:not([hidden])')].filter(el=>el.offsetParent).map(el=>el.getBoundingClientRect().height)};
            });
            assert(geom.document<=width+1);
            assert(geom.scroll<=geom.modal+1);
            assert(geom.buttons.every(height=>height>=44));
            report.viewports.push({provider,width,height,...geom});
            if(width===390)await page.screenshot({path:path.join(out,provider+'-390.png')});
        }
        await page.setViewportSize({width:390,height:844});
    }
    await page.route('**/*',async route=>{
        const request=route.request(),url=new URL(request.url()),pathname=url.pathname,method=request.method();
        if(url.origin===bunnyOrigin) {
            const fixture=state;
            const headers={'access-control-allow-origin':origin,'access-control-allow-headers':'*','access-control-allow-methods':'POST, HEAD, PATCH, OPTIONS',
                'access-control-expose-headers':'Location, Upload-Offset, Upload-Length, Tus-Resumable','tus-resumable':'1.0.0'};
            if(method==='OPTIONS')return route.fulfill({status:204,headers});
            const auth=request.headers();
            assert(auth.authorizationsignature?.startsWith(secret));
            assert(!auth['x-csrf-token']);
            assert(!auth['accesskey']);
            assert.equal(auth.videoid,guid);
            fixture.tus.push({method,pathname,offset:auth['upload-offset'],version:Number(auth.authorizationsignature.split('-').at(-1))});
            if(method==='POST'){
                assert.equal(pathname,'/tusupload');
                assert.equal(Number(auth['upload-length']),fixture.size);
                const metadata=Object.fromEntries(auth['upload-metadata'].split(',').map(pair=>{const [k,v]=pair.trim().split(' ');return [k,Buffer.from(v,'base64').toString()];}));
                assert.deepEqual(metadata,{filetype:'video/mp4',title:'5BMath '+id});
                return route.fulfill({status:201,headers:{...headers,location:fixture.foreignLocation?'https://untrusted.test/tusupload/private':resource}});
            }
            assert.equal(pathname,resource);
            if(method==='HEAD'){
                if(fixture.denyHead){fixture.denyHead=false;return route.fulfill({status:401,headers});}
                return route.fulfill({status:200,headers:{...headers,'upload-offset':String(fixture.offset),'upload-length':String(fixture.size)}});
            }
            assert.equal(method,'PATCH');
            if(fixture.holdPatch&&!fixture.patchHeld){
                fixture.patchHeld=true;
                fixture.offset=Math.floor(fixture.size/3);
                await pause(1800);
                return route.fulfill({status:204,headers:{...headers,'upload-offset':String(fixture.offset)}}).catch(()=>{});
            }
            assert.equal(Number(auth['upload-offset']),fixture.offset);
            assert.equal(request.postDataBuffer().length,fixture.size-fixture.offset);
            fixture.offset=fixture.size;
            fixture.status=fixture.instantReady?'ready':'processing';
            return route.fulfill({status:204,headers:{...headers,'upload-offset':String(fixture.offset)}});
        }
        if(url.origin===playerOrigin)return route.fulfill({status:200,contentType:'text/html',body:'<p>Video QA</p>'});
        if(url.origin!==origin)return route.abort();
        if(pathname==='/quan-tri/')return route.fulfill({status:200,contentType:'text/html',body:html});
        if(pathname.startsWith('/api/staff/')){
            const fixture=state;
            const endpoint=pathname.slice('/api/staff/'.length);
            let body,status=200;
            if(method==='POST')assert.equal(request.headers()['x-csrf-token'],'fixture-csrf');
            if(endpoint==='session')body={user:{id:fixture.owner,full_name:'Quản trị QA',role:'admin'},csrf:'fixture-csrf'};
            else if(endpoint==='content')body={rows:[fixture.row],topics:[{id:7,grade_id:4,title:'Số học'}],total:1,page:1,pageSize:25};
            else if(endpoint==='native-lessons/item')body={item:fixture.row};
            else if(endpoint==='native-lessons'&&method==='GET')body={rows:[fixture.row],total:1,page:1,pageSize:25};
            else if(endpoint==='bunny-stream/config')body={configured:fixture.configured,maxVideos:10,maxUploadBytes:1073741824};
            else if(endpoint==='bunny-stream/uploads'){
                const data=request.postDataJSON();
                assert.deepEqual(Object.keys(data).sort(),['lessonKey','provider','requestKey','size']);
                assert.equal(data.provider,fixture.provider);
                assert.equal(data.lessonKey,fixture.row.client_key||fixture.row.lessonKey);
                assert.match(data.requestKey,/^[a-f0-9]{32}$/);
                fixture.creates.push(data);
                fixture.size=data.size;
                if(fixture.delayCreate)await pause(fixture.delayCreate);
                if(fixture.failCreate){fixture.failCreate=false;status=502;body={code:'bunny_upstream',error:'private fixture body'};}
                else body={upload:upload(),tus:credentials(fixture.renews)};
            }
            else if(endpoint.endsWith('/renew')){fixture.renews++;body={upload:upload(),tus:credentials(fixture.renews)};}
            else if(endpoint.endsWith('/refresh')){fixture.refreshes++;body={upload:upload()};}
            else if(endpoint.endsWith('/preview')){
                fixture.previews++;
                if(fixture.status!=='ready'){status=409;body={code:'bunny_video_not_ready'};}
                else body={playback:{embedUrl:(fixture.foreignPreview?'https://untrusted.test':playerOrigin)+'/embed/19/'+guid+'?token=mock-preview-secret',expiresAt:Math.floor(Date.now()/1000)+120}};
            }
            else if(method==='POST'&&['lessons','native-lessons'].includes(endpoint)){
                const data=request.postDataJSON();
                fixture.saves.push(data);
                if(fixture.failSave){status=fixture.failSave;fixture.failSave=0;body={error:'Bài giảng vừa thay đổi. Tải lại trước khi lưu.'};}
                else body={saved:true,item:fixture.row};
            }
            else throw Error('Unexpected fixture '+method+' '+endpoint);
            return route.fulfill({status,contentType:'application/json',body:JSON.stringify(body)});
        }
        const target=path.join(source,pathname.slice(1));
        if(fs.existsSync(target)&&fs.statSync(target).isFile())return route.fulfill({status:200,contentType:pathname.endsWith('.js')?'application/javascript':pathname.endsWith('.css')?'text/css':'image/svg+xml',body:fs.readFileSync(target)});
        return route.abort();
    });

    try {
        await check('Unconfigured provider leaves URL preview and normal save usable',async()=>{
            await open('main',{configured:false});
            await chooseBunny();
            await page.locator('[data-bunny-config]').filter({hasText:'chưa được cấu hình'}).waitFor();
            assert.equal(await page.locator('[data-bunny-file]').isVisible(),false);
            await page.locator('[name=videoSource]').selectOption('url');
            await page.locator('[name=videoUrl]').fill('https://youtu.be/dQw4w9WgXcQ');
            await page.locator('[data-lesson-preview]').click();
            assert.equal(await page.locator('[data-lesson-preview-area] iframe').getAttribute('src'),'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ');
            await save();
            await page.locator('#modal').waitFor({state:'hidden'});
            assert.equal(state.saves[0].videoUrl,'https://youtu.be/dQw4w9WgXcQ');
            assert.equal(state.creates.length,0);
        });
        await check('Normal editor pause, reopen, reject wrong contents and resume with renewed TUS credentials',async()=>{
            await open('main',{holdPatch:true});
            await chooseBunny();
            await file({name:'wrong.txt',mimeType:'text/plain',buffer:Buffer.from('No video')});
            await status(page,'Chọn một tệp video');
            await file();
            await layout('main');
            await action(page,'start').click();
            await wait(()=>state.patchHeld);
            assert(await page.locator('[data-bunny-progress]').isVisible());
            await action(page,'pause').click();
            await status(page,'Đã tạm dừng');
            await close();
            await edit();
            await chooseBunny();
            await page.locator('[data-bunny-file-hint]').filter({hasText:'Chọn lại đúng tệp'}).waitFor();
            await file({...uploadFile,buffer:Buffer.alloc(uploadFile.buffer.length,2)});
            await action(page,'start').click();
            await status(page,'Tệp này khác tệp');
            assert.equal(state.renews,0);
            state.denyHead=true;
            await file();
            await action(page,'start').click();
            await status(page,'Bunny đang xử lý');
            assert.equal(state.creates.length,1);
            assert.equal(state.renews,2);
            assert.deepEqual(state.tus.map(item=>item.method),['POST','PATCH','HEAD','HEAD','PATCH']);
            assert.equal(Number(state.tus.at(-1).offset),Math.floor(state.size/3));
            assert.equal(await action(page,'preview').isVisible(),false);
            assert.equal(await action(page,'use').isVisible(),false);
            await save();
            await page.locator('#staff-form-error').filter({hasText:'Chọn video Bunny đã sẵn sàng'}).waitFor();
            assert.equal(state.saves.length,0);
            state.status='ready';
            await action(page,'refresh').click();
            await status(page,'Video đã sẵn sàng');
            state.foreignPreview=true;
            await action(page,'preview').click();
            await status(page,'Chưa thể thực hiện');
            assert.equal(await page.locator('[data-bunny-preview] iframe').count(),0);
            state.foreignPreview=false;
            await action(page,'preview').click();
            const frame=page.locator('[data-bunny-preview] iframe');
            await frame.waitFor();
            assert.equal(new URL(await frame.getAttribute('src')).searchParams.get('rememberPosition'),'false');
            await action(page,'use').click();
            assert.equal(await frame.count(),0);
            await page.locator('[data-lesson-pdf]').setInputFiles(pdf);
            await page.locator('[data-lesson-file-status]').filter({hasText:'1 PDF đã thêm'}).waitFor();
            await page.locator('[name=status]').selectOption('published');
            await save();
            await page.locator('#modal').waitFor({state:'hidden'});
            assert.deepEqual(state.saves[0].bunnyVideo,{uploadId:id});
            assert.equal(state.saves[0].videoUrl,'');
            assert.equal(state.saves[0].status,'published');
            assert.equal(state.saves[0].examples.length,1);
            assert.equal(state.saves[0].materials[0].upload.base64,pdf.buffer.toString('base64'));
            const stored=await page.evaluate(()=>JSON.stringify(localStorage));
            for(const forbidden of [secret,'mock-preview-secret','PRIVATE-FILENAME','fixture-csrf'])assert(!stored.includes(forbidden));
            assert(!JSON.stringify(state.saves).includes('mock-preview-secret'));
        });
        await check('Native editor handles create retry with same idempotency key and preserves fixed metadata',async()=>{
            await open('native',{failCreate:true,instantReady:true});
            await chooseBunny();
            await file();
            await layout('native');
            await action(page,'start').click();
            await status(page,'chưa kết nối được Bunny Stream');
            await action(page,'start').click();
            await status(page,'Video đã sẵn sàng');
            assert.equal(state.creates.length,2);
            assert.deepEqual(state.creates[0],state.creates[1]);
            await action(page,'use').click();
            await save();
            await page.locator('#modal').waitFor({state:'hidden'});
            assert.deepEqual(state.saves[0].bunnyVideo,{uploadId:id});
            assert.equal(state.saves[0].videoRef,'');
            assert.equal(state.saves[0].action,'draft');
            assert(!('fixed' in state.saves[0]));
            assert(!('solution' in state.saves[0]));
        });
        await check('Native saved video preserved, stale revision guarded, explicit URL switch clears reference',async()=>{
            await open('native',{row:{...structuredClone(native),bunnyVideo:attachment},failSave:409,status:'ready'});
            await action(page,'preview-current').click();
            await page.locator('[data-bunny-preview] iframe').waitFor();
            await save();
            await page.locator('[data-lesson-conflict]:not([hidden])').waitFor();
            assert(!('bunnyVideo' in state.saves[0]));
            assert(await page.locator('#staff-modal-form button[type=submit]').isDisabled());
            assert.equal(await page.locator('[data-bunny-preview] iframe').count(),0);
            state.row.draftRevision++;
            await page.locator('[data-lesson-reload]').click();
            await page.locator('[data-lesson-conflict]').waitFor({state:'hidden'});
            await page.locator('[name=videoSource]').selectOption('url');
            await page.locator('[name=videoUrl]').fill('https://example.test/replacement.mp4');
            await save();
            await page.locator('#modal').waitFor({state:'hidden'});
            assert.equal(state.saves[1].bunnyVideo,null);
            assert.equal(state.saves[1].videoRef,'https://example.test/replacement.mp4');
            assert.equal(state.saves[1].draftRevision,native.draftRevision+1);
        });
        await check('Delayed create response cannot start TUS after switching video source',async()=>{
            await open('main',{delayCreate:1000});
            await chooseBunny();
            await file();
            await action(page,'start').click();
            await wait(()=>state.creates.length===1);
            await page.locator('[name=videoSource]').selectOption('url');
            await pause(1100);
            assert.equal(state.tus.length,0);
            assert.equal(await page.locator('[data-bunny-upload]').isVisible(),false);
            await chooseBunny();
            await action(page,'start').click();
            await status(page,'Bunny đang xử lý');
            assert.deepEqual(state.creates[1],state.creates[0]);
        });
        await check('Foreign TUS Location is never followed or kept in resumable storage',async()=>{
            await open('main',{foreignLocation:true});
            await chooseBunny();
            await file();
            await action(page,'start').click();
            await status(page,'Lượt tải bị gián đoạn');
            assert(state.tus.every(item=>item.method==='POST'));
            assert(!(await page.evaluate(()=>JSON.stringify(localStorage))).includes('untrusted.test'));
        });
        await check('Stop aborts transfer, then same file resumes without a second TUS creation',async()=>{
            await open('main',{holdPatch:true,instantReady:true});
            await chooseBunny();
            await file();
            await action(page,'start').click();
            await wait(()=>state.patchHeld);
            await action(page,'stop').click();
            await status(page,'Đã dừng tải');
            assert.equal(await action(page,'start').isVisible(),false);
            await file();
            await action(page,'start').click();
            await status(page,'Video đã sẵn sàng');
            assert.deepEqual(state.tus.map(item=>item.method),['POST','PATCH','HEAD','PATCH']);
        });
        await check('Switching staff account does not recover another owner’s stored transfer',async()=>{
            await open('main',{holdPatch:true});
            await chooseBunny();
            await file();
            await action(page,'start').click();
            await wait(()=>state.patchHeld);
            await action(page,'stop').click();
            await close();
            state.owner+=100;
            await page.goto(origin+'/quan-tri/?fixture='+(++navigation)+'#content');
            await edit();
            await chooseBunny();
            await page.locator('[data-bunny-file-hint]').filter({hasText:'Định dạng MP4'}).waitFor();
            assert.equal(state.refreshes,0);
            assert.equal(state.renews,0);
        });
        await check('New normal lesson must be saved before it can upload to Bunny',async()=>{
            await open();
            await close();
            await page.locator('[data-staff=new-content]').click();
            await chooseBunny();
            await page.locator('[data-bunny-config]').filter({hasText:'Lưu bản nháp'}).waitFor();
            assert.equal(await page.locator('[data-bunny-file]').isVisible(),false);
            await page.locator('form.lesson-editor [name=grade]').selectOption('4');
            await page.locator('[name=title]').fill('Bài mới');
            await page.locator('[name=intro]').fill('Nội dung bài mới');
            await save();
            await page.locator('#modal').waitFor({state:'hidden'});
            assert.equal(state.saves[0].status,'draft');
            assert(!('bunnyVideo' in state.saves[0]));
            assert.equal(state.creates.length,0);
        });
        assert.deepEqual(report.errors,[]);
        report.success=true;
    } catch(error) {
        report.lastStatus=await page.locator('[data-bunny-status]').textContent().catch(()=>null);
        report.lastTransfer={attempts:state.tus,creates:state.creates.length,renews:state.renews};
        throw error;
    } finally {
        fs.writeFileSync(path.join(out,'RESULT.json'),JSON.stringify(report,null,2));
        await browser.close();
    }
}
async function wait(predicate){
    for(let i=0;i<120;i++){if(predicate())return;await pause(25);}
    throw Error('Fixture wait timed out');
}
suite().catch(error=>{console.error(error);process.exitCode=1;});
