const app = document.getElementById('app');
const nav = document.getElementById('bottomNav');
window.addEventListener('popstate', render);
nav.addEventListener('click', e => { const b=e.target.closest('button'); if(b?.dataset.route) go(b.dataset.route); });
if('serviceWorker' in navigator){ window.addEventListener('load',()=>navigator.serviceWorker.register('/service-worker.js?v=6').catch(()=>{})); }

let currentSpeechRecognition = null;

function protect(){ if(!store.token){ go('/'); return false; } return true; }
function showNav(show=true){ nav.classList.toggle('hidden', !show); }
function logo(){ return `<div class="logo"><img src="/assets/logo.svg" alt="Clube do Inglês"></div>`; }
function card(content, extra=''){ return `<section class="card ${extra}">${content}</section>`; }
function escapeHtml(s){ return String(s ?? '').replace(/[&<>'"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function speak(text, lang='en-US'){
  if(!('speechSynthesis' in window)){ toast('Este navegador não suporta leitura por voz.', 'warn'); return; }
  speechSynthesis.cancel();
  const u=new SpeechSynthesisUtterance(text);
  u.lang=lang;
  u.rate=.9;
  speechSynthesis.speak(u);
}

function rewardSound(){
  try{
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    const ctx = new AudioCtx();
    [523.25,659.25,783.99].forEach((freq,i)=>{
      const osc=ctx.createOscillator(); const gain=ctx.createGain();
      osc.type='sine'; osc.frequency.value=freq;
      gain.gain.setValueAtTime(0.0001, ctx.currentTime+i*0.09);
      gain.gain.exponentialRampToValueAtTime(0.13, ctx.currentTime+i*0.09+0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime+i*0.09+0.22);
      osc.connect(gain); gain.connect(ctx.destination);
      osc.start(ctx.currentTime+i*0.09); osc.stop(ctx.currentTime+i*0.09+0.24);
    });
  }catch(e){}
}
function celebrate(text='Parabéns!'){
  rewardSound();
  const wrap=document.createElement('div');
  wrap.className='celebrate';
  wrap.innerHTML=`<div class="celebrate-card"><div class="celebrate-emoji">🎉</div><b>${escapeHtml(text)}</b><small>Você está evoluindo no Clube!</small></div>`;
  document.body.appendChild(wrap);
  for(let i=0;i<22;i++){
    const p=document.createElement('span'); p.className='confetti';
    p.style.left=(10+Math.random()*80)+'%'; p.style.animationDelay=(Math.random()*0.18)+'s';
    p.style.transform=`rotate(${Math.random()*180}deg)`; wrap.appendChild(p);
  }
  setTimeout(()=>wrap.remove(),1600);
}
function supportsSpeechRecognition(){ return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window; }

function isSecureForMic(){
  return location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1';
}
function micUnavailableMessage(){
  if(!isSecureForMic()){
    return 'Para usar o microfone, acesse pelo HTTPS: https://clube-do-ingles.4cloud.tech';
  }
  if(!supportsSpeechRecognition()){
    return 'Reconhecimento de voz não disponível neste navegador. Use Chrome/Android ou Chrome no computador.';
  }
  return null;
}
function startSpeechToInput(inputId, onFinal){
  const input = document.getElementById(inputId);
  const mic = document.getElementById('micBtn') || document.getElementById('voiceAnswerBtn');
  if(!input) return;
  const unavailable = micUnavailableMessage();
  if(unavailable){ toast(unavailable, 'warn'); return; }
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if(currentSpeechRecognition){ currentSpeechRecognition.stop(); currentSpeechRecognition = null; }
  const recognition = new SR();
  currentSpeechRecognition = recognition;
  recognition.lang = 'en-US';
  recognition.interimResults = true;
  recognition.continuous = false;
  let finalText = '';
  if(mic) mic.classList.add('mic-listening');
  recognition.onstart = () => toast('Estou ouvindo... fale uma frase curta em inglês.', 'success');
  recognition.onresult = (event) => {
    let interim = '';
    for(let i=event.resultIndex; i<event.results.length; i++){
      const text = event.results[i][0].transcript;
      if(event.results[i].isFinal) finalText += text;
      else interim += text;
    }
    input.value = (finalText || interim).trim();
  };
  recognition.onerror = (event) => {
    const msg = event?.error === 'not-allowed'
      ? 'Permissão do microfone bloqueada. Libere o microfone no navegador e tente novamente.'
      : 'Não consegui ouvir bem. Tente novamente mais perto do microfone.';
    toast(msg, 'warn');
  };
  recognition.onend = () => {
    if(mic) mic.classList.remove('mic-listening');
    currentSpeechRecognition = null;
    const value = input.value.trim();
    if(value && typeof onFinal === 'function') onFinal(value);
  };
  recognition.start();
}

function toggleTranslation(id){
  const el = document.getElementById(id);
  if(!el) return;
  const hidden = el.classList.toggle('translation-hidden');
  const btn = document.querySelector(`[data-translation-target="${id}"]`);
  if(btn) btn.textContent = hidden ? '🌍 Mostrar tradução' : '🙈 Ocultar tradução';
}

async function render(){
  const path = location.pathname;
  try {
    if(path.startsWith('/convite/')) return renderInvite(path.split('/').pop());
    if(path === '/' || path === '/login') return renderLogin();
    if(path.startsWith('/admin')) return renderAdmin();
    if(path === '/app') return renderDashboard();
    if(path === '/app/trilha') return renderTrail();
    if(path.startsWith('/app/aula/')) return renderLesson(path.split('/').pop());
    if(path === '/app/ranking') return renderRanking();
    if(path === '/app/perfil') return renderProfile();
    if(path === '/app/ia') return renderAI();
    return renderLogin();
  } catch(err){
    toast(err.message, 'error');
    if(String(err.message).includes('Token') || String(err.message).includes('401')) { store.clear(); go('/'); }
  }
}

function renderLogin(){
  showNav(false);
  app.innerHTML = `<div class="hero">
    <div>${logo()}<span class="badge">🌟 Web App/PWA</span><h1>Aprenda inglês conversando, jogando e evoluindo.</h1><p>Entre com o código da turma, nickname e senha. Sem e-mail, sem telefone e sem dados pessoais.</p></div>
    <section class="hero-card"><h2>Entrar no Clube</h2><form id="loginForm" class="form">
      <label>Código da turma</label><input name="class_code" value="HELENA2026" required>
      <label>Nickname</label><input name="nickname" value="Helena" required>
      <label>Senha</label><input name="password" type="password" value="helena123" required>
      <button class="btn">Entrar</button>
      <button type="button" class="btn secondary" id="adminBtn">Entrar como admin</button>
    </form></section></div>`;
  document.getElementById('adminBtn').onclick = async()=>{
    const data = await api('/auth/login',{method:'POST', body:JSON.stringify({class_code:'HELENA2026', nickname:'admin', password:'admin123'})});
    store.token=data.access_token; store.user=data.user; go('/admin');
  };
  document.getElementById('loginForm').onsubmit = async e => {
    e.preventDefault();
    const f=Object.fromEntries(new FormData(e.target));
    const data=await api('/auth/login',{method:'POST', body:JSON.stringify(f)});
    store.token=data.access_token; store.user=data.user;
    go(data.user.role==='admin'?'/admin':'/app');
  };
}

async function renderInvite(code){
  showNav(false);
  const invite = await api(`/invites/${code}`);
  app.innerHTML = `<div class="hero"><div>${logo()}<span class="badge">Convite</span><h1>Bem-vindo ao Clube do Inglês!</h1><p>Você está entrando na turma <b>${escapeHtml(invite.class_name)}</b>.</p><div class="safe-note">Use apenas seu primeiro nome. Não informe sobrenome, telefone, escola, endereço ou redes sociais.</div></div>
  <section class="hero-card"><h2>Criar acesso</h2><form id="inviteForm" class="form">
    <label>Primeiro nome</label><input name="first_name" placeholder="Helena" required>
    <label>Nickname para ranking</label><input name="nickname" placeholder="StarCat" required>
    <label>Avatar</label><select name="avatar"><option>🌟</option><option>🦊</option><option>🐱</option><option>🐼</option><option>🚀</option><option>🎧</option></select>
    <label>Senha</label><input name="password" type="password" required>
    <label>Confirmar senha</label><input name="confirm_password" type="password" required>
    <button class="btn">Entrar no clube</button>
  </form></section></div>`;
  document.getElementById('inviteForm').onsubmit = async e => { e.preventDefault(); const f=Object.fromEntries(new FormData(e.target)); const data=await api(`/auth/register-invite/${code}`,{method:'POST',body:JSON.stringify(f)}); store.token=data.access_token; store.user=data.user; go('/app'); };
}

async function renderDashboard(){
  if(!protect()) return; showNav(true);
  const d = await api('/student/dashboard');
  app.innerHTML = `<div class="topbar"><div class="title"><h1>Olá, ${escapeHtml(d.student.first_name)}! ${d.student.avatar||''}</h1><p>${escapeHtml(d.class?.name||'Sem turma')} · ${escapeHtml(d.student.level)}</p></div><button class="btn ghost" onclick="logout()">Sair</button></div>
  <section class="card mission"><div><span class="badge">🎯 Próxima missão</span>${d.mission?`<div class="big">${escapeHtml(d.mission.title)}</div><p class="translation">Pratique: <b>${escapeHtml(d.mission.phrase_en)}</b></p>`:'<div class="big">Trilha concluída!</div><p>Você concluiu todas as aulas disponíveis. Parabéns!</p>'}</div>${d.mission?`<button class="btn" onclick="go('/app/aula/${d.mission.lesson_id}')">Continuar</button>`:''}</section>
  <div class="grid cols-3">
    ${card(`<div class="stat"><div class="avatar">⚡</div><div><b>${d.student.total_xp}</b><span>XP total</span></div></div>`)}
    ${card(`<div class="stat"><div class="avatar">🔥</div><div><b>${d.student.streak_days}</b><span>dias de sequência</span></div></div>`)}
    ${card(`<div class="stat"><div class="avatar">✅</div><div><b>${d.progress.completed_lessons}/${d.progress.total_lessons}</b><span>aulas concluídas</span></div></div>`)}
  </div>
  ${card(`<h2>Progresso da trilha</h2><div class="progress"><div style="width:${d.progress.percent}%"></div></div><p>${d.progress.percent}% concluído</p>`)}
  <div class="grid cols-2"><button class="btn secondary" onclick="go('/app/trilha')">🗺️ Ver trilha</button><button class="btn secondary" onclick="go('/app/ia')">🎙️ Conversar por voz com IA</button></div>`;
}

function moduleIcon(title){
  const t = String(title).toLowerCase();
  if(t.includes('hello')) return '👋'; if(t.includes('about')) return '⭐'; if(t.includes('family')) return '👨‍👩‍👧'; if(t.includes('school')) return '🎒'; if(t.includes('food')) return '🍕'; if(t.includes('travel')) return '✈️'; return '🧭';
}

async function renderTrail(){
  if(!protect()) return; showNav(true);
  const modules = await api('/student/trail');
  const allLessons = modules.flatMap(m => m.lessons.map(l => ({...l, moduleTitle:m.title})));
  const next = allLessons.find(l => l.status !== 'completed') || allLessons[0];
  const completed = allLessons.filter(l=>l.status==='completed').length;
  const total = allLessons.length || 1;
  const percentAll = Math.round(completed/total*100);
  app.innerHTML = `<div class="topbar"><div class="title"><h1>Mapa da evolução</h1><p>Caminho A1 Beginner · avance de fase respondendo o quiz obrigatório</p></div></div>
  <section class="quest-banner">
    <div>
      <span class="badge">🧭 Jornada individual</span>
      <h2>${next ? `Próxima fase: ${escapeHtml(next.title)}` : 'Todas as fases concluídas!'}</h2>
      <p>${next ? escapeHtml(next.phrase_en||'') : 'Você completou a trilha disponível. Hora de revisar e conversar com a Luma!'}</p>
    </div>
    <div class="quest-progress"><strong>${percentAll}%</strong><span>${completed}/${total} fases</span></div>
    ${next ? `<button class="btn" onclick="go('/app/aula/${next.id}')">🚀 Continuar</button>` : `<button class="btn" onclick="go('/app/ia')">🤖 Falar com a Luma</button>`}
  </section>
  <div class="map-road">${modules.map((m, mi)=>{
    const done = m.lessons.filter(l=>l.status==='completed').length;
    const totalM = m.lessons.length || 1;
    const percent = Math.round(done/totalM*100);
    const status = percent===100 ? 'done' : done>0 ? 'active' : (mi===0 || modules[mi-1]?.lessons?.some(l=>l.status==='completed') ? 'open' : 'locked');
    return `<section class="world-card ${status}">
      <div class="world-top">
        <div class="world-badge">${moduleIcon(m.title)}</div>
        <div><h2>${escapeHtml(m.title)}</h2><p>${escapeHtml(m.description||'')}</p></div>
        <span class="world-status">${status==='done'?'✅ Concluído':status==='active'?'▶ Em andamento':status==='locked'?'🔒 Em breve':'✨ Disponível'}</span>
      </div>
      <div class="progress"><div style="width:${percent}%"></div></div>
      <div class="stage-list">${m.lessons.map((l,idx)=>{
        const isNext = l.id===next?.id;
        const cls = l.status==='completed'?'done':isNext?'next':'open';
        return `<button class="stage ${cls}" onclick="go('/app/aula/${l.id}')">
          <span class="stage-dot">${l.status==='completed'?'✓':idx+1}</span>
          <span><b>${escapeHtml(l.title)}</b><small>${escapeHtml(l.phrase_en||'')}</small></span>
          <em>${l.status==='completed'?'XP ganho':isNext?'Próxima missão':'Quiz obrigatório'}</em>
        </button>`;
      }).join('')}</div>
    </section>`;
  }).join('')}</div>`;
}

async function renderLesson(id){
  if(!protect()) return; showNav(true);
  const l = await api(`/lessons/${id}`);
  const stepPercent = Math.round((l.position / Math.max(l.total_in_module,1)) * 100);
  app.innerHTML = `<div class="lesson-shell">
    <div class="lesson-toolbar"><button class="btn secondary" ${!l.previous_id?'disabled':''} onclick="${l.previous_id?`go('/app/aula/${l.previous_id}')`:''}">← Anterior</button><span class="step-pill">${escapeHtml(l.module_title)} · Aula ${l.position}/${l.total_in_module}</span><button class="btn secondary" ${!l.next_id?'disabled':''} onclick="${l.next_id?`go('/app/aula/${l.next_id}')`:''}">Próxima →</button></div>
    <div class="progress"><div style="width:${stepPercent}%"></div></div>
    ${card(`<div class="topbar compact"><div class="title"><h1>${escapeHtml(l.title)}</h1><p>${escapeHtml(l.objective||'')}</p></div>${l.status==='completed'?`<span class="lesson-status completed">Concluída</span>`:''}</div><div class="phrase">${escapeHtml(l.phrase_en)}</div><div class="translation-tools"><button class="btn secondary btn-small" data-translation-target="mainTranslation" onclick="toggleTranslation('mainTranslation')">🌍 Mostrar tradução</button><button class="btn secondary btn-small" onclick="speak('${escapeHtml(l.phrase_en).replace(/'/g,"\'")}')">🔊 Ouvir</button></div><p class="translation translation-hidden" id="mainTranslation">${escapeHtml(l.phrase_pt)}</p><div class="example-box"><p><b>Exemplo:</b> ${escapeHtml(l.example_en)}</p><button class="btn secondary btn-small" data-translation-target="exampleTranslation" onclick="toggleTranslation('exampleTranslation')">🌍 Mostrar tradução</button><p class="translation translation-hidden" id="exampleTranslation">${escapeHtml(l.example_pt)}</p></div><div class="lesson-actions"><button class="btn" onclick="loadQuiz(${l.id})">🧩 Fazer desafio</button>${l.status==='completed' && l.next_id ? `<button class="btn success" onclick="go('/app/aula/${l.next_id}')">🚀 Próxima aula</button>`:''}</div><p class="translation">Resolva o desafio para avançar. Quando acertar, você segue automaticamente para a próxima missão.</p>`, 'lesson-hero')}
    <div id="quizBox"></div>
  </div>`;
  loadQuiz(l.id);
}

async function completeLesson(id, autoNext=false){
  try {
    const r=await api(`/lessons/${id}/complete`,{method:'POST',body:'{}'});
    if(autoNext && r.next_id){
      toast(r.points ? `Aula concluída! +${r.points} XP` : 'Aula concluída!', 'success');
      setTimeout(()=>go(`/app/aula/${r.next_id}`), 1200);
      return;
    }
    showModalFeedback('ok', '✅ Aula concluída!', r.points ? `Você ganhou +${r.points} XP.` : 'Essa aula já estava concluída.', 'Agora você pode seguir para a próxima missão.', r.next_id);
  } catch(e){
    toast(e.message, 'warn');
    loadQuiz(id);
  }
}

async function loadQuiz(id){
  const q=await api(`/lessons/${id}/quiz`);
  document.getElementById('quizBox').innerHTML = card(`<div class="quiz-header"><div><span class="badge">🧩 Desafio rápido</span><h2>${escapeHtml(q.question)}</h2><p class="translation">${escapeHtml(q.hint||'')}</p></div></div><div class="options">${Object.entries(q.options).map(([k,v])=>`<button class="option" id="opt-${k}" onclick="answerQuiz(${id}, '${k}')"><b>${k}</b> ${escapeHtml(v)}</button>`).join('')}</div><div id="quizFeedback"></div>`, 'quiz-panel');
}

async function answerQuiz(id, answer){
  const r=await api(`/lessons/${id}/quiz/answer`,{method:'POST',body:JSON.stringify({answer})});
  document.querySelectorAll('.option').forEach(o => o.disabled = true);
  const selected = document.getElementById(`opt-${r.selected_option}`);
  const correct = document.getElementById(`opt-${r.correct_option}`);
  if(selected) selected.classList.add(r.correct ? 'correct' : 'wrong');
  if(correct) correct.classList.add('correct');
  const box = document.getElementById('quizFeedback');
  box.innerHTML = `<div class="feedback ${r.correct?'ok':'err'}"><h3>${r.correct?'🎉 Parabéns!':'😅 Quase isso!'}</h3><p>${escapeHtml(r.feedback_message)}</p>${!r.correct?`<p><b>Você marcou:</b> ${escapeHtml(r.selected_option)} — ${escapeHtml(r.selected_text)}</p>`:''}<p><b>Resposta correta:</b> ${escapeHtml(r.correct_option)} — ${escapeHtml(r.correct_text)}</p><p class="translation">${escapeHtml(r.explanation||'')}</p>${r.points?`<span class="xp">+${r.points} XP</span>`:''}<div style="margin-top:14px; display:flex; gap:10px; flex-wrap:wrap;">${r.correct?`<span class="badge">🚀 Indo para a próxima missão...</span>`:`<button class="btn" onclick="loadQuiz(${id})">Tentar novamente</button>`}<button class="btn secondary" onclick="speak('${escapeHtml(r.correct_text).replace(/'/g,"\'")}')">🔊 Ouvir correta</button></div></div>`;
  if(r.correct){
        toast(r.points ? `Parabéns! +${r.points} XP` : 'Parabéns! Resposta correta.', 'success');
    celebrate('Quiz correto!');
    setTimeout(()=>completeLesson(id, true), 1700);
  } else {
    document.querySelectorAll('.option').forEach(o => o.disabled = false);
    toast('Quase! Veja a explicação e tente de novo.', 'warn');
  }
}

