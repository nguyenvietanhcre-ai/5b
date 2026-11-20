/* Shared lesson controls. Resource metadata comes from the published lesson revision. */
'use strict';
(function(root,factory){const helper=factory();if(typeof module==='object'&&module.exports)module.exports=helper;root.LessonStudy=helper;})(typeof globalThis!=='undefined'?globalThis:this,()=>{
 const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const origin=()=>typeof location!=='undefined'?location.origin:'https://5bmath.vn';
 function resourceHref(value){
  if(typeof value!=='string'||!value||value!==value.trim()||/[\u0000-\u001f\u007f\\]/.test(value)||value.startsWith('//')||(!value.startsWith('/')&&!/^https:\/\//i.test(value)))return '';
  try{const url=new URL(value,origin());return ((url.origin===origin()&&['http:','https:'].includes(url.protocol))||url.protocol==='https:')&&!url.username&&!url.password?url.href:'';}catch{return '';}
 }
 function video(value,title=''){
  const href=resourceHref(value);if(!href)return '';
  const url=new URL(href),direct=/\.(mp4|webm|ogv|ogg)$/i.test(url.pathname),youtube=/(^|\.)youtube\.com$/.test(url.hostname)||url.hostname==='youtu.be';
  return `<div class="lesson-study-video-preview">${direct?`<video controls preload="none" playsinline src="${escape(href)}" aria-label="${escape('Video bài giảng'+(title?' '+title:''))}"></video>`:`<p class="lesson-study-video-link-note">${youtube?'Video bài giảng trên YouTube.':'Video bài giảng được mở tại trang cung cấp.'}</p>`}<a class="btn outline" href="${escape(href)}" target="_blank" rel="noopener noreferrer">Mở video bài giảng ↗</a></div>`;
 }
 function render({completed=false,videoRef='',videoTitle='',videoHTML='',bunnyVideo=false,exerciseAvailable=false,exerciseTarget='lesson-exercises',materials=[]}={}){
  const files=Array.isArray(materials)?materials.filter(file=>file&&resourceHref(file.href)):[];
  const articleVideo=bunnyVideo
   ?'<div class="lesson-video-gate" data-bunny-video><button type="button" class="btn dark" data-bunny-toggle aria-controls="lesson-video-frame" aria-expanded="false" disabled>Mở video</button><div data-bunny-frame id="lesson-video-frame"></div><p data-bunny-status role="status"></p></div>'
   :video(videoRef,videoTitle)||videoHTML||'<p class="lesson-study-video-empty">Bài học này chưa có video. Em đọc nội dung bài học bên dưới để tìm hiểu cách giải nhé.</p>';
  return `<section class="lesson-study card card-pad" data-lesson-study aria-label="Học bài"><section class="lesson-study-video" aria-labelledby="lesson-study-video-title"><div class="lesson-study-video-heading"><span aria-hidden="true">▶</span><h2 id="lesson-study-video-title">Video bài giảng</h2></div>${articleVideo}</section><div class="lesson-study-actions"><button type="button" class="btn ${completed?'outline':'dark'}" data-lesson-study-action="complete" ${completed?'disabled':''}>${completed?'✓ Đã học':'Đánh dấu đã học'}</button><button type="button" class="btn outline" data-lesson-study-action="exercise" aria-controls="${escape(exerciseTarget)}" aria-expanded="false" ${exerciseAvailable?'':'disabled'}>Làm bài tập</button>${files.map(file=>`<a class="btn outline lesson-study-material" href="${escape(resourceHref(file.href))}" ${file.download?'download="'+escape(typeof file.download==='string'?file.download:'')+'"':''} ${new URL(resourceHref(file.href)).origin!==origin()?'target="_blank" rel="noopener noreferrer"':''}>Tải tài liệu${files.length>1?' · '+escape(file.title||'Tài liệu'):''}</a>`).join('')}</div>${exerciseAvailable?'':'<p class="lesson-study-exercise-empty">Bài học này chưa có bài tập mẫu đính kèm.</p>'}<p class="lesson-study-status" data-lesson-study-status role="status">${completed?'Đã lưu trạng thái đã học.':''}</p></section>`;
 }
 function section(root){return root?.matches?.('[data-lesson-study]')?root:root?.querySelector?.('[data-lesson-study]');}
 function setCompleted(root,completed=true){
  const host=section(root),button=host?.querySelector('[data-lesson-study-action="complete"]');if(!button)return;
  button.disabled=Boolean(completed);button.textContent=completed?'✓ Đã học':'Đánh dấu đã học';button.classList.toggle('dark',!completed);button.classList.toggle('outline',Boolean(completed));
  host.querySelector('[data-lesson-study-status]').textContent=completed?'Đã lưu trạng thái đã học.':'';
 }
 function mount(root,{onComplete,onExercise,videoLesson}={}){
  const host=section(root);if(!host)return ()=>{};let active=true,pending=false;
  const videoHost=host.querySelector('[data-bunny-video]');
  let stopVideo;
  if(videoHost){
   if(videoLesson&&globalThis.BunnyLessonPlayer&&typeof PlatformAPI!=='undefined')stopVideo=BunnyLessonPlayer.mount(videoHost,videoLesson,PlatformAPI);
   else videoHost.querySelector('[data-bunny-status]').textContent='Trình phát video chưa sẵn sàng. Em có thể đọc nội dung bài học.';
  }
  const click=async event=>{
   const button=event.target.closest?.('[data-lesson-study-action]');if(!button||!host.contains(button)||button.disabled)return;
   const action=button.dataset.lessonStudyAction,status=host.querySelector('[data-lesson-study-status]');
   if(action==='exercise'){
    const target=document.getElementById(button.getAttribute('aria-controls'));
    if(target){target.hidden=false;if(target.tagName==='DETAILS')target.open=true;button.setAttribute('aria-expanded','true');}
    try{await onExercise?.();if(!active)return;const focusTarget=target?.querySelector('h2,h3,legend,input,button')||target;if(focusTarget){if(!focusTarget.hasAttribute('tabindex')&&!focusTarget.matches('input,button'))focusTarget.setAttribute('tabindex','-1');focusTarget.focus({preventScroll:true});target.scrollIntoView({block:'start',behavior:'auto'});}}catch(error){if(active&&error.name!=='AbortError')status.textContent=error.message;}
    return;
   }
   if(action!=='complete'||pending||typeof onComplete!=='function')return;
   pending=true;button.disabled=true;status.textContent='Đang lưu trạng thái đã học…';
   try{const result=await onComplete();if(active)setCompleted(host,result?.completed!==false);}catch(error){if(active){button.disabled=false;if(error.name!=='AbortError')status.textContent='Chưa lưu được trạng thái. '+error.message;}}finally{pending=false;}
  };
  host.addEventListener('click',click);return ()=>{active=false;stopVideo?.();host.removeEventListener('click',click);};
 }
 return {render,mount,setCompleted,resourceHref,video};
});
