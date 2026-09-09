# Contexto do Projeto — Parrot

## Descrição
O **Parrot** é uma aplicação desktop inteligente para tradução de chamadas internacionais em tempo real (Google Meet, Zoom, Microsoft Teams, Discord, etc.).
O usuário fala em Português no seu microfone, e o software traduz e sintetiza a fala em Inglês para a chamada através de um microfone virtual (como o driver Perssua/BlackHole). Do mesmo modo, a fala em Inglês dos participantes da chamada é transcrita e traduzida para Português em tempo real, fornecendo legendas dinâmicas e áudio nos fones do usuário.

## Stack / Tecnologias
- **Desktop Frontend**: Interface moderna desktop com suporte a overlay de legendas HUD, seleção de dispositivos de áudio e visualização de ondas sonoras.
- **Backend / Engine de Áudio**: Python 3 com suporte a CoreAudio / PyAudio / SoundDevice.
- **Microfone Virtual**: Integração com BlackHole / Perssua (driver virtual de áudio já presente no macOS).
- **Motores de IA**:
  1. **Modo OpenAI (Alta Fidelidade)**: Whisper / gpt-4o-transcribe + GPT-4o-mini (tradução contextual instantânea) + OpenAI TTS (tts-1).
  2. **Modo Gratuito (100% Free / Offline-friendly)**: Deep-Translator / Google Translate + Edge-TTS (vozes neurais gratuitas de alta qualidade) / macOS `say` nativo.

## Convenções e Padrões
- UI moderna e intuitiva no padrão Dark Mode com estética nativa macOS.
- Cursor pointer em todos os elementos clicáveis e feedback visual imediato de status (gravando, traduzindo, falando).
- Latência minimizada com streaming e detecção de silêncio (VAD - Voice Activity Detection).

## Notas Importantes
- No macOS, a injeção de áudio traduzido no Meet/Zoom/Discord usa o driver virtual **Perssua** (Existential Audio / BlackHole) como microfone da chamada.
- O aplicativo deve funcionar tanto com chave OpenAI quanto em modo gratuito.

## Histórico de Decisões
- **2026-09-09**: Criação do projeto Parrot. Definição da arquitetura de áudio bidirecional (microfone físico -> tradução -> microfone virtual Perssua; e áudio da reunião -> transcrição/tradução -> fone + HUD de legendas). Suporte duplo a motor OpenAI e motor gratuito Edge-TTS.