function showModalFeedback(type, title, message, sub, nextId){
  const html = `<div class="feedback ${type==='ok'?'ok':'err'}"><h3>${escapeHtml(title)}</h3><p>${escapeHtml(message)}</p><p class="translation">${escapeHtml(sub||'')}</p><div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:12px;">${nextId?`<button class="btn" onclick="go('/app/aula/${nextId}')">Próxima aula</button>`:''}<button class="btn secondary" onclick="go('/app/trilha')">Voltar para trilha</button></div></div>`;
  const box = document.getElementById('quizBox');
  if(box) box.innerHTML = card(html);
  toast(message, type==='ok'?'success':'warn');
}

async function renderRanking(){
  if(!protect()) return; showNav(true);
  const weekly = await api('/student/ranking?kind=weekly'); const general = await api('/student/ranking?kind=general');
  app.innerHTML = `<div class="topbar"><div class="title"><h1>Ranking</h1><p>Competição saudável: somente nickname, avatar e XP.</p></div></div>
  ${card(`<h2>🏆 Semanal</h2><div class="grid">${weekly.map(r=>`<div class="ranking-row"><b>#${r.position}</b><span>${r.avatar||'⭐'} ${escapeHtml(r.nickname)}</span><b>${r.xp} XP</b></div>`).join('')||'<p>Sem pontuação ainda.</p>'}</div>`)}
  ${card(`<h2>🌍 Geral</h2><div class="grid">${general.map(r=>`<div class="ranking-row"><b>#${r.position}</b><span>${r.avatar||'⭐'} ${escapeHtml(r.nickname)}</span><b>${r.xp} XP</b></div>`).join('')||'<p>Sem pontuação ainda.</p>'}</div>`)};`;
}

