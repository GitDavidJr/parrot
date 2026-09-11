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
const btnBottomAction = document.getElementById('btn-bottom-action');
const btnBottomText = document.getElementById('btn-bottom-text');
const micMeterFill = document.getElementById('mic-meter-fill');
const micMeterVal = document.getElementById('mic-meter-val');
const feedChat = document.getElementById('feed-chat');
const inputQuickSpeak = document.getElementById('input-quick-speak');
const chatStatusDot = document.getElementById('chat-status-dot');
const chatStatusLabel = document.getElementById('chat-status-label');
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
      if (feedChat) feedChat.innerHTML = '';
      data.history.forEach(appendMessageCard);
    }

    // Auto launch onboarding on first visit or if OpenAI API key is not yet configured
    if (!localStorage.getItem('parrot_onboarding_completed') || !(data.settings && data.settings.openai_api_key_configured)) {
      setTimeout(() => openOnboardingModal(1), 500);
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
  if (statusText) statusText.textContent = message || (status === 'listening' ? 'Ouvindo...' : 'Inativo');
  const avatarDot = document.getElementById('avatar-status-dot');
  const chatDot = document.getElementById('chat-status-dot');
  const chatLabel = document.getElementById('chat-status-label');
  const micWrap = document.getElementById('mic-visualizer-wrap');

  const isActive = currentStatus.is_active || ['listening', 'transcribing', 'translating', 'speaking'].includes(status);

  // Smooth appearance/disappearance of the Mic level bar
  if (isActive) {
    if (micWrap) {
      micWrap.classList.remove('hidden');
      requestAnimationFrame(() => {
        micWrap.classList.remove('opacity-0', 'scale-90');
        micWrap.classList.add('opacity-100', 'scale-100');
      });
    }
  } else {
    if (micWrap) {
      micWrap.classList.remove('opacity-100', 'scale-100');
      micWrap.classList.add('opacity-0', 'scale-90');
      setTimeout(() => {
        if (!currentStatus.is_active) micWrap.classList.add('hidden');
      }, 200);
    }
  }

  const labelMap = {
    listening: 'Ouvindo...',
    transcribing: 'Transcrevendo...',
    translating: 'Traduzindo...',
    speaking: 'Transmitindo...',
    idle: 'Inativo'
  };

  if (chatLabel) {
    chatLabel.textContent = message || labelMap[status] || 'Inativo';
  }

  if (status === 'listening') {
    if (statusDot) statusDot.className = 'w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse';
    if (avatarDot) avatarDot.className = 'absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-slate-900 animate-pulse pointer-events-none';
    if (chatDot) chatDot.className = 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse';
  } else if (status === 'transcribing') {
    if (statusDot) statusDot.className = 'w-1.5 h-1.5 rounded-full bg-amber-500 animate-ping';
    if (avatarDot) avatarDot.className = 'absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-amber-500 ring-2 ring-white dark:ring-slate-900 pointer-events-none';
    if (chatDot) chatDot.className = 'w-2 h-2 rounded-full bg-amber-500 animate-pulse';
  } else if (status === 'translating') {
    if (statusDot) statusDot.className = 'w-1.5 h-1.5 rounded-full bg-sky-500 animate-pulse';
    if (avatarDot) avatarDot.className = 'absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-sky-500 ring-2 ring-white dark:ring-slate-900 pointer-events-none';
    if (chatDot) chatDot.className = 'w-2 h-2 rounded-full bg-sky-500 animate-pulse';
  } else if (status === 'speaking') {
    if (statusDot) statusDot.className = 'w-1.5 h-1.5 rounded-full bg-emerald-600 animate-bounce';
    if (avatarDot) avatarDot.className = 'absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-emerald-600 ring-2 ring-white dark:ring-slate-900 pointer-events-none';
    if (chatDot) chatDot.className = 'w-2 h-2 rounded-full bg-emerald-600 animate-bounce';
  } else {
    if (statusDot) statusDot.className = 'w-1.5 h-1.5 rounded-full bg-slate-400';
    if (avatarDot) avatarDot.className = 'absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full bg-slate-400 ring-2 ring-white dark:ring-slate-900 pointer-events-none';
    if (chatDot) chatDot.className = 'w-2 h-2 rounded-full bg-slate-400';
  }

  updateBottomButtonState();
}

