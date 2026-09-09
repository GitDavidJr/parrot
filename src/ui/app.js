// Parrot Desktop Application Controller
let ws = null;
let currentStatus = {
  is_active: false,
  status: 'idle',
  engine: 'openai',
  settings: {},
  devices: {}
};

// DOM Elements
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const btnMasterToggle = document.getElementById('btn-master-toggle');
const btnMasterText = document.getElementById('btn-master-text');
const btnMasterIcon = document.getElementById('btn-master-icon');
const micMeterFill = document.getElementById('mic-meter-fill');
const micMeterVal = document.getElementById('mic-meter-val');
const feedUser = document.getElementById('feed-user');
const feedMeeting = document.getElementById('feed-meeting');
const btnPtt = document.getElementById('btn-ptt');
const userDropdown = document.getElementById('user-dropdown');
const badgeLangPreview = document.getElementById('badge-lang-preview');
const ddModelText = document.getElementById('dd-model-text');
const ddBtnOpenAI = document.getElementById('dd-btn-openai');
const ddBtnFree = document.getElementById('dd-btn-free');

// -------------------------------------------------------------
// 1. Theme Management (Light Mode Default)
// -------------------------------------------------------------
function initTheme() {
  const savedTheme = localStorage.getItem('parrot_theme') || 'light';
  applyTheme(savedTheme);
}

function applyTheme(theme) {
  const html = document.documentElement;
  const themeIcon = document.getElementById('theme-icon');
  const themeText = document.getElementById('theme-status-text');
  if (theme === 'dark') {
    html.classList.remove('light');
    html.classList.add('dark');
    if (themeIcon) themeIcon.textContent = '☀️';
    if (themeText) themeText.textContent = 'Escuro';
  } else {
    html.classList.remove('dark');
    html.classList.add('light');
    if (themeIcon) themeIcon.textContent = '🌙';
    if (themeText) themeText.textContent = 'Claro';
  }
  localStorage.setItem('parrot_theme', theme);
}

function toggleTheme() {
  const isDark = document.documentElement.classList.contains('dark');
  const newTheme = isDark ? 'light' : 'dark';
  applyTheme(newTheme);
  fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ theme: newTheme })
  }).catch(() => {});
}

// -------------------------------------------------------------
// 2. User / Config Dropdown Menu
// -------------------------------------------------------------
function toggleUserDropdown(e) {
  if (e) e.stopPropagation();
  userDropdown.classList.toggle('hidden');
}

function closeUserDropdown() {
  userDropdown.classList.add('hidden');
}

window.addEventListener('click', (e) => {
  const container = document.getElementById('user-menu-container');
  if (container && !container.contains(e.target)) {
    closeUserDropdown();
  }
});

