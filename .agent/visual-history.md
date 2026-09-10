# Histórico Visual do Projeto — Parrot

> Use os identificadores para restaurar qualquer versão: `Cores - C - v1`, `Tipografia - T - v1`, `Componentes - K - v2`, `Tema Completo - TC - v3`, etc.

---

## Cores - C - v1

**Data:** 2026-09-09  
**Motivo:** Definição inicial da paleta do Parrot (Verde Papagaio Brasileiro + Dark Glassmorphism)

```json
{
  "primary": "#10B981",
  "primary-hover": "#059669",
  "accent-yellow": "#F59E0B",
  "accent-blue": "#38BDF8",
  "background": "#0F172A",
  "surface": "#1E293B",
  "surface-border": "#334155",
  "error": "#EF4444",
  "success": "#10B981",
  "warning": "#F59E0B",
  "text-primary": "#F8FAFC",
  "text-secondary": "#94A3B8"
}
```

---

## Tipografia - T - v1

**Data:** 2026-09-09  
**Motivo:** Definição inicial da tipografia (SF Pro Display / system-ui com legibilidade para legendas HUD)

```json
{
  "display": "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', Roboto, sans-serif",
  "body": "-apple-system, BlinkMacSystemFont, 'SF Pro Text', 'Segoe UI', Roboto, sans-serif",
  "code": "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
  "size-base": "14px",
  "size-hud": "18px",
  "weight-regular": "400",
  "weight-semibold": "600",
  "weight-bold": "700"
}
```

---

## Componentes - K - v2

**Data:** 2026-09-09  
**Motivo:** Atualização do ícone oficial para silhueta 3D verde minimalista virada para a direita (estilo minimalista Reserva / macOS squircle app icon)

---

## Tema Completo - TC - v3 (Light Mode Padrão)

**Data:** 2026-09-09  
**Motivo:** Transição para Light Mode como padrão do sistema (Apple macOS Light HIG), com superfícies limpas, cards brancos e acentos esmeralda.

```json
{
  "theme": "light",
  "primary": "#059669",
  "primary-hover": "#047857",
  "background": "#F8FAFC",
  "surface": "#FFFFFF",
  "surface-border": "#E2E8F0",
  "text-primary": "#0F172A",
  "text-secondary": "#475569",
  "text-muted": "#64748B",
  "feed-user": "#ECFDF5",
  "feed-meeting": "#F0F9FF"
}
```

---

## Componentes - K - v4 (Restauração da Silhueta Canônica do Papagaio no Galho)

**Data:** 2026-09-09  
**Motivo:** Restauração fiel e canônica da silhueta exata do papagaio pousado no galho (do commit `a2ca0ec`), eliminando o fundo escuro/squircle (100% transparente) e o relevo 3D/clay/sombras, convertendo em vetor 2D flat moderno na cor esmeralda (`#10B981`) perfeitamente centralizado e balanceado em 1024x1024 para ícone de app, dock e navbar.

```json
{
  "logo_style": "canonical_perched_parrot_flat_vector",
  "logo_color": "#10B981",
  "logo_background": "transparent_100%",
  "source_shape": "commit_a2ca0ec_canonical",
  "canvas_size": "1024x1024",
  "bounding_box": "631x820_centered"
}
```

---

## Componentes - K - v5 (Navbar Integrada, Barra de Chat Slim & Botão Tradução com Tooltip)

**Data:** 2026-09-09  
**Motivo:** Remoção completa da subheader intermediária. O botão de ajuda (?) e os indicadores de status/áudio foram integrados diretamente na barra de navegação superior. O campo de digitação e o botão de ação no rodapé foram refinados para um perfil mais baixo e elegante (`h-9 / h-9.5`). O botão principal agora exibe exclusivamente o ícone universal de tradução (Languages SVG), com o texto da ação movido para tooltip flutuante no hover ("Iniciar Tradução", "Parar Tradução", "Falar na Chamada").