function updateBottomButtonState() {
  const input = document.getElementById('input-quick-speak');
  const btn = document.getElementById('btn-bottom-action');
  if (!btn) return;

  const hasText = input && input.value.trim().length > 0;
  const isActive = currentStatus.is_active || ['listening', 'transcribing', 'translating', 'speaking'].includes(currentStatus.status);

  if (hasText) {
    btn.className = "cursor-pointer w-9 h-9 sm:w-10 sm:h-10 rounded-lg font-medium text-sm transition-all duration-150 shadow-xs flex items-center justify-center bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white shadow-emerald-600/15 shrink-0 select-none";
    btn.innerHTML = `
      <svg class="w-5 h-5 text-white" style="width: 20px; height: 20px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z"/></svg>
    `;
    const tooltipText = document.getElementById('btn-bottom-text');
    if (tooltipText) tooltipText.textContent = "Falar na Chamada (Enter)";
    btn.title = "Falar na Chamada (Enter)";
    btn.setAttribute('aria-label', "Falar na Chamada");
  } else {
    if (isActive) {
      btn.className = "cursor-pointer w-9 h-9 sm:w-10 sm:h-10 rounded-lg font-medium text-sm transition-all duration-150 shadow-xs flex items-center justify-center bg-rose-600 hover:bg-rose-500 active:scale-95 text-white shadow-rose-600/20 shrink-0 select-none";
      btn.innerHTML = `
        <svg class="w-5 h-5 text-white" style="width: 20px; height: 20px;" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>
      `;
      const tooltipText = document.getElementById('btn-bottom-text');
      if (tooltipText) tooltipText.textContent = "Parar Tradução";
      btn.title = "Parar Tradução";
      btn.setAttribute('aria-label', "Parar Tradução");
    } else {
      btn.className = "cursor-pointer w-9 h-9 sm:w-10 sm:h-10 rounded-lg font-medium text-sm transition-all duration-150 shadow-xs flex items-center justify-center bg-emerald-600 hover:bg-emerald-500 active:scale-95 text-white shadow-emerald-600/15 shrink-0 select-none";
      btn.innerHTML = `
        <svg class="w-5 h-5 text-white" style="width: 20px; height: 20px;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="m5 8 6 6"/>
          <path d="m4 14 6-6 2-3"/>
          <path d="M2 5h12"/>
          <path d="M7 2h1"/>
          <path d="m22 22-5-10-5 10"/>
          <path d="M14 18h6"/>
        </svg>
      `;
      const tooltipText = document.getElementById('btn-bottom-text');
      if (tooltipText) tooltipText.textContent = "Iniciar Tradução";
      btn.title = "Iniciar Tradução";
      btn.setAttribute('aria-label', "Iniciar Tradução");
    }
  }
}

function handleInputChange() {
  updateBottomButtonState();
}

async function handleBottomAction(e) {
  if (e) e.preventDefault();
  const input = document.getElementById('input-quick-speak');
  const text = input ? input.value.trim() : '';

  if (text) {
    if (currentStatus.settings.engine === 'openai' && !currentStatus.settings.openai_api_key_configured) {
      openOnboardingModal(2);
      return;
    }
    input.value = '';
    updateBottomButtonState();
    await fetch('/api/quick-speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    }).catch(err => console.error(err));
  } else {
    toggleSession();
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

  // Sync model dropdown & badge
  const ddModelSelect = document.getElementById('sel-dd-openai-model');
  const ddModelBadge = document.getElementById('dd-model-badge');
  const ddModelSec = document.getElementById('dd-model-section');
  if (ddModelSelect) ddModelSelect.value = model;
  if (ddModelBadge) ddModelBadge.textContent = model;
  if (ddModelSec) ddModelSec.style.display = (engine === 'openai') ? 'block' : 'none';

  // Sync headphones monitor checkboxes
  const isMonitor = Boolean(currentStatus.settings.play_translated_to_headphones);
  const chkDropdown = document.getElementById('chk-headphones-monitor');
  const chkModal = document.getElementById('modal-chk-headphones-monitor');
  if (chkDropdown) chkDropdown.checked = isMonitor;
  if (chkModal) chkModal.checked = isMonitor;

  updateStatusPill(currentStatus.status);
}

async function changeOpenAIModel(model) {
  currentStatus.settings.openai_model = model;
  const badge = document.getElementById('dd-model-badge');
  if (badge) badge.textContent = model;
  if (ddModelText) ddModelText.textContent = model.replace('-mini', ' Mini').replace('gpt-', 'GPT-');
  const selModal = document.getElementById('sel-openai-model');
  if (selModal) selModal.value = model;

  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ openai_model: model })
  }).catch(() => {});
}

async function toggleHeadphonesMonitor(checked) {
  currentStatus.settings.play_translated_to_headphones = checked;
  const chkDropdown = document.getElementById('chk-headphones-monitor');
  const chkModal = document.getElementById('modal-chk-headphones-monitor');
  if (chkDropdown) chkDropdown.checked = checked;
  if (chkModal) chkModal.checked = checked;

  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ play_translated_to_headphones: checked })
  }).catch(() => {});
}

