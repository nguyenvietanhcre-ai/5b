(function(global){'use strict';
const escape=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const book='<svg viewBox="0 0 24 24" width="23" height="23" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 6C9 3 5 3 3 4v15c3-1 6-1 9 1 3-2 6-2 9-1V4c-2-1-6-1-9 2zm0 0v14"/></svg>';
const chevron='<svg class="game-rules-chevron" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>';
function markup(mode='duel'){
 const duel=mode==='duel',title=duel?'Luật đấu trí':mode==='capture_flag'?'Luật Cướp Cờ':'Luật Đua Thú';
 const cards=duel?[
  ['💗','100 máu · 60 giây','Mỗi linh vật bắt đầu với <strong>100 máu</strong>. Mỗi câu có <strong>60 giây</strong>, gửi đáp án một lần.'],
  ['⚡','Đúng trước & phòng thủ','Đáp án đúng đầu tiên mở <strong>3 giây phòng thủ</strong>. Đối thủ đúng trong hạn mất <strong>10 máu</strong>; sai hoặc quá hạn mất <strong>20 máu</strong>.'],
  ['⚑','Khi nào thua?','Linh vật hết máu là thua. <strong>Rời trận giữa chừng tính là thua.</strong>'],
  ['🤝','Khi nào hòa?','Hết <strong>20 câu hỏi</strong> mà hai linh vật vẫn còn máu là hòa. Nghỉ <strong>3 giây</strong> giữa các câu.']
 ]:[
  ['👋','5 người cùng khối','Chơi với bạn: đủ <strong>5 người</strong> thì bắt đầu. '+(mode==='capture_flag'?'Cùng linh vật tiến về lá cờ.':'Cùng linh vật chạy, bay, bơi về đích.')],
  ['⚡','Đúng một câu, tiến một bước','Người đạt <strong>5 câu đúng</strong> trước thắng. Mỗi câu chỉ gửi đáp án <strong>một lần</strong>.'],
  ['⏱️','60 giây mỗi câu','Hết giờ hoặc tất cả đã trả lời thì chốt câu. Nghỉ <strong>3 giây</strong> rồi sang câu tiếp.'],
  ['🏁','Xếp hạng theo kết quả','Các hạng còn lại theo <strong>số câu đúng</strong>, tổng thời gian, rồi thứ tự đạt bước. Bỏ trận hoặc trận bị hủy không nhận thưởng.']
 ];
 const rewards=duel?[['🏆','Thắng','+2'],['🌱','Thua','−1'],['🤝','Hòa','0']]:[['🥇','Hạng 1','+5'],['🥈','Hạng 2','+4'],['🥉','Hạng 3','+3'],['🌟','Hạng 4','+2'],['🌱','Hạng 5','+1']];
 const bot='Luyện với Bot: <strong>0 kinh nghiệm</strong>, không tính bảng xếp hạng.';
 return `<details class="card game-rules garden-game-rules" open><summary>${book}<span class="game-rules-heading"><strong>${escape(title)}</strong><small>Nắm luật thật nhanh, sẵn sàng tranh tài!</small></span>${chevron}</summary><div class="game-rules-body"><ul class="game-rule-grid">${cards.map(([icon,heading,body])=>`<li><span class="game-rule-icon" aria-hidden="true">${icon}</span><div><h3>${escape(heading)}</h3><p>${body}</p></div></li>`).join('')}</ul><h3 class="game-rewards-title">${duel?'Kinh nghiệm sau trận hoàn tất':'Kinh nghiệm khi hoàn tất trận 5 bạn thật'}</h3><ul class="game-reward-grid ${duel?'':'game-reward-five'}">${rewards.map(([icon,label,xp],i)=>`<li class="${i===0?'game-reward-first':''}"><span aria-hidden="true">${icon}</span><strong>${label}</strong><b>${xp}</b><small>kinh nghiệm</small></li>`).join('')}</ul><p class="game-rules-bot-note">${bot}</p></div></details>`;
}
const api={markup};global.GameRules=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