async function renderProfile(){
  if(!protect()) return; showNav(true);
  const p = await api('/student/profile');
  app.innerHTML = `<div class="topbar"><div class="title"><h1>Meu perfil</h1><p>${escapeHtml(p.class||'')}</p></div></div>
  ${card(`<div class="stat"><div class="avatar">${p.avatar||'⭐'}</div><div><b>${escapeHtml(p.nickname)}</b><span>${escapeHtml(p.first_name)} · ${escapeHtml(p.level)}</span></div></div><hr><p><b>XP total:</b> ${p.total_xp}</p><p><b>Aulas concluídas:</b> ${p.lessons_completed}</p><p><b>Conversas com IA:</b> ${p.ai_conversations}</p><p><b>Sequência:</b> ${p.streak_days} dias</p><button class="btn danger" onclick="logout()">Sair</button>`)};`;
}

async function renderAI(){
  if(!protect()) return; showNav(true);
  const params = new URLSearchParams(location.search);
  const lessonId = params.get('lesson') || '';
  const micWarn = micUnavailableMessage();
  app.innerHTML = `<div class="topbar"><div class="title"><h1>Conversa com a Luma</h1><p>Modo voz: a Luma fala, você responde, e ela corrige com carinho.</p></div></div>
  ${card(`<div class="ai-stage voice-first">
    <div class="luma-hero">
      <img class="robot-avatar-img big-luma" src="/assets/luma.svg" alt="Luma, robô professora">
      <div>
        <span class="badge">🤖 Luma · robô professora</span>
        <h2>Vamos conversar em inglês?</h2>
        <p class="translation">Aperte “Iniciar conversa”. A Luma vai falar com você. Depois responda por voz ou escreva.</p>
      </div>
    </div>
    ${micWarn ? `<div class="safe-note">🎙️ ${escapeHtml(micWarn)}</div>` : `<div class="voice-ready">🎙️ Microfone pronto. Use frases curtas em inglês.</div>`}
    <div class="ai-context">
      <div class="context-pill">🎯 Cena: você conhece uma amiga em Londres.</div>
      <div class="context-pill">🗣️ Responda com frases simples.</div>
      <div class="context-pill">✨ A Luma fala e depois escuta você.</div>
    </div>
    <div class="luma-control-panel">
      <button class="btn luma-start" id="startVoiceLesson">▶️ Iniciar conversa</button>
      <button class="btn secondary" id="hearLastBtn">🔊 Ouvir Luma de novo</button>
      <button class="btn secondary" id="voiceAnswerBtn">🎙️ Responder por voz</button>
    </div>
    <div id="chat" class="chat voice-chat">
      <div class="msg ai robot"><div class="msg-head"><img class="robot-mini-img" src="/assets/luma.svg" alt=""><b>Luma</b></div><span id="lastLumaText">Hello, explorer! I’m Luma. What is your name?</span><br><small>Toque em “Iniciar conversa” para me ouvir.</small></div>
    </div>
    <div class="chat-input typed-fallback"><input id="chatText" placeholder="Ou escreva sua resposta em inglês..." autocomplete="off"><button class="btn" id="sendChat">Enviar</button></div>
    <input type="hidden" id="chatLessonId" value="${lessonId}">
  </div>`)};`;
  const first = "Hello, explorer! I am Luma. What is your name?";
  window.lastLumaSpeech = first;
  document.getElementById('sendChat').onclick = sendChat;
  document.getElementById('startVoiceLesson').onclick = () => { speak(first); setTimeout(()=>startSpeechToInput('chatText', ()=>sendChat()), 1400); };
  document.getElementById('hearLastBtn').onclick = () => speak(window.lastLumaSpeech || first);
  document.getElementById('voiceAnswerBtn').onclick = () => startSpeechToInput('chatText', ()=>sendChat());
  document.getElementById('chatText').addEventListener('keydown', e=>{ if(e.key==='Enter') sendChat(); });
}