// -------------------------------------------------------------
// 4. Robust Master Start/Stop Toggle
// -------------------------------------------------------------
async function toggleSession() {
  const btn = document.getElementById('btn-bottom-action');
  const btnText = document.getElementById('btn-bottom-text');

  const willStart = !currentStatus.is_active;
  if (willStart && currentStatus.settings.engine === 'openai' && !currentStatus.settings.openai_api_key_configured) {
    openOnboardingModal(2);
    return;
  }
  
  // Immediate tactile feedback
  if (btnText) btnText.textContent = willStart ? "LIGANDO..." : "PARANDO...";
  if (btn) btn.disabled = true;

  try {
    const endpoint = willStart ? '/api/start' : '/api/stop';
    const res = await fetch(endpoint, { method: 'POST' });
    const data = await res.json();

    if (res.ok && data.success) {
      currentStatus.is_active = willStart;
      currentStatus.status = data.status || (willStart ? 'listening' : 'idle');
      const captureLabel = data.system_audio_backend && data.system_audio_backend !== 'idle'
        ? `Capturando computador via ${data.system_audio_backend}`
        : 'Ouvindo microfone...';
      updateStatusPill(currentStatus.status, willStart ? captureLabel : 'Inativo');
      if (willStart && data.system_audio_error) {
        alert(`A captura nativa não iniciou. O Parrot tentou a contingência: ${data.system_audio_error}`);
      }
      
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
    if (btn) btn.disabled = false;
    updateBottomButtonState();
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
  const container = document.getElementById('feed-chat');
  if (!container) return;

  const emptyState = document.getElementById('chat-empty-state');
  if (emptyState) {
    emptyState.remove();
  }

  const isUser = item.channel === 'user_to_meeting';
  const row = document.createElement('div');
  row.className = `flex flex-col w-full ${isUser ? 'items-end' : 'items-start'} transition-all`;

  if (isUser) {
    // Right side: User spoke/typed in Portuguese -> English spoken to meeting
    row.innerHTML = `
      <div class="max-w-[85%] sm:max-w-[75%] md:max-w-[65%] bg-emerald-600 dark:bg-emerald-650 text-white rounded-2xl rounded-tr-xs p-3.5 shadow-xs space-y-1.5 transition-all">
        <div class="flex items-center justify-between gap-3 text-[11px] text-emerald-100 font-medium">
          <span class="flex items-center gap-1.5 font-bold">
            <span class="w-1.5 h-1.5 rounded-full bg-emerald-200"></span>
            Você ➔ Chamada (Inglês)
          </span>
          <span class="text-[10px] text-emerald-200/90 font-mono">${escapeHtml(item.timestamp || '')}</span>
        </div>
        <div class="text-sm font-semibold leading-snug">
          "${escapeHtml(item.translated || '')}"
        </div>
        <div class="text-xs text-emerald-100/80 pt-1 border-t border-emerald-500/50 italic">
          Original (PT): "${escapeHtml(item.original || '')}"
        </div>
      </div>
    `;
  } else {
    // Left side: Meeting participant spoke English -> Portuguese translated to user
    row.innerHTML = `
      <div class="max-w-[85%] sm:max-w-[75%] md:max-w-[65%] bg-slate-100 dark:bg-slate-850 text-slate-900 dark:text-white border border-slate-200 dark:border-slate-700/80 rounded-2xl rounded-tl-xs p-3.5 shadow-xs space-y-1.5 transition-all">
        <div class="flex items-center justify-between gap-3 text-[11px] text-slate-500 dark:text-slate-400 font-medium">
          <span class="flex items-center gap-1.5 text-sky-600 dark:text-sky-400 font-bold">
            <span class="w-1.5 h-1.5 rounded-full bg-sky-500"></span>
            Chamada ➔ Você (Português)
          </span>
          <span class="text-[10px] text-slate-400 font-mono">${escapeHtml(item.timestamp || '')}</span>
        </div>
        <div class="text-sm font-semibold leading-snug">
          "${escapeHtml(item.translated || '')}"
        </div>
        <div class="text-xs text-slate-500 dark:text-slate-400 pt-1 border-t border-slate-200 dark:border-slate-700/60 italic">
          Original (EN): "${escapeHtml(item.original || '')}"
        </div>
      </div>
    `;
  }

  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Simulate Meeting Speech
async function simulateSpeech(text) {
  await fetch('/api/simulate-incoming', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text, play_audio: true })
  });
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
  fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ capture_mode: mode })
  }).catch(() => {});
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
  const selMeetingMic = document.getElementById('sel-meeting-mic');
  const selHeadphones = document.getElementById('sel-headphones');
  const selVirtualOutput = document.getElementById('sel-virtual-output');
  const selSystemBackend = document.getElementById('sel-system-backend');
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

  if (devices && (devices.meeting_inputs || devices.inputs)) {
    if (selMeetingMic) {
      selMeetingMic.innerHTML = '';
      const list = devices.meeting_inputs || devices.inputs;
      const chosenMeeting = setts.meeting_device_id ?? devices.recommended.meeting_device_id;
      list.forEach(d => {
        const opt = document.createElement('option');
        opt.value = d.id;
        opt.textContent = `${d.name}${d.id === devices.recommended.meeting_device_id ? ' (contingência recomendada)' : ''}`;
        if (d.id === chosenMeeting) opt.selected = true;
        selMeetingMic.appendChild(opt);
      });
    }
  }

  if (devices && devices.outputs && selHeadphones) {
    selHeadphones.innerHTML = '';
    const chosenOutput = setts.headphones_device_id ?? devices.recommended.headphones_id;
    devices.outputs.forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.id;
      opt.textContent = d.name;
      if (d.id === chosenOutput) opt.selected = true;
      selHeadphones.appendChild(opt);
    });
  }

  if (devices && selVirtualOutput) {
    selVirtualOutput.innerHTML = '';
    const noCable = document.createElement('option');
    noCable.value = '';
    noCable.textContent = 'Nenhum cabo virtual detectado';
    selVirtualOutput.appendChild(noCable);
    const chosenVirtual = setts.virtual_output_device_id ?? devices.recommended.virtual_mic_id;
    (devices.virtual_outputs || []).forEach(d => {
      const opt = document.createElement('option');
      opt.value = d.id;
      opt.textContent = d.name;
      if (d.id === chosenVirtual) opt.selected = true;
      selVirtualOutput.appendChild(opt);
    });
  }

  if (selModel && setts.openai_model) selModel.value = setts.openai_model;
  if (selVoice && setts.openai_voice) selVoice.value = setts.openai_voice;
  if (selSource && setts.source_lang) selSource.value = setts.source_lang;
  if (selTarget && setts.target_lang) selTarget.value = setts.target_lang;
  if (selPause && setts.vad_silence_threshold_ms) selPause.value = String(setts.vad_silence_threshold_ms);
  if (selSystemBackend) {
    const nativeBackend = devices && devices.platform === 'win32' ? 'wasapi' : 'screencapturekit';
    const nativeLabel = nativeBackend === 'wasapi' ? 'Nativo Windows (WASAPI)' : 'Nativo macOS (ScreenCaptureKit)';
    selSystemBackend.innerHTML = '';
    [['auto', 'Automático (recomendado)'], [nativeBackend, nativeLabel], ['virtual_device', 'Perssua / BlackHole / cabo virtual']].forEach(([value, label]) => {
      const opt = document.createElement('option');
      opt.value = value;
      opt.textContent = label;
      selSystemBackend.appendChild(opt);
    });
    const configuredBackend = setts.system_audio_backend || 'auto';
    selSystemBackend.value = [...selSystemBackend.options].some(opt => opt.value === configuredBackend) ? configuredBackend : 'auto';
  }

  const chkSystemAudio = document.getElementById('modal-chk-system-audio');
  const chkDubSystem = document.getElementById('modal-chk-dub-system');
  if (chkSystemAudio) chkSystemAudio.checked = setts.system_audio_capture !== false;
  if (chkDubSystem) chkDubSystem.checked = setts.dub_system_audio !== false;

  const mode = setts.capture_mode || 'vad';
  const radioVad = document.getElementById('radio-mode-vad');
  const radioPtt = document.getElementById('radio-mode-ptt');
  if (radioVad && radioPtt) {
    if (mode === 'ptt') radioPtt.checked = true;
    else radioVad.checked = true;
  }

  const chkMonitor = document.getElementById('modal-chk-headphones-monitor');
  if (chkMonitor) chkMonitor.checked = Boolean(setts.play_translated_to_headphones);
}

