// Parrot Client Controller
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
const btnEngineOpenAI = document.getElementById('btn-engine-openai');
const btnEngineFree = document.getElementById('btn-engine-free');
const feedUser = document.getElementById('feed-user');
const feedMeeting = document.getElementById('feed-meeting');
const btnPtt = document.getElementById('btn-ptt');
const lblVirtualDev = document.getElementById('lbl-virtual-dev');

function initWebSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${protocol}//${location.host}/ws`);

  ws.onopen = () => {
    console.log('[Parrot WS] Conectado ao servidor de áudio.');
  };

  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    handleServerMessage(message);
  };

  ws.onclose = () => {
    console.log('[Parrot WS] Desconectado. Reconectando em 1s...');
    setTimeout(initWebSocket, 1000);
  };
}

function handleServerMessage(msg) {
  const { type, data } = msg;

  if (type === 'init') {
    currentStatus.is_active = data.is_active;
    currentStatus.status = data.status;
    currentStatus.settings = data.settings;
    currentStatus.devices = data.devices;
    updateUIState();
    populateDevices(data.devices, data.settings);

    if (data.history && data.history.length > 0) {
      feedUser.innerHTML = '';
      feedMeeting.innerHTML = '';
      data.history.forEach(appendMessageCard);
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
    micMeterFill.className = "w-full bg-emerald-400 rounded shadow-lg shadow-emerald-500/50";
  } else {
    micMeterFill.className = "w-full bg-parrot-500 rounded transition-all duration-75";
  }
}

function updateStatusPill(status, message) {
  statusText.textContent = message || status;

  if (status === 'listening') {
    statusDot.className = 'w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse';
    btnMasterText.textContent = 'PAUSAR TRADUÇÃO';
    btnMasterToggle.className = 'cursor-pointer group relative px-7 py-4 rounded-2xl font-bold text-base transition-all duration-200 shadow-xl flex items-center gap-3 bg-red-600 hover:bg-red-500 text-white shadow-red-500/25 active:scale-95';
    btnMasterIcon.innerHTML = '<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>';
  } else if (status === 'transcribing') {
    statusDot.className = 'w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping';
  } else if (status === 'translating') {
    statusDot.className = 'w-2.5 h-2.5 rounded-full bg-sky-400 animate-pulse';
  } else if (status === 'speaking') {
    statusDot.className = 'w-2.5 h-2.5 rounded-full bg-emerald-400 animate-bounce';
  } else {
    statusDot.className = 'w-2.5 h-2.5 rounded-full bg-slate-500';
    btnMasterText.textContent = 'INICIAR TRADUÇÃO';
    btnMasterToggle.className = 'cursor-pointer group relative px-7 py-4 rounded-2xl font-bold text-base transition-all duration-200 shadow-xl flex items-center gap-3 bg-gradient-to-r from-parrot-500 to-parrot-600 hover:from-parrot-400 hover:to-parrot-500 text-slate-950 shadow-parrot-500/25 active:scale-95';
    btnMasterIcon.innerHTML = '<path d="M8 5v14l11-7z"/>';
  }
}

function updateUIState() {
  const engine = currentStatus.settings.engine || 'openai';
  if (engine === 'openai') {
    btnEngineOpenAI.className = 'cursor-pointer px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 bg-parrot-600 text-white shadow-sm';
    btnEngineFree.className = 'cursor-pointer px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 text-slate-400 hover:text-white';
  } else {
    btnEngineFree.className = 'cursor-pointer px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 bg-sky-600 text-white shadow-sm';
    btnEngineOpenAI.className = 'cursor-pointer px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center gap-1.5 text-slate-400 hover:text-white';
  }

  updateStatusPill(currentStatus.status);
}

async function toggleSession() {
  if (currentStatus.is_active) {
    await fetch('/api/stop', { method: 'POST' });
  } else {
    await fetch('/api/start', { method: 'POST' });
  }
}

async function setEngine(engine) {
  currentStatus.settings.engine = engine;
  await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ engine })
  });
  updateUIState();
}

