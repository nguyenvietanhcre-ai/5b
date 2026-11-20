/* study: extracted behavior; state and cross-feature services supplied explicitly. */
(function(global){'use strict';
function create(ctx){
function homeworkPanel() {
        return `<details class="card card-pad"><summary>Phiếu luyện tập mẫu · Khối 5</summary><p>Phiếu luyện tập tự biên soạn để tham khảo. Nộp bài cho thầy cô ở đúng bài tập của buổi học phía trên.</p>${ctx.button('Tải phiếu bài tập','download-material','outline')}</details>`;
    }

function lessonVideo(lesson) {
        return ctx.lessonStudy.video(lesson?.videoRef||lesson?.video_ref||'',lesson?.title)||'<div class="video-art"><div class="formula">'+ctx.escape(lesson?.symbol||'Toán')+'</div><p>Video bài giảng đang được chuẩn bị.</p></div>';
    }

function lessonExamples(lesson) {
        const examples=Array.isArray(lesson.examples)?lesson.examples:[ctx.live?lesson.example:ctx.content.problem(ctx.grade(),lesson.topic,1,0)];
        return examples.filter(example=>example&&typeof example.text==='string'&&example.text.trim()).slice(0,10);
    }

function lessonSamples(examples) {
        if(!examples.length)return '';
        return '<section id="lesson-exercises" class="card card-pad lesson-sample" hidden><h2>Câu hỏi mẫu theo bài</h2><p class="lesson-sample-notice">Em tự trình bày cách làm rồi đối chiếu lời giải mẫu. Phần này không chấm điểm.</p>'+examples.map((example,index)=>{
            const steps=Array.isArray(example.steps)?example.steps.filter(step=>typeof step==='string'&&step.trim()):[],hasAnswer=example.answer!==undefined&&example.answer!==null&&String(example.answer).trim()!=='';
            const solution=(steps.length?'<ol>'+steps.map(step=>'<li>'+ctx.solutionView.text(step)+'</li>').join('')+'</ol>':'')+(hasAnswer?ctx.solutionView.answer(example.answer):'')+(example.thinking?'<p>'+ctx.solutionView.text(example.thinking)+'</p>':'');
            return '<section class="lesson-sample-question" aria-labelledby="lesson-sample-title-'+index+'"><h3 id="lesson-sample-title-'+index+'">Câu '+(index+1)+'</h3><p class="lesson-sample-prompt">'+ctx.escape(example.text)+'</p><label class="field"><span>Cách làm của em · Câu '+(index+1)+'</span><textarea rows="5" maxlength="20000" placeholder="Em thử viết cách giải trước khi xem bài giải mẫu."></textarea></label>'+(solution?'<details class="lesson-sample-solution"><summary>Xem lời giải mẫu · Câu '+(index+1)+'</summary>'+solution+'</details>':'<p>Em đọc lại nội dung bài học và thử trình bày cách làm của mình.</p>')+'</section>';
        }).join('')+'</section>';
    }
const views = {
dashboard() {
            const lesson = ctx.lessonList().find(item => item.id === ctx.state.lastLesson) || ctx.lessonList()[0];
            const learned = Object.values(ctx.state.completed).filter(item => item.grade === ctx.grade()).length;
            if (!lesson) return `${ctx.intro('Góc Học Tập','Chào '+ctx.name()+'! · Khối '+ctx.grade())}<section class="card card-pad"><h2>Học liệu đang được cập nhật</h2><p>Em có thể xem lịch sử luyện tập, tài khoản và lớp học trong menu.</p>${ctx.link('Xem luyện tập','exams','dark')}${ctx.link('Tài khoản','profile','outline')}</section>`;
            return `<div class="garden-dashboard"><section class="hero-app garden-welcome"><div class="hero-copy"><div class="garden-welcome-kicker">${ctx.badge('GÓC HỌC TẬP','light')}<span>Chào ${ctx.escape(ctx.name())}! · Khối ${ctx.grade()} · Tuần ${ctx.week()}</span></div><h1 class="garden-welcome-heading">Mỗi ngày một<br><span class="garden-heading-emphasis">mầm tri thức</span></h1><p class="garden-welcome-description">Cùng khám phá <strong>${ctx.escape(lesson.title)}</strong>.</p><div class="garden-welcome-actions">${ctx.link('Học tiếp','lesson','orange','arrow',{id:lesson.id})}${ctx.link('Xem bài học','weekly','outline','')}</div></div><div class="hero-art">${ctx.art('sprout','Mầm Sách đang đọc sách')}<span class="orbit" aria-hidden="true">✦</span></div></section>
            <div class="grid3 stats garden-stats">${ctx.stat('book',learned + ' bài','Đã học')}${ctx.stat('file',ctx.submittedExams().length + ' đề','Đã hoàn thành','peach')}${ctx.stat('zap',ctx.content.format(ctx.state.points) + ' điểm','Kinh nghiệm linh vật','sand')}</div>
            <div class="section-head garden-activities-heading"><h2>Hôm nay em muốn làm gì?</h2></div><div class="grid3 garden-shortcuts">${[['book','Bài giảng','Bài giảng theo tuần và chuyên đề.','weekly','sage'],['file','Luyện tập','Làm đề ngẫu nhiên và xem lời giải.','exams','peach'],['zap','Đấu trí','Luyện phản xạ toán học cùng linh vật.','arena','sand']].map(([symbol,title,copy,route,color]) => `<a class="card card-pad shortcut garden-shortcut" href="${ctx.href(route)}">${ctx.gardenActivityArt(symbol)}<span class="garden-classic-icon">${ctx.tile(symbol,color)}</span><h3>${title}</h3><p>${copy}</p><span class="inline-arrow">${ctx.icon('arrow')}</span></a>`).join('')}</div>
            <aside class="garden-tip"><strong class="garden-tip-label">${ctx.icon('leaf',23)}Mẹo học tốt</strong><p class="garden-tip-copy">Đọc kỹ đề, làm <mark>từng bước.</mark></p></aside></div>`;
        },
weekly() {
            const lessons=ctx.lessonList();
            if (!lessons.length) return `${ctx.intro('Bài giảng','Bài giảng khối '+ctx.grade())}<div class="toolbar">${ctx.tabs('weekly')}</div>${ctx.notice('Học liệu đang được cập nhật.')}`;
            const filtered=lessons.filter(l=>l.week<=ctx.week() && (ctx.lessonRange==='all'||(ctx.lessonRange==='current'?l.week<=ctx.week():!ctx.state.completed[l.id]))).sort((a,b)=>b.week-a.week);
            const upcoming=lessons.filter(l=>l.week===ctx.week()+1).slice(0,3);
            return `${ctx.intro('Bài giảng',ctx.live?'Học liệu tự biên soạn, sắp xếp từ tuần gần nhất.':'Demo ngoại tuyến · Học liệu mẫu tự biên soạn, chỉ lưu trên trình duyệt này.',ctx.badge('Khối '+ctx.grade(),'sage'))}<div class="toolbar">${ctx.tabs('weekly')}${ctx.field('Hiển thị','learning-range',[['all','Tất cả bài mẫu'],['current','Đến tuần hiện tại'],['unfinished','Bài chưa học']],ctx.lessonRange)}</div>
            ${ctx.heading('Bài giảng theo tuần')}<div class="card list">${filtered.map(lesson=>ctx.lessonRow(lesson)).join('')||'<p class="card-pad">Chưa có bài trong bộ lọc này.</p>'}</div>
            ${ctx.heading('Khám phá tuần sau')}<div class="grid3">${upcoming.map(l=>`<a class="card card-pad" href="${ctx.href('lesson',{id:l.id})}">${ctx.badge('HỌC TRƯỚC','peach')}<h3>Tuần ${l.week}: ${ctx.escape(l.title)}</h3><p>${ctx.escape(l.description)}</p></a>`).join('')||'<p>Ba bài học tuần sau đang được biên soạn.</p>'}</div>`;
        },
topics() {
            const lessons=[...new Map(ctx.lessonList().map(l=>[l.topic,l])).values()];
            if (!lessons.length) return `${ctx.intro('Bài giảng','Chuyên đề khối '+ctx.grade())}<div class="toolbar">${ctx.tabs('topics')}</div>${ctx.notice('Học liệu đang được cập nhật.')}`;
            return `${ctx.intro('Bài giảng','Chọn một chuyên đề để đọc lý thuyết và tự luyện.',ctx.badge('Khối '+ctx.grade(),'sage'))}<div class="toolbar">${ctx.tabs('topics')}<label class="search">${ctx.icon('search',17)}<input id="topic-search" type="search" value="${ctx.escape(ctx.topicSearch)}" placeholder="Tìm chuyên đề" aria-label="Tìm chuyên đề"></label></div><p id="topic-count" role="status"></p>
            <div class="grid3 topic-results">${lessons.map((lesson,index)=>`<a data-topic-title="${ctx.escape(lesson.title.toLocaleLowerCase('vi'))}" class="card topic" href="${ctx.href('advanced',{id:lesson.id})}"><div class="topic-art ${index%2?'sage':'peach'}" aria-hidden="true">${ctx.escape(lesson.symbol)}</div><div class="card-pad"><h3>${ctx.escape(lesson.title)}</h3><p>${ctx.escape(lesson.description)}</p><small>Lý thuyết · Ví dụ · Luyện tập</small></div></a>`).join('')}</div><p id="topic-empty" hidden>Chưa tìm thấy chuyên đề phù hợp.</p>`;
        },
lesson(advanced = false) {
            const lesson=ctx.selectedLesson();if(!lesson)return ctx.back('Bài giảng','weekly')+ctx.intro('Bài giảng','Bài học này chưa có trong danh mục của em.');
            const examples=lessonExamples(lesson),isDone=Boolean(ctx.state.completed[lesson.id]);
            const controls=ctx.lessonStudy.render({completed:isDone,videoRef:lesson.videoRef||lesson.video_ref||'',videoTitle:lesson.title,bunnyVideo:lesson.video?.provider==='bunny',exerciseAvailable:examples.length>0,exerciseTarget:'lesson-exercises',materials:lesson.materials});
            const sample=lessonSamples(examples);
            return ctx.back(advanced?'Chuyên đề':'Bài giảng',advanced?'topics':'weekly')+ctx.intro(lesson.title,'Khối '+ctx.grade()+' · '+(advanced?'Chuyên đề':'Tuần '+lesson.week),ctx.badge('Học liệu tự biên soạn','peach'))+controls+'<article class="card card-pad lesson-reading"><h2>Nội dung bài học</h2>'+(ctx.live&&lesson.body?ctx.rich(lesson.body,lesson.assets||[]):'<p>'+ctx.escape(lesson.theory)+'</p>')+'</article>'+sample;
        }
};
const actions = {
async complete() {
            const lesson = ctx.selectedLesson();
            if(ctx.live){await ctx.mutate('lessons/'+lesson.id+'/complete');ctx.refresh();return;}
            if (!ctx.state.completed[lesson.id]) {
                ctx.state.completed[lesson.id] = {date:new Date().toISOString(),grade:ctx.grade()};
                if (ctx.grade() === 5 && ['decimal','percent'].includes(lesson.topic) && !ctx.host.progress.completed.includes(lesson.topic)) {
                    ctx.host.progress.completed.push(lesson.topic);
                    ctx.host.saveProgress();
                }
                ctx.save();
            }
            ctx.refresh();
        },
practice:() => ctx.createExam({topic:ctx.selectedLesson().topic,count:3}),
video:() => ctx.host.showModal('<h2 class="modal-title">Video bài giảng</h2>'+lessonVideo(ctx.selectedLesson())),
'download-material':async()=>{if(!ctx.live){ctx.host.toast('Tài liệu cần tài khoản VIP trên máy chủ.');return;}const r=await PlatformAPI.request('materials');const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([r.text],{type:'text/plain;charset=utf-8'}));a.download='5bmath-phieu-luyen-tap.txt';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),5000);}
};
return {views,actions,homeworkPanel,lessonVideo,lessonExamples,lessonSamples};
}
const api={create};(global.LearningFeatures??={})['study']=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