async function previewSpecificVoice(voice) {
  const selVoice = document.getElementById('sel-call-voice');
  if (selVoice) selVoice.value = voice;
  await previewCurrentVoice(voice);
}

function previewVoiceChip(voice) {
  previewSpecificVoice(voice);
}

async function previewCurrentVoice(overrideVoice) {
  const selVoice = document.getElementById('sel-call-voice');
  const voice = overrideVoice || (selVoice ? selVoice.value : 'alloy');
  const btnIcon = document.getElementById('preview-voice-icon');
  const btnText = document.getElementById('preview-voice-text');

  if (btnText) btnText.textContent = 'Tocando...';
  if (btnIcon) btnIcon.textContent = '⏳';

  try {
    const res = await fetch('/api/preview-voice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        voice: voice,
        engine: currentStatus.settings.engine || 'openai',
        text: `Hello! This is a preview of the ${voice} voice in Parrot.`
      })
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.detail || 'Erro ao ouvir voz.');
    }
  } catch (e) {
    alert('Erro ao conectar para ouvir voz: ' + e);
  } finally {
    if (btnText) btnText.textContent = 'Ouvir Voz';
    if (btnIcon) btnIcon.textContent = '🔊';
  }
}

async function saveConfigModal() {
  const selMic = document.getElementById('sel-input-mic');
  const selMeetingMic = document.getElementById('sel-meeting-mic');
  const selHeadphones = document.getElementById('sel-headphones');
  const selVirtualOutput = document.getElementById('sel-virtual-output');
  const selSystemBackend = document.getElementById('sel-system-backend');
  const selModel = document.getElementById('sel-openai-model');
  const selVoice = document.getElementById('sel-call-voice');
  const selSource = document.getElementById('sel-source-lang');
  const selTarget = document.getElementById('sel-target-lang');
  const selPause = document.getElementById('sel-silence-pause');
  const chkMonitor = document.getElementById('modal-chk-headphones-monitor');
  const chkSystemAudio = document.getElementById('modal-chk-system-audio');
  const chkDubSystem = document.getElementById('modal-chk-dub-system');
  const inputOpenAIKey = document.getElementById('input-openai-key');
  const selCaptureMode = document.querySelector('input[name="modal_capture_mode"]:checked');

  const payload = {
    input_device_id: parseInt(selMic.value),
    meeting_device_id: selMeetingMic ? parseInt(selMeetingMic.value) : undefined,
    headphones_device_id: selHeadphones && selHeadphones.value !== '' ? parseInt(selHeadphones.value) : null,
    virtual_output_device_id: selVirtualOutput && selVirtualOutput.value !== '' ? parseInt(selVirtualOutput.value) : null,
    openai_model: selModel.value,
    openai_voice: selVoice.value,
    source_lang: selSource.value,
    target_lang: selTarget.value,
    vad_silence_threshold_ms: parseInt(selPause.value),
    play_translated_to_headphones: chkMonitor ? chkMonitor.checked : false,
    capture_mode: selCaptureMode ? selCaptureMode.value : 'vad',
    system_audio_capture: chkSystemAudio ? chkSystemAudio.checked : true,
    dub_system_audio: chkDubSystem ? chkDubSystem.checked : true,
    system_audio_backend: selSystemBackend ? selSystemBackend.value : 'auto'
  };
  if (inputOpenAIKey && inputOpenAIKey.value.trim()) {
    payload.openai_api_key = inputOpenAIKey.value.trim();
  }

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

async function testModalOpenAIKey() {
  const input = document.getElementById('input-openai-key');
  const btn = document.getElementById('btn-test-modal-key');
  const feedback = document.getElementById('modal-key-feedback');
  const val = input ? input.value.trim() : '';

  if (!val) {
    if (feedback) {
      feedback.className = 'text-[11px] text-amber-600 dark:text-amber-400 mt-1';
      feedback.textContent = 'Digite uma chave para validar.';
      feedback.classList.remove('hidden');
    }
    return;
  }

  if (btn) btn.textContent = 'Validando...';
  try {
    const res = await fetch('/api/validate-openai-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: val, save_if_valid: false })
    });
    const data = await res.json();
    if (res.ok && data.valid) {
      if (feedback) {
        feedback.className = 'text-[11px] text-emerald-600 dark:text-emerald-400 mt-1';
        feedback.textContent = '✓ Chave válida e autorizada!';
        feedback.classList.remove('hidden');
      }
    } else {
      if (feedback) {
        feedback.className = 'text-[11px] text-red-600 dark:text-red-400 mt-1';
        feedback.textContent = '⚠️ ' + (data.detail || data.error || 'Chave inválida.');
        feedback.classList.remove('hidden');
      }
    }
  } catch (e) {
    if (feedback) {
      feedback.className = 'text-[11px] text-red-600 dark:text-red-400 mt-1';
      feedback.textContent = 'Erro ao conectar: ' + e;
      feedback.classList.remove('hidden');
    }
  } finally {
    if (btn) btn.textContent = 'Validar Chave';
  }
}

