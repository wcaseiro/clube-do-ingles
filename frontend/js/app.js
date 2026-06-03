const app = document.getElementById('app');
const nav = document.getElementById('bottomNav');
window.addEventListener('popstate', render);
nav.addEventListener('click', e => { const b=e.target.closest('button'); if(b?.dataset.route) go(b.dataset.route); });
if('serviceWorker' in navigator){ window.addEventListener('load',()=>navigator.serviceWorker.register('/service-worker.js?v=8').catch(()=>{})); }

let currentSpeechRecognition = null;

function protect(){ if(!store.token){ go('/'); return false; } return true; }
function showNav(show=true){ nav.classList.toggle('hidden', !show); }
function logo(){ return `<div class="logo"><img src="/assets/logo.svg" alt="Clube do Inglês"></div>`; }
function card(content, extra=''){ return `<section class="card ${extra}">${content}</section>`; }
function escapeHtml(s){ return String(s ?? '').replace(/[&<>'"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])); }
function getVoiceRate(){ return localStorage.getItem('voice_rate') === 'slow' ? 0.68 : 0.92; }
function setVoiceRate(rate){ localStorage.setItem('voice_rate', rate); document.querySelectorAll('[data-rate]').forEach(b => b.classList.toggle('active', b.dataset.rate === rate)); toast(rate === 'slow' ? 'Velocidade lenta ativada.' : 'Velocidade normal ativada.', 'success'); }
function speak(text, lang='en-US'){
  if(!('speechSynthesis' in window)){ toast('Este navegador não suporta leitura por voz.', 'warn'); return; }
  speechSynthesis.cancel(); const u=new SpeechSynthesisUtterance(text); u.lang=lang; u.rate=getVoiceRate(); u.pitch=1.08; speechSynthesis.speak(u); animateLumaSpeaking();
}
function animateLumaSpeaking(){ document.querySelectorAll('.robot-avatar-img,.big-luma').forEach(el => { el.classList.add('talking'); setTimeout(()=>el.classList.remove('talking'), 1400); }); }

function rewardSound(){
  playToneSequence([523.25,659.25,783.99], 'sine', 0.12);
}

function correctionSound(){
  playToneSequence([392,329.63], 'triangle', 0.09);
}

function playToneSequence(freqs, type='sine', volume=0.1){
  try{
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    const ctx = new AudioCtx();
    freqs.forEach((freq,i)=>{
      const osc=ctx.createOscillator(); const gain=ctx.createGain();
      osc.type=type; osc.frequency.value=freq;
      const t = ctx.currentTime+i*0.11;
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(volume, t+0.025);
      gain.gain.exponentialRampToValueAtTime(0.0001, t+0.24);
      osc.connect(gain); gain.connect(ctx.destination);
      osc.start(t); osc.stop(t+0.26);
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
  if(!isSecureForMic()) return 'Para usar o microfone, acesse pelo HTTPS: https://clube-do-ingles.4cloud.tech:8083';
  if(!supportsSpeechRecognition()) return 'Reconhecimento de voz não disponível neste navegador. Use Chrome/Android ou Chrome no computador.';
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
  recognition.continuous = true;

  let finalText = '';
  let interimText = '';
  let silenceTimer = null;
  let alreadySent = false;
  const silenceMs = Number(localStorage.getItem('voice_silence_ms') || 2400);

  function scheduleStop(){
    clearTimeout(silenceTimer);
    silenceTimer = setTimeout(()=>{
      try { recognition.stop(); } catch(e){}
    }, silenceMs);
  }

  if(mic) mic.classList.add('mic-listening');
  recognition.onstart = () => toast('Estou ouvindo... fale a frase completa. Eu espero você terminar.', 'success');

  recognition.onresult = (event) => {
    interimText = '';
    for(let i=event.resultIndex; i<event.results.length; i++){
      const text = event.results[i][0].transcript;
      if(event.results[i].isFinal){
        finalText += (finalText ? ' ' : '') + text.trim();
      } else {
        interimText += text;
      }
    }
    input.value = (finalText + ' ' + interimText).trim();
    scheduleStop();
  };

  recognition.onerror = (event) => {
    clearTimeout(silenceTimer);
    const msg = event?.error === 'not-allowed'
      ? 'Permissão do microfone bloqueada. Libere o microfone no navegador e tente novamente.'
      : 'Não consegui ouvir bem. Tente novamente mais perto do microfone.';
    toast(msg, 'warn');
  };

  recognition.onend = () => {
    clearTimeout(silenceTimer);
    if(mic) mic.classList.remove('mic-listening');
    currentSpeechRecognition = null;
    const value = input.value.trim();
    if(value && !alreadySent && typeof onFinal === 'function'){
      alreadySent = true;
      setTimeout(()=>onFinal(value), 250);
    }
  };

  recognition.start();
  scheduleStop();
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
  store.clear();
  app.innerHTML = `<div class="hero">
    <div>${logo()}<span class="badge">🌟 Web App/PWA</span><h1>Aprenda inglês conversando, jogando e evoluindo.</h1><p>Entre com o código da turma, nickname e senha. Sem e-mail, sem telefone e sem dados pessoais.</p></div>
    <section class="hero-card"><h2>Entrar no Clube</h2><form id="loginForm" class="form" autocomplete="off">
      <label>Código da turma</label><input name="class_code" inputmode="text" placeholder="Ex: HELENA2026" autocomplete="off" autocapitalize="characters" spellcheck="false" required>
      <label>Nickname</label><input name="nickname" placeholder="Seu nickname" autocomplete="off" autocapitalize="off" spellcheck="false" required>
      <label>Senha</label><input name="password" type="password" placeholder="Sua senha" autocomplete="new-password" required>
      <button class="btn">Entrar</button>
      <p class="safe-note mini">Os campos não vêm mais preenchidos automaticamente pelo app. Se aparecerem preenchidos, é o gerenciador de senhas do navegador.</p>
    </form></section></div>`;
  document.getElementById('loginForm').onsubmit = async e => {
    e.preventDefault();
    const f=Object.fromEntries(new FormData(e.target));
    f.class_code = String(f.class_code || '').trim().toUpperCase();
    f.nickname = String(f.nickname || '').trim();
    const data=await api('/auth/login',{method:'POST', body:JSON.stringify(f)});
    store.token=data.access_token; store.user=data.user;
    go(data.user.role==='admin'?'/admin':'/app');
  };
}

async function renderInvite(code){
  showNav(false);
  store.clear();
  const invite = await api(`/invites/${code}`);
  if(!invite.is_active){
    app.innerHTML = `<div class="hero"><div>${logo()}<span class="badge">Convite</span><h1>Convite indisponível</h1><p>Este convite está inativo ou expirado.</p></div></div>`;
    return;
  }
  app.innerHTML = `<div class="hero"><div>${logo()}<span class="badge">Convite</span><h1>Bem-vindo ao Clube do Inglês!</h1><p>Você está entrando na turma <b>${escapeHtml(invite.class_name)}</b>.</p><div class="safe-note">Use apenas seu primeiro nome. Não informe sobrenome, telefone, escola, endereço ou redes sociais.</div></div>
  <section class="hero-card"><h2>Criar acesso</h2><form id="inviteForm" class="form" autocomplete="off">
    <label>Turma</label><input name="class_view" value="${escapeHtml(invite.class_code || invite.class_name)}" readonly class="readonly-input" autocomplete="off">
    <label>Primeiro nome</label><input name="first_name" placeholder="Ex: Helena" autocomplete="off" autocapitalize="words" required>
    <label>Nickname para ranking</label><input name="nickname" placeholder="Ex: StarCat" autocomplete="off" autocapitalize="off" spellcheck="false" required>
    <small class="form-hint">Use um apelido amigável. Nicknames ofensivos são bloqueados automaticamente.</small>
    <label>Avatar</label><select name="avatar"><option>🌟</option><option>🦊</option><option>🐱</option><option>🐼</option><option>🚀</option><option>🎧</option></select>
    <label>Senha</label><input name="password" type="password" autocomplete="new-password" required>
    <label>Confirmar senha</label><input name="confirm_password" type="password" autocomplete="new-password" required>
    <button class="btn">Criar e entrar direto</button>
  </form></section></div>`;
  document.getElementById('inviteForm').onsubmit = async e => {
    e.preventDefault();
    const f=Object.fromEntries(new FormData(e.target));
    delete f.class_view;
    f.first_name = String(f.first_name || '').trim();
    f.nickname = String(f.nickname || '').trim();
    if(isOffensiveNickname(f.nickname)){ toast('Escolha um nickname amigável para o ranking.', 'warn'); return; }
    const data=await api(`/auth/register-invite/${code}`,{method:'POST',body:JSON.stringify(f)});
    store.token=data.access_token; store.user=data.user;
    toast('Cadastro criado! Entrando na turma...', 'success');
    go('/app');
  };
}

function isOffensiveNickname(nickname=''){
  const map = {'0':'o','1':'i','3':'e','4':'a','5':'s','7':'t','8':'b','@':'a','$':'s','!':'i'};
  const norm = String(nickname).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[0134578@$!]/g, c=>map[c]||c).replace(/[^a-z0-9]/g,'');
  const blocked = ['puta','puto','caralho','karalho','porra','merda','bosta','buceta','xota','piroca','rola','sexo','sex','porn','porno','xxx','nude','nudes','foda','fodase','fdp','filhodaputa','arrombado','otario','idiota','burro','babaca','hitler','nazista','nazi','racista','terrorista','fuck','shit','bitch','asshole','dick','pussy'];
  return blocked.some(w => norm.includes(w));
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

function renderRankingList(rows, empty='Sem pontuação ainda.'){
  return rows.map(r=>`<div class="ranking-row ranking-row-evo">
    <b>#${r.position}</b>
    <span class="ranking-player">
      <span class="ranking-avatar">${r.evolution_avatar || r.avatar || '⭐'}</span>
      <span><b>${escapeHtml(r.nickname)}</b><small>${escapeHtml(r.evolution_name || 'Explorador')}</small></span>
    </span>
    <b>${r.xp} pts</b>
  </div>`).join('') || `<p>${empty}</p>`;
}

async function renderRanking(){
  if(!protect()) return; showNav(true);
  const [weekly, general, trail, conversation] = await Promise.all([
    api('/student/ranking?kind=weekly'),
    api('/student/ranking?kind=general'),
    api('/student/ranking?kind=trail').catch(()=>[]),
    api('/student/ranking?kind=conversation').catch(()=>[])
  ]);

  app.innerHTML = `<div class="topbar"><div class="title"><h1>Ranking</h1><p>Competição saudável: trilha, conversação e evolução de avatar.</p></div></div>

  ${card(`<h2>🧭 Score por trilha</h2>
    <p class="muted">Pontuação das aulas, quizzes e desafios concluídos.</p>
    <div class="grid">${renderRankingList(trail)}</div>`)}

  ${card(`<h2>🤖 Score por conversação</h2>
    <p class="muted">Pontuação baseada nas conversas com a Luma.</p>
    <div class="grid">${renderRankingList(conversation)}</div>`)}

  ${card(`<h2>🏆 Semanal</h2><div class="grid">${renderRankingList(weekly)}</div>`)}

  ${card(`<h2>🌍 Geral</h2><div class="grid">${renderRankingList(general)}</div>
    <div class="avatar-evolution-note">
      <b>Avatares evolutivos:</b> ao juntar XP, novos avatares são liberados automaticamente: 🤖 → 🛸 → 🚀 → 🦾 → 🌟 → 👑
    </div>`)}
  `;
}

async function renderProfile(){
  if(!protect()) return; showNav(true);
  const p = await api('/student/profile');
  app.innerHTML = `<div class="topbar"><div class="title"><h1>Meu perfil</h1><p>${escapeHtml(p.class||'')}</p></div></div>
  ${card(`<div class="stat"><div class="avatar">${p.avatar||'⭐'}</div><div><b>${escapeHtml(p.nickname)}</b><span>${escapeHtml(p.first_name)} · ${escapeHtml(p.level)}</span></div></div><hr><p><b>XP total:</b> ${p.total_xp}</p><p><b>Aulas concluídas:</b> ${p.lessons_completed}</p><p><b>Conversas com IA:</b> ${p.ai_conversations}</p><p><b>Sequência:</b> ${p.streak_days} dias</p><button class="btn danger" onclick="logout()">Sair</button>`)};`;
}


function getLumaStatus(resp){
  const status = String(resp?.status || '').toLowerCase();
  if(resp?.needs_repeat || status === 'repeat'){
    return {
      type: 'warn',
      badge: '🟡 Preciso de mais uma tentativa',
      title: 'Quase! A Luma precisa que você tente de novo.'
    };
  }

  if(resp && resp.correction){
    return {
      type: 'warn',
      badge: '🟡 Vamos ajustar',
      title: 'Eu entendi sua ideia, mas vamos melhorar a frase.'
    };
  }

  return {
    type: 'ok',
    badge: '✅ Entendi você',
    title: 'Muito bem! Sua resposta foi entendida.'
  };
}

function renderAIUsage(usage){
  if(!usage) return '<div id="aiUsage" class="ai-usage loading"><span>Uso diário da Luma</span><div class="ai-usage-bar"><i style="width:0%"></i></div></div>';
  const limit = Number(usage.limit_today ?? 20);
  const used = Number(usage.used_today ?? 0);
  const percent = Math.max(0, Math.min(100, Number(usage.usage_percent ?? (limit ? used / limit * 100 : 0))));
  const provider = escapeHtml(usage.provider || 'ia');
  const danger = percent >= 85 ? ' danger' : '';
  const label = percent >= 85 ? 'Quase no limite de hoje' : percent >= 50 ? 'Bom treino hoje' : 'Pronto para conversar';
  return `<div id="aiUsage" class="ai-usage${danger}">
    <div class="ai-usage-top"><span>💬 Uso diário da Luma</span><small>${provider}</small></div>
    <div class="ai-usage-bar" title="${used}/${limit} interações usadas"><i style="width:${percent}%"></i></div>
    <small>${label}</small>
  </div>`;
}

function updateLumaUsage(resp){
  const box = document.getElementById('aiUsage');
  if(!box || typeof resp?.used_today !== 'number') return;
  const limit = Number(resp.limit_today ?? 20);
  const used = Number(resp.used_today ?? 0);
  const percent = Math.max(0, Math.min(100, Number(resp.usage_percent ?? (limit ? used / limit * 100 : 0))));
  const source = escapeHtml(resp.source || resp.provider || 'ia');
  const danger = percent >= 85 ? ' danger' : '';
  const label = percent >= 85 ? 'Quase no limite de hoje' : percent >= 50 ? 'Bom treino hoje' : 'Pronto para conversar';
  box.className = `ai-usage${danger}`;
  box.innerHTML = `<div class="ai-usage-top"><span>💬 Uso diário da Luma</span><small>${source}</small></div>
    <div class="ai-usage-bar" title="${used}/${limit} interações usadas"><i style="width:${percent}%"></i></div>
    <small>${label}</small>`;
}

function renderUserBubble(text){
  return `
    <div class="ai-row user">
      <div class="ai-bubble-user">
        <b>Você:</b> ${escapeHtml(text)}
      </div>
    </div>
  `;
}

function shouldShowExplanation(resp){
  const txt = String(resp?.explanation_pt || '').trim();
  if(!txt) return false;
  if(!resp?.correction && !resp?.needs_repeat){
    const low = txt.toLowerCase();
    if(low.includes('perfeita') || low.includes('foi entendida') || low.includes('fez sentido')) return false;
  }
  return true;
}

function renderLumaCard(resp, originalText=''){
  resp = resp || {};
  const status = getLumaStatus(resp);
  const feedback = resp.feedback || status.title;
  const explanation = resp.explanation_pt || '';
  const nextQuestion = resp.next_question || 'Can you try again?';
  const correction = resp.correction || '';
  const source = resp.source || '';
  const fallback = Boolean(resp.fallback);

  const originalBlock = (correction || resp.needs_repeat) && originalText ? `
    <div class="luma-block original">
      <small>💬 Sua frase</small>
      <strong>${escapeHtml(originalText)}</strong>
    </div>
  ` : '';

  const correctionBlock = correction ? `
    <div class="luma-block correction">
      <small>🛠️ Tente assim</small>
      <strong>${escapeHtml(correction)}</strong>
    </div>
  ` : '';

  const explainBlock = shouldShowExplanation(resp) ? `
    <div class="luma-explain ${status.type}">
      <b>${status.type === 'warn' ? '📚 Por quê?' : '✨ Dica rápida'}</b><br>
      ${escapeHtml(explanation)}
    </div>
  ` : '';

  const nextLabel = correction || resp.needs_repeat ? '🔁 Tente responder essa missão' : '🎯 Próxima missão';
  const sourceChip = source ? `<span class="luma-source ${fallback ? 'fallback' : ''}">${fallback ? 'modo local' : source}</span>` : '';

  return `
    <div class="ai-row luma">
      <div class="luma-card ${status.type}" data-speak="${escapeHtml(`${feedback}. ${correction ? 'Try saying: ' + correction + '. ' : ''}${nextQuestion}`)}">
        <div class="luma-head">
          <div class="luma-head-left">
            <img src="/assets/luma-avatar.png" class="luma-avatar-mini" alt="Luma">
            <div>
              <div class="luma-name">Luma</div>
              <div class="luma-subtitle">Professora de inglês</div>
            </div>
          </div>
          <div class="luma-head-badges">
            ${sourceChip}
            <div class="luma-badge ${status.type}">${status.badge}</div>
          </div>
        </div>

        <div class="luma-feedback">${escapeHtml(feedback)}</div>

        ${originalBlock}
        ${correctionBlock}
        ${explainBlock}

        <div class="luma-block next">
          <small>${nextLabel}</small>
          <strong>${escapeHtml(nextQuestion)}</strong>
        </div>

        <div class="luma-actions">
          <button class="luma-btn-small" onclick="speakLumaMessage(this)">🔊 Ouvir</button>
        </div>
      </div>
    </div>
  `;
}

function renderLumaStartCard(){
  return `
    <div class="ai-row luma">
      <div class="luma-card start">
        <div class="luma-head">
          <div class="luma-head-left">
            <img src="/assets/luma-avatar.png" class="luma-avatar-mini" alt="Luma">
            <div>
              <div class="luma-name">Luma</div>
              <div class="luma-subtitle">Professora de inglês</div>
            </div>
          </div>
          <div class="luma-badge start">✨ pronta</div>
        </div>
        <div class="luma-feedback">Vamos praticar inglês juntos?</div>
        <div class="luma-tip">Clique em <b>Vamos conversar</b>. Eu vou me apresentar e começar uma conversa no seu ritmo.</div>
        <div class="luma-actions">
          <button id="startLumaBtn" class="btn luma-start-btn">🚀 Vamos conversar</button>
        </div>
      </div>
    </div>
  `;
}

function renderLumaLoading(){
  return `
    <div class="ai-row luma" id="lumaLoading">
      <div class="luma-card thinking">
        <div class="luma-head">
          <div class="luma-head-left">
            <img src="/assets/luma-avatar.png" class="luma-avatar-mini" alt="Luma">
            <div>
              <div class="luma-name">Luma</div>
              <div class="luma-subtitle">analisando com calma...</div>
            </div>
          </div>
          <div class="luma-badge thinking">✨ Pensando</div>
        </div>
        <div class="luma-thinking-text">Estou esperando a frase completa e comparando com a missão atual.</div>
        <div class="luma-dots"><span></span><span></span><span></span></div>
      </div>
    </div>
  `;
}

function speakLumaMessage(btn){
  const card = btn.closest('.luma-card');
  if(!card) return;
  const text = card.dataset.speak || card.innerText.replace(/\s+/g, ' ').trim();
  speak(text, 'en-US');
}

function renderAIComposer(){
  return `
    <div class="ai-composer">
      <input
        id="chatText"
        class="ai-input"
        type="text"
        placeholder="Escreva sua resposta em inglês..."
        autocomplete="off"
      />
      <button id="sendChat" class="ai-send">Enviar</button>
    </div>

    <div class="ai-helper">
      🎤 Ao falar, faça a frase completa. A Luma espera uma pausa maior antes de enviar.
    </div>

    <button id="voiceAnswerBtn" class="ai-mic-fab" type="button" aria-label="Falar com a Luma">
      <span>🎙️</span>
      <span>Falar</span>
    </button>
  `;
}

async function loadAIUsage(){
  try { return await api('/ai/usage'); }
  catch { return null; }
}

async function renderAI(){
  if(!protect()) return;
  showNav(true);

  const params = new URLSearchParams(location.search);
  const lessonId = params.get('lesson') || '';
  const micWarn = micUnavailableMessage();
  const currentRate = localStorage.getItem('voice_rate') || 'normal';
  const usage = await loadAIUsage();

  app.innerHTML = `
    <div class="ai-page ai-page-clean">
      <section class="luma-header luma-header-clean">
        <img class="robot-avatar-img big-luma" src="/assets/luma-avatar.png" alt="Luma, robô professora">
        <div>
          <div class="luma-header-top">
            <span class="badge">🤖 Luma · professora de inglês</span>
            ${renderAIUsage(usage)}
          </div>
          <h1>Fale inglês comigo!</h1>
          <p>Converse sobre assuntos do dia a dia. Eu vou lembrar do que já falamos e mudar os temas com o tempo.</p>
          <div class="speed-toggle">
            <button class="btn secondary ${currentRate==='normal'?'active':''}" data-rate="normal" onclick="setVoiceRate('normal')">⚡ Normal</button>
            <button class="btn secondary ${currentRate==='slow'?'active':''}" data-rate="slow" onclick="setVoiceRate('slow')">🐢 Mais lento</button>
          </div>
        </div>
      </section>

      ${micWarn ? `<div class="safe-note">🎙️ ${escapeHtml(micWarn)}</div>` : `<div class="voice-ready">🎙️ Microfone pronto. Toque no botão laranja e fale a frase completa.</div>`}

      <section class="ai-stage">
        <div id="chat" class="ai-chat">
          ${renderLumaStartCard()}
        </div>

        ${renderAIComposer()}
        <input type="hidden" id="chatLessonId" value="${lessonId}">
      </section>
    </div>
  `;

  document.getElementById('sendChat').onclick = sendChat;
  document.getElementById('voiceAnswerBtn').onclick = () => startSpeechToInput('chatText', ()=>sendChat());
  document.getElementById('chatText').addEventListener('keydown', e=>{ if(e.key==='Enter') sendChat(); });
  document.getElementById('startLumaBtn')?.addEventListener('click', startLumaConversation);
}

async function startLumaConversation(){
  const chat = document.getElementById('chat');
  if(!chat) return;
  document.getElementById('startLumaBtn')?.setAttribute('disabled','disabled');
  chat.innerHTML += renderLumaLoading();
  chat.scrollTop = chat.scrollHeight;

  let r;
  try{
    r = await api('/ai/start', {method:'POST', body:'{}'});
  }catch(err){
    document.getElementById('lumaLoading')?.remove();
    chat.innerHTML += renderLumaCard({
      feedback: 'Ops! Não consegui iniciar agora.',
      correction: null,
      explanation_pt: err.message || 'Tente novamente em alguns segundos.',
      next_question: 'Can you try again?',
      mood: 'helping',
      topic: 'retry',
      status: 'repeat',
      understood: false,
      needs_repeat: true,
      source: 'erro'
    });
    return;
  }

  document.getElementById('lumaLoading')?.remove();
  chat.innerHTML += renderLumaCard(r);
  updateLumaUsage(r);
  window.lastLumaSpeech = `${r.feedback || ''}. ${r.next_question || ''}`.trim();
  speak(window.lastLumaSpeech, 'en-US');
  chat.scrollTop = chat.scrollHeight;
}

async function sendChat(){
  const input = document.getElementById('chatText');
  const lessonId = document.getElementById('chatLessonId')?.value || null;
  const chat = document.getElementById('chat');

  if(!input || !chat) return;

  const msg = input.value.trim();
  if(!msg) return;

  chat.innerHTML += renderUserBubble(msg);
  input.value = '';
  input.focus();
  chat.innerHTML += renderLumaLoading();
  chat.scrollTop = chat.scrollHeight;

  let r;
  try {
    r = await api('/ai/chat',{
      method:'POST',
      body:JSON.stringify({
        lesson_id: lessonId ? Number(lessonId) : null,
        message: msg
      })
    });
  } catch(err) {
    document.getElementById('lumaLoading')?.remove();
    correctionSound();
    chat.innerHTML += renderLumaCard({
      feedback: 'Ops! Não consegui responder agora.',
      correction: null,
      explanation_pt: err.message || 'Tente novamente em alguns segundos.',
      next_question: 'Can you try again?',
      mood: 'helping',
      topic: 'retry',
      status: 'repeat',
      understood: false,
      needs_repeat: true,
      source: 'erro'
    }, msg);
    chat.scrollTop = chat.scrollHeight;
    toast(err.message || 'Erro ao conversar com a Luma', 'warn');
    return;
  }

  document.getElementById('lumaLoading')?.remove();

  const spoken = `${r.feedback || ''}. ${r.correction ? 'Try saying: ' + r.correction + '. ' : ''}${r.next_question || ''}`.trim();
  window.lastLumaSpeech = spoken;

  chat.innerHTML += renderLumaCard(r, msg);
  chat.scrollTop = chat.scrollHeight;
  updateLumaUsage(r);

  if(r.correction || r.needs_repeat || r.status === 'repeat' || r.status === 'correction') correctionSound();
  else rewardSound();

  if(r.points) toast(`+${r.points} XP por conversar com a Luma!`, 'success');

  speak(spoken, 'en-US');
}

async function renderAdmin(){
  if(!protect()) return;
  showNav(false);
  const user=store.user;
  if(user?.role!=='admin'){
    app.innerHTML=card('<h1>Acesso restrito</h1><button class="btn" onclick="go(\'/app\')">Voltar</button>');
    return;
  }

  const d=await api('/admin/dashboard');
  const classes=await api('/admin/classes');
  const students=await api('/admin/students');

  app.innerHTML = `${logo()}
  <div class="topbar">
    <div class="title"><h1>Painel admin</h1><p>Gerencie turmas, convites e alunos.</p></div>
    <button class="btn ghost" onclick="logout()">Sair</button>
  </div>

  <div class="grid cols-3">
    ${card(`<b>${d.students}</b><p>Alunos ativos</p>`)}
    ${card(`<b>${d.classes}</b><p>Turmas ativas</p>`)}
    ${card(`<b>${d.xp_total}</b><p>XP gerado</p>`)}
  </div>

  ${card(`<h2>Nova turma</h2>
    <form id="classForm" class="form admin-form-inline" autocomplete="off">
      <input name="name" placeholder="Nome da turma" required autocomplete="off">
      <input name="code" placeholder="Código ex: HELENA2026" required autocomplete="off" autocapitalize="characters">
      <input name="level" value="A1 Beginner" autocomplete="off">
      <button class="btn">Criar turma</button>
    </form>`)}

  ${card(`<h2>Turmas</h2>
    <table class="table admin-table">
      <thead><tr><th>Nome</th><th>Código</th><th>Status</th><th>Alunos</th><th>Convite</th></tr></thead>
      <tbody>${classes.map(c=>`<tr>
        <td>${escapeHtml(c.name)}</td>
        <td><b>${escapeHtml(c.code)}</b></td>
        <td>${c.is_active?'<span class="status-pill ok">Ativa</span>':'<span class="status-pill off">Inativa</span>'}</td>
        <td>${c.students}</td>
        <td><button class="btn secondary btn-small" onclick="makeInvite(${c.id})">Gerar convite</button></td>
      </tr>`).join('')}</tbody>
    </table>`)}

  ${card(`<div class="admin-section-title"><div><h2>Alunos</h2><p>Edite dados, desabilite acesso ou gere nova senha.</p></div></div>
    <table class="table admin-table">
      <thead><tr><th>Nome</th><th>Nickname</th><th>Turma</th><th>XP</th><th>Status</th><th>Ações</th></tr></thead>
      <tbody>${students.map(s=>`<tr class="${s.is_active?'':'row-disabled'}">
        <td>${escapeHtml(s.first_name)}</td>
        <td><b>${escapeHtml(s.nickname)}</b></td>
        <td>${escapeHtml(s.class_name || '-')}</td>
        <td>${s.total_xp}</td>
        <td>${s.is_active?'<span class="status-pill ok">Ativo</span>':'<span class="status-pill off">Desabilitado</span>'}</td>
        <td class="actions-cell">
          <button class="btn secondary btn-mini" onclick='adminEditStudent(${JSON.stringify(s).replaceAll("'", "&#39;")})'>Editar</button>
          <button class="btn secondary btn-mini" onclick="adminResetPassword(${s.id}, '${escapeHtml(s.nickname)}')">Resetar senha</button>
          <button class="btn ${s.is_active?'danger':'success'} btn-mini" onclick="adminToggleStudent(${s.id}, ${s.is_active})">${s.is_active?'Desabilitar':'Habilitar'}</button>
        </td>
      </tr>`).join('')}</tbody>
    </table>`)}

  <div id="adminModal" class="modal hidden"></div>`;

  document.getElementById('classForm').onsubmit = async e=>{
    e.preventDefault();
    const f=Object.fromEntries(new FormData(e.target));
    f.code = String(f.code || '').trim().toUpperCase();
    await api('/admin/classes',{method:'POST',body:JSON.stringify(f)});
    toast('Turma criada!', 'success');
    renderAdmin();
  };
}

async function makeInvite(id){
  const r=await api(`/admin/classes/${id}/invite`,{method:'POST',body:'{}'});
  const full=location.origin + r.link;
  await navigator.clipboard?.writeText(full).catch(()=>{});
  toast(`Convite gerado e copiado: ${full}`, 'success');
  alert(`Convite da turma ${r.class_code || ''}\n\n${full}\n\nAo abrir esse link, a turma já aparece preenchida e o aluno entra direto após criar o cadastro.`);
}

function closeAdminModal(){
  const modal = document.getElementById('adminModal');
  if(modal){ modal.classList.add('hidden'); modal.innerHTML=''; }
}

function adminEditStudent(student){
  const modal = document.getElementById('adminModal');
  if(!modal) return;
  modal.classList.remove('hidden');
  modal.innerHTML = `<div class="modal-card">
    <div class="modal-head"><h2>Editar aluno</h2><button class="btn ghost" onclick="closeAdminModal()">Fechar</button></div>
    <form id="studentEditForm" class="form" autocomplete="off">
      <label>Primeiro nome</label><input name="first_name" value="${escapeHtml(student.first_name || '')}" autocomplete="off" required>
      <label>Nickname</label><input name="nickname" value="${escapeHtml(student.nickname || '')}" autocomplete="off" autocapitalize="off" spellcheck="false" required>
      <small class="form-hint">Nicknames ofensivos são bloqueados automaticamente.</small>
      <label>Avatar</label><select name="avatar">
        ${['🌟','🦊','🐱','🐼','🚀','🎧','🤖','⚽','🎮','📚'].map(a=>`<option ${student.avatar===a?'selected':''}>${a}</option>`).join('')}
      </select>
      <label>Nível</label><input name="level" value="${escapeHtml(student.level || 'Beginner 1')}" autocomplete="off">
      <label class="check-line"><input type="checkbox" name="is_active" ${student.is_active?'checked':''}> Usuário ativo</label>
      <button class="btn">Salvar alterações</button>
    </form>
  </div>`;

  document.getElementById('studentEditForm').onsubmit = async e=>{
    e.preventDefault();
    const f=Object.fromEntries(new FormData(e.target));
    f.first_name = String(f.first_name || '').trim();
    f.nickname = String(f.nickname || '').trim();
    f.is_active = Boolean(f.is_active);
    if(isOffensiveNickname(f.nickname)){ toast('Escolha um nickname amigável para o ranking.', 'warn'); return; }
    await api(`/admin/students/${student.id}`,{method:'PUT',body:JSON.stringify(f)});
    toast('Aluno atualizado!', 'success');
    closeAdminModal();
    renderAdmin();
  };
}

async function adminResetPassword(id, nickname){
  if(!confirm(`Resetar a senha de ${nickname}?`)) return;
  const r = await api(`/admin/students/${id}/reset-password`,{method:'POST',body:'{}'});
  alert(`Nova senha de ${r.nickname}:\n\n${r.new_password}\n\nCopie e envie ao aluno/responsável.`);
}

async function adminToggleStudent(id, isActive){
  const action = isActive ? 'desabilitar' : 'habilitar';
  if(!confirm(`Deseja ${action} este usuário?`)) return;
  await api(`/admin/students/${id}/toggle-active`,{method:'POST',body:'{}'});
  toast(isActive ? 'Usuário desabilitado.' : 'Usuário habilitado.', 'success');
  renderAdmin();
}

function logout(){ store.clear(); go('/'); }
render();
