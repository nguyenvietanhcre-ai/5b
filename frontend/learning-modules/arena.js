/* arena: extracted behavior; state and cross-feature services supplied explicitly. */
(function(global){'use strict';
function create(ctx){
function liveRank() {
        return `${ctx.intro('Bảng xếp hạng','Cùng học, cùng tiến bộ trên 5BMath.')}<div class="toolbar rank-tools"><div class="tabs">${[['battle','Linh vật'],['activity','Chăm chỉ']].map(([type,title])=>`<button type="button" data-rank="${type}" class="${ctx.rankType===type?'selected':''}" aria-pressed="${ctx.rankType===type}">${title}</button>`).join('')}</div><div class="actions">${ctx.field('Phạm vi','rank-scope',[['all','Tất cả'],['grade','Lớp '+ctx.grade()],...(ctx.isInternal()?[['class','Lớp Zoom']]:[])],ctx.rankScope)}${ctx.field('Thời gian','rank-period',[['all','Tất cả'],['day','Hôm nay'],['week','Tuần này'],['month','Tháng này']],ctx.rankPeriod)}</div></div><div class="card leaderboard" id="live-rank" role="status">Đang tải bảng xếp hạng…</div>`;
    }

async function loadRank() {
        const container=document.querySelector('#live-rank');if(!container)return;
        try{
            const result=ctx.live?await PlatformAPI.request('leaderboard?'+new URLSearchParams({kind:ctx.rankType,period:ctx.rankPeriod,scope:ctx.rankScope})):{rows:[]};
            if(!container.isConnected)return;
            container.innerHTML=result.rows.length?`<table><thead><tr><th>Hạng</th>${ctx.rankType==='battle'?'<th>Linh vật</th>':''}<th>Học sinh</th><th>Lớp</th><th>${ctx.rankType==='activity'?'Giờ học':'Kinh nghiệm'}</th></tr></thead><tbody>${result.rows.map(row=>`<tr class="${row.mine?'mine':''}"><td>${ctx.medal(row.rank)}</td>${ctx.rankType==='battle'?'<td>'+ctx.art(row.mascot,'',false,row.xp??0)+'</td>':''}<td><strong>${ctx.escape(ctx.displayName(row.name))}</strong> ${ctx.rankType==='battle'?'<small>'+ctx.escape(ctx.petRank(row.level))+'</small>':''}</td><td>${ctx.escape(row.class)}</td><td><strong>${ctx.escape(row.value)}</strong>${ctx.rankType==='battle'?'<small>'+row.wins+' thắng / '+row.losses+' thua</small>':''}</td></tr>`).join('')}</tbody></table>`:'<p class="card-pad">Chưa có dữ liệu trong phạm vi này.</p>';
        }catch(error){container.textContent=error.message;}
    }

function openArenaPreflight(kind,settings={},trigger=document.activeElement) {
        const human=true;
        if(kind!=='create')throw new Error('Chỉ phòng mời bạn cần bước xác nhận này.');
        if(human)ctx.requireHumanPlay();
        if(!ctx.canUse(human?'human':'bot'))throw new Error('Em đã hết lượt hôm nay. Hãy vào Nâng cấp gói.');
        if(ctx.live&&ctx.duelAllowance?.errorMessage())throw new Error(ctx.duelAllowance.errorMessage());
        if(ctx.arenaPreflight)return;
        const dialog=document.querySelector('#modal'),scroll={x:scrollX,y:scrollY},oldLabel=dialog.getAttribute('aria-labelledby'),oldDescription=dialog.getAttribute('aria-describedby');
        const context={dialog,trigger,kind,busy:false};
        const label='tạo phòng';
        const cleanup=(restoreFocus=true)=>{
            if(ctx.arenaPreflight!==context)return;
            ctx.arenaPreflight=null;dialog.classList.remove('arena-preflight-modal');document.body.classList.remove('arena-preflight-open');
            dialog.removeEventListener('close',onClose);dialog.removeEventListener('cancel',onCancel);dialog.removeEventListener('keydown',trap);dialog.removeEventListener('click',blockBackdrop,true);
            for(const [attribute,value]of [['aria-labelledby',oldLabel],['aria-describedby',oldDescription]]){if(value===null)dialog.removeAttribute(attribute);else dialog.setAttribute(attribute,value);}
            document.querySelector('#close-modal').disabled=false;
            if(restoreFocus&&trigger?.isConnected){trigger.focus({preventScroll:true});window.scrollTo({left:scroll.x,top:scroll.y,behavior:'instant'});}
        };
        const close=(restoreFocus=true)=>{if(dialog.open)dialog.close();cleanup(restoreFocus);};
        const onClose=()=>cleanup();
        const onCancel=event=>{if(context.busy)event.preventDefault();};
        const blockBackdrop=event=>{if(context.busy&&event.target===dialog){event.preventDefault();event.stopImmediatePropagation();}};
        const trap=event=>{
            if(event.key!=='Tab')return;
            const controls=[...dialog.querySelectorAll('button:not(:disabled),input:not(:disabled),a[href]')].filter(node=>node.getClientRects().length),index=controls.indexOf(document.activeElement);
            if(event.shiftKey&&index<=0){event.preventDefault();controls.at(-1)?.focus();}
            else if(!event.shiftKey&&index===controls.length-1){event.preventDefault();controls[0]?.focus();}
        };
        context.close=close;ctx.arenaPreflight=context;
        dialog.classList.add('arena-preflight-modal');document.body.classList.add('arena-preflight-open');
        ctx.host.showModal(`<section id="arena-preflight"><div class="arena-preflight-handle" aria-hidden="true"></div><p class="arena-preflight-kicker">Trước khi ${label}</p><div class="arena-preflight-icon">${ctx.icon('grid',28)}</div><h2 class="modal-title" id="arena-preflight-title">Sẵn sàng đấu trí?</h2><p id="arena-preflight-copy">Câu hỏi cho trận đấu do hệ thống chuẩn bị. Em chỉ cần sẵn sàng và chọn cách chơi.</p>${kind==='create'?'<fieldset class="arena-preflight-visibility"><legend>Ai có thể vào phòng?</legend><label><input type="radio" name="arena-visibility" value="private" checked><span>Bạn bè có mã</span></label><label><input type="radio" name="arena-visibility" value="public"><span>Tất cả</span></label></fieldset>':''}<p class="arena-preflight-context"><b>Khối ${ctx.grade()}</b> · Tối đa 20 câu<small>60 giây/câu</small></p><p class="game-allowance-dialog-message" id="arena-preflight-allowance" role="status"></p><p id="arena-preflight-error" role="alert" hidden></p><button type="button" class="btn dark" id="arena-preflight-confirm" data-game-admission ${human?'data-human-play data-human-quota="true"':''}>Xác nhận & ${label} ${ctx.icon('arrow',19)}</button><button type="button" id="arena-preflight-back">Quay lại chọn cách chơi</button></section>`);
        dialog.setAttribute('aria-labelledby','arena-preflight-title');dialog.setAttribute('aria-describedby','arena-preflight-copy');
        dialog.addEventListener('close',onClose);dialog.addEventListener('cancel',onCancel);dialog.addEventListener('keydown',trap);dialog.addEventListener('click',blockBackdrop,true);
        dialog.querySelector('#arena-preflight-back').onclick=()=>close();
        dialog.querySelector('#arena-preflight-confirm').onclick=async event=>{
            if(context.busy||event.currentTarget.disabled)return;
            const confirm=event.currentTarget,errorNode=dialog.querySelector('#arena-preflight-error');
            try{
                if(human)ctx.requireHumanPlay();
                if(!ctx.canUse(human?'human':'bot'))throw new Error('Em đã hết lượt hôm nay. Hãy vào Nâng cấp gói.');
                context.busy=true;confirm.dataset.humanPending='true';
                dialog.querySelectorAll('button,input').forEach(control=>{if(control!==confirm)control.disabled=true;});ctx.updateArenaDiscipline();errorNode.hidden=true;
                await enterRoom('create',{...roomSettings(),public:dialog.querySelector('[name="arena-visibility"]:checked').value==='public'});
                close(false);
            }catch(error){if(window.GameSession?.conflict(error)){close(false);return;}if(ctx.arenaPreflight===context){errorNode.textContent=error.message;errorNode.hidden=false;}}
            finally{context.busy=false;delete confirm.dataset.humanPending;if(ctx.arenaPreflight===context){dialog.querySelectorAll('button,input').forEach(control=>{if(control!==confirm)control.disabled=false;});ctx.updateArenaDiscipline();}}
        };
        ctx.updateArenaDiscipline();ctx.duelAllowance?.sync(dialog.querySelector('#arena-preflight'));ctx.updateDuelAllowance();dialog.querySelector(kind==='create'?'[name="arena-visibility"]':'#arena-preflight-confirm').focus();
    }

function battleTime(battle) {
        const duration=battle.defenseUntil&&!battle.resolved?3:ctx.content.battleSeconds(battle.grade,battle.questions[battle.index].difficulty);
        const now=battle.mode==='bot'?Date.now():ctx.arenaNow();
        const remaining=Math.min(duration,Math.max(0,Math.ceil(((battle.defenseUntil&&!battle.resolved?battle.defenseUntil:battle.deadline)-now)/1000)));
        return {duration,remaining,percent:remaining/duration*100};
    }

function updateBattleTimer(battle) {
        const time=battleTime(battle),label=ctx.timeText(time.remaining);
        const timer=document.querySelector('#learning-battle-timer');
        if(timer)timer.textContent=label;
        const meter=document.querySelector('#learning-battle-time-meter');
        if(meter){
            meter.setAttribute('aria-valuemax',time.duration);
            meter.setAttribute('aria-valuenow',time.remaining);
            meter.setAttribute('aria-valuetext',label+' còn lại');
            meter.firstElementChild.style.setProperty('--value',time.percent+'%');
        }
    }

function updateBattleRound(battle) {
        const panel=document.querySelector('.battle-round-status');
        const question=document.querySelector('.battle-question-content');
        if(!panel||!question)return;
        const now=battle.mode==='bot'?Date.now():ctx.arenaNow();
        const expired=now>=battle.deadline;
        // The fallback also supports bot rounds saved before roundOutcome existed.
        let outcome=battle.roundOutcome;
        if(!outcome||outcome==='waiting'){
            outcome=battle.answer!==null
                ? battle.mode==='bot'
                    ? ctx.isCorrect(battle.questions[battle.index],battle.answer)?'correct':'wrong'
                    : battle.feedback?.includes('chưa đúng')?'wrong':'correct'
                : battle.resolved&&battle.feedback?.includes('trả lời đúng')?'opponent'
                : expired?'timeout':'waiting';
        }
        const defending=Boolean(battle.defenseUntil&&!battle.resolved);
        const correctDefenseWait=defending&&outcome==='correct'&&battle.answer!==null;
        const shown=(!defending||correctDefenseWait)&&outcome!=='waiting';
        if(panel.hidden===shown)panel.hidden=!shown;
        question.classList.toggle('round-hidden',shown);
        if(question.inert!==shown)question.inert=shown;
        if(question.getAttribute('aria-hidden')!==String(shown))question.setAttribute('aria-hidden',String(shown));
        if(!shown)return;
        if(panel.dataset.outcome!==outcome)panel.dataset.outcome=outcome;
        const titles={correct:'Em trả lời đúng!',wrong:'Em trả lời sai',opponent:'Bạn trả lời nhanh hơn',timeout:'Hết giờ!'};
        const symbols={correct:'check',wrong:'flag',opponent:'zap',timeout:'clock'};
        const setText=(selector,text)=>{const node=panel.querySelector(selector);if(node.textContent!==text)node.textContent=text;};
        setText('#battle-round-title',battle.resolved&&battle.damage===10&&!battle.attacking?'Đỡ đòn thành công!':titles[outcome]);
        const symbol=panel.querySelector('.battle-round-symbol');
        if(symbol.dataset.symbol!==symbols[outcome]){symbol.innerHTML=ctx.icon(symbols[outcome],28);symbol.dataset.symbol=symbols[outcome];}
        let detail=outcome==='correct'?battle.feedback||'Em trả lời đúng.':outcome==='opponent'?'Bạn trả lời đúng trước. Em bị trừ 20 máu.':'Chưa có đáp án đúng. Hai bên giữ nguyên máu.';
        if(outcome==='wrong')detail=!battle.resolved?'Em hãy chờ bạn trả lời hoặc hết thời gian câu này.':battle.roundReason==='correct'?'Bạn trả lời đúng. Em bị trừ 20 máu.':'Câu này chưa có đáp án đúng. Hai bên giữ nguyên máu.';
        if(outcome==='timeout'&&!battle.resolved)detail='Đang nhận kết quả câu này…';
        setText('#battle-round-detail',battle.resolved&&battle.feedback?battle.feedback:detail);
        const final=battle.hp===0||battle.opponentHp===0||battle.index>=battle.questions.length-1;
        setText('#battle-round-next',correctDefenseWait?'Thời gian phòng thủ của đối thủ còn':final?'Hãy xem kết quả trận đấu':'Hãy chuẩn bị cho câu '+(battle.index+2));
        const roundUntil=correctDefenseWait?battle.defenseUntil:battle.nextAt;
        const seconds=Math.max(0,Math.ceil(((roundUntil||now)-now)/1000));
        const countdown=panel.querySelector('.battle-round-countdown'),hideCount=(!battle.resolved&&!correctDefenseWait)||seconds===0;
        if(countdown.hidden!==hideCount)countdown.hidden=hideCount;
        setText('#next-round-count',String(seconds));
        setText('#battle-round-wait',correctDefenseWait?'Đáp án đã được gửi. Đang chờ đối thủ phòng thủ.':battle.resolved?(seconds===0?'Đang chuyển…':''):expired?'Đang đồng bộ câu tiếp theo…':'Câu này còn '+ctx.timeText(((battle.defenseUntil&&!battle.resolved?battle.defenseUntil:battle.deadline)-now)/1000));
    }

function emoteSeconds(battle) {
        const now=battle.mode==='bot'?Date.now():ctx.arenaNow();
        const until=Math.max(battle.emoteAvailableAt||0,ctx.emoteLock.id===battle.id?ctx.emoteLock.until:0);
        return Math.max(0,Math.ceil((until-now)/1000));
    }

function updateEmoteControls(battle) {
        if(battle.mode==='bot'&&battle.myEmote!=null&&Date.now()>=(battle.myEmoteUntil||0)){
            battle.myEmote=null;persistBot();
        }
        if(battle.mode==='bot'){
            const bubble=document.querySelector('#my-emote'),text=ctx.emotes[battle.myEmote]?.join(' ')||'';
            if(bubble&&bubble.textContent!==text)bubble.textContent=text;
        }
        const seconds=emoteSeconds(battle),pending=ctx.emoteLock.id===battle.id&&ctx.emoteLock.pending;
        battle.emoteUsed=seconds>0;
        document.querySelectorAll('[data-emote]').forEach(control=>{const disabled=seconds>0||pending;if(control.disabled!==disabled)control.disabled=disabled;});
        const bar=document.querySelector('.emote-bar'),disabled=seconds>0||pending;
        if(bar){
            bar.classList.toggle('is-cooling',disabled);
            if(bar.getAttribute('aria-disabled')!==String(disabled))bar.setAttribute('aria-disabled',String(disabled));
        }
    }

async function sendEmote(index) {
        const battle=ctx.currentBattle;
        if(!battle||emoteSeconds(battle)>0||ctx.emoteLock.id===battle.id&&ctx.emoteLock.pending)return;
        const now=battle.mode==='bot'?Date.now():ctx.arenaNow();
        ctx.emoteLock={id:battle.id,until:now+5000,pending:true};
        updateEmoteControls(battle);
        try{
            if(battle.mode==='bot'){
                battle.emoteAvailableAt=now+5000;battle.myEmoteUntil=now+4000;battle.myEmote=index;
                persistBot();updateBattleVisuals();
            }else{
                const result=await arenaRequest('emote',{emote:index});
                if(result.battle?.id===battle.id){
                    if(ctx.emoteLock.id===battle.id)ctx.emoteLock.until=result.battle.emoteAvailableAt||0;
                    if(ctx.currentBattle?.id===battle.id){
                        ctx.currentBattle.emoteAvailableAt=result.battle.emoteAvailableAt;
                        ctx.currentBattle.myEmote=result.battle.myEmote;
                        updateBattleVisuals();
                    }
                }
                await pollRoom();
            }
        }catch(error){if(ctx.emoteLock.id===battle.id)ctx.emoteLock.until=0;throw error;}
        finally{if(ctx.emoteLock.id===battle.id)ctx.emoteLock.pending=false;if(ctx.currentBattle?.id===battle.id)updateEmoteControls(ctx.currentBattle);}
    }

function buildBotBattle(questions,level=1,id=ctx.uid(),classGrade=ctx.grade()) {
        const battle={id,mode:'bot',grade:classGrade,questions,index:0,hp:100,opponentHp:100,opponent:'Bot',botLevel:level,readyAt:Date.now()+5000,answer:null,resolved:false,correct:0,feedback:'',review:[]};
        setBotRoundTiming(battle,battle.readyAt);return battle;
    }

function backupLegacyBot(){const raw=sessionStorage.getItem('5bmath-bot-battle');if(!raw)return;try{const saved=JSON.parse(raw);if(!saved.gameClaimId)sessionStorage.setItem('5bmath-legacy-bot-backup:'+(PlatformAPI.snapshot.account?.id||'offline'),raw);}catch{}}

async function startBot() {
        if(ctx.botStarting||ctx.roomStarting)return;ctx.botStarting=true;ctx.updateArenaDiscipline();
        let sent=false;
        try{
            const scope='all';let result=null;
            if(ctx.live){
                const options=await ctx.requireDuelAllowance();
                if(!ctx.canUse('bot'))throw new Error('Em đã hết lượt luyện Bot hôm nay theo hạn mức gói.');
                result=await window.GameSession.admit('duel-bot',{scope},requestKey=>{sent=true;return PlatformAPI.request('bot/start',{requestKey,scope},options);});
                ctx.duelAllowance?.refresh();
            }
            const questions=ctx.live?result.questions:ctx.content.generate({grade:ctx.grade(),difficulty:0,count:20,maxWeek:35});
            if(ctx.live&&!result.gameClaim?.claimId)throw new Error('Máy chủ chưa xác nhận phòng luyện Bot; chưa thể bắt đầu.');
            if(!ctx.live){ctx.consumeLocal('bot');for(let index=0;index<6;index++)questions[index]=ctx.content.problem(ctx.grade(),questions[index].topic,index,1);}
            backupLegacyBot();ctx.currentBattle=buildBotBattle(questions,ctx.live?Number(result.botRules?.level??1):1,ctx.live?result.gameClaim.claimId:ctx.uid(),ctx.live?(result.gameClaim.botBattle?.grade||ctx.grade()):ctx.grade());
            if(ctx.live)ctx.currentBattle.gameClaimId=result.gameClaim.claimId;
            sessionStorage.removeItem('5bmath-room');sessionStorage.setItem('5bmath-bot-battle',JSON.stringify(ctx.currentBattle));
            if(ctx.live){const claim=await window.GameSession.saveBot(result.gameClaim,ctx.currentBattle);window.GameSession.accept(claim);ctx.currentBattle={...ctx.currentBattle,...claim.botBattle,gameClaimId:claim.claimId,gameClaimRevision:claim.checkpointRevision};sessionStorage.setItem('5bmath-bot-battle',JSON.stringify(ctx.currentBattle));}
            ctx.go('battle',ctx.live?{bot:ctx.currentBattle.gameClaimId}:{});
        }catch(error){window.GameSession?.conflict(error);if(ctx.live&&ctx.currentBattle?.gameClaimId)window.GameSession?.show(window.GameSession.current,error.message);await ctx.recoverDuelAdmission(error,sent);throw error;}
        finally{ctx.botStarting=false;ctx.updateArenaDiscipline();}
    }

function ensureBotLease(){
        if(!ctx.live){ctx.botLeaseReady=true;return Promise.resolve(true);}
        const battle=ctx.currentBattle,epoch=ctx.botLeaseEpoch;
        if(!battle||battle.mode!=='bot')return Promise.resolve(false);
        if(ctx.botValidation?.epoch===epoch)return ctx.botValidation.promise;
        const prior=ctx.botValidation?.promise||Promise.resolve(),validation={epoch,promise:null};ctx.botLeaseReady=false;document.querySelector('#battle-answer-form')?.querySelectorAll('input,button').forEach(control=>control.disabled=true);
        validation.promise=(async()=>{
            await prior.catch(()=>{});if(epoch!==ctx.botLeaseEpoch||ctx.currentBattle!==battle)return false;
            try{
                const claim=await window.GameSession.validateBot(battle);if(!claim||epoch!==ctx.botLeaseEpoch||ctx.currentBattle!==battle)return false;
                const initial={...buildBotBattle(claim.botBattle.questions,1,claim.claimId,claim.botBattle.grade),...battle,questions:claim.botBattle.questions,gameClaimId:claim.claimId,botLevel:1};
                const saved=await window.GameSession.saveBot(claim,initial);if(epoch!==ctx.botLeaseEpoch||ctx.currentBattle!==battle)return false;
                window.GameSession.accept(saved);ctx.currentBattle={...initial,...saved.botBattle,gameClaimId:saved.claimId,gameClaimRevision:saved.checkpointRevision};sessionStorage.setItem('5bmath-bot-battle',JSON.stringify(ctx.currentBattle));ctx.botLeaseReady=true;
                window.GameSession.watchBot(saved,{state:()=>ctx.currentBattle,onClaim:(next,info)=>{if(epoch===ctx.botLeaseEpoch&&info.checkpoint&&ctx.currentBattle?.gameClaimId===next.claimId){ctx.currentBattle.gameClaimRevision=next.checkpointRevision;sessionStorage.setItem('5bmath-bot-battle',JSON.stringify(ctx.currentBattle));}},onLost:(next,error)=>{if(epoch!==ctx.botLeaseEpoch)return;ctx.botLeaseReady=false;window.GameSession.unwatch();window.GameSession.show(next,error?.message||'Phiên luyện đã tạm dừng. Tiếp tục trận để đồng bộ.');updateBattleVisuals();}});
                if(!document.querySelector('#battle-answer-form'))ctx.refresh();else updateBattleVisuals();return true;
            }catch(error){if(epoch===ctx.botLeaseEpoch){ctx.botLeaseReady=false;window.GameSession?.conflict(error);window.GameSession?.show(error.details?.gameClaim||window.GameSession.current,'Chưa xác nhận được phòng luyện. '+error.message);updateBattleVisuals();}return false;}
            finally{if(ctx.botValidation===validation)ctx.botValidation=null;}
        })();ctx.botValidation=validation;return validation.promise;
    }

function setBotRoundTiming(battle,startedAt) {
        battle.botForcedCorrect=false;battle.forcedReason=null;
        const duration=ctx.content.battleSeconds(battle.grade,battle.questions[battle.index].difficulty)*1000;
        battle.deadline=startedAt+duration;
        battle.botAnswered=false;battle.defenseUntil=null;battle.attacking=false;battle.damage=null;battle.draftAnswer='';
        // Leave one polling interval before expiry so a scheduled bot answer
        // is processed while the question is still open.
        battle.botAt=startedAt+duration*0.7+Math.random()*(duration*0.3-1000);
    }

function persistBot() {
        sessionStorage.setItem('5bmath-bot-battle',JSON.stringify(ctx.currentBattle));
        if(ctx.live&&ctx.botLeaseReady&&ctx.currentBattle?.gameClaimId)window.GameSession?.changedBot(ctx.currentBattle);
    }

function settleBotAttack(battle,defended,now) {
        if(battle.resolved)return;
        const damage=defended?10:20;
        const attacker=battle.attacking?'me':'opponent';
        if(battle.attacking)battle.opponentHp=Math.max(0,battle.opponentHp-damage);
        else battle.hp=Math.max(0,battle.hp-damage);
        battle.damage=damage;
        recordBotAttack(battle,attacker);
        Object.assign(battle.lastAttack,{damage,defended});
        battle.resolved=true;battle.roundReason='correct';battle.nextAt=now+3000;
        battle.feedback=battle.attacking
            ?(defended?'Bot đỡ đòn! ':'')+'Em gây '+damage+' sát thương.'
            :(defended?'Đỡ đòn! ':'Trúng đòn! ')+'Em mất '+damage+' máu.';
        if(battle.answer===null)battle.roundOutcome='opponent';
        persistBot();updateBattleVisuals();
    }

function beginBotAttack(battle,attacking,now) {
        battle.attacking=attacking;battle.defenseUntil=now+3000;
        const defenderAnswered=attacking?battle.botAnswered:battle.answer!==null;
        if(defenderAnswered){settleBotAttack(battle,false,now);return;}
        battle.feedback=attacking?'Em trả lời đúng! Chờ đối thủ phòng thủ.':'Đối thủ chuẩn bị tấn công! Trả lời đúng để giảm sát thương.';
    }

function answerBot(answer) {
        const battle=ctx.currentBattle,index=battle?.index;
        if(ctx.live&&(!ctx.botLeaseReady||document.hidden))return;
        tickBot();
        if(!battle||battle!==ctx.currentBattle||battle.index!==index||battle.resolved||battle.answer!==null||Date.now()>=(battle.defenseUntil||battle.deadline)||Date.now()<(battle.readyAt||0))return;
        battle.answer=answer;
        const correct=ctx.isCorrect(battle.questions[battle.index],answer);
        if(correct)battle.correct++;
        battle.roundOutcome=correct?'correct':'wrong';
        if(!correct){
            // Explicit BOT-only forced round outcome; no second bot submission.
            battle.botAnswered=true;battle.botForcedCorrect=true;
            battle.forcedReason='human_wrong_bots_correct';
            beginBotAttack(battle,false,Date.now());
            battle.roundReason='human_wrong_bots_correct';
            battle.feedback='Em trả lời sai: BOT được tính đúng và chốt câu ngay.';
            ArenaAudio.effect('wrong');
        }else if(battle.defenseUntil)settleBotAttack(battle,true,Date.now());
        else beginBotAttack(battle,true,Date.now());
        persistBot();updateBattleVisuals();
    }

function tickBot() {
        const battle=ctx.currentBattle;if(!battle||battle.mode!=='bot'||ctx.live&&(!ctx.botLeaseReady||document.hidden))return;
        const now=Date.now();if(now<(battle.readyAt||0))return;
        if(battle.resolved){if(now>=battle.nextAt)nextBot();return;}
        const limit=battle.defenseUntil||battle.deadline;
        if(!battle.botAnswered&&now>=battle.botAt&&battle.botAt<limit){
            battle.botAnswered=true;
            const correct=battle.questions[battle.index].difficulty<=battle.botLevel;
            if(battle.defenseUntil)settleBotAttack(battle,correct,battle.botAt);
            else if(correct)beginBotAttack(battle,false,battle.botAt);
            else if(battle.answer!==null){battle.resolved=true;battle.roundReason='both_wrong';battle.feedback='Hai bên chưa trả lời đúng. Giữ nguyên máu.';battle.nextAt=now+3000;}
        }
        if(!battle.resolved){
            if(battle.defenseUntil){if(now>=battle.defenseUntil)settleBotAttack(battle,false,battle.defenseUntil);}
            else if(now>=battle.deadline){battle.resolved=true;battle.feedback='Hết thời gian câu này. Hai bên giữ nguyên máu.';battle.roundOutcome=battle.answer!==null?'wrong':'timeout';battle.roundReason='timeout';battle.nextAt=now+3000;}
        }
        persistBot();updateBattleVisuals();
    }

function nextBot() {
        const battle = ctx.currentBattle;
        if (!battle?.resolved||ctx.live&&(!ctx.botLeaseReady||document.hidden)) return;
        if(battle.review.length===battle.index)battle.review.push({...battle.questions[battle.index],myAnswer:battle.answer,correct:ctx.isCorrect(battle.questions[battle.index],battle.answer)});
        if (battle.hp === 0 || battle.opponentHp === 0 || battle.index === battle.questions.length - 1) {
            const outcome = battle.hp === 0 ? 'lose' : battle.opponentHp === 0 ? 'win' : 'draw';
            finishBattle({...battle,outcome,rounds:battle.index + 1,points:0});
            return;
        }
        battle.index++;
        setTimeout(()=>ArenaAudio.effect('next'),100);
        battle.answer = null;
        battle.resolved = false;
        battle.feedback = '';battle.nextAt=null;
        battle.roundOutcome='waiting';battle.roundReason=null;
        setBotRoundTiming(battle,Date.now());
        persistBot();
        ctx.refresh();
    }

function challengeOpponent(result){const s=result.opponentStats||{},code=Object.hasOwn(ctx.mascotAvatars,s.mascot)?s.mascot:'sprout',xp=Math.max(0,Number(s.xp)||0);return `<div class="challenge-opponent">${ctx.art(code,ctx.mascotAvatars[code][0],false,xp)}<div><h3>${ctx.escape(ctx.mascotAvatars[code][0])}</h3><p>${ctx.mascotVisuals.rankFor(xp)} · ${ctx.content.format(xp)} XP</p><dl><div><dt>Khối</dt><dd>${Number(result.opponentGrade)||ctx.grade()}</dd></div><div><dt>Máu khi vào trận</dt><dd>100 HP</dd></div><div><dt>Thắng / Thua</dt><dd>${Math.max(0,Number(s.wins)||0)} / ${Math.max(0,Number(s.losses)||0)}</dd></div></dl></div></div>`;}

function finishBattle(result) {
        const visualUntil=ctx.browser?ctx.mascotVisuals.pendingUntil():0;if(result.outcome!=='left'&&ctx.currentRoute==='battle'&&Date.now()<visualUntil){if(!ctx.catFinishTimer)ctx.catFinishTimer=setTimeout(()=>{ctx.catFinishTimer=null;if(ctx.currentBattle?.id===result.id)finishBattle(result);},visualUntil-Date.now()+30);return;}

        const horsePending=ctx.browser?window.HorseAnimation?.pendingUntil?.()||0:0;
        if(result.outcome!=='left'&&ctx.currentRoute==='battle'&&Date.now()<horsePending){
            if(!ctx.catFinishTimer)ctx.catFinishTimer=setTimeout(()=>{ctx.catFinishTimer=null;if(ctx.currentBattle?.id===result.id&&ctx.currentRoute==='battle')finishBattle(result);},Math.max(40,horsePending-Date.now()+40));
            return;
        }
        if(result.outcome!=='left'&&ctx.currentRoute==='battle'&&Date.now()<ctx.octopusFinaleUntil){
            if(!ctx.octopusFinishTimer)ctx.octopusFinishTimer=setTimeout(()=>{ctx.octopusFinishTimer=null;if(ctx.currentBattle?.id===result.id&&ctx.currentRoute==='battle')finishBattle(result);},ctx.octopusFinaleUntil-Date.now()+40);
            return;
        }
        // Visual completion only; authoritative damage, score and deadlines stay unchanged.
        if(result.outcome!=='left'&&ctx.currentRoute==='battle'&&Date.now()<ctx.owlFinaleUntil){
            if(!ctx.owlFinishTimer)ctx.owlFinishTimer=setTimeout(()=>{ctx.owlFinishTimer=null;if(ctx.currentBattle?.id===result.id&&ctx.currentRoute==='battle')finishBattle(result);},ctx.owlFinaleUntil-Date.now()+30);
            return;
        }
        // Let an already resolved visual finish; server HP/score/deadlines stay authoritative.
        if(result.outcome!=='left'&&ctx.currentRoute==='battle'&&Date.now()<ctx.catFinaleUntil){
            if(!ctx.catFinishTimer)ctx.catFinishTimer=setTimeout(()=>{ctx.catFinishTimer=null;if(ctx.currentBattle?.id===result.id&&ctx.currentRoute==='battle')finishBattle(result);},ctx.catFinaleUntil-Date.now()+40);
            return;
        }
        if(ctx.live&&result.mode==='bot'&&result.gameClaimId&&!result.gameClaimReleased){
            ctx.botLeaseReady=false;window.GameSession?.unwatch();
            if(ctx.botReleasePending===result.gameClaimId)return;ctx.botReleasePending=result.gameClaimId;
            window.GameSession.releaseBot({...ctx.currentBattle,...result},result.outcome==='left'?'leave':'finish').then(()=>{finishBattle({...result,gameClaimReleased:true});}).catch(error=>{window.GameSession?.show(error.details?.gameClaim||window.GameSession.current,'Chưa thể đóng phòng luyện. '+error.message);}).finally(()=>{ctx.botReleasePending=null;});return;
        }
        if(result.mode==='bot'&&!result.gameClaimId)backupLegacyBot();
        ctx.load();
        if(Number.isFinite(result.xpBefore)&&Number.isFinite(result.xpAfter))ctx.queuePromotion(result,result.xpBefore,result.xpAfter);
        if (!ctx.state.battles[result.id]) {
            ctx.state.battles[result.id] = {
                id:result.id, mode:result.mode, grade:result.grade, outcome:result.outcome,
                correct:result.correct, rounds:result.rounds, points:result.points,
                completed:result.completed,reason:result.reason,penalty:result.penalty,quotaRefunded:result.quotaRefunded,
                review:result.review || [], date:new Date().toISOString(),
            };
            const xpBefore=Number.isFinite(result.xpBefore)?result.xpBefore:ctx.state.points;const xpAfter=Number.isFinite(result.xpAfter)?result.xpAfter:Math.max(0,ctx.state.points+result.points);ctx.queuePromotion(result,xpBefore,xpAfter);ctx.state.points=xpAfter;
            ctx.save();
        }
        sessionStorage.removeItem('5bmath-bot-battle');
        sessionStorage.removeItem('5bmath-room');
        if(document.querySelector('#modal .arena-leave-confirm'))document.querySelector('#modal').close();
        ctx.currentBattle = null;
        sessionStorage.setItem('5bmath-last-battle',JSON.stringify(ctx.state.battles[result.id]||result));
        ctx.go('battleResult',{id:result.id});
    }

async function arenaRequest(action, values = {}, options) {
        const session = JSON.parse(sessionStorage.getItem('5bmath-room') || 'null') || {};
        if(ctx.live){
            try{const send=requestKey=>PlatformAPI.request('arena',{action,...session,...values,...(requestKey?{requestKey}:{})},options);const result=['quick','create','join'].includes(action)?await window.GameSession.admit('duel-'+action,values,send):await send();if(Object.hasOwn(result,'gameClaim'))window.GameSession?.accept(result.gameClaim);ctx.receiveArenaDiscipline(result);return result;}
            catch(error){
                window.GameSession?.conflict(error);
                if(error.details?.arenaDiscipline)ctx.receiveArenaDiscipline(error.details);
                else if(error.status===429&&error.details?.code!=='parent_game_limit')try{ctx.applySnapshot(await PlatformAPI.refresh());ctx.updateArenaDiscipline();}catch{}
                throw error;
            }
        }
        const response = await fetch('/api/arena',{
            method:'POST', headers:{'Content-Type':'application/json'},
            body:JSON.stringify({action,...session,...values}), signal:AbortSignal.timeout(8000),
        });
        const result = await response.json().catch(() => ({}));
        ctx.receiveArenaDiscipline(result);
        if (!response.ok) throw new Error(result.error || 'Máy chủ đấu trí chưa sẵn sàng. Em có thể luyện với bot.');
        return result;
    }

function roomSettings() {
        const difficulty = 0;
        const scope = ctx.arenaScope;
        return {name:ctx.name(),grade:ctx.grade(),difficulty,scope,mascot:ctx.state.mascot};
    }

async function enterRoom(action, values = {}) {
        if(ctx.roomStarting||ctx.botStarting)return;ctx.roomStarting=true;ctx.updateArenaDiscipline();
        let sent=false;
        try{
            ctx.requireHumanPlay();
            const options=ctx.live?await ctx.requireDuelAllowance():undefined;
            ctx.requireHumanPlay();
            if(!ctx.canUse('human'))throw new Error('Em đã hết lượt đấu với người hôm nay theo hạn mức gói.');
            sent=true;
            const result=await arenaRequest(action,{...roomSettings(),...values},options);
            if(ctx.live)ctx.duelAllowance?.refresh();
            if(!result.code||!result.token)throw new Error('Máy chủ chưa trả về phòng đấu hợp lệ.');
            sessionStorage.setItem('5bmath-room',JSON.stringify({code:result.code,token:result.token}));
            ctx.go('room',{code:result.code});
        }catch(error){await ctx.recoverDuelAdmission(error,sent);throw error;}
        finally{ctx.roomStarting=false;ctx.updateArenaDiscipline();}
    }

async function openRoomLink(code) {
        try {
            if(ctx.live){
                const claim=await window.GameSession.get();
                const credentials=claim?.credentials;
                if(claim?.game==='duel'&&claim.playMode==='human'&&credentials?.code===code&&credentials.token){
                    sessionStorage.setItem('5bmath-room',JSON.stringify(credentials));
                    await pollRoom();
                    return;
                }
            }
            await enterRoom('join',{code});
        } catch(error) {
            const status=document.querySelector('#learning-room-status');
            if(status)status.textContent=error.message;
            ctx.host.toast(error.message);
        }
    }

function overlay(html) {
        if(html)ctx.setMobileMenu(false,false);
        let node=document.querySelector('#arena-overlay');
        if(!html){node?.remove();return;}
        if(!node){node=document.createElement('div');node.id='arena-overlay';node.className='arena-overlay';document.body.append(node);}
        node.innerHTML=html;
        node.querySelector('[data-cancel-challenge]')?.addEventListener('click',()=>ctx.actions['leave-room']().catch(e=>ctx.host.toast(e.message)));
        node.querySelector('[data-accept-challenge]')?.addEventListener('click',async e=>{const control=e.currentTarget;control.dataset.humanPending='true';control.disabled=true;try{ctx.requireHumanPlay();await arenaRequest('accept');await pollRoom();}catch(error){ctx.host.toast(error.message);}finally{if(control.isConnected){delete control.dataset.humanPending;control.disabled=false;}ctx.updateArenaDiscipline();}});
        ctx.updateArenaDiscipline();
    }

function countdown(until,clock=ctx.arenaNow()) {
        const seconds=Math.max(0,Math.ceil((until-clock)/1000));
        if(seconds===ctx.lastCount&&document.querySelector('.prepare-count'))return;
        if(seconds!==ctx.lastCount){ctx.lastCount=seconds;if(typeof ArenaAudio!=='undefined')ArenaAudio.effect(seconds?'count':'go');}
        if(ctx.currentRoute==='room'){overlay('');const node=document.querySelector('#learning-room-content');if(node)node.innerHTML=`<section class="game-ready-inline" role="status"><h2>Đã đủ hai bạn</h2><strong>${seconds||'BẮT ĐẦU!'}</strong><p>Trận tự bắt đầu sau thời gian chuẩn bị.</p></section>`;return;}
        overlay(`<div class="prepare-count" role="status"><strong>${seconds||'BẮT ĐẦU!'}</strong><span>Sẵn sàng cùng linh vật!</span></div>`);
    }

function ownPublicRoomCodes(){
        const values=new Set();try{const saved=JSON.parse(sessionStorage.getItem('5bmath-game-claim')||'null');if(saved?.owner===PlatformAPI.snapshot.account?.id){const claim=window.GameSession?.current||saved.claim;if(claim?.game==='duel'&&claim.playMode==='human'){for(const value of [claim.code,claim.credentials?.code])if(value)values.add(String(value).toUpperCase());}}}catch{}return values;
    }

async function loadPublicRooms() {
        const target=document.querySelector('#public-rooms');if(!target||document.querySelector('#arena-panel-quick')?.hidden)return;
        try{
            const result=await arenaRequest('list');if(!target.isConnected)return;
            const owned=ownPublicRoomCodes(),listed=result.rooms.filter(r=>r.mine!==true&&!owned.has(String(r.code).toUpperCase()));
            target.innerHTML=listed.length?listed.map(r=>`<article class="public-room">${ctx.art(r.mascot||'sprout','',false,r.xp??0)}<div><strong>${ctx.escape(ctx.displayName(r.name))}</strong><p>${ctx.arenaScopeLabel(r.scope)} · Lớp ${r.grade}</p><small>${ctx.petRank(r.level||1)} · ${r.xp??0} XP · ${r.wins||0} thắng / ${r.losses||0} thua</small></div><button type="button" class="btn dark" data-game-admission data-human-play data-human-quota="true" data-challenge="${r.code}">Thách Đấu</button></article>`).join(''):'<p>Chưa có phòng phù hợp.</p>';
            ctx.updateArenaDiscipline();ctx.duelAllowance?.sync();
        }catch(e){target.textContent=e.message;}
    }

function inlineChallenge(result) {
        overlay('');document.querySelector('#waiting-popup')?.remove();
        if(ctx.currentRoute!=='room'){roomPopup(result.code||'');return;}
        const node=document.querySelector('#learning-room-content');if(!node)return;
        const seconds=Math.max(0,Math.ceil((result.challengeUntil-ctx.arenaNow())/1000));
        if(!node.querySelector('.challenge-inline')){
            node.innerHTML=`<section class="challenge-inline" aria-label="Lời mời đấu với bạn"><h2>${result.host?'Bạn đã vào phòng':'Đang chờ bạn xác nhận'}</h2>${challengeOpponent(result)}<p class="challenge-time" role="timer">${seconds}s</p><div class="actions">${result.host?'<button class="btn dark" type="button" data-human-play data-accept-challenge>Chấp nhận lời mời</button>':''}<button class="btn outline" type="button" data-cancel-challenge>Rời phòng</button></div></section>`;
            node.querySelector('[data-accept-challenge]')?.addEventListener('click',async event=>{const button=event.currentTarget;button.disabled=true;try{ctx.requireHumanPlay();await arenaRequest('accept');await pollRoom();}catch(error){window.GameSession?.conflict(error);ctx.host.toast(error.message);}finally{if(button.isConnected)button.disabled=false;}});
            node.querySelector('[data-cancel-challenge]')?.addEventListener('click',()=>ctx.actions['leave-room']().catch(error=>ctx.host.toast(error.message)));
        }else node.querySelector('.challenge-time').textContent=seconds+'s';
    }

function roomPopup() {
        document.querySelector('#waiting-popup')?.remove();
        if(window.GameSession?.current)window.GameSession.show(window.GameSession.current);
    }

async function pollRoom() {
        if(ctx.polling||!sessionStorage.getItem('5bmath-room'))return;ctx.polling=true;
        try{
            const result=await arenaRequest('state');window.GameSession?.setRoomView?.({id:result.id,code:result.code,mode:'duel',status:result.status});ctx.serverOffset=(result.serverNow||Date.now())-Date.now();
            if(result.status==='cancelled'){
                overlay('');sessionStorage.removeItem('5bmath-room');document.querySelector('#waiting-popup')?.remove();ctx.host.toast('Phòng đã hủy hoặc hết thời gian chờ.');ctx.go('arena');
            }else if(result.status==='finished'){
                if(ctx.currentBattle&&Number.isFinite(result.result.hp)&&ctx.currentRoute==='battle'){
                    ctx.currentBattle.hp=result.result.hp;ctx.currentBattle.opponentHp=result.result.opponentHp;
                    ctx.currentBattle.lastAttack=result.result.lastAttack;
                    updateBattleVisuals();
                }
                overlay('');finishBattle(result.result);
            }else if(result.status==='challenged'){
                inlineChallenge(result);
            }else if(result.status==='preparing'){
                document.querySelector('#waiting-popup')?.remove();countdown(result.readyAt);
            }else if(result.status==='playing'){
                overlay('');document.querySelector('#waiting-popup')?.remove();
                const changed=!ctx.currentBattle||result.battle.index!==ctx.currentBattle.index;
                const refreshHp=changed&&ctx.currentRoute==='battle'&&ctx.currentBattle?.id===result.battle.id?ctx.visualHp?.slice():null;
                if(!changed&&ctx.currentBattle?.draftAnswer!==undefined)result.battle.draftAnswer=ctx.currentBattle.draftAnswer;
                ctx.currentBattle=result.battle;
                if(ctx.currentRoute!=='battle')ctx.go('battle');else if(changed){ctx.refresh();setTimeout(()=>ArenaAudio.effect('next'),100);}else updateBattleVisuals();
                if(refreshHp&&ctx.currentRoute==='battle'){ctx.visualHp=refreshHp;updateBattleVisuals();}
            }else {
                overlay('');
                if(ctx.currentRoute==='room'){
                    document.querySelector('#waiting-popup')?.remove();
                    const status=document.querySelector('#learning-room-status'),container=document.querySelector('#learning-room-content');
                    if(status)status.textContent=`${result.public?'Phòng công khai':'Phòng bạn bè'} · Tự đóng sau ${ctx.timeText((result.expiresAt-ctx.arenaNow())/1000)}`;
                    if(container&&(!container.children.length||container.querySelector('.challenge-inline,.game-ready-inline')))container.innerHTML=`<div class="room-code"><small>Mã phòng</small><strong>${ctx.escape(result.code)}</strong><div class="actions">${ctx.button('Sao chép mã','copy-room','outline','copy')}${ctx.button('Sao chép liên kết','copy-room-link','outline','copy')}</div></div><p>${result.players.map(value=>ctx.escape(ctx.displayName(value))).join(' · ')} · ${result.players.length}/2 người · Đang chờ đối thủ</p>`;
                }else roomPopup(result.code);
            }
        }catch(e){ctx.host.toast(e.message);if(/hết hạn|không thuộc|không hợp lệ/.test(e.message)){sessionStorage.removeItem('5bmath-room');overlay('');document.querySelector('#waiting-popup')?.remove();ctx.currentBattle=null;if(ctx.currentRoute==='battle'||ctx.currentRoute==='room')ctx.go('arena');}}
        finally{ctx.polling=false;}
    }

function recordBotAttack(battle,attacker) {
        battle.lastAttack={id:battle.id+':'+battle.index,spell:ctx.attackSpells[Math.floor(Math.random()*ctx.attackSpells.length)][0],index:battle.index,attacker};
    }

function attackSpell(attacker) {
        const battle=ctx.currentBattle,event=battle?.lastAttack,side=attacker==='#fighter-me'?'me':'opponent';
        const chosen=event?.attacker===side&&ctx.attackSpells.find(([key])=>key===event.spell);
        // Compatibility for a bot session saved before lastAttack existed.
        return chosen||ctx.attackSpells[ctx.artSeed((battle?.id||'')+':'+(battle?.index||0))%ctx.attackSpells.length];
    }

function aimUltimateBeam(stage,source,victim) {
        const beam=stage?.querySelector('.energy-beam');
        const actor=source?.querySelector('.battle-pet'),target=victim?.querySelector('.battle-pet');
        if(!beam||!actor||!target)return;
        const box=stage.getBoundingClientRect(),scaleX=box.width/stage.offsetWidth,scaleY=box.height/stage.offsetHeight;
        const point=node=>{const r=node.getBoundingClientRect();return {
            x:(r.left-box.left+r.width/2)/scaleX-stage.clientLeft,
            y:(r.top-box.top+r.height*.55)/scaleY-stage.clientTop};};
        const from=point(actor),to=point(target),dx=to.x-from.x,dy=to.y-from.y;
        beam.style.cssText=`left:${from.x}px;top:${from.y-beam.offsetHeight/2}px;width:${Math.hypot(dx,dy)}px;transform:rotate(${Math.atan2(dy,dx)}rad);transform-origin:left center`;
    }

function playHitSpell(target,attacker,spell,final) {
        const battle=ctx.currentBattle,stage=document.querySelector('#battle-stage');
        if(!battle||!stage||final)return;
        if(ctx.hitSpellBattle!==battle.id){ctx.shownHitSpells.clear();ctx.hitSpellBattle=battle.id;}
        const side=attacker==='#fighter-me'?'me':'opponent';
        const eventId=battle.lastAttack?.attacker===side?battle.lastAttack.id:battle.id+':'+battle.index+':'+side;
        if(ctx.shownHitSpells.has(eventId))return;
        ctx.shownHitSpells.add(eventId);
        stage.dataset.randomSpells='true';
        const effect={node:null,timers:[]};ctx.activeHitSpells.add(effect);
        const show=()=>{
            const body=document.querySelector(target+' .battle-pet');
            if(!stage.isConnected||!body||ctx.currentBattle?.id!==battle.id){ctx.activeHitSpells.delete(effect);return;}
            const arena=stage.getBoundingClientRect(),pet=body.getBoundingClientRect();
            const width=stage.clientWidth,height=stage.clientHeight,padding=6;
            const scaleX=arena.width/stage.offsetWidth,scaleY=arena.height/stage.offsetHeight;
            const x=(pet.left-arena.left+pet.width/2)/scaleX-stage.clientLeft;
            const y=(pet.top-arena.top+pet.height*.55)/scaleY-stage.clientTop;
            // The rock and lightning land below the centre of their atlas cell.
            // Fit around the impact point instead of shifting the whole spell at an edge.
            const anchorY={rock:.78,vine:.55,lightning:.84}[spell[0]]??.5;
            const size=Math.max(1,Math.min(pet.width/scaleX*1.55,pet.height/scaleY*1.55,
                (x-padding)*2,(width-padding-x)*2,(y-padding)/anchorY,(height-padding-y)/(1-anchorY)));
            const left=x-size/2,top=y-size*anchorY;
            const node=document.createElement('span');effect.node=node;
            node.className='random-hit-spell';node.dataset.spell=spell[0];node.dataset.attackId=eventId;node.setAttribute('aria-hidden','true');
            node.style.cssText=`left:${left}px;top:${top}px;width:${size}px;height:${size}px;--hit-duration:1500ms`;
            stage.append(node);
            effect.timers.push(setTimeout(()=>{node.remove();ctx.activeHitSpells.delete(effect);},1500));
        };
        show();
    }

function animateHit(target,attacker,final,spell) {
        if(window.ArenaCrabAnimation?.hit({source:document.querySelector(attacker),victim:document.querySelector(target),final})){
            if(final)ctx.catFinaleUntil=Math.max(ctx.catFinaleUntil,Date.now()+3100);
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(final&&document.querySelector(target)?.querySelector('.battle-pet.octopus'))ctx.octopusFinaleUntil=Date.now()+4100;
        if(final){const pet=document.querySelector(target)?.querySelector('.battle-pet.ca-map');if(pet){window.SharkAnimation?.markDefeated(pet);ctx.catFinaleUntil=Math.max(ctx.catFinaleUntil,Date.now()+3100);}}
        const mamSource=document.querySelector(attacker),mamVictim=document.querySelector(target);
        const mamSourcePet=mamSource?.querySelector('.battle-pet.sprout');
        if(mamSourcePet&&window.MamSachAnimation){
            if(final)ctx.catFinaleUntil=Math.max(ctx.catFinaleUntil,Date.now()+3100);
            const mamVictimPet=mamVictim?.querySelector('.battle-pet'),label=document.querySelector('#spell-announcement');
            if(label)label.textContent='';
            if(mamVictim)mamVictim.dataset.spell='mam-sach';
            const impact=()=>{
                if(!mamVictim?.isConnected||!mamVictimPet)return;
                mamVictimPet.dataset.mood=final?'lose':'hit';mamVictim.classList.add('taking-hit');
                if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(mamVictimPet,final?'lose':'hit');
            };
            mamSource.classList.add('attacking');window.MamSachAnimation.hit({source:mamSource,victim:mamVictim,final});
            if(final)setTimeout(impact,1750);else impact();
            ArenaAudio.effect(final?'beam':spell[0]);
            setTimeout(()=>{
                mamSource?.classList.remove('attacking');mamVictim?.classList.remove('taking-hit');
                if(mamSourcePet.isConnected)mamSourcePet.dataset.mood=final?'win':'idle';
                if(mamVictimPet?.isConnected){mamVictimPet.dataset.mood=final?'lose':'idle';if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(mamVictimPet,final?'lose':'idle');}
                if(label?.isConnected&&label.dataset.mamSach==='true')label.textContent='';
            },final?3000:1100);
            return;
        }
        const owlSource=document.querySelector(attacker),owlVictim=document.querySelector(target);
        if(typeof OwlAnimation!=='undefined'&&OwlAnimation.hit({source:owlSource,victim:owlVictim,final})){
            if(final)ctx.owlFinaleUntil=Date.now()+3100;
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(window.HorseAnimation?.hit({source:document.querySelector(attacker),victim:document.querySelector(target),final})){
            if(final)ctx.catFinaleUntil=Math.max(ctx.catFinaleUntil,Date.now()+3100);
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(typeof ArenaStarfish!=='undefined' && ArenaStarfish.animate(target,attacker,final)){
            if(final)ctx.catFinaleUntil=Math.max(ctx.catFinaleUntil,Date.now()+3100);
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(window.ArenaDolphin?.hit({source:document.querySelector(attacker),victim:document.querySelector(target),final})){
            if(final)ctx.catFinaleUntil=Math.max(ctx.catFinaleUntil,Date.now()+3100);
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(ctx.browser&&window.SharkAnimation?.animate(target,attacker,final)){
            if(final)ctx.catFinaleUntil=Date.now()+3100;
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(window.ButterflyAnimation?.hit({source:document.querySelector(attacker),victim:document.querySelector(target),final})){
            if(final)ctx.catFinaleUntil=Math.max(ctx.catFinaleUntil,Date.now()+3100);
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(typeof TigerAnimation!=='undefined' && TigerAnimation.hit({source:document.querySelector(attacker),victim:document.querySelector(target),final})){
            if(final&&TigerAnimation.remaining()>0)ctx.catFinaleUntil=Math.max(ctx.catFinaleUntil,Date.now()+3100);
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(typeof ArenaVoi!=='undefined' && ArenaVoi.animate(target,attacker,final)){
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        if(typeof ArenaLion!=='undefined' && ArenaLion.animate(target,attacker,final)){
            if(final)ctx.catFinaleUntil=Date.now()+3100;
            ArenaAudio.effect(final?'beam':spell[0]);return;
        }
        const stage=document.querySelector('#battle-stage'),victim=document.querySelector(target),source=document.querySelector(attacker);
        const sourcePet=source?.querySelector('.battle-pet'),victimPet=victim?.querySelector('.battle-pet');
        if(sourcePet?.classList.contains('fox')&&window.FoxAnimation){
            if(final)ctx.catFinaleUntil=Date.now()+3100;
            if(victim)victim.dataset.spell='fox';
            const impact=()=>{if(!victim?.isConnected||!victimPet)return;victimPet.dataset.mood=final?'lose':'hit';victim.classList.add('taking-hit');};
            const show=()=>{
                if(!stage?.isConnected||!sourcePet.isConnected)return;
                if(final)ctx.catFinaleUntil=Date.now()+3100;
                if(final)setTimeout(impact,1750);else impact();
                source.classList.add('attacking');window.FoxAnimation.hit({source,victim,final});
                const label=document.querySelector('#spell-announcement');if(label)label.textContent='';
                ArenaAudio.effect(final?'beam':spell[0]);
                setTimeout(()=>{victim?.classList.remove('taking-hit');source?.classList.remove('attacking');if(victimPet?.isConnected&&!final)victimPet.dataset.mood='idle';if(sourcePet.isConnected)window.FoxAnimation.play(sourcePet,final?'win':'idle');},final?3000:1100);
            };
            // Start the impact and result delay with the decoded images on a cold load.
            window.FoxAnimation.ready().then(show).catch(()=>{
                if(!sourcePet.isConnected)return;
                sourcePet.dataset.mood='attack';impact();
                setTimeout(()=>{victim?.classList.remove('taking-hit');if(victimPet?.isConnected&&!final)victimPet.dataset.mood='idle';if(sourcePet.isConnected)sourcePet.dataset.mood='idle';},1100);
            });
            return;
        }
        if(sourcePet?.classList.contains('eagle')&&window.EagleAnimation){
            if(final)ctx.catFinaleUntil=Date.now()+3100;
            if(victim)victim.dataset.spell='eagle';
            const impact=()=>{if(!victim?.isConnected)return;victimPet.dataset.mood=final?'lose':'hit';victim.classList.add('taking-hit');};
            if(final)setTimeout(impact,1750);else impact();
            source.classList.add('attacking');window.EagleAnimation.hit({source,victim,final});
            const label=document.querySelector('#spell-announcement');if(label)label.textContent='';
            ArenaAudio.effect(final?'beam':spell[0]);
            setTimeout(()=>{victim?.classList.remove('taking-hit');source?.classList.remove('attacking');if(sourcePet.isConnected)window.EagleAnimation.play(sourcePet,final?'win':'idle');},final?3000:1100);
            return;
        }
        if(sourcePet?.classList.contains('octopus')&&typeof OctopusAnimation!=='undefined'){
            if(final)ctx.octopusFinaleUntil=Math.max(ctx.octopusFinaleUntil,Date.now()+3100);
            sourcePet.dataset.mood=final?'ultimate':'attack';source?.classList.add('attacking');
            const label=document.querySelector('#spell-announcement');if(label)label.textContent=final?'':'✦ Sóng tay Bạch tuộc';
            const impact=()=>{if(!victim?.isConnected||!victimPet)return;victim.dataset.spell='ink';victimPet.dataset.mood=final?'lose':'hit';victim.classList.add('taking-hit');};
            if(final)setTimeout(impact,1750);else impact();
            ArenaAudio.effect(final?'beam':spell[0]);
            setTimeout(()=>{
                source?.classList.remove('attacking');victim?.classList.remove('taking-hit');
                if(sourcePet.isConnected)sourcePet.dataset.mood='idle';
                if(victimPet?.isConnected&&!final)victimPet.dataset.mood='idle';
                if(label?.isConnected)label.textContent='';
            },final?3000:1200);
            return;
        }
        const rabbitUltimate=final&&sourcePet?.classList.contains('rabbit')&&typeof RabbitAnimation!=='undefined';
        if(rabbitUltimate)ctx.catFinaleUntil=Math.max(ctx.catFinaleUntil,Date.now()+3100);
        const bearUltimate=final&&sourcePet?.classList.contains('gau')&&typeof BearAnimation!=='undefined';
        if(bearUltimate){ctx.catFinaleUntil=Math.max(ctx.catFinaleUntil,Date.now()+3100);stage?.classList.add('bear-ultimate');setTimeout(()=>stage?.classList.remove('bear-ultimate'),3000);}
        const playBear=(pet,mode,onFinish)=>{const canvas=pet?.querySelector('canvas[data-bear]');if(canvas&&typeof BearAnimation!=='undefined')BearAnimation.play(canvas,mode,{onFinish});};
        const beeAttack=sourcePet?.classList.contains('bee')&&Boolean(window.ArenaBeeAnimation);
        const beeUltimate=final&&beeAttack;
        if(beeUltimate)ctx.catFinaleUntil=Date.now()+3100;
        const catAttack=sourcePet?.classList.contains('cat')&&Boolean(window.ArenaCatAnimation);
        const catUltimate=final&&catAttack;
        const sparrowAttack=sourcePet?.classList.contains('sparrow')&&Boolean(window.ArenaSparrowAnimation);
        const sparrowUltimate=final&&sparrowAttack;
        if(sparrowUltimate)ctx.catFinaleUntil=Date.now()+3100;
        if(catUltimate)ctx.catFinaleUntil=Date.now()+3100;
        victim?.classList.remove('taking-hit');source?.classList.remove('attacking');if(victim)void victim.offsetWidth;
        const hit=()=>{if(!victim?.isConnected||!victimPet)return;victim.dataset.spell=beeAttack?'bee':catAttack?'cat':rabbitUltimate?'moon':bearUltimate?'bear':spell[0];victimPet.dataset.mood=final&&!victimPet.classList.contains('gau')?'lose':'hit';victim.classList.add('taking-hit');playBear(victimPet,'hit',()=>{if(final&&victimPet.isConnected){victimPet.dataset.mood='lose';playBear(victimPet,'defeat');}});};
        if(beeUltimate||rabbitUltimate||catUltimate||bearUltimate||sparrowUltimate)setTimeout(hit,1750);else hit();
        if(sourcePet)sourcePet.dataset.mood=beeUltimate||rabbitUltimate||catUltimate||bearUltimate||sparrowUltimate?'ultimate':'attack';
        if(sparrowUltimate)window.ArenaSparrowAnimation.ultimate({source,victim});
        if(beeAttack)window.ArenaBeeAnimation.hit({source,victim,final,animateVictim:false});
        window.ArenaCatAnimation?.hit({source,victim,final});
        source?.classList.add('attacking');
        if(typeof RabbitAnimation!=='undefined')RabbitAnimation.play(sourcePet,rabbitUltimate?'ultimate':'attack');
        playBear(sourcePet,bearUltimate?'ultimate':'attack');
        const announcement=document.querySelector('#spell-announcement');
        if(announcement)announcement.textContent=beeAttack||rabbitUltimate||catAttack||bearUltimate||sparrowAttack?'':final?'✦ Chiêu cuối':'✦ '+spell[1];
        if(final){if(!beeUltimate&&!rabbitUltimate&&!catUltimate&&!bearUltimate&&!sparrowUltimate){aimUltimateBeam(stage,source,victim);stage?.classList.add(attacker==='#fighter-me'?'ultimate-right':'ultimate-left');}ArenaAudio.effect('beam');}else ArenaAudio.effect(spell[0]);
        setTimeout(()=>{
            victim?.classList.remove('taking-hit');source?.classList.remove('attacking');
            for(const node of [victim,source])if(node?.isConnected){const pet=node.querySelector('.battle-pet');const mood=final&&node===victim?'lose':'idle';pet.dataset.mood=mood;if(pet!==victimPet&&typeof RabbitAnimation!=='undefined')RabbitAnimation.play(pet,mood);const bearMode=final?(node===victim?'defeat':'win'):'idle';playBear(pet,bearMode);if(pet?.classList.contains('gau'))pet.dataset.mood=bearMode==='defeat'?'lose':bearMode;}
            if(announcement?.isConnected)announcement.textContent='';
        },beeUltimate||rabbitUltimate||catUltimate||bearUltimate||sparrowUltimate?3000:1600);
    }

function dispatchBattleHit(target,attacker,final) {
        if(ctx.mascotVisuals.hit(target,attacker,final)){ArenaAudio.effect(final?'beam':'hit');return;}

        const spell=attackSpell(attacker);
        const stage=document.querySelector('#battle-stage');
        // Suppress legacy default spells inside mascot reactions as well.
        if(stage)stage.dataset.randomSpells='true';
        if(final)ctx.clearHitSpells();
        else playHitSpell(target,attacker,spell,false);
        if(final&&[target,attacker].some(selector=>document.querySelector(selector)?.querySelector('.battle-pet.cu-meo')))ctx.owlFinaleUntil=Math.max(ctx.owlFinaleUntil,Date.now()+3100);
        window.HorseAnimation?.notifyVictim(target,attacker,final);
        if(typeof RabbitAnimation!=='undefined')RabbitAnimation.notifyVictim(target,attacker,final);
        if(typeof ArenaVoi!=='undefined')ArenaVoi.notifyVictim(target,attacker,final);
        animateHit(target,attacker,final,spell);
    }

function updateBattleVisuals() {
        const b=ctx.currentBattle;if(!b||ctx.currentRoute!=='battle')return;
        const current=[b.hp,b.opponentHp],before=ctx.visualHp;
        for(const [id,delta]of [['#fighter-me',before?before[0]-b.hp:0],['#fighter-opponent',before?before[1]-b.opponentHp:0]]){const el=document.querySelector(id+' .damage');if(el&&delta>0)el.textContent='−'+delta+' ♥';}
        if(before){if(b.hp<before[0])dispatchBattleHit('#fighter-me','#fighter-opponent',b.hp===0);if(b.opponentHp<before[1])dispatchBattleHit('#fighter-opponent','#fighter-me',b.opponentHp===0);}
        ctx.visualHp=current;
        for(const [id,hp]of [['#fighter-me',b.hp],['#fighter-opponent',b.opponentHp]]){
            const node=document.querySelector(id);if(!node)continue;
            node.querySelector('.split b:last-child').textContent=hp+' / 100 ♥';
            const m=node.querySelector('.meter');m.setAttribute('aria-valuenow',hp);m.querySelector('span').style.setProperty('--value',hp+'%');
        }
        const now=b.mode==='bot'?Date.now():ctx.arenaNow();
        const closed=b.answer!==null||b.resolved||now>=(b.defenseUntil||b.deadline)||now<(b.readyAt||0)||ctx.battleSending||(ctx.live&&b.mode==='bot'&&(!ctx.botLeaseReady||document.hidden));
        document.querySelectorAll('#battle-answer-form input,#battle-answer-form button').forEach(el=>el.disabled=closed);
        const defense=document.querySelector('#battle-defense-status');
        if(defense){
            defense.hidden=!b.defenseUntil||b.resolved;
            const seconds=Math.max(0,Math.ceil(((b.defenseUntil||now)-now)/1000));
            const text=(b.attacking?'Em trả lời đúng! Chờ đối thủ phòng thủ: ':'Đối thủ chuẩn bị tấn công! Trả lời đúng để giảm sát thương: ')+seconds;
            if(defense.textContent!==text)defense.textContent=text;
        }
        for(const [id,blocked]of [['#fighter-me',!b.attacking],['#fighter-opponent',b.attacking]]){
            // The answer window offers a chance to block; only a confirmed correct reply earns a shield.
            const defended=Boolean(blocked&&b.resolved&&b.damage===10&&b.lastAttack?.defended===true);
            const node=document.querySelector(id);if(node)node.classList.toggle('defending',defended);ctx.mascotVisuals.defend(id,defended);
        }
        updateBattleRound(b);
        const feedback=document.querySelector('#learning-battle-feedback');if(feedback){feedback.textContent=b.feedback||(b.questions[b.index]?.responseMode==='choice'?'Chọn đáp án để gửi ngay.':'Em hãy nhập đáp án rồi bấm Gửi.');feedback.classList.toggle('wrong',Boolean(b.feedback?.includes('chưa đúng')));}
        for(const [id,value]of [['#my-emote',b.myEmote],['#opponent-emote',b.opponentEmote]]){
            const node=document.querySelector(id);if(node)node.textContent=value===null||value===undefined?'':ctx.emotes[value].join(' ');
        }
        updateEmoteControls(b);
    }

function setArenaMode(mode) {
        if(!['quick','friends','bot'].includes(mode))return;
        ctx.arenaMode=mode;try{sessionStorage.setItem('5bmath-arena-mode',mode);}catch{}
        document.querySelectorAll('[data-arena-mode]').forEach(button=>{
            const selected=button.dataset.arenaMode===mode;
            button.setAttribute('aria-selected',String(selected));button.tabIndex=selected?0:-1;button.classList.toggle('selected',selected);
        });
        for(const key of ['quick','friends','bot']){const panel=document.querySelector('#arena-panel-'+key);if(panel)panel.hidden=key!==mode;}
        const usage=document.querySelector('#arena-mode-usage');if(usage)usage.innerHTML=ctx.duelProductUsage(mode==='bot'?'bot':'human');
        ctx.updateArenaDiscipline();
        if(mode==='quick')loadPublicRooms();
    }
const views = {
arena() {
            const controls=[['quick','zap','Đấu nhanh'],['friends','users','Với bạn'],['bot','bot','Với máy']];
            const quotaGame=ctx.live&&ctx.learnerBackgroundAllowed()?'duel':undefined;
            return `${ctx.groupGames.tabs('duel')}${ctx.intro('Đấu trí toán học','Chọn cách chơi và đồng hành cùng linh vật của em.')}
            <div class="arena-lobby">${ctx.arenaLobby.playerCard({game:quotaGame,pets:ctx.mascotVisuals,mascot:ctx.state.mascot,xp:ctx.state.points})}${ctx.arenaLobby.showcase('duel')}
            <div class="arena-player-usage" id="arena-mode-usage">${ctx.duelProductUsage(ctx.arenaMode==='bot'?'bot':'human')}</div>
            ${ctx.disciplinePanel()}${ctx.gameAllowance?.feedback?.(quotaGame)||''}<div class="arena-modes" role="tablist" aria-label="Chế độ đấu trí">${controls.map(([key,symbol,label])=>`<button type="button" role="tab" id="arena-tab-${key}" data-arena-mode="${key}" aria-controls="arena-panel-${key}" aria-selected="${ctx.arenaMode===key}" tabindex="${ctx.arenaMode===key?'0':'-1'}" class="${ctx.arenaMode===key?'selected':''}">${ctx.icon(symbol,25)}<span>${label}</span></button>`).join('')}</div>
            <section class="arena-mode-panel" id="arena-panel-quick" role="tabpanel" aria-labelledby="arena-tab-quick" ${ctx.arenaMode==='quick'?'':'hidden'}>
              <h2 class="arena-panel-title">Tìm trận nhanh</h2><button type="button" class="arena-action arena-action-quick" data-game-admission data-human-play data-human-quota="true" data-learning="quick-match" ${ctx.canPlayHuman()?'':'disabled'}>${ctx.icon('search',30)}<span><strong>Tìm đối thủ</strong><small>Ghép với bạn cùng lớp ${ctx.grade()} hoặc mở phòng công khai</small></span></button>
              <div class="section-head arena-rooms-heading"><h3>Phòng đang mở</h3>${ctx.badge('Lớp '+ctx.grade(),'sage')}</div><section class="card card-pad" id="public-rooms" aria-live="polite">Đang tìm phòng…</section>
            </section>
            <section class="arena-mode-panel" id="arena-panel-friends" role="tabpanel" aria-labelledby="arena-tab-friends" ${ctx.arenaMode==='friends'?'':'hidden'}>
              <h2 class="arena-panel-title">Đấu với bạn</h2><button type="button" class="arena-action arena-action-friends" data-game-admission data-human-play data-human-quota="true" data-learning="create-room" ${ctx.canPlayHuman()?'':'disabled'}>${ctx.art('sprout')}<span><strong>Tạo phòng đấu</strong><small>Mời bạn bằng mã hoặc mở phòng cho tất cả</small></span>${ctx.icon('plus',24)}</button>
              <section class="card card-pad arena-join"><h3>Có mã phòng?</h3><form id="learning-join-form"><label class="field"><span>Mã phòng hoặc liên kết</span><input id="learning-room-code" placeholder="Nhập mã hoặc dán liên kết" required maxlength="500" autocomplete="off"></label><button class="btn dark" data-game-admission data-human-play data-human-quota="true" type="submit" ${ctx.canPlayHuman()?'':'disabled'}>Vào phòng</button></form><small>Dán liên kết bạn gửi cũng được. Câu hỏi của trận do hệ thống chuẩn bị cho hai bạn.</small></section>
            </section>
            <section class="arena-mode-panel" id="arena-panel-bot" role="tabpanel" aria-labelledby="arena-tab-bot" ${ctx.arenaMode==='bot'?'':'hidden'}>
              <h2 class="arena-panel-title">Luyện với Bot</h2>
              <button type="button" class="arena-action arena-action-bot" data-game-admission data-learning="start-bot" ${ctx.canUse('bot')?'':'disabled'}>${ctx.art('fox','',false,0)}<span><strong>Bắt đầu luyện với Bot</strong></span>${ctx.icon('play',22)}</button>
            </section>
            ${ctx.gameRulesView.markup('duel')}</div>`;
        },
room() {
            return `${ctx.back('Đấu trí','arena')}${ctx.intro('Phòng chờ','Chia sẻ mã hoặc chờ một lời thách đấu.')}<section class="card card-pad"><h2>Phòng của em</h2><div id="learning-room-status" role="status">Đang kết nối phòng…</div><div id="learning-room-content"></div><div class="actions">${ctx.button('Đi học tiếp trong thời gian chờ','minimize-room','dark','book')}${ctx.button('Rời phòng','leave-room','outline')}</div></section>`;
        },
battle() {
            if(!ctx.currentBattle)return ctx.intro('Trận đấu','Đang kết nối trận đấu…')+ctx.link('Về đấu trí','arena');
            const b=ctx.currentBattle,q=b.questions[b.index],scene=ctx.battleScenery(b),time=battleTime(b);
            return `${ctx.intro('Đấu trí toán học','Khối '+b.grade+' · '+(b.mode==='bot'?'Luyện với Bot':'Đấu với bạn'))}
            <div class="battle-play-layout"><div class="battle-stage illustrated-arena" id="battle-stage" data-scenery="${scene[0]}" style="--arena-background:url('arena-art/${scene[0]}.webp')"><span class="arena-scene-name">${ctx.escape(scene[1])}</span><span class="spell-announcement" id="spell-announcement" role="status"></span><div class="fighter" id="fighter-me"><div class="split"><b>${ctx.escape(ctx.name())}</b><b id="my-hp">${b.hp} / 100 ♥</b></div>${ctx.meter(b.hp,'Máu của em')}<div class="pet-body">${ctx.battlePet(ctx.state.mascot,ctx.petName())}<span class="spell-effect" aria-hidden="true"></span><span class="damage" aria-hidden="true">−20 ♥</span><span class="emote-bubble" id="my-emote"></span></div><strong>${ctx.escape(ctx.petName())}</strong></div><div class="versus">VS</div><div class="energy-beam" aria-hidden="true"></div><div class="fighter right" id="fighter-opponent"><div class="split"><b>${ctx.escape(ctx.displayName(b.opponent))}</b><b id="opponent-hp">${b.opponentHp} / 100 ♥</b></div>${ctx.meter(b.opponentHp,'Máu đối thủ')}<div class="pet-body">${ctx.battlePet(b.opponentMascot||(ctx.state.mascot==='fox'?'sprout':'fox'),'Linh vật đối thủ','idle',b.opponentXp??0)}<span class="spell-effect" aria-hidden="true"></span><span class="damage" aria-hidden="true">−20 ♥</span><span class="emote-bubble" id="opponent-emote"></span></div><strong>${b.mode==='bot'?'Bot luyện tập':'Đối thủ'}</strong></div></div>
            <section class="card card-pad battle-question"><div class="battle-round-content"><div class="battle-question-content"><div class="battle-question-meta">${ctx.badge('Câu '+(b.index+1)+' / '+b.questions.length,'sage')}<div class="battle-countdown"><div class="meter battle-time-meter" id="learning-battle-time-meter" role="progressbar" aria-label="Thời gian còn lại" aria-valuemin="0" aria-valuemax="${time.duration}" aria-valuenow="${time.remaining}" aria-valuetext="${ctx.timeText(time.remaining)} còn lại"><span style="--value:${time.percent}%"></span></div><span class="battle-time-remaining" id="learning-battle-timer">${ctx.timeText(time.remaining)}</span></div></div><h2>${ctx.escape(q.text)}</h2><form id="battle-answer-form">${ctx.answerInput(b.answer??b.draftAnswer??'',true,q.answerKind,q)}</form><p id="battle-defense-status" class="defense-status" role="status" hidden></p><p id="learning-battle-feedback" class="learning-feedback ${b.feedback?.includes('chưa đúng')?'wrong':''}" role="status">${ctx.escape(b.feedback||(q.responseMode==='choice'?'Chọn đáp án để gửi ngay.':'Em hãy nhập đáp án rồi bấm Gửi.'))}</p></div><section class="battle-round-status" aria-labelledby="battle-round-title" hidden><div class="battle-round-message" role="status" aria-atomic="true"><span class="battle-round-symbol" aria-hidden="true"></span><h2 id="battle-round-title"></h2><p id="battle-round-detail"></p></div><p class="battle-round-next" id="battle-round-next"></p><div class="battle-round-countdown" aria-live="off"><strong id="next-round-count"></strong></div><p class="battle-round-wait" id="battle-round-wait"></p></section></div><div class="emote-bar" role="group" aria-label="Gửi lời cổ vũ">${ctx.emotes.map(([symbol,text],i)=>`<button type="button" data-emote="${i}" title="${ctx.escape(text)}" aria-label="${ctx.escape(text)}" ${emoteSeconds(b)>0?'disabled':''}>${symbol}<small>${text}</small></button>`).join('')}</div>${ctx.button('Rời trận','leave-battle','outline')}</section></div>`;
        },
battleResult() {
            let cached=null; if(ctx.browser)try{cached=JSON.parse(sessionStorage.getItem('5bmath-last-battle')||'null');}catch{}
            const result=ctx.state.battles[ctx.query('id')]||(cached?.id===ctx.query('id')?cached:null)||Object.values(ctx.state.battles).at(-1);
            if(!result)return ctx.intro('Kết quả trận','Chưa có trận hoàn thành.')+ctx.link('Vào đấu trí','arena');
            const win=result.outcome==='win',lose=result.outcome==='lose',unfinished=result.mode!=='bot'&&result.completed===false;
            const resultTitle=unfinished?(result.reason==='server_restart'?'Trận đấu đã dừng':win?(result.reason==='disconnect'?'Đối thủ đã mất kết nối':'Đối thủ đã rời trận'):result.reason==='disconnect'?'Trận đấu bị gián đoạn':'Em đã rời trận'):(win?'Chúc mừng! Em đã chiến thắng!':lose?'Cố lên, em sẽ tiến bộ mỗi ngày!':result.outcome==='left'?'Đã rời trận':'Hai bạn đã rất cố gắng!');
            const interruptionNote=unfinished?`<p class="battle-interruption-note">${result.reason==='server_restart'?'Trận đấu đã dừng do máy chủ khởi động lại. Em không bị trừ kinh nghiệm.':win?'Em thắng do đối thủ rời trận và không nhận kinh nghiệm.':result.penalty?.disconnectForgiven?'Lần mất kết nối kéo dài đầu tiên trong 24 giờ được bỏ qua; em không bị trừ kinh nghiệm.':result.points<0?'Em bị trừ 1 kinh nghiệm vì bỏ trận.':lose?'Rời trận tính là thua.':'Trận đấu chưa hoàn thành.'} Trận này không cộng vào số trận thắng/thua của cả hai.${result.quotaRefunded?' Em đã được hoàn lượt đấu trong ngày.':''}</p>${result.penalty?.kind&&!result.penalty?.disconnectForgiven?`<p class="battle-penalty-note">${result.penalty.cooldownSeconds?'Em cần nghỉ đấu với người '+Math.ceil(result.penalty.cooldownSeconds/60)+' phút.':'Đây là lần vi phạm đầu tiên trong 24 giờ. Hãy chơi trọn trận cùng bạn nhé.'}</p>`:''}`:'';
            return `${ctx.back('Đấu trí','arena')}${ctx.intro('Kết quả trận đấu',result.mode==='bot'?'Luyện với Bot':'Đấu với bạn')}
            <section class="result-band sage battle-result ${win&&!unfinished?'victory':lose?'defeat':''}"><div class="score-circle"><strong>${result.points>0?'+':''}${result.points}</strong><small>Kinh nghiệm</small></div><div><h2>${resultTitle}</h2><p>${result.correct} câu đúng · ${Math.max(0,result.rounds-result.correct)} câu chưa đúng · ${result.rounds} câu đã chơi</p>${interruptionNote}${ctx.link('Chơi tiếp','arena')}</div><div class="result-pet">${ctx.art(ctx.state.mascot,ctx.petName())}</div>${win&&!unfinished?ctx.celebrationMarkup({seed:'battle:'+result.id,className:'confetti'}):''}</section>${ctx.disciplinePanel()}
            ${ctx.heading('Xem lại câu hỏi')}<label class="review-filter"><input type="checkbox" id="review-incorrect"> Chỉ xem câu chưa đúng</label><div class="solution-list">${(result.review||[]).map((item,i)=>`<article class="card card-pad" data-review-correct="${Boolean(item.correct)}"><div class="split"><b>Câu ${i+1}. ${ctx.escape(item.text)}</b>${ctx.badge(item.correct?'Đúng':'Cần xem lại',item.correct?'sage':'peach')}</div><p>Em chọn: ${ctx.escape(item.myAnswer??'Chưa trả lời')}</p><details class="hint"><summary>Xem cách giải</summary>${ctx.solutionView.answer(item.answer,'Đáp án')}<ol>${(item.steps||[]).map(step=>'<li>'+ctx.solutionView.text(step)+'</li>').join('')}</ol></details></article>`).join('')||'<p>Chưa có câu hỏi để xem lại.</p>'}</div>`;
        },
rank() { return ctx.groupGames.tabs('rank')+ctx.intro('Bảng xếp hạng','Linh vật · Đấu trí · Cướp Cờ · Đua Thú')+'<section class="card card-pad"><p>Đăng nhập trên máy chủ để xem kết quả thật của bốn bảng xếp hạng.</p></section>'; }
};
const actions = {
'start-bot':trigger=>startBot(trigger),
'next-battle':() => ctx.currentBattle.mode === 'bot' ? nextBot() : arenaRequest('next',{index:ctx.currentBattle.index}).then(pollRoom),
'create-room':trigger=>openArenaPreflight('create',{},trigger),
'minimize-room':()=>{sessionStorage.setItem('5bmath-room-mini','1');ctx.go('arena');},
'quick-match':()=>enterRoom('quick'),
'copy-room':() => ctx.copyText(JSON.parse(sessionStorage.getItem('5bmath-room')).code),
'copy-room-link':() => ctx.copyText(new URL(ctx.href('room',{code:JSON.parse(sessionStorage.getItem('5bmath-room')).code}),document.baseURI).href),
async 'leave-room'() {
            if (sessionStorage.getItem('5bmath-room')) await arenaRequest('leave');
            sessionStorage.removeItem('5bmath-room');
            overlay('');document.querySelector('#waiting-popup')?.remove();ctx.go('arena');
        },
async 'leave-battle'() {
            if(!ctx.currentBattle)return;
            if (ctx.currentBattle.mode === 'bot') {
                finishBattle({...ctx.currentBattle,outcome:'left',rounds:ctx.currentBattle.index,points:0});
            } else {
                if(ctx.currentBattle.hp<=0||ctx.currentBattle.opponentHp<=0||ctx.currentBattle.resolved&&ctx.currentBattle.index>=ctx.currentBattle.questions.length-1){await pollRoom();return;}
                const battleId=ctx.currentBattle.id;
                ctx.host.showModal('<div class="arena-leave-confirm"><h2 class="modal-title">Em muốn rời trận?</h2><p class="modal-copy">Rời trận bây giờ sẽ tính là thua và trừ 1 kinh nghiệm. Đối thủ không nhận kinh nghiệm từ trận bỏ dở. Trận này không cộng vào số trận thắng/thua.</p><p class="modal-copy">Bỏ trận nhiều lần sẽ phải tạm nghỉ đấu với người.</p><div class="actions"><button type="button" class="btn dark" id="arena-continue-playing">Tiếp tục chơi</button><button type="button" class="btn outline" id="arena-confirm-leave">Rời trận</button></div></div>');
                document.querySelector('#arena-continue-playing').onclick=()=>document.querySelector('#modal').close();
                document.querySelector('#arena-confirm-leave').onclick=async event=>{
                    const control=event.currentTarget;control.disabled=true;
                    try{if(ctx.currentBattle?.id===battleId){const result=await arenaRequest('leave');document.querySelector('#modal').close();if(result.status==='finished')finishBattle(result.result);else await pollRoom();}}
                    catch(error){ctx.host.toast(error.message);}
                    finally{if(control.isConnected)control.disabled=false;}
                };
                const dialog=document.querySelector('#modal'),trap=event=>{
                    if(event.key!=='Tab')return;
                    const controls=[...dialog.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled)')].filter(node=>node.getClientRects().length),index=controls.indexOf(document.activeElement);
                    if(event.shiftKey&&index<=0){event.preventDefault();controls.at(-1)?.focus();}
                    else if(!event.shiftKey&&index===controls.length-1){event.preventDefault();controls[0]?.focus();}
                };
                dialog.addEventListener('keydown',trap);dialog.addEventListener('close',()=>dialog.removeEventListener('keydown',trap),{once:true});
                document.querySelector('#arena-continue-playing').focus();
            }
        }
};
return {views,actions,liveRank,loadRank,openArenaPreflight,battleTime,updateBattleTimer,updateBattleRound,emoteSeconds,updateEmoteControls,sendEmote,buildBotBattle,backupLegacyBot,startBot,ensureBotLease,setBotRoundTiming,persistBot,settleBotAttack,beginBotAttack,answerBot,tickBot,nextBot,challengeOpponent,finishBattle,arenaRequest,roomSettings,enterRoom,openRoomLink,overlay,countdown,ownPublicRoomCodes,loadPublicRooms,inlineChallenge,roomPopup,pollRoom,recordBotAttack,attackSpell,aimUltimateBeam,playHitSpell,animateHit,dispatchBattleHit,updateBattleVisuals,setArenaMode};
}
const api={create};(global.LearningFeatures??={})['arena']=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