```json
{
  "header_layout": "single_navbar_integrated",
  "help_tooltip_location": "navbar_adjacent_to_logo",
  "status_indicators_location": "navbar_right",
  "bottom_input_height": "h-9_to_h-9.5",
  "action_button": {
    "style": "icon_only_square_rounded_lg",
    "icon": "lucide_languages_translate",
    "tooltip": "floating_hover_tooltip"
  }
}
```

---

## Componentes - K - v6

**Data:** 2026-09-09  
**Motivo:** Restauração do dimensionamento do ícone de tradução no botão inferior (SVG explícito 20x20), restauração do avatar DJ (`w-8 h-8` com ponto de status `8px` no canto), remoção de `• Inativo` da navbar e reposicionamento do botão `?` para a direita (antes do dropdown DJ).

```json
{
  "navbar": {
    "left": "brand_logo_and_title_only",
    "right": [
      "mic_visualizer_when_active",
      "help_button_question_mark",
      "user_menu_avatar_dj_with_status_dot"
    ],
    "removed": "status_text_inativo"
  },
  "avatar_dj": {
    "size": "w-8 h-8 (32px)",
    "status_dot": "w-2 h-2 (8px) at -bottom-0.5 -right-0.5"
  },
  "action_button": {
    "dimensions": "w-9 h-9 sm:w-10 sm:h-10",
    "icon": "lucide_languages_20x20_explicit_white",
    "hover_tooltip": "dynamic_action_description"
  }
}
```

---

## Componentes - K - v7

**Data:** 2026-09-09  
**Motivo:** Remoção do subtítulo longo explicativo no estado vazio do chat e estilização do texto "Nenhuma fala registrada na chamada ainda" com cor cinza desbotada/apagada (`text-slate-400 dark:text-slate-500 font-normal`), eliminando o peso preto e negrito.

```json
{
  "chat_empty_state": {
    "title_text": "Nenhuma fala registrada na chamada ainda",
    "title_style": "text-slate-400 dark:text-slate-500 text-xs sm:text-sm font-normal",
    "subtitle": "removed"
  }
}
```

---

## Componentes - K - v8 (Ícone do Aplicativo macOS com Squircle Branco no Padrão Telegram/Safari)

**Data:** 2026-09-09  
**Motivo:** Atualização do ícone da aplicação para a Dock / barra de tarefas macOS (`icon.png`, `AppIcon.icns`, `Parrot.app` e `assets/icon.svg`) implementando o padrão de design macOS (Apple HIG): base squircle com curvatura contínua (824x824 em canvas 1024x1024), fundo branco suave com sutil gradiente vertical (2.5%), borda interna de 1.5px e dupla sombra de elevação (difusa + contato). O papagaio verde canônico (`#10B981`) fica centralizado a 71% de proporção vertical, em total harmonia visual ao lado de apps como Telegram e Safari. Na barra de navegação da interface web, foi preservada a silhueta vetorial plana (`icon-flat.svg`) para manter a integração limpa sem caixa artificial em modo escuro.

```json
{
  "dock_app_icon": {
    "canvas": "1024x1024_rgba",
    "tile_shape": "macos_squircle_continuous_curvature",
    "tile_dimensions": "824x824_centered",
    "corner_radius": "185px (smoothing 0.6)",
    "tile_background": "linear_gradient(#FFFFFF to #F8FAFC)",
    "tile_border": "1.5px rgba(0,0,0,0.07)",
    "tile_shadow": {
      "diffuse": "offset_y_32px_blur_44px_opacity_15%",
      "ambient": "offset_y_8px_blur_16px_opacity_8%"
    },
    "emblem": {
      "graphic": "canonical_perched_parrot",
      "color": "#10B981",
      "scale": "71%_of_squircle_height (585px)",
      "alignment": "centered_horizontal_and_vertical"
    }
  },
  "navbar_brand": {
    "source": "/assets/icon-flat.svg",
    "style": "clean_flat_vector_transparent"
  }
}
```
