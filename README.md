# 🦜 Parrot — Tradutor de Voz em Tempo Real para Chamadas Internacionais

<p align="center">
  <img src="assets/icon.png" alt="Parrot Icon" width="160" style="border-radius: 50%; box-shadow: 0 10px 30px rgba(16, 185, 129, 0.3);" />
</p>

O **Parrot** é uma aplicação desktop para macOS e Windows projetada para reuniões internacionais (Google Meet, Zoom, Microsoft Teams, Discord, etc.).

Com o Parrot, você pode participar de qualquer chamada falando em **Português**: o sistema transcreve, traduz e sintetiza a sua fala em **Inglês fluente com voz humana**, injetando o áudio diretamente na reunião através de um cabo virtual (`Perssua` / `BlackHole` no macOS ou `VB-CABLE` / `VoiceMeeter` no Windows).

Além disso, o Parrot pode capturar **todo o áudio reproduzido pelo computador**. Quando detecta fala em inglês no Meet, Zoom, Discord, navegador ou vídeo, cria legendas em português e fala a tradução por cima do áudio original, no estilo dublagem de jornal, com atraso por frase.

---

## ⚡ Como Funciona a Arquitetura de Áudio

```
 [Você fala em Português] 
           │
           ▼
 [Seu Microfone Físico] (MacBook / Fone)
           │
           ▼
 [Detecção VAD / Push-to-Talk]
           │
           ▼
 [STT: Transcrição em Português]
           │
           ▼
 [Tradução: PT ➔ EN (OpenAI GPT-4o / Google)]
           │
           ▼
 [TTS: Síntese de Voz Humana em Inglês]
           │
           ▼
 [Cabo virtual Perssua / BlackHole / VB-CABLE]
           │
           ▼
 [Google Meet / Zoom / Discord / Teams]
    (O gringo ouve você falando em Inglês fluente!)
```

### Dublagem do áudio do computador (EN ➔ PT)

```text
Qualquer aplicativo reproduzindo áudio em inglês
           │
           ▼
Captura nativa do sistema
  macOS: ScreenCaptureKit
  Windows: WASAPI loopback
           │
           ▼
VAD por frase → STT → tradução EN/PT → TTS português
           │
           ▼
Saída física selecionada (fone/alto-falante)
           └── voz portuguesa sobre o áudio original
```

No macOS, Perssua/BlackHole é apenas contingência. No Windows, a captura padrão usa o loopback da saída ativa, sem exigir cabo virtual.

---

## 🚀 Como Iniciar

### 1. Início Rápido com 1 clique:

No terminal, dentro da pasta do projeto:

```bash
./start.sh
```

Ou diretamente via Python:

```bash
source .venv/bin/activate
python3 main.py
```