// -------------------------------------------------------------
// 7. Onboarding Step-by-Step Controller (Setup Inicial)
// -------------------------------------------------------------
let currentOnboardStep = 1;

async function openOnboardingModal(step = 1) {
  const modal = document.getElementById('modal-onboarding');
  if (!modal) return;
  modal.classList.remove('hidden');
  goToOnboardStep(step);
  await refreshPermissions();
  initOnboardOpenAIField();
}

function closeOnboardingModal() {
  const modal = document.getElementById('modal-onboarding');
  if (modal) modal.classList.add('hidden');
}

function goToOnboardStep(step) {
  currentOnboardStep = step;
  const badge = document.getElementById('onboard-step-badge');
  if (badge) badge.textContent = `Passo ${step} de 3`;

  // Update progress bars & visible step panel
  for (let i = 1; i <= 3; i++) {
    const bar = document.getElementById(`onboard-bar-${i}`);
    const stepEl = document.getElementById(`onboard-step-${i}`);
    if (bar) {
      if (i <= step) {
        bar.className = 'h-1 rounded-full bg-emerald-500 transition-colors';
      } else {
        bar.className = 'h-1 rounded-full bg-slate-200 dark:bg-slate-800 transition-colors';
      }
    }
    if (stepEl) {
      if (i === step) {
        stepEl.classList.remove('hidden');
      } else {
        stepEl.classList.add('hidden');
      }
    }
  }

  if (step === 1) {
    refreshPermissions();
  } else if (step === 2) {
    initOnboardOpenAIField();
  }
}

