'use strict';
document.addEventListener('DOMContentLoaded',async()=>{
 const status=document.getElementById('question-access-status'),container=document.getElementById('question-access-app');
 try{
  const response=await fetch('/api/staff/session',{credentials:'same-origin',cache:'no-store'});
  const state=await response.json();
  if(!response.ok||!state.authenticated||state.user?.role!=='admin'){status.textContent='Đăng nhập quản trị để xem và phân loại kho câu.';const link=document.createElement('a');link.href='/quan-tri/';link.textContent='Mở trang quản trị';container.append(link);return;}
  if(!window.QuestionAccessAdmin)throw new Error('Chưa tải được công cụ phân loại. Vui lòng tải lại.');
  await window.QuestionAccessAdmin.mount(container,{csrf:state.csrf});
  status.textContent='Chỉ tài khoản quản trị được thay đổi phân loại.';
 }catch(error){status.textContent=error.message||'Chưa thể tải phân loại.';}
});
