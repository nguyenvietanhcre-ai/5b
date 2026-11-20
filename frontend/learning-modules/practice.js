/* practice: extracted behavior; state and cross-feature services supplied explicitly. */
(function(global){'use strict';
function create(ctx){
function examOptions(scope,search='') {
        const lessons=ctx.lessonList(),options=scope==='weekly'?[['','Tổng hợp đến hiện tại'],...Array.from({length:ctx.week()},(_,i)=>{
            const list=lessons.filter(l=>l.week===i+1);return ['week-'+(i+1),'Tuần '+(i+1)+' : '+(list.map(l=>l.title).join(' · ')||'Đang biên soạn'),!list.length];
        })]:[...new Map(lessons.map(l=>[l.topic,[l.topic,l.title.replace(/^Ôn tập: /,'')]])).values()];
        return options.filter(([,label])=>!search||label.toLocaleLowerCase('vi').includes(search.toLocaleLowerCase('vi'))).map(([value,label,disabled])=>`<option value="${ctx.escape(value)}" ${disabled?'disabled':''}>${ctx.escape(label)}</option>`).join('');
    }

function getExam() {
        return ctx.state.exams[ctx.query('id') || ctx.state.activeExam];
    }

function rememberExamAnswer(input) {
        const exam=getExam();if(!exam||exam.submittedAt)return;
        const position=Number(input.dataset.position),qid=input.dataset.questionId;
        exam.answers[qid]=input.value;
        if(!ctx.live){ctx.save();updateExamProgress(exam);return;}
        ctx.examDrafts.set(exam.id+':'+position,{id:exam.id,position,answer:input.value,owner:PlatformAPI.snapshot.account?.id});
        updateExamProgress(exam);
        const status=document.querySelector('#answer-save-status');if(status)status.textContent='Đang lưu…';
        clearTimeout(ctx.draftTimer);ctx.draftTimer=setTimeout(()=>flushExamDrafts().catch(e=>ctx.host.toast(e.message)),250);
    }

function updateExamProgress(exam) {
        const done=q=>Boolean(String(exam.answers[q.id]??'').trim());
        const progress=document.querySelector('#learning-answered');if(progress)progress.textContent=exam.questions.filter(done).length+' / '+exam.questions.length+' câu đã trả lời';
        document.querySelectorAll('[data-question]').forEach(nav=>{const i=Number(nav.dataset.question),answered=done(exam.questions[i]);nav.classList.toggle('done',answered);nav.setAttribute('aria-label','Câu '+(i+1)+(answered?' · Đã trả lời':' · Chưa trả lời'));});
    }

async function flushExamDrafts() {
        if(!ctx.learnerBackgroundAllowed()){clearTimeout(ctx.draftTimer);return;}
        clearTimeout(ctx.draftTimer);
        if(ctx.draftSaving){await ctx.draftSaving;if(ctx.examDrafts.size)return flushExamDrafts();return;}
        ctx.draftSaving=(async()=>{
            while(ctx.examDrafts.size){
                const [key,item]=ctx.examDrafts.entries().next().value;
                if(item.owner!==PlatformAPI.snapshot.account?.id){ctx.examDrafts.delete(key);continue;}
                try{const exam=ctx.state.exams[item.id];const result=await PlatformAPI.request('exams/'+item.id+'/answers',{position:item.position,answer:item.answer,revision:exam?.revision??0},{owner:item.owner});if(exam&&Number.isInteger(result.exam?.revision))exam.revision=result.exam.revision;}
                catch(error){const status=document.querySelector('#answer-save-status');if(status)status.textContent='Chưa lưu được. Hãy thử lại trước khi rời bài.';throw error;}
                if(ctx.examDrafts.get(key)===item)ctx.examDrafts.delete(key);
            }
            const status=document.querySelector('#answer-save-status');if(status)status.textContent='Đã lưu';
        })();
        try{await ctx.draftSaving;}finally{ctx.draftSaving=null;}
    }

function practiceCreateButton(label,action,category){
        const create=ctx.button(label,action,'dark','arrow');
        if(!ctx.live)return ctx.canUse(category)?create:ctx.link('Nâng cấp gói','upgrade');
        const standard=ctx.canUse(category);
        return `<div data-main-practice-create data-standard-allowed="${standard}" ${standard?'':'hidden'}>${create}</div>`;
    }

async function loadPurchasedPractice(){
        const panel=document.querySelector('#main-purchased-practice'),owner=PlatformAPI.snapshot.account?.id;
        if(!panel||!owner||!window.FamilyCart)return;
        const bought=document.querySelector('#main-purchased-exams');
        PlatformAPI.request('premium',undefined,{owner}).then(result=>FamilyCart.mountPurchasedExams(bought,result.purchases,openCreatedExam)).catch(()=>{});
        let markup,wallet;
        try{wallet=await PlatformAPI.request('purchased-credits',undefined,{owner});markup=FamilyCart.fundingPanel(wallet);}
        catch(error){if(error.name==='AbortError')return;markup='<p role="status">Chưa đọc được số dư lượt đã mua.</p>';}
        if(!panel.isConnected||!markup)return;
        panel.innerHTML=markup;
        panel.hidden=false;
        const select=panel.querySelector('#exam-funding');
        if(!select)return;
        select.closest('label').insertAdjacentHTML('afterend','<label class="field" data-main-funded-count hidden><span>Số câu</span><select id="main-funded-count"></select></label><p data-main-funded-count-note hidden>Đề 3 câu dùng cho Ôn theo nội dung. Đề tổng hợp dùng 10 câu.</p>');
        const countField=panel.querySelector('[data-main-funded-count]'),countSelect=panel.querySelector('#main-funded-count');
        const countNote=panel.querySelector('[data-main-funded-count-note]');
        countSelect.onchange=()=>{countNote.hidden=countSelect.value!=='3';};
        select.onchange=()=>{
            const app=panel.closest('#learning-app');
            for(const control of app.querySelectorAll('[data-main-practice-create]'))control.hidden=!select.value&&control.dataset.standardAllowed!=='true';
            const options=wallet.products.find(product=>product.sku===select.value)?.eligibleCounts||[];
            countField.hidden=options.length===0;
            countSelect.replaceChildren(...options.map(count=>new Option(count+' câu',count,false,count===options.at(-1))));
            countSelect.onchange();
        };
    }

function openCreatedExam(exam){
        ctx.state.exams[exam.id]=exam;
        ctx.state.activeExam=exam.id;
        ctx.go('testing',{id:exam.id});
    }

async function quotePurchasedExam(criteria){
        const panel=document.querySelector('#main-purchased-practice'),owner=PlatformAPI.snapshot.account?.id;
        if(!panel||panel.getAttribute('aria-busy')==='true'||!owner)return;
        panel.setAttribute('aria-busy','true');
        try{
            const quote=await PlatformAPI.request('exams/quote',criteria,{owner});
            if(!panel.isConnected||ctx.currentRoute!=='exams')return;
            const purchased=quote.purchased;
            const unit=purchased.sku==='questions-100'?'câu luyện tập':'lượt tạo đề tự chọn';
            const body={...criteria,requestKey:ctx.uid(),quoteId:quote.quoteId,confirmPurchased:true};
            ctx.host.showModal(`<form id="confirm-purchased-exam"><h2 class="modal-title">Xác nhận dùng lượt đã mua</h2><p>Tạo đề ${criteria.count} câu sẽ dùng <strong>${Number(purchased.quantity)} ${unit}</strong>.</p><p>Số dư sau khi tạo đề còn <strong>${Number(purchased.remainingAfter)} ${unit}</strong>.</p><p role="alert" data-purchased-exam-error></p><div class="actions"><button class="btn dark" type="submit">Xác nhận tạo đề</button><button class="btn outline" type="button" data-cancel-purchased-exam>Quay lại</button></div></form>`);
            const form=document.querySelector('#confirm-purchased-exam'),dialog=form.closest('dialog'),submit=form.querySelector('[type=submit]');
            const cancel=form.querySelector('[data-cancel-purchased-exam]');
            cancel.onclick=()=>dialog.close();
            form.onsubmit=async event=>{
                event.preventDefault();
                if(submit.disabled||!panel.isConnected)return;
                submit.disabled=cancel.disabled=true;
                const feedback=form.querySelector('[data-purchased-exam-error]');
                feedback.textContent='';
                let stale=false;
                try{
                    const {exam}=await PlatformAPI.request('exams',body,{owner});
                    if(panel.isConnected){dialog.close();openCreatedExam(exam);}
                }catch(error){
                    if(error.name==='AbortError'||!form.isConnected)return;
                    stale=error.status===409;
                    feedback.textContent=error.message+(stale?' Quay lại để kiểm tra và xác nhận lại số lượt.':'');
                }finally{submit.disabled=stale;cancel.disabled=false;}
            };
        }finally{panel.removeAttribute('aria-busy');}
    }

async function createExam({topic = '', count = 10, difficulty = 0, maxWeek, week:exactWeek, category, school} = {}) {
        if(ctx.live){
            const criteria={topic,count,difficulty,maxWeek,week:exactWeek,category:category||(topic||maxWeek!==undefined?'content':'combined'),school};
            const funding=document.querySelector('#exam-funding')?.value;
            if(funding&&criteria.category==='school')throw new Error('Lượt đã mua dùng cho Ôn theo nội dung hoặc Đề tổng hợp. Hãy chọn lại nguồn lượt để luyện đề theo trường.');
            if(funding){
                const fundedCount=Number(document.querySelector('#main-funded-count')?.value)||count;
                if(criteria.category==='combined'&&fundedCount!==10)throw new Error('Đề tổng hợp dùng 10 câu. Em chọn 10 câu hoặc tạo đề 3 câu trong Ôn theo nội dung.');
                return quotePurchasedExam({...criteria,count:fundedCount,funding});
            }
            const {exam}=await PlatformAPI.request('exams',{...criteria,requestKey:ctx.uid()});
            openCreatedExam(exam);return;
        }
        ctx.consumeLocal(category||(topic||maxWeek!==undefined?'content':'combined'));
        maxWeek = maxWeek ?? 35;
        const previous = Object.values(ctx.state.exams).at(-1);
        const questions = ctx.content.generate({grade:ctx.grade(),topic,count,difficulty,maxWeek},previous?.questions.map(question => question.id));
        const id = ctx.uid();
        const startedAt = Date.now();
        const exam = {
            id, code:'5B-' + id.replaceAll('-','').slice(0,8).toUpperCase(),
            title: topic ? 'Ôn luyện · ' + questions[0].topicTitle : 'Thi thử tổng hợp',
            grade:ctx.grade(), questions, answers:{}, index:0, startedAt,
            expiresAt:startedAt + (count === 3 ? 10 : 30) * 60000,
        };
        ctx.state.exams[id] = exam;
        ctx.state.activeExam = id;
        ctx.save();
        ctx.go('testing',{id});
    }

async function finishExam(exam) {
        try{await flushExamDrafts();}catch(error){ctx.host.toast(error.message);return;}
        if(ctx.live){
            if(ctx.submitting)return;
            ctx.submitting=true;
            try {
                const result=await PlatformAPI.request('exams/'+exam.id+'/submit',{revision:ctx.state.exams[exam.id]?.revision??exam.revision??0});
                ctx.state.exams[exam.id]=result.exam;
                ctx.go('results',{id:exam.id});
            }catch(error){ctx.host.toast(error.message);}finally{ctx.submitting=false;}
            return;
        }
        ctx.load();
        const saved = ctx.state.exams[exam.id];
        if (!saved || saved.submittedAt) {
            if (saved) ctx.go('results',{id:saved.id});
            return;
        }
        saved.correct = saved.questions.filter(question => ctx.isCorrect(question,saved.answers[question.id])).length;
        saved.score = Math.round(saved.correct / saved.questions.length * 100) / 10;
        saved.duration = Math.floor((Math.min(Date.now(),saved.expiresAt) - saved.startedAt) / 1000);
        saved.submittedAt = new Date().toISOString();
        ctx.save();
        ctx.go('results',{id:saved.id});
    }

function requestSubmit() {
        const exam = getExam();
        if (!exam || exam.submittedAt) return;
        const missing = exam.questions.filter(question => !exam.answers[question.id]).length;
        ctx.host.showModal(`<h2 class="modal-title">Nộp bài thi thử?</h2><p>${missing ? 'Em còn ' + missing + ' câu chưa trả lời. Câu trống được tính 0 điểm.' : 'Em đã trả lời toàn bộ câu hỏi.'}</p><div class="actions"><button class="btn outline" id="learning-continue" type="button">Làm tiếp</button><button class="btn dark" id="learning-confirm-submit" type="button">Nộp bài</button></div>`);
        document.querySelector('#learning-continue').onclick = () => document.querySelector('#modal').close();
        document.querySelector('#learning-confirm-submit').onclick = () => {
            document.querySelector('#modal').close();
            finishExam(exam);
        };
    }
const views = {
exams() {
            const history=ctx.submittedExams().sort((a,b)=>b.submittedAt.localeCompare(a.submittedAt));
            const active=ctx.state.exams[ctx.state.activeExam];
            return `${ctx.intro('Luyện tập','Chọn nội dung, làm đề và xem lại lời giải.',ctx.badge('Khối '+ctx.grade(),'sage'))}${ctx.bankNotice()}${ctx.live?'<section class="card card-pad purchased-practice" id="main-purchased-practice" hidden></section>':''}
            ${active&&!active.submittedAt?`<section class="card card-pad"><h2>Tiếp tục đề đang làm</h2><p>${ctx.escape(active.code)}</p>${ctx.link('Làm tiếp','testing','dark','arrow',{id:active.id})}</section>`:''}${ctx.live?'<section class="card card-pad purchased-practice" id="main-purchased-exams" hidden></section>':''}
            <div class="grid3 exam-types"><section class="card card-pad">${ctx.tile('target')}<h2>Ôn theo nội dung</h2><p>Luyện tập theo chương trình trên lớp hoặc theo chuyên đề nâng cao</p>${ctx.usagePanel('content')}${ctx.field('Phạm vi','exam-scope',[['weekly','Theo chương trình học trên lớp'],['topic','Chuyên đề nâng cao']])}<label class="field"><span>Nội dung · Tìm kiếm</span><input id="exam-content-search" type="search" placeholder="Tìm tuần hoặc nội dung" aria-label="Tìm nội dung luyện tập"></label><label class="field"><span>Nội dung</span><select id="exam-topic" size="5" aria-label="Nội dung luyện tập">${examOptions('weekly')}</select></label>${practiceCreateButton('Tạo đề theo nội dung','create-topic','content')}</section>
            <section class="card card-pad">${ctx.tile('file','peach')}<h2>Đề tổng hợp</h2><p>Thi thử với mẫu đề thi cấp 2 CLC trên cả nước</p>${ctx.usagePanel('combined')}${ctx.field('Độ khó','exam-difficulty',ctx.content.levels.slice(0,3).map((label,index)=>[index,label]))}${practiceCreateButton('Tạo đề ngẫu nhiên','create-exam','combined')}<small>Đề luyện mẫu tự biên soạn.</small></section>
            <section class="card card-pad"><div class="split">${ctx.tile('lock','sand')}${ctx.badge('Chỉ dành cho khối 5','peach')}</div><h2>Đề theo trường</h2><p>Đề theo mẫu chuẩn của các trường cấp 2 CLC trên địa bàn Hà Nội. Phù hợp với học sinh có mục tiêu trường cụ thể hoặc các bạn HSG trên cả nước muốn thử sức.</p>${ctx.badge(['VIP+','SVip'].includes(ctx.member())?'Đã mở khóa · VIP+':'Dành cho VIP+','sand')}${ctx.field('Trường','exam-school',[['cau-giay','THCS Cầu Giấy'],['ngoai-ngu','THCS Ngoại ngữ'],['ntt','Nguyễn Tất Thành']])}${['VIP+','SVip'].includes(ctx.member())&&ctx.grade()===5?ctx.button('Luyện đề theo trường','create-school','dark'):ctx.isPaid()?ctx.notice('Chức năng dành cho học sinh khối 5.'):ctx.link('Nâng cấp gói','upgrade','outline','lock')}<small>Hiện dùng ngân hàng mẫu tự biên soạn; cấu trúc chuẩn theo từng trường đang được biên tập, chưa phải đề chính thức.</small></section></div>
            <section class="card card-pad practice-lookup"><h2>Tra cứu câu hỏi</h2><p>Xem lại câu hỏi bằng mã khi cần ôn tập.</p>${ctx.link('Tra cứu mã câu hỏi','lookup','outline','search')}</section>${ctx.heading('Đề đã làm')}<div class="card list">${history.map(exam=>`<a class="list-row" href="${ctx.href('results',{id:exam.id})}">${ctx.tile('file','peach')}<div><strong>${ctx.escape(exam.title)}</strong><small>${ctx.escape(exam.code)} · ${new Date(exam.submittedAt).toLocaleDateString('vi-VN')}</small></div>${ctx.badge(exam.score+'/10','sage')}${ctx.icon('chevron',17)}</a>`).join('')||'<p class="card-pad">Em chưa hoàn thành đề nào.</p>'}</div>`;
        },
testing() {
            const exam=getExam();if(!exam)return ctx.intro('Làm đề','Chọn một đề để bắt đầu.')+ctx.link('Chọn cách luyện','exams');if(exam.submittedAt)return ctx.views.results();
            const index=Math.min(exam.index||0,exam.questions.length-1),question=exam.questions[index],count=exam.questions.filter(q=>String(exam.answers[q.id]??'').trim()).length;
            const choice=question.responseMode==='choice'||exam.responseMode==='choice';
            const answer=choice?'<div class="answers">'+ctx.questionFrame.choices(question,{provider:'main'}).map(option=>'<label class="answer"><input type="radio" name="learning-answer" value="'+ctx.escape(option.submitValue)+'" '+(exam.answers[question.id]===option.submitValue?'checked':'')+'><b>'+option.label+'</b>'+ctx.escape(typeof question.answer==='number'?ctx.content.format(Number(option.submitValue)):option.text)+'</label>').join('')+'</div>':ctx.answerInput(exam.answers[question.id]??'',false,question.answerKind);
            return ctx.back('Luyện tập','exams')+ctx.intro(exam.title,'Khối '+exam.grade+' · '+exam.code)+'<div class="grid-wide"><section class="card card-pad question practice-content-section"><div class="practice-sticky-stack"><div class="practice-question-meta">'+ctx.badge('Câu '+(index+1)+' / '+exam.questions.length,'sage')+'<span class="practice-time-badge" id="learning-timer" role="timer" aria-live="off">'+ctx.icon('clock')+' '+ctx.timeLeft(exam.expiresAt)+'</span></div><div class="practice-question-text" tabindex="0" aria-label="Đề bài">'+ctx.questionFrame.prompt(question,{provider:'main',renderBlocks:blocks=>ctx.rich(blocks,exam.assets),renderText:ctx.escape})+'</div><div class="practice-answer-controls">'+answer+'</div><div class="practice-question-navigation">'+ctx.button('Câu trước','previous','outline','back',index===0?'disabled':'')+ctx.button('Câu sau','next','dark','arrow',index===exam.questions.length-1?'disabled':'')+'</div></div>'+ctx.PracticeScratchpad.markup()+'</section><aside class="card card-pad self-start"><h2>Phiếu làm bài</h2><p id="learning-answered">'+count+' / '+exam.questions.length+' câu đã trả lời</p><div class="question-grid">'+exam.questions.map((item,n)=>'<button type="button" data-question="'+n+'" class="'+(n===index?'current ':'')+(String(exam.answers[item.id]??'').trim()?'done':'')+'" aria-current="'+(n===index?'step':'false')+'" aria-label="Câu '+(n+1)+(String(exam.answers[item.id]??'').trim()?' · Đã trả lời':' · Chưa trả lời')+'">'+(n+1)+'</button>').join('')+'</div><div class="practice-export-actions">'+ctx.button('Nộp bài','submit-exam','dark','check')+(ctx.browser&&ctx.live&&PlatformAPI.snapshot.practiceExport?.enabled&&typeof PracticeExport!=='undefined'?PracticeExport.button('main',exam.id):'')+'</div></aside></div>';
        },
results() {
            const exam=getExam();if(!exam?.submittedAt)return ctx.intro('Kết quả','Chưa có kết quả cho đề này.')+ctx.link('Về luyện tập','exams');
            if(exam.legacy)return ctx.back('Luyện tập','exams')+ctx.intro('Kết quả đã lưu',exam.title)+'<section class="card card-pad"><h2>'+exam.score+' / 10 điểm</h2><p>Bản ghi cũ giữ điểm và ngày làm. Em có thể xem lại đề mẫu ban đầu.</p><a class="btn outline" href="/de-thi-thu-toan-vao-lop-6/">Mở đề mẫu</a></section>';
            return ctx.back('Luyện tập','exams')+ctx.intro('Kết quả',exam.title+' · '+exam.code)+'<section class="result-band sage"><div class="score-circle"><strong>'+exam.score+'<span>/10</span></strong><small>Điểm của em</small></div><div><h2>Đã chấm xong!</h2><p>'+exam.correct+' / '+exam.questions.length+' câu đúng · Thời gian '+ctx.timeText(exam.duration)+'</p><div class="actions">'+(exam.canRetake===false?'':ctx.button('Làm lại đề này','retake-exam','dark'))+ctx.link('Tạo đề khác','exams','outline')+'</div></div></section>'+ctx.heading('Xem lại câu hỏi')+'<label class="review-filter"><input type="checkbox" id="review-incorrect"> Xem lại câu sai</label><div class="solution-list">'+exam.questions.map((q,i)=>{const correct=typeof q.correct==='boolean'?q.correct:ctx.isCorrect(q,exam.answers[q.id]);return '<article class="card card-pad solution '+(correct?'is-correct':'is-wrong')+'" data-review-correct="'+correct+'"><h3 class="solution-question-title">Câu '+(i+1)+' - '+ctx.escape(q.questionCode||q.contentKey||'Chưa có mã')+' - '+(correct?'Đúng':'Sai')+'</h3><div>'+(ctx.live&&q.prompt?ctx.rich(q.prompt,exam.assets)+ctx.solutionView.sampleFigure(q):'<p>'+ctx.escape(q.text)+'</p>')+'</div><p>Em trả lời: '+ctx.escape(exam.answers[q.id]??'chưa trả lời')+'</p><button type="button" class="solution-inline-toggle" data-solution-toggle="main-solution-'+i+'" aria-expanded="false" aria-controls="main-solution-'+i+'">Xem lời giải</button><div id="main-solution-'+i+'" hidden>'+(ctx.studySolution?ctx.studySolution.render(q,{renderBlocks:blocks=>ctx.rich(blocks,exam.assets,true)}):ctx.solutionView.answer(q.answer,'Đáp án')+(ctx.live&&q.solution?ctx.rich(q.solution,exam.assets,true):'<ol>'+q.steps.map(step=>'<li>'+ctx.solutionView.text(step)+'</li>').join('')+'</ol>'))+'</div></article>';}).join('')+'</div>';
        }
};
const actions = {
'retake-exam':async()=>{
            const exam=getExam();if(!exam?.submittedAt)return;
            if(ctx.live){const result=await PlatformAPI.request('exams/'+encodeURIComponent(exam.id)+'/retake',{requestKey:ctx.uid()});ctx.go('testing',{id:result.exam.id});return;}
            const id=ctx.uid(),started=Date.now(),duration=Math.max(60000,exam.expiresAt-exam.startedAt);ctx.state.exams[id]={...exam,id,rootExamId:exam.rootExamId||exam.id,index:0,startedAt:started,expiresAt:started+duration,submittedAt:null,score:null,correct:null,answers:{}};ctx.state.activeExam=id;ctx.save();ctx.go('testing',{id});
        },
'create-exam':() => createExam({difficulty:Number(document.querySelector('#exam-difficulty').value)}),
'create-topic':()=>{const value=document.querySelector('#exam-topic').value;return createExam(document.querySelector('#exam-scope').value==='weekly'?{maxWeek:ctx.week(),week:value?Number(value.replace('week-','')):undefined,category:'content'}:{topic:value,category:'content'});},
'create-school':()=>createExam({category:'school',school:document.querySelector('#exam-school').value}),
previous() { const exam = getExam(); exam.index = Math.max(0,exam.index - 1); ctx.save(); ctx.refresh(); },
next() { const exam = getExam(); exam.index = Math.min(exam.questions.length - 1,exam.index + 1); ctx.save(); ctx.refresh(); },
'submit-exam':requestSubmit
};
return {views,actions,examOptions,getExam,rememberExamAnswer,updateExamProgress,flushExamDrafts,practiceCreateButton,loadPurchasedPractice,openCreatedExam,quotePurchasedExam,createExam,finishExam,requestSubmit};
}
const api={create};(global.LearningFeatures??={})['practice']=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