async function refreshPermissions() {
  const micEl = document.getElementById('onboard-perm-mic');
  const sysEl = document.getElementById('onboard-perm-sys');
  const perssuaEl = document.getElementById('onboard-perm-perssua');

  try {
    const res = await fetch('/api/permissions');
    if (!res.ok) return;
    const perms = await res.json();

    // 1. Microfone
    if (micEl) {
      if (perms.microphone && perms.microphone.granted) {
        micEl.innerHTML = `
          <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            ✓ Liberado
          </span>`;
      } else {
        micEl.innerHTML = `
          <button onclick="requestSystemPermission('microphone')" class="cursor-pointer px-3 py-1 rounded-md text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs transition-colors">
            Liberar
          </button>`;
      }
    }

    // 2. Áudio do Sistema
    if (sysEl) {
      if (perms.system_audio && perms.system_audio.granted) {
        sysEl.innerHTML = `
          <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            ✓ Liberado
          </span>`;
      } else {
        sysEl.innerHTML = `
          <button onclick="requestSystemPermission('system_audio')" class="cursor-pointer px-3 py-1 rounded-md text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-xs transition-colors">
            Liberar
          </button>`;
      }
    }

    // 3. Driver Perssua
    if (perssuaEl) {
      if (perms.perssua_detected) {
        perssuaEl.innerHTML = `
          <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
            ✓ Detectado
          </span>`;
      } else {
        perssuaEl.innerHTML = `
          <span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
            Pronto
          </span>`;
      }
    }
  } catch (err) {
    console.error('Erro ao verificar permissões:', err);
  }
}

async function requestSystemPermission(permType) {
  try {
    await fetch('/api/permissions/request', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ permission: permType })
    });
    setTimeout(refreshPermissions, 900);
  } catch (err) {
    console.error('Erro ao requisitar permissão:', err);
  }
}

function initOnboardOpenAIField() {
  const inputKey = document.getElementById('onboard-input-key');
  const statusText = document.getElementById('onboard-key-status-text');
  const feedback = document.getElementById('onboard-key-feedback');

  if (feedback) {
    feedback.className = 'hidden';
    feedback.textContent = '';
  }

  if (currentStatus.settings && currentStatus.settings.openai_api_key_configured) {
    if (inputKey && !inputKey.value) {
      const masked = currentStatus.settings.openai_api_key_masked || '••••••••••••';
      inputKey.placeholder = `Configurada (${masked})`;
    }
    if (statusText) statusText.textContent = 'Chave ativa';
  }
}

function toggleOnboardKeyVisibility() {
  const input = document.getElementById('onboard-input-key');
  const eye = document.getElementById('btn-toggle-key-eye');
  if (!input) return;
  if (input.type === 'password') {
    input.type = 'text';
    if (eye) eye.textContent = '🔒';
  } else {
    input.type = 'password';
    if (eye) eye.textContent = '👁️';
  }
}

