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
- UI moderna e limpa no padrão **Light Mode** por padrão (com alternador para Dark Mode no menu).
- Estilo macOS nativo com bordas suaves (`rounded-lg`, sem formatos de pílula exagerados).
- Cursor pointer em todos os elementos clicáveis e feedback visual imediato de status (gravando, traduzindo, falando).
- Spotlight Tour onboarding usando máscara SVG nativa com recorte (`mask cutout`), garantindo que os cartões destacados nunca fiquem por cima do balão de explicação.
- Latência minimizada com streaming e detecção de silêncio (VAD - Voice Activity Detection).

## Notas Importantes
- No macOS, a injeção de áudio traduzido no Meet/Zoom/Discord usa o driver virtual **Perssua** (Existential Audio / BlackHole) como microfone da chamada.
- O aplicativo funciona tanto com chave OpenAI (usando o modelo mais recente `gpt-5.4-mini`) quanto em modo gratuito com Edge-TTS.

## Histórico de Decisões
- **2026-09-09**: Criação do projeto Parrot. Definição da arquitetura de áudio bidirecional (microfone físico -> tradução -> microfone virtual Perssua; e áudio da reunião -> transcrição/tradução -> fone + HUD de legendas). Suporte duplo a motor OpenAI e motor gratuito Edge-TTS.
- **2026-09-09**: Refatoração do Spotlight Tour Onboarding: substituição do hack de `box-shadow` e `z-index: 9995` nos elementos do DOM por máscara SVG com recorte transparente (`<mask id="tour-mask">`) e balão posicionado de forma inteligente no lado oposto ao elemento destacado (ex: quando destaca a coluna da reunião à direita, o balão flutua à esquerda sobre a área escura), garantindo sobreposição e legibilidade perfeitas.
- **2026-09-09**: Refinamento visual da barra de navegação: eliminação da borda/quadrado externo do ícone (o papagaio verde agora preenche o squircle com cantos transparentes e tamanho ampliado). Remoção das badges avulsas de status e ajuda da navbar, centralizando tudo dentro do dropdown do botão de perfil `DJ` com indicador sutil de atividade.
- **2026-09-09**: Implementação do Gravador de Áudio da Chamada (Meeting Audio Capture): inclusão de um segundo stream `meeting_recorder` nativo no CoreAudio para capturar a voz dos gringos do Discord/Meet/Zoom via driver Perssua/Loopback; supressão de auto-eco durante transmissões do microfone do usuário; tradução ao vivo EN -> PT com envio para coluna de reunião, HUD e sintetização nos fones; e inclusão do seletor de áudio da chamada no modal de configurações.
- **2026-09-09**: Unificação da interface em Chat Conversacional Único: substituição do layout de 2 colunas paralelas por um stream contínuo de mensagens no estilo mensageiro (WhatsApp/iMessage/Telegram). As falas do usuário traduzidas para a chamada ficam alinhadas à direita em balões verdes (`bg-emerald-600`), e as falas dos participantes da reunião traduzidas para o usuário ficam alinhadas à esquerda em balões neutros (`bg-slate-100`). Remoção completa de botões de simulação e segundo input de teste, mantendo apenas a barra de digitação rápida no rodapé e o toggle de voz VAD/PTT no topo do chat.
- **2026-09-09**: Eliminação de Vícios de IA & Interface em Tela Cheia Sem Card: remoção completa da section hero superior (`Tradução em Tempo Real`, botão avulso e subtitle redundante). O chat agora ocupa 100% da viewport vertical de forma fluida e sem container em formato de card artificial. Título simplificado para "Conversa" com tooltip discreto `(?)` no hover. Botão de ação unificado dinamicamente no rodapé: com o campo de texto vazio funciona como play/pause da tradução contínua (`Iniciar / Parar Tradução`); ao digitar, transforma-se instantaneamente em botão de envio (`Falar`). O seletor de modo de voz (Automático vs Push-to-Talk) foi integrado ao modal de configurações.
- **2026-09-09**: Restauração da Silhueta Canônica do Papagaio (Ícone Flat e Transparente): recuperação da silhueta exata do papagaio original pousado no galho (do commit `a2ca0ec`), remoção total do fundo preto/squircle e do relevo 3D/sombras, gerando um vetor 2D flat puro na cor verde esmeralda (`#10B981`) centralizado perfeitamente para `icon.png`, `icon.svg`, `AppIcon.icns` e `Parrot.app`.
- **2026-09-09**: Preservação do Subtítulo de Orientação: manutenção explícita do subtítulo *"Inicie a tradução para ouvir os participantes do Meet, Zoom ou Discord e transmitir sua voz em inglês"* no estado vazio do chat, assegurando orientação contextual imediata ao usuário.
- **2026-09-09**: Refinamento Minimalista da Navbar e Barra de Ação: eliminação do subheader intermediário com migração do botão de ajuda (?) e indicadores de status/mic para a barra superior. Redução da espessura do input e botão no rodapé para formato slim e elegante (`h-9/h-9.5`), tornando o botão exclusivamente iconográfico com o ícone universal de tradução (Languages SVG) e texto contextual movido para tooltip flutuante no hover.
- **2026-09-09**: Restauro e Reorganização da Navbar e Botão de Ação: correção do dimensionamento do ícone de tradução no botão de ação inferior (eliminando o colapso por classe Tailwind não-padrão e aplicando dimensões explícitas 20x20); restauração do diâmetro e tipografia do avatar de perfil `DJ` (`w-8 h-8` com ponto de status `8px` no canto inferior direito); remoção completa do rótulo textual `• Inativo` da barra superior; e reposicionamento do botão de ajuda `?` para a extremidade direita, imediatamente antes do avatar `DJ`.
- **2026-09-09**: Limpeza do Estado Vazio do Chat: remoção definitiva do subtítulo explicativo e reformatação da mensagem "Nenhuma fala registrada na chamada ainda" para tom cinza suave e desbotado (`text-slate-400 dark:text-slate-500 font-normal`), eliminando o preto/negrito anterior e tornando o visual minimalista e calmo.
- **2026-09-09**: Ícone Nativo macOS com Squircle Branco e Sombra (Padrão Telegram/Safari): criação da base squircle contínua Apple HIG (824x824 em 1024x1024) com fundo branco, sutil gradiente vertical (2.5%), borda interna 1.5px e dupla sombra de elevação para `icon.png`, `AppIcon.icns` e `Parrot.app`. O papagaio verde canônico (`#10B981`) fica proporcionalmente centralizado (71% de altura), integrando-se nativamente à Dock/barra de tarefas ao lado de aplicativos como Telegram e Safari. Na barra de navegação da interface web, foi preservada a silhueta vetorial plana transparente (`icon-flat.svg`) para manter o visual limpo sem bloco artificial em modo escuro.