async function sendChat(){
  const input=document.getElementById('chatText'); const msg=input.value.trim(); if(!msg) return;
  const lessonId = document.getElementById('chatLessonId')?.value || null;
  const chat=document.getElementById('chat'); chat.innerHTML += `<div class="msg me">${escapeHtml(msg)}</div>`; input.value='';
  const r=await api('/ai/chat',{method:'POST', body:JSON.stringify({lesson_id: lessonId ? Number(lessonId) : null, message:msg})});
  const spoken = `${r.feedback || ''}. ${r.correction ? 'Try saying: ' + r.correction + '. ' : ''}${r.next_question || ''}`.trim();
  window.lastLumaSpeech = spoken;
  let html = `<div class="msg-head"><img class="robot-mini-img" src="/assets/luma.svg" alt=""><b>Luma</b></div>`;
  html += `<div class="voice-response">🔊 ${escapeHtml(r.feedback)}</div>`;
  if(r.correction) html += `<div class="robot-tip"><b>Tente assim:</b> ${escapeHtml(r.correction)}</div>`;
  if(r.explanation_pt) html += `<small>${escapeHtml(r.explanation_pt)}</small>`;
  html += `<div class="robot-question"><b>Agora responda:</b> ${escapeHtml(r.next_question)}</div>`;
  if(r.points) toast(`+${r.points} XP por conversar com a IA!`, 'success');
  chat.innerHTML += `<div class="msg ai robot">${html}<div style="margin-top:10px; display:flex; gap:10px; flex-wrap:wrap;"><button class="btn secondary" onclick="speak(window.lastLumaSpeech)">🔊 Ouvir</button><button class="btn secondary" onclick="startSpeechToInput('chatText', ()=>sendChat())">🎙️ Responder</button></div></div>`;
  chat.scrollTop=chat.scrollHeight;
  speak(spoken);
}

