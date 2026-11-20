/* Shared lobby presentation. Quotas and admission remain owned by the server. */
(function(global){'use strict';
const e=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const names={duel:'Đấu trí',capture_flag:'Cướp Cờ',animal_race:'Đua Thú'};
function playerCard({game,mascot='sprout',xp=0,pets=global.BadgeMascots}={}){
 const points=Math.max(0,Number(xp)||0),percent=points>=280?100:points%20*5;
 const rank=pets?.rankFor?.(points)||'Linh vật của em',next=pets?.rankFor?.(points+20-points%20)||'bậc tiếp theo';
 const portrait=pets?.portrait?.(mascot,points,'','mascot-art')||'';
 const allowance=game?global.GameAllowance?.summary?.(game)||'':'';
 const activeRoom=game?global.GameSession?.inlineMarkup?.()||'':'';
 return `<section class="card card-pad arena-player arena-shared-player" aria-label="Thông tin linh vật">
  <div class="arena-player-overview"><div class="arena-player-pet">${portrait}<div><strong>${e(rank)}</strong><small>${points.toLocaleString('vi-VN')} kinh nghiệm</small></div></div>${allowance}</div>
  <div class="meter" role="progressbar" aria-label="Tiến độ linh vật" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}"><span style="--value:${percent}%"></span></div>
  <small>${points>=280?'Đã đạt Vàng V · Tiếp tục tích lũy kinh nghiệm.':`Còn ${20-points%20} kinh nghiệm đến ${e(next)}`}</small>
  ${activeRoom}
 </section>`;
}
function groupUsage(catalogue,selected='quick'){
 const label=selected==='bot'?'Luyện với BOT':'Đấu với người';
 if(catalogue?.unlimitedGames===true||(typeof PlatformAPI!=='undefined'&&PlatformAPI.snapshot.gameLimitsUnlimited===true))return '';
 const usage=catalogue?.usage?.[selected==='bot'?'bot':'human'];
 if(usage?.limit===null)return '';
 if(usage&&Number.isFinite(usage.used)&&usage.used>=0&&Number.isFinite(usage.limit)&&usage.limit>=0){
  const exhausted=usage.used>=usage.limit;
  return `<p class="usage-note">Hạn mức gói · ${usage.used} / ${usage.limit} lượt hôm nay${exhausted?' · Đã đạt giới hạn':''}</p>${exhausted?'<a class="btn outline" href="/nang-cap/">Nâng cấp gói</a>':''}`;
 }
 const notice=catalogue?.limitsNotice||'Chính sách lượt chơi đang chờ được duyệt.';
 return `<p class="usage-note"><strong>${label}</strong></p><small class="arena-usage-policy">${e(notice)}</small>`;
}
function illustration(game){
 if(game==='capture_flag')return `<svg class="group-lobby-illustration" viewBox="0 0 260 160" role="img" aria-label="Lá cờ Việt Nam ở giữa vòng tròn năm bước"><ellipse cx="130" cy="126" rx="109" ry="21" fill="#a2ca82"/><ellipse cx="130" cy="114" rx="103" ry="32" fill="#eaf3cd" stroke="#a2c27c" stroke-width="3"/><path d="M52 114h156M130 90v48" stroke="#fff9ed" stroke-width="3" stroke-dasharray="6 7"/><path d="M123 115V25" stroke="#866748" stroke-width="5" stroke-linecap="round"/><path d="M126 27q30-12 62 0v45q-32-12-62 0z" fill="#dc2929"/><path d="m156 35 4 11 12 1-10 7 3 12-9-7-10 7 4-12-10-7 12-1z" fill="#ffdf58"/><g fill="#ffbe73" stroke="#fff9ed" stroke-width="3"><circle cx="35" cy="109" r="12"/><circle cx="78" cy="140" r="12"/><circle cx="184" cy="140" r="12"/><circle cx="227" cy="109" r="12"/><circle cx="195" cy="84" r="12"/></g><path d="m26 42 7 5m12-22 4 10m159-15-3 10m20 15-9 5" stroke="#f1b560" stroke-width="4" stroke-linecap="round"/></svg>`;
 if(game==='animal_race')return `<svg class="group-lobby-illustration" viewBox="0 0 260 160" role="img" aria-label="Đường đua có làn bay, đi bộ và làn nước, đích căng băng rôn"><rect x="21" y="43" width="218" height="94" rx="24" fill="#dcebd1"/><path d="M35 65h188M35 93h188M35 122h188" stroke="#fff9ed" stroke-width="4" stroke-dasharray="10 9"/><path d="M34 120q10-10 20 0t20 0t20 0t20 0t20 0t20 0t20 0t20 0t20 0" stroke="#75bdc9" fill="none" stroke-width="4"/><path d="M211 24v116M173 24v116" stroke="#67876c" stroke-width="5"/><path d="M173 27h38v20h-38z" fill="#fff9ed"/><path d="M173 27h9v10h-9zm18 0h10v10h-10zm-9 10h9v10h-9zm19 0h10v10h-10z" fill="#1f6248"/><path d="m45 33 12-12 7 12m15-6 7-7 6 7" fill="none" stroke="#e5a459" stroke-width="4" stroke-linecap="round"/><g fill="#ffbe73"><circle cx="58" cy="66" r="9"/><circle cx="89" cy="92" r="9"/><circle cx="47" cy="119" r="9"/></g></svg>`;
 return `<svg class="group-lobby-illustration" viewBox="0 0 260 160" role="img" aria-label="Hai linh vật cùng giải Toán trong đấu trường, có khiên phòng thủ"><ellipse cx="130" cy="133" rx="110" ry="19" fill="#b4d49e"/><path d="M34 125q22-25 43 0m106 0q22-25 43 0" fill="none" stroke="#e9f3d7" stroke-width="6"/><rect x="95" y="22" width="70" height="45" rx="13" fill="#fff9ed" stroke="#82aa75" stroke-width="3"/><path d="M108 44h15m-7-7v14m21-12h15m-15 9h15" stroke="#1f6248" stroke-width="4" stroke-linecap="round"/><g stroke="#508054" stroke-width="3"><path d="M60 70q-20-26-35-10 0 22 35 20m0-10q8-31 29-21 4 22-29 31" fill="#83b76f"/><rect x="32" y="77" width="58" height="49" rx="23" fill="#b8d68c"/><path d="M201 70q20-26 35-10 0 22-35 20m0-10q-8-31-29-21-4 22 29 31" fill="#83b76f"/><rect x="172" y="77" width="58" height="49" rx="23" fill="#b8d68c"/></g><g fill="#203a32"><circle cx="52" cy="96" r="3"/><circle cx="72" cy="96" r="3"/><circle cx="190" cy="96" r="3"/><circle cx="210" cy="96" r="3"/></g><g fill="#ffbe73"><ellipse cx="42" cy="103" rx="6" ry="4"/><ellipse cx="81" cy="103" rx="6" ry="4"/><ellipse cx="180" cy="103" rx="6" ry="4"/><ellipse cx="219" cy="103" rx="6" ry="4"/></g><path d="M55 107q7 7 14 0m124 0q7 7 14 0" fill="none" stroke="#508054" stroke-width="2.5" stroke-linecap="round"/><path d="m130 77-17 22h15l-4 23 23-29h-16l5-16z" fill="#ffbe73" stroke="#dc9e53" stroke-width="2"/><path d="m98 99 12 6v15q-6 10-12 14-6-4-12-14v-15zm65 0 12 6v15q-6 10-12 14-6-4-12-14v-15z" fill="#c7e5dc" stroke="#508d80" stroke-width="2"/></svg>`;
}
function showcase(game){
 if(!Object.hasOwn(names,game))return '';
 const detail={duel:['Thử tài kiến thức','Hai linh vật, một cuộc đấu trí','Giải đúng, ra đòn và phòng thủ để cùng linh vật tranh tài.'],capture_flag:['Vòng tròn tranh tài','Một lá cờ, năm linh vật','Trả lời đúng để tiến từng bước và giành lá cờ Việt Nam.'],animal_race:['Đường đua linh vật','Cùng nhau chạm vạch đích','Cùng linh vật chạy, bay, bơi; giải đúng để tiến về đích.']}[game];
 return `<section class="group-lobby-showcase group-lobby-showcase-${game} arena-shared-showcase" aria-label="Hình minh họa ${e(names[game])}"><div><span class="group-showcase-label">${e(detail[0])}</span><h2>${e(detail[1])}</h2><p>${e(detail[2])}</p></div>${illustration(game)}</section>`;
}
const api={playerCard,groupUsage,showcase};global.ArenaLobby=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof window!=='undefined'?window:globalThis);
