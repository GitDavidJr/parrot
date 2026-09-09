# Contexto de Design — Parrot

## 🎨 Design System
- Interface Desktop moderna com tema escuro nativo (Dark Glassmorphism / macOS HIG).
- Cores vibrantes com verde esmeralda e papagaio brasileiro (#10B981, #059669, #047857) e toques de amarelo canário (#F59E0B) e azul celeste (#0284C7).
- Painel de controle compacto com abas intuitivas: Tradução ao Vivo, Dispositivos de Áudio, HUD de Legendas, Configurações de IA.

## 🖋️ Tipografia
- Fonte da interface: SF Pro Display / Inter / system-ui (-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif).
- Tamanhos:
  - Títulos: 18px a 24px, semibold/bold
  - Texto base: 14px, regular
  - Legendas ao vivo (HUD): 16px a 20px, medium, com alto contraste
  - Metadados e status: 12px, regular/medium

## 🎨 Paleta de Cores
- Primary (Verde Papagaio): `#10B981` (Emerald 500), Hover: `#059669`
- Accent (Amarelo Canário): `#F59E0B`
- Accent Blue: `#38BDF8`
- Background Escuro: `#0F172A` (Slate 900)
- Surface / Cards: `#1E293B` (Slate 800) com bordas sutis `#334155`
- Text Primary: `#F8FAFC`
- Text Secondary: `#94A3B8`
- Active Recording / Waveform: `#EF4444` (Gravando) e `#10B981` (Falando/Traduzindo)

## 📐 Espaçamento e Grid
- Escala de 4px / 8px (p-2: 8px, p-3: 12px, p-4: 16px, gap-3: 12px, gap-4: 16px).
- Border-radius padrão: 12px (rounded-xl) para containers e 8px para botões.

## 🧩 Componentes Base
- StatusIndicator (badge com pulso animado: Pronto, Escutando, Traduzindo, Transmitindo)
- AudioDeviceSelector (dropdowns com identificação automática de Mic Físico, Mic Virtual Perssua, e Saída de Som)
- LiveCaptionsPanel (janela / card com transcrição lado a lado: "Você (PT) -> Chamada (EN)" e "Chamada (EN) -> Você (PT)")
- EngineToggle (Botão seletor rápido: ⚡ OpenAI vs 🆓 Modo Gratuito)
- AudioVisualizer (indicador de nível sonoro em tempo real)

## ♿ Padrões de Acessibilidade
- Contraste WCAG AA em todos os textos e botões.
- Foco visível e atalhos rápidos de teclado (ex: Mute / Ativar Tradução com Espaço ou tecla global).

## 📱 Cursores
- Todos os botões, selects, switches e abas possuem explicitamente `cursor-pointer`.
- Entradas de texto possuem `cursor-text`.
- Elementos desabilitados possuem `cursor-not-allowed` com opacidade reduzida.