function appendMessageCard(item) {
  const isUser = item.channel === 'user_to_meeting';
  const container = isUser ? feedUser : feedMeeting;

  // Clear placeholder if first message
  if (container.querySelector('svg')) {
    container.innerHTML = '';
  }

  const card = document.createElement('div');
  card.className = `p-4 rounded-xl border transition-all animate-fade-in ${
    isUser 
      ? 'bg-slate-900/90 border-emerald-500/30 shadow-md' 
      : 'bg-slate-900/90 border-sky-500/30 shadow-md'
  }`;

  const headerColor = isUser ? 'text-emerald-400' : 'text-sky-400';
  const headerLabel = isUser ? 'Você (Falou em Português)' : 'Participante (Falou em Inglês)';
  const translatedLabel = isUser ? 'Injetado no Meet/Zoom (Inglês):' : 'Traduzido para Você (Português):';

  card.innerHTML = `
    <div class="flex items-center justify-between mb-2">
      <span class="text-xs font-bold ${headerColor} flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full ${isUser ? 'bg-emerald-500' : 'bg-sky-500'}"></span>
        ${headerLabel}
      </span>
      <div class="flex items-center gap-2">
        <span class="text-[10px] font-mono text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
          ⚡ ${item.latency_ms || 0}ms
        </span>
        <span class="text-[10px] text-slate-500 font-mono">${item.timestamp}</span>
      </div>
    </div>
    <div class="text-xs text-slate-300 italic mb-2 border-l-2 border-slate-700 pl-2">
      "${escapeHtml(item.original)}"
    </div>
    <div class="text-sm font-semibold text-white bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
      <span class="text-[10px] block font-normal text-slate-400 mb-0.5">${translatedLabel}</span>
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

// Quick Speak
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

// Simulate English Speech
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

// Keyboard shortcuts (Spacebar for PTT if in PTT mode)
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

// HUD Subtitles
function openHUD() {
  window.open('/hud', 'ParrotHUD', 'width=540,height=280,resizable=yes,scrollbars=no,status=no,location=no');
}

// Settings Modal
function openSettingsModal() {
  document.getElementById('modal-settings').classList.remove('hidden');
}

function closeSettingsModal() {
  document.getElementById('modal-settings').classList.add('hidden');
}

function toggleKeyVisibility() {
  const input = document.getElementById('input-openai-key');
  input.type = input.type === 'password' ? 'text' : 'password';
}

function populateDevices(devices, setts) {
  const selMic = document.getElementById('sel-input-mic');
  const selVirt = document.getElementById('sel-virtual-mic');
  const selPhones = document.getElementById('sel-headphones');

  selMic.innerHTML = '';
  devices.inputs.forEach(d => {
    const opt = document.createElement('option');
    opt.value = d.id;
    opt.textContent = `${d.name} (${d.sample_rate}Hz)`;
    if (d.id === (setts.input_device_id ?? devices.recommended.mic_id)) opt.selected = true;
    selMic.appendChild(opt);
  });

  selVirt.innerHTML = '';
  devices.virtual_outputs.forEach(d => {
    const opt = document.createElement('option');
    opt.value = d.id;
    opt.textContent = `${d.name} [Recomendado para Meet/Zoom]`;
    if (d.id === (setts.virtual_output_device_id ?? devices.recommended.virtual_mic_id)) opt.selected = true;
    selVirt.appendChild(opt);
  });
  if (devices.virtual_outputs.length > 0) {
    lblVirtualDev.textContent = devices.virtual_outputs[0].name;
  }

  selPhones.innerHTML = '';
  devices.outputs.forEach(d => {
    const opt = document.createElement('option');
    opt.value = d.id;
    opt.textContent = `${d.name}`;
    if (d.id === (setts.headphones_device_id ?? devices.recommended.headphones_id)) opt.selected = true;
    selPhones.appendChild(opt);
  });

  document.getElementById('input-openai-key').value = setts.openai_api_key || '';
  document.getElementById('sel-openai-voice').value = setts.openai_voice || 'alloy';
  document.getElementById('sel-edge-voice').value = setts.edge_voice_en || 'en-US-ChristopherNeural';
  document.getElementById('range-silence').value = setts.vad_silence_threshold_ms || 650;
  document.getElementById('lbl-silence-val').textContent = (setts.vad_silence_threshold_ms || 650) + 'ms';
}

async function saveSettingsForm() {
  const payload = {
    input_device_id: parseInt(document.getElementById('sel-input-mic').value),
    virtual_output_device_id: parseInt(document.getElementById('sel-virtual-mic').value),
    headphones_device_id: parseInt(document.getElementById('sel-headphones').value),
    openai_api_key: document.getElementById('input-openai-key').value.trim(),
    openai_voice: document.getElementById('sel-openai-voice').value,
    edge_voice_en: document.getElementById('sel-edge-voice').value,
    vad_silence_threshold_ms: parseInt(document.getElementById('range-silence').value),
  };

  const res = await fetch('/api/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (res.ok) {
    closeSettingsModal();
    alert('Configurações salvas com sucesso!');
  }
}

async function testAudioDevice(target) {
  try {
    const res = await fetch('/api/test-audio', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target, engine: currentStatus.settings.engine || 'openai' })
    });
    const data = await res.json();
    alert(data.message || 'Teste concluído!');
  } catch (e) {
    alert('Erro no teste: ' + e);
  }
}

// Initialize
initWebSocket();
