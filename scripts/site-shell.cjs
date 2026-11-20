'use strict';
const fs=require('node:fs'),path=require('node:path');
const routes=Object.fromEntries(['phap-ly','lien-he','dieu-khoan','bao-ve-du-lieu','thanh-toan-va-cung-cap','huy-va-hoan-tien','khieu-nai'].map(slug=>['/'+slug+'/','legal/'+slug+'/index.html']));
Object.assign(routes,{'/ho-tro/':'support-center/index.html','/quan-tri/website/':'support-center/index.html','/gia-dinh/':'family/index.html','/trai-nghiem/':'trial-experience/index.html','/quan-tri/phan-loai-cau/':'question-access-admin/index.html'});
const assets=['legal.css','legal.js','website-shell.css','support-center.js','support-center.css','checkout-readiness.css','family-app.js','family-app.css','trial-experience.js','trial-experience.css','question-access-admin.js','question-access-admin.css','question-access-page.js','family-profiles.js','family-profiles.css','family-parent.svg','app-shell.js','app-shell.css'];
function shell(html){
 if(!html.includes('family-profiles.js'))html=html.replace('<head>','<head><link rel="stylesheet" href="/family-profiles.css"><script src="/family-profiles.js" defer></script>');
 if(!html.includes('website-shell.css'))html=html.replace('</head>','<link rel="stylesheet" href="/website-shell.css"></head>');
 if(!html.includes('app-shell.js'))html=html.replace('</head>','<link rel="stylesheet" href="/app-shell.css"><script src="/app-shell.js" defer></script></head>');
 if(!html.includes('legal-footer')&&!html.includes('data-website-footer')){
  const links=Object.keys(routes).slice(0,7).map(route=>`<a href="${route}">${({'/phap-ly/':'Thông tin pháp lý','/lien-he/':'Liên hệ','/dieu-khoan/':'Điều khoản','/bao-ve-du-lieu/':'Bảo vệ dữ liệu','/thanh-toan-va-cung-cap/':'Thanh toán và cung cấp','/huy-va-hoan-tien/':'Hủy và hoàn tiền','/khieu-nai/':'Khiếu nại'})[route]}</a>`).join('');
  html=html.replace('</body>','<div class="website-footer" data-website-footer><nav aria-label="Thông tin dịch vụ">'+links+'<a href="/ho-tro/">Hỗ trợ và đơn hàng</a></nav><p>Chính sách đang chờ chủ quản duyệt. Thông tin chủ quản xem tại trang Liên hệ.</p></div></body>');
 }
 return html;
}
function rebase(html,target){return target==='github'?html.replace(/(\b(?:src|href|action)\s*=\s*["'])\/(?!\/)/g,'$1/5b/'):html;}
function copyExtra(frontend,output,target){
 for(const asset of assets){const dest=path.join(output,asset);fs.mkdirSync(path.dirname(dest),{recursive:true});fs.copyFileSync(path.join(frontend,asset),dest);}
 for(const[route,file]of Object.entries(routes)){const dest=path.join(output,route,'index.html');fs.mkdirSync(path.dirname(dest),{recursive:true});let html=shell(fs.readFileSync(path.join(frontend,file),'utf8'));if(target==='github')html=html.replace(/<base href="\/">/,'<base href="/5b/">');fs.writeFileSync(dest,rebase(html,target));}
}
module.exports={routes,assets,shell,rebase,copyExtra};