async function validateOnboardKey() {
  const inputKey = document.getElementById('onboard-input-key');
  const btn = document.getElementById('btn-onboard-validate');
  const feedback = document.getElementById('onboard-key-feedback');
  const val = inputKey ? inputKey.value.trim() : '';

  if (!val) {
    if (currentStatus.settings && currentStatus.settings.openai_api_key_configured) {
      if (feedback) {
        feedback.className = 'p-2.5 rounded-lg text-xs bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300';
        feedback.textContent = '✓ A chave existente já está ativa e configurada.';
      }
      return true;
    }
    if (feedback) {
      feedback.className = 'p-2.5 rounded-lg text-xs bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300';
      feedback.textContent = 'Por favor, insira sua chave da OpenAI que inicia com "sk-".';
    }
    return false;
  }

  if (btn) {
    btn.disabled = true;
    btn.textContent = 'Validando...';
  }

  try {
    const res = await fetch('/api/validate-openai-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: val, save_if_valid: true })
    });
    const data = await res.json();
    if (res.ok && data.valid) {
      if (feedback) {
        feedback.className = 'p-2.5 rounded-lg text-xs bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300';
        feedback.textContent = '✓ ' + (data.message || 'Chave validada e conectada com sucesso!');
      }
      if (data.settings) {
        Object.assign(currentStatus.settings, data.settings);
        updateUIState();
      }
      return true;
    } else {
      if (feedback) {
        feedback.className = 'p-2.5 rounded-lg text-xs bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300';
        feedback.textContent = '⚠️ ' + (data.detail || data.error || 'Chave inválida. Verifique os caracteres.');
      }
      return false;
    }
  } catch (e) {
    if (feedback) {
      feedback.className = 'p-2.5 rounded-lg text-xs bg-red-50 dark:bg-red-950/60 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300';
      feedback.textContent = 'Erro de conexão ao validar chave: ' + e;
    }
    return false;
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = 'Validar';
    }
  }
}

async function submitOnboardStep2() {
  const inputKey = document.getElementById('onboard-input-key');
  const val = inputKey ? inputKey.value.trim() : '';

  if (!val) {
    if (currentStatus.settings && currentStatus.settings.openai_api_key_configured) {
      goToOnboardStep(3);
      return;
    }
    const feedback = document.getElementById('onboard-key-feedback');
    if (feedback) {
      feedback.className = 'p-2.5 rounded-lg text-xs bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 text-amber-700 dark:text-amber-300';
      feedback.textContent = 'Por favor, insira sua chave da OpenAI para prosseguir.';
    }
    return;
  }

  const ok = await validateOnboardKey();
  if (ok) {
    goToOnboardStep(3);
  }
}

async function openOpenAIPlatformLink() {
  try {
    await fetch('/api/open-url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: 'https://platform.openai.com/api-keys' })
    });
  } catch (_) {
    window.open('https://platform.openai.com/api-keys', '_blank');
  }
}

function finishOnboarding() {
  localStorage.setItem('parrot_onboarding_completed', 'true');
  closeOnboardingModal();
}

// -------------------------------------------------------------
// 8. Interactive Spotlight Onboarding Tour (SVG Cutout Mask)
// -------------------------------------------------------------
let tourIndex = 0;
const tourSteps = [
  {
    targetId: 'btn-bottom-action',
    title: '1. Iniciar / Parar Tradução',
    desc: 'Clique aqui (ou pressione Enter com o campo vazio) para iniciar a tradução da reunião. O Parrot começa a ouvir seu microfone e a traduzir os participantes.'
  },
  {
    targetId: 'feed-chat',
    title: '2. Conversa da Chamada em Tempo Real',
    desc: 'Toda a reunião flui aqui em uma linha do tempo unificada: suas falas traduzidas aparecem à direita (verde) e o que os estrangeiros falam aparece à esquerda (azul).'
  },
  {
    targetId: 'input-quick-speak',
    title: '3. Digitar para Falar (Opcional)',
    desc: 'Se preferir não falar no microfone, digite sua mensagem em português aqui. O botão se transforma em "Falar" e injeta sua fala sintetizada em inglês diretamente na chamada.'
  },
  {
    targetId: 'btn-user-menu',
    title: '4. Menu e Ajustes de Áudio',
    desc: 'Neste menu você ajusta idiomas, vozes e dispositivos. Na chamada, selecione Perssua/BlackHole no macOS ou CABLE Output/VoiceMeeter Output no Windows como microfone.'
  }
];

function startTour() {
  tourIndex = 0;
  const overlay = document.getElementById('tour-overlay');
  if (overlay) overlay.classList.remove('hidden');
  renderTourStep();
}