// -------------------------------------------------------------
// 3. WebSocket Connection
// -------------------------------------------------------------
function initWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${location.host}/ws`);

  ws.onopen = () => {
    console.log('[Parrot WS] Conectado ao servidor.');
  };

  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      handleServerMessage(msg);
    } catch (e) {
      console.error('[Parrot WS] Erro ao processar:', e);
    }
  };

  ws.onclose = () => {
    console.log('[Parrot WS] Reconectando em 1.5s...');
    setTimeout(initWebSocket, 1500);
  };
}

function handleServerMessage(msg) {
  const { type, data } = msg;

  if (type === 'init') {
    currentStatus.is_active = data.is_active;
    currentStatus.status = data.status;
    currentStatus.settings = data.settings || {};
    currentStatus.devices = data.devices || {};

    if (data.settings && data.settings.theme) {
      applyTheme(data.settings.theme);
    }

    updateUIState();
    populateConfigModal(data.devices, data.settings);

    if (data.history && data.history.length > 0) {
      feedUser.innerHTML = '';
      feedMeeting.innerHTML = '';
      data.history.forEach(appendMessageCard);
    }

    // Auto launch tour on first visit
    if (!localStorage.getItem('parrot_tour_shown')) {
      setTimeout(startTour, 700);
    }
  } else if (type === 'audio_level') {
    updateMeter(data.level, data.is_speaking);
  } else if (type === 'status_change') {
    currentStatus.status = data.status;
    if (data.is_active !== undefined) {
      currentStatus.is_active = data.is_active;
    }
    updateStatusPill(data.status, data.message);
  } else if (type === 'new_message') {
    appendMessageCard(data);
  } else if (type === 'error') {
    alert(data.message || 'Erro no Parrot');
  }
}

function updateMeter(level, isSpeaking) {
  const pct = Math.round(level * 100);
  micMeterFill.style.height = `${pct}%`;
  micMeterVal.textContent = `${pct}%`;

  if (isSpeaking) {
    micMeterFill.className = "w-full bg-emerald-500 rounded-sm shadow-sm shadow-emerald-500/50";
  } else {
    micMeterFill.className = "w-full bg-emerald-600/80 rounded-sm transition-all duration-75";
  }
}

function updateStatusPill(status, message) {
  statusText.textContent = message || (status === 'listening' ? 'Ouvindo...' : 'Inativo');

  if (status === 'listening') {
    statusDot.className = 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse';
    btnMasterText.textContent = 'PAUSAR TRADUÇÃO';
    btnMasterToggle.className = 'cursor-pointer group relative px-6 py-3.5 rounded-lg font-bold text-sm transition-all duration-150 shadow-sm flex items-center gap-2 bg-rose-600 hover:bg-rose-500 active:scale-98 text-white shadow-rose-600/20';
    btnMasterIcon.innerHTML = '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';
  } else if (status === 'transcribing') {
    statusDot.className = 'w-2 h-2 rounded-full bg-amber-500 animate-ping';
  } else if (status === 'translating') {
    statusDot.className = 'w-2 h-2 rounded-full bg-sky-500 animate-pulse';
  } else if (status === 'speaking') {
    statusDot.className = 'w-2 h-2 rounded-full bg-emerald-600 animate-bounce';
  } else {
    statusDot.className = 'w-2 h-2 rounded-full bg-slate-400';
    btnMasterText.textContent = 'INICIAR TRADUÇÃO';
    btnMasterToggle.className = 'cursor-pointer group relative px-6 py-3.5 rounded-lg font-bold text-sm transition-all duration-150 shadow-sm flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 active:scale-98 text-white shadow-emerald-600/10';
    btnMasterIcon.innerHTML = '<path d="M8 5v14l11-7z"/>';
  }
}

function updateUIState() {
  const engine = currentStatus.settings.engine || 'openai';
  const model = currentStatus.settings.openai_model || 'gpt-5.4-mini';
  const src = currentStatus.settings.source_lang || 'pt';
  const tgt = currentStatus.settings.target_lang || 'en';

  if (ddModelText) {
    ddModelText.textContent = model.replace('-mini', ' Mini').replace('gpt-', 'GPT-');
  }

  if (badgeLangPreview) {
    const langNames = { pt: 'Português', en: 'Inglês', es: 'Espanhol', fr: 'Francês' };
    badgeLangPreview.textContent = `${langNames[src] || src} ➔ ${langNames[tgt] || tgt}`;
  }

  if (engine === 'openai') {
    if (ddBtnOpenAI) ddBtnOpenAI.className = 'cursor-pointer px-2 py-1.5 rounded-md text-[11px] font-semibold text-center border transition-all bg-emerald-50 dark:bg-emerald-950/50 border-emerald-300 dark:border-emerald-700 text-emerald-700 dark:text-emerald-300';
    if (ddBtnFree) ddBtnFree.className = 'cursor-pointer px-2 py-1.5 rounded-md text-[11px] font-semibold text-center border transition-all border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700';
  } else {
    if (ddBtnFree) ddBtnFree.className = 'cursor-pointer px-2 py-1.5 rounded-md text-[11px] font-semibold text-center border transition-all bg-sky-50 dark:bg-sky-950/50 border-sky-300 dark:border-sky-700 text-sky-700 dark:text-sky-300';
    if (ddBtnOpenAI) ddBtnOpenAI.className = 'cursor-pointer px-2 py-1.5 rounded-md text-[11px] font-semibold text-center border transition-all border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700';
  }

  updateStatusPill(currentStatus.status);
}

// -------------------------------------------------------------
// 4. Robust Master Start/Stop Toggle
// -------------------------------------------------------------
async function toggleSession() {
  const btn = document.getElementById('btn-master-toggle');
  const btnText = document.getElementById('btn-master-text');

  const willStart = !currentStatus.is_active;
  
  // Immediate tactile feedback
  btnText.textContent = willStart ? "LIGANDO..." : "PARANDO...";
  btn.disabled = true;

  try {
    const endpoint = willStart ? '/api/start' : '/api/stop';
    const res = await fetch(endpoint, { method: 'POST' });
    const data = await res.json();

    if (res.ok && data.success) {
      currentStatus.is_active = willStart;
      currentStatus.status = data.status || (willStart ? 'listening' : 'idle');
      updateStatusPill(currentStatus.status, willStart ? 'Parrot ouvindo microfone...' : 'Parrot pausado.');
      
      // Notify WS
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: willStart ? 'start' : 'stop' }));
      }
    } else {
      alert("Não foi possível iniciar: " + (data.detail || "Verifique o microfone."));
      updateStatusPill(currentStatus.status);
    }
  } catch (err) {
    console.error("Erro na requisição:", err);
    alert("Falha ao comunicar com o servidor Parrot. Verifique se a aplicação está em execução.");
    updateStatusPill(currentStatus.status);
  } finally {
    btn.disabled = false;
  }
}

async function setEngine(engine) {
  currentStatus.settings.engine = engine;
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ engine })
  }).catch(() => {});
  updateUIState();
}

// -------------------------------------------------------------
// 5. Message Cards Rendering
// -------------------------------------------------------------
function appendMessageCard(item) {
  const isUser = item.channel === 'user_to_meeting';
  const container = isUser ? feedUser : feedMeeting;

  if (container.querySelector('svg')) {
    container.innerHTML = '';
  }

  const card = document.createElement('div');
  card.className = `p-3 rounded-lg border transition-all ${
    isUser 
      ? 'bg-emerald-50/40 dark:bg-slate-900/90 border-emerald-200 dark:border-emerald-800 shadow-xs' 
      : 'bg-sky-50/40 dark:bg-slate-900/90 border-sky-200 dark:border-sky-800 shadow-xs'
  }`;

  const headerColor = isUser ? 'text-emerald-700 dark:text-emerald-400' : 'text-sky-700 dark:text-sky-400';
  const headerLabel = isUser ? 'Você (Português)' : 'Participante (Inglês)';
  const translatedLabel = isUser ? 'Injetado na Chamada (Inglês):' : 'Traduzido para Você (Português):';

  card.innerHTML = `
    <div class="flex items-center justify-between mb-1">
      <span class="text-xs font-bold ${headerColor} flex items-center gap-1.5">
        <span class="w-1.5 h-1.5 rounded-full ${isUser ? 'bg-emerald-600' : 'bg-sky-600'}"></span>
        ${headerLabel}
      </span>
      <div class="flex items-center gap-1.5">
        <span class="text-[10px] font-mono text-slate-500 bg-white dark:bg-slate-800 px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-700">
          ⚡ ${item.latency_ms || 0}ms
        </span>
        <span class="text-[10px] text-slate-400 font-mono">${item.timestamp}</span>
      </div>
    </div>
    <div class="text-xs text-slate-600 dark:text-slate-300 italic mb-1.5 pl-2 border-l-2 ${isUser ? 'border-emerald-300 dark:border-emerald-700' : 'border-sky-300 dark:border-sky-700'}">
      "${escapeHtml(item.original)}"
    </div>
    <div class="text-xs font-semibold text-slate-900 dark:text-white bg-white dark:bg-slate-950 p-2 rounded border ${isUser ? 'border-emerald-100 dark:border-slate-800' : 'border-sky-100 dark:border-slate-800'}">
      <span class="text-[9px] block font-normal text-slate-400 mb-0.5">${translatedLabel}</span>
      "${escapeHtml(item.translated)}"
    </div>
  `;

  container.appendChild(card);
  container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Quick Speak Text
async function handleQuickSpeak(e) {
  e.preventDefault();
  const input = document.getElementById('input-quick-speak');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';

  await fetch('/api/quick-speak', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  });
}

// Simulate Meeting Speech
async function simulateSpeech(text) {
  await fetch('/api/simulate-incoming', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, play_audio: true })
  });
}

async function handleSimulateCustom(e) {
  e.preventDefault();
  const input = document.getElementById('input-simulate-en');
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  await simulateSpeech(text);
}

// Push to Talk (PTT)
function pttPress() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ptt_press' }));
  }
}

function pttRelease() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: 'ptt_release' }));
  }
}

function changeCaptureMode(mode) {
  currentStatus.settings.capture_mode = mode;
  if (mode === 'ptt') {
    btnPtt.classList.remove('hidden');
  } else {
    btnPtt.classList.add('hidden');
  }
  fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ capture_mode: mode })
  });
}

// Spacebar PTT listener
window.addEventListener('keydown', (e) => {
  if (e.code === 'Space' && currentStatus.settings.capture_mode === 'ptt') {
    if (document.activeElement.tagName === 'INPUT') return;
    e.preventDefault();
    pttPress();
  }
});

window.addEventListener('keyup', (e) => {
  if (e.code === 'Space' && currentStatus.settings.capture_mode === 'ptt') {
    if (document.activeElement.tagName === 'INPUT') return;
    e.preventDefault();
    pttRelease();
  }
});

// HUD Floating Window
function openHUD() {
  window.open('/hud', 'ParrotHUD', 'width=520,height=260,resizable=yes,scrollbars=no,status=no,location=no');
}

// -------------------------------------------------------------
// 6. "Configurar Idiomas & Áudio" Dialog
// -------------------------------------------------------------
function openConfigModal() {
  document.getElementById('modal-config').classList.remove('hidden');
}

function closeConfigModal() {
  document.getElementById('modal-config').classList.add('hidden');
}

function populateConfigModal(devices, setts) {
  const selMic = document.getElementById('sel-input-mic');
  const selModel = document.getElementById('sel-openai-model');
  const selVoice = document.getElementById('sel-call-voice');
  const selSource = document.getElementById('sel-source-lang');
  const selTarget = document.getElementById('sel-target-lang');
  const selPause = document.getElementById('sel-silence-pause');

  if (devices && devices.inputs) {
    selMic.innerHTML = '';
    const chosenMic = setts.input_device_id ?? devices.recommended.mic_id;
    devices.inputs.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.id;
      opt.textContent = `${d.name}`;
      if (d.id === chosenMic) opt.selected = true;
      selMic.appendChild(opt);
    });
  }

  if (selModel && setts.openai_model) selModel.value = setts.openai_model;
  if (selVoice && setts.openai_voice) selVoice.value = setts.openai_voice;
  if (selSource && setts.source_lang) selSource.value = setts.source_lang;
  if (selTarget && setts.target_lang) selTarget.value = setts.target_lang;
  if (selPause && setts.vad_silence_threshold_ms) selPause.value = String(setts.vad_silence_threshold_ms);
}

async function saveConfigModal() {
  const selMic = document.getElementById('sel-input-mic');
  const selModel = document.getElementById('sel-openai-model');
  const selVoice = document.getElementById('sel-call-voice');
  const selSource = document.getElementById('sel-source-lang');
  const selTarget = document.getElementById('sel-target-lang');
  const selPause = document.getElementById('sel-silence-pause');

  const payload = {
    input_device_id: parseInt(selMic.value),
    openai_model: selModel.value,
    openai_voice: selVoice.value,
    source_lang: selSource.value,
    target_lang: selTarget.value,
    vad_silence_threshold_ms: parseInt(selPause.value)
  };

  const res = await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    Object.assign(currentStatus.settings, payload);
    updateUIState();
    closeConfigModal();
  }
}

async function testAudioOutput() {
  try {
    const res = await fetch('/api/test-audio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target: 'perssua', engine: currentStatus.settings.engine || 'openai' })
    });
    const data = await res.json();
    alert('Som de teste enviado para a chamada com sucesso!');
  } catch (e) {
    alert('Erro no teste: ' + e);
  }
}

// -------------------------------------------------------------
// 7. Interactive Spotlight Onboarding Tour
// -------------------------------------------------------------
let tourIndex = 0;
const tourSteps = [
  {
    targetId: 'btn-master-toggle',
    title: '1. Ativar o Tradutor',
    desc: 'Clique aqui quando sua reunião começar. O Parrot fica ouvindo seu microfone e a barrinha de volume ao lado mostra quando você está falando.',
    position: 'bottom'
  },
  {
    targetId: 'col-user',
    title: '2. Seu Canal de Voz (Você ➔ Reunião)',
    desc: 'Fale normalmente em Português. Quando você fizer uma pausa, o Parrot sintetiza a fala em Inglês fluente para as pessoas da reunião ouvirem.',
    position: 'right'
  },
  {
    targetId: 'col-meeting',
    title: '3. Fala dos Estrangeiros (Reunião ➔ Você)',
    desc: 'Aqui você acompanha o que os participantes falam em inglês, transcrito e traduzido para português em tempo real para você não perder nada.',
    position: 'left'
  },
  {
    targetId: 'btn-user-menu',
    title: '4. Menu e Ajustes de Áudio',
    desc: 'Neste menu você ajusta idiomas, vozes e microfones. No seu Google Meet ou Zoom, lembre-se de selecionar o microfone da chamada como "Perssua"!',
    position: 'bottom-left'
  }
];

function startTour() {
  tourIndex = 0;
  document.getElementById('tour-overlay').classList.remove('hidden');
  renderTourStep();
}

function skipTour() {
  cleanupTourHighlights();
  document.getElementById('tour-overlay').classList.add('hidden');
  localStorage.setItem('parrot_tour_shown', 'true');
}

function nextTourStep() {
  tourIndex++;
  if (tourIndex >= tourSteps.length) {
    skipTour();
  } else {
    renderTourStep();
  }
}

function prevTourStep() {
  if (tourIndex > 0) {
    tourIndex--;
    renderTourStep();
  }
}

function cleanupTourHighlights() {
  document.querySelectorAll('.spotlight-active').forEach(el => {
    el.classList.remove('spotlight-active');
  });
}

function renderTourStep() {
  cleanupTourHighlights();

  const step = tourSteps[tourIndex];
  const target = document.getElementById(step.targetId);
  const balloon = document.getElementById('tour-balloon');
  const badge = document.getElementById('tour-step-badge');
  const title = document.getElementById('tour-title');
  const desc = document.getElementById('tour-desc');
  const btnPrev = document.getElementById('tour-btn-prev');
  const btnNext = document.getElementById('tour-btn-next');

  badge.textContent = `Passo ${tourIndex + 1} de ${tourSteps.length}`;
  title.textContent = step.title;
  desc.textContent = step.desc;

  if (tourIndex === 0) {
    btnPrev.classList.add('hidden');
  } else {
    btnPrev.classList.remove('hidden');
  }

  if (tourIndex === tourSteps.length - 1) {
    btnNext.textContent = 'Concluir ✨';
  } else {
    btnNext.textContent = 'Próximo ➔';
  }

  if (target) {
    target.classList.add('spotlight-active');
    const rect = target.getBoundingClientRect();
    
    // Position balloon
    let top = rect.bottom + 16;
    let left = rect.left;

    if (step.position === 'right') {
      top = rect.top + 40;
      left = rect.right - 340;
    } else if (step.position === 'left') {
      top = rect.top + 40;
      left = rect.left + 20;
    } else if (step.position === 'bottom-left') {
      top = rect.bottom + 16;
      left = Math.max(20, rect.right - 320);
    } else {
      top = rect.bottom + 16;
      left = Math.max(20, rect.left - 120);
    }

    // Clamp within viewport
    top = Math.max(20, Math.min(window.innerHeight - 240, top));
    left = Math.max(20, Math.min(window.innerWidth - 380, left));

    balloon.style.top = `${top}px`;
    balloon.style.left = `${left}px`;
  }
}

// -------------------------------------------------------------
// 8. Initialization
// -------------------------------------------------------------
initTheme();
initWebSocket();