async function renderAdmin(){
  if(!protect()) return; showNav(false);
  const user=store.user; if(user?.role!=='admin'){ app.innerHTML=card('<h1>Acesso restrito</h1><button class="btn" onclick="go(\'/app\')">Voltar</button>'); return; }
  const d=await api('/admin/dashboard'); const classes=await api('/admin/classes'); const students=await api('/admin/students');
  app.innerHTML = `${logo()}<div class="topbar"><div class="title"><h1>Painel admin</h1><p>Gerencie turmas, convites e alunos.</p></div><button class="btn ghost" onclick="logout()">Sair</button></div>
  <div class="grid cols-3">${card(`<b>${d.students}</b><p>Alunos</p>`)}${card(`<b>${d.classes}</b><p>Turmas ativas</p>`)}${card(`<b>${d.xp_total}</b><p>XP gerado</p>`)}</div>
  ${card(`<h2>Nova turma</h2><form id="classForm" class="form"><input name="name" placeholder="Nome da turma" required><input name="code" placeholder="Código ex: HELENA2026" required><input name="level" value="A1 Beginner"><button class="btn">Criar turma</button></form>`)}
  ${card(`<h2>Turmas</h2><table class="table"><thead><tr><th>Nome</th><th>Código</th><th>Alunos</th><th>Convite</th></tr></thead><tbody>${classes.map(c=>`<tr><td>${escapeHtml(c.name)}</td><td>${escapeHtml(c.code)}</td><td>${c.students}</td><td><button class="btn secondary" onclick="makeInvite(${c.id})">Gerar</button></td></tr>`).join('')}</tbody></table>`)}
  ${card(`<h2>Alunos</h2><table class="table"><thead><tr><th>Nome</th><th>Nickname</th><th>Turma</th><th>XP</th></tr></thead><tbody>${students.map(s=>`<tr><td>${escapeHtml(s.first_name)}</td><td>${escapeHtml(s.nickname)}</td><td>${escapeHtml(s.class_name)}</td><td>${s.total_xp}</td></tr>`).join('')}</tbody></table>`)};`;
  document.getElementById('classForm').onsubmit = async e=>{ e.preventDefault(); const f=Object.fromEntries(new FormData(e.target)); await api('/admin/classes',{method:'POST',body:JSON.stringify(f)}); toast('Turma criada!', 'success'); renderAdmin(); };
}
async function makeInvite(id){ const r=await api(`/admin/classes/${id}/invite`,{method:'POST',body:'{}'}); const full=location.origin + r.link; await navigator.clipboard?.writeText(full).catch(()=>{}); toast(`Convite gerado/copiadо: ${full}`, 'success'); }
function logout(){ store.clear(); go('/'); }
render();