function skipTour() {
  const overlay = document.getElementById('tour-overlay');
  if (overlay) overlay.classList.add('hidden');
  const cutout = document.getElementById('tour-cutout');
  if (cutout) {
    cutout.setAttribute('width', '0');
    cutout.setAttribute('height', '0');
  }
  const border = document.getElementById('tour-spotlight-border');
  if (border) {
    border.setAttribute('width', '0');
    border.setAttribute('height', '0');
  }
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

function renderTourStep() {
  const step = tourSteps[tourIndex];
  const target = document.getElementById(step.targetId);
  const cutout = document.getElementById('tour-cutout');
  const border = document.getElementById('tour-spotlight-border');
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

  if (target && balloon) {
    // Scroll element smoothly into view if needed
    target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    const rect = target.getBoundingClientRect();
    const padding = 8;

    // SVG spotlight cutout window
    const cutX = Math.max(0, rect.left - padding);
    const cutY = Math.max(0, rect.top - padding);
    const cutW = rect.width + (padding * 2);
    const cutH = rect.height + (padding * 2);

    if (cutout) {
      cutout.setAttribute('x', cutX);
      cutout.setAttribute('y', cutY);
      cutout.setAttribute('width', cutW);
      cutout.setAttribute('height', cutH);
    }
    if (border) {
      border.setAttribute('x', cutX);
      border.setAttribute('y', cutY);
      border.setAttribute('width', cutW);
      border.setAttribute('height', cutH);
    }

    // Balloon placement: NEVER collide with or cover the spotlighted card
    const balloonWidth = Math.min(360, window.innerWidth - 48);
    const balloonHeight = 190;
    balloon.style.width = `${balloonWidth}px`;

    let balloonTop = 0;
    let balloonLeft = 0;

    const screenMidX = window.innerWidth / 2;
    const targetCenterX = rect.left + (rect.width / 2);

    if (step.targetId === 'btn-bottom-action') {
      // Above the bottom action button
      balloonTop = Math.max(20, rect.top - balloonHeight - 16);
      balloonLeft = Math.max(20, Math.min(window.innerWidth - balloonWidth - 20, rect.right - balloonWidth));
    } else if (step.targetId === 'feed-chat') {
      // Top right within chat container
      balloonTop = Math.max(80, rect.top + 24);
      balloonLeft = Math.max(20, rect.right - balloonWidth - 24);
    } else if (step.targetId === 'input-quick-speak') {
      // Above the quick speak input bar
      balloonTop = Math.max(20, rect.top - balloonHeight - 16);
      balloonLeft = Math.max(20, rect.left);
    } else if (step.targetId === 'btn-user-menu') {
      // Underneath user menu avatar at top right
      balloonTop = rect.bottom + 14;
      balloonLeft = Math.max(20, window.innerWidth - balloonWidth - 24);
    } else if (targetCenterX < screenMidX) {
      // Target is on LEFT half (e.g. col-user) -> place balloon on RIGHT side!
      if (window.innerWidth - rect.right >= balloonWidth + 32) {
        balloonLeft = rect.right + 24;
        balloonTop = Math.max(80, Math.min(window.innerHeight - balloonHeight - 30, rect.top + 40));
      } else {
        balloonLeft = (window.innerWidth - balloonWidth) / 2;
        balloonTop = window.innerHeight - balloonHeight - 24;
      }
    } else {
      // Target is on RIGHT half (e.g. col-meeting) -> place balloon on LEFT side!
      if (rect.left >= balloonWidth + 32) {
        balloonLeft = rect.left - balloonWidth - 24;
        balloonTop = Math.max(80, Math.min(window.innerHeight - balloonHeight - 30, rect.top + 40));
      } else {
        balloonLeft = (window.innerWidth - balloonWidth) / 2;
        balloonTop = window.innerHeight - balloonHeight - 24;
      }
    }

    // Viewport bounds clamp
    balloonTop = Math.max(20, Math.min(window.innerHeight - balloonHeight - 16, balloonTop));
    balloonLeft = Math.max(16, Math.min(window.innerWidth - balloonWidth - 16, balloonLeft));

    balloon.style.top = `${balloonTop}px`;
    balloon.style.left = `${balloonLeft}px`;
  }
}

// Window resize & scroll listeners for dynamic positioning
window.addEventListener('resize', () => {
  const overlay = document.getElementById('tour-overlay');
  if (overlay && !overlay.classList.contains('hidden')) {
    renderTourStep();
  }
});
window.addEventListener('scroll', () => {
  const overlay = document.getElementById('tour-overlay');
  if (overlay && !overlay.classList.contains('hidden')) {
    renderTourStep();
  }
});

// -------------------------------------------------------------
// 8. Initialization
// -------------------------------------------------------------
initTheme();
initWebSocket();