O Parrot abrirá automaticamente a janela desktop nativa. Você também pode acessar pelo navegador em [http://localhost:8765](http://localhost:8765).

---

## 🎧 Configuração no Google Meet / Zoom / Discord / Teams

Para que as pessoas da reunião ouçam a sua voz traduzida em inglês:

1. Abra as **Configurações de Áudio** do seu aplicativo de chamada (Meet, Zoom, Discord, etc.).
2. No campo **Microfone (Entrada de Áudio)**, selecione:
   - macOS: **`Perssua`** ou o endpoint BlackHole usado como cabo virtual;
   - Windows com VB-CABLE: **`CABLE Output (VB-Audio Virtual Cable)`**;
   - Windows com VoiceMeeter: normalmente **`VoiceMeeter Output`**.
3. No Parrot, em **“Cabo virtual que envia sua voz à chamada”**, selecione:
   - macOS: `Perssua` / `BlackHole`;
   - Windows com VB-CABLE: **`CABLE Input (VB-Audio Virtual Cable)`**.
4. No campo **Alto-falante (Saída de Áudio)** da chamada, mantenha os seus fones de ouvido normais.
5. No Parrot, clique em **“INICIAR TRADUÇÃO”**.
6. Fale normalmente em português. Ao terminar a frase, o Parrot falará em inglês para todos na reunião.

Para ouvir outras pessoas traduzidas, ative **Dublagem do Áudio do Computador**. Não é necessário alterar a saída do Meet/Discord: o áudio original continua no dispositivo normal e o Parrot sobrepõe a voz portuguesa.

Na primeira execução, autorize Microfone e Captura de Tela/Áudio do Sistema no macOS. No Windows, permita Microfone quando solicitado; o WASAPI captura a saída padrão. O cabo virtual só é necessário para enviar a sua voz traduzida à chamada, não para ouvir a dublagem.

---

## 🧠 Motores de IA Disponíveis

O Parrot permite alternar entre dois motores com 1 clique na barra superior:

| Recurso | ⚡ Motor OpenAI (Alta Fidelidade) | 🆓 Motor Gratuito (100% Free) |
| :--- | :--- | :--- |
| **STT (Reconhecimento)** | OpenAI Whisper (`whisper-1`) | Google Speech Recognition |
| **Tradução** | `gpt-4o-mini` (conversacional, gírias e contexto) | Google Translate (`deep-translator`) |
| **TTS (Síntese de Voz)** | OpenAI TTS-1 (`alloy`, `echo`, `nova`, `onyx`, etc.) | Microsoft Edge Neural Voices (`Christopher`, `Jenny`, etc.) |
| **Custo** | Utiliza créditos da sua API Key da OpenAI | Sem cobrança de API pelo Parrot; usa serviços gratuitos de terceiros |

A chave OpenAI pode ser informada no painel de configurações. Sem chave, o Parrot usa automaticamente o motor gratuito.

---

## 🖥️ Recursos da Interface

- **Controle Master**: Botão para iniciar/pausar com indicador visual pulsante e medidor de VU do microfone.
- **Modo de Voz**:
  - **Automático (VAD)**: Detecta quando você começa a falar e traduz automaticamente quando detecta uma pausa/silêncio.
  - **Push-to-Talk (PTT)**: Segure a barra de espaço ou o botão no app para falar; solte para disparar a tradução imediatamente.
- **Campo de Fala Rápida por Texto**: Digite uma frase em português e aperte Enter para que o Parrot fale em inglês na reunião sem que você precise falar em voz alta.
- **Dublagem do Sistema**: Captura fala em inglês de qualquer aplicativo e reproduz a tradução portuguesa em uma fila ordenada, sem cortar frases.
- **Legendas HUD Flutuantes**: Clique em **"Legendas HUD"** para abrir uma janela translúcida independente que fica sempre no topo da tela, perfeita para posicionar sobre o Zoom ou Google Meet.
- **Painel de Configurações**: Ajuste dispositivos de entrada/saída, vozes, tempo de pausa do VAD e teste de som.

---

## 🛠️ Tecnologias Utilizadas

- **Frontend**: HTML5, Tailwind CSS, WebSockets e Glassmorphism UI.
- **Desktop Runtime**: `pywebview` com WebKit no macOS e WebView2 no Windows.
- **Backend**: FastAPI, Uvicorn e AsyncIO.
- **Áudio Core**: `sounddevice`, `soundfile`, `miniaudio`, `numpy`.
- **Captura do Sistema**: ScreenCaptureKit (macOS) e SoundCard/WASAPI loopback (Windows).
- **Drivers Virtuais**: `Perssua` / BlackHole no macOS; VB-CABLE / VoiceMeeter no Windows.
- **IA & TTS**: `openai`, `deep-translator`, `edge-tts`, `SpeechRecognition`.

---

## 📦 Builds distribuíveis

O workflow `.github/workflows/build-release.yml` gera um `.app`/`.dmg` autocontido para macOS e um `.exe` autocontido para Windows com PyInstaller. As configurações do usuário ficam fora do pacote:

- macOS: `~/Library/Application Support/Parrot/.env`
- Windows: `%APPDATA%\Parrot\.env`

Ao criar uma tag `v*`, o GitHub Actions publica os pacotes da versão automaticamente.
