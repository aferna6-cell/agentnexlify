# AgentNexLiFy Design System

## Brand Identity
- Product: AgentNexLiFy — AI-powered business automation
- Personality: Professional, modern, trustworthy, technical
- Target: Small business owners managing leads, appointments, and automations

## Color Palette

### Dark Theme (Default)
- Background primary: `#0a0a0f` — main app background
- Background secondary: `#111118` — sidebar, secondary panels
- Background card: `#16161f` — cards, modals, drawers
- Accent: `#00bfff` — CTAs, active states, links, highlights
- Accent dim: `rgba(0, 191, 255, 0.15)` — accent backgrounds, badges
- Accent glow: `rgba(0, 191, 255, 0.3)` — focus rings, hover states
- Text primary: `#f0f0f5` — headings, body text
- Text secondary: `#9494a8` — labels, descriptions, metadata
- Text muted: `#5c5c72` — placeholders, disabled text
- Border: `#222233` — card borders, dividers
- Border hover: `#2a2a3d` — interactive border states
- Hover overlay: `rgba(255, 255, 255, 0.04)` — row/item hover

### Light Theme
- Background primary: `#f5f5f7`
- Background secondary: `#f8f8fa`
- Background card: `#ffffff`
- Accent: `#0088cc`
- Text primary: `#1a1a2e`
- Text secondary: `#555566`
- Border: `#e0e0e8`
- Shadow card: `0 1px 3px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(0, 0, 0, 0.04)`

### Status Colors
- Success/Green: `#34d399` — completed, online, positive metrics
- Error/Red: `#ff4444` — errors, destructive actions, negative metrics
- Warning/Yellow: `#f5a623` — warnings, pending states
- Purple: `#8b5cf6` — tags, categories, special highlights
- Each has a dim variant at 15% opacity for backgrounds

## Typography
- Font family: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`
- Body text: 14px regular
- Small text: 12px regular
- Headings: 16-24px semibold (600)
- Page titles: 20-24px bold (700)
- Stat numbers: 28-36px bold
- Labels: 12px uppercase tracking, text-secondary color
- Monospace (code): `'SF Mono', 'Fira Code', monospace`

## Spacing
- Base unit: 4px
- Padding xs: 4px
- Padding sm: 8px
- Padding md: 16px
- Padding lg: 24px
- Padding xl: 32px
- Gap between cards: 16px
- Section spacing: 24-32px
- Sidebar width: 240px (collapsed: 64px)

## Border Radius
- Default (cards, modals): `10px`
- Small (buttons, inputs, badges): `6px`
- Pill (tags, status badges): `20px`
- Circle (avatars, icons): `50%`

## Components

### Buttons
- Primary: accent background, dark text, 6px radius, semibold, 8-12px vertical padding, 16-24px horizontal
- Secondary: transparent, accent text, 1px accent border, 6px radius
- Danger: red background on hover, red-dim default
- Ghost: transparent, text-secondary, hover overlay on hover
- Disabled: 50% opacity, cursor not-allowed
- All buttons: transition 0.15s ease

### Cards
- Background: var(--bg-card)
- Border: 1px solid var(--border)
- Radius: 10px
- Padding: 20-24px
- No shadow in dark mode; light shadow in light mode
- Hover: border-color transitions to var(--border-hover)

### Inputs & Forms
- Background: var(--bg-secondary)
- Border: 1px solid var(--border)
- Radius: 6px
- Padding: 10px 14px
- Text: var(--text-primary)
- Placeholder: var(--text-muted)
- Focus: 2px accent glow outline, border-color accent
- Labels: 12px, text-secondary, uppercase tracking, margin-bottom 6px

### Tables
- Header: text-secondary, 12px uppercase, border-bottom
- Rows: hover with var(--hover-overlay)
- Cell padding: 12px 16px
- Alternating rows: not used (hover highlight only)

### Modals & Drawers
- Overlay: rgba(0, 0, 0, 0.6) with backdrop-blur 4px
- Content: bg-card, 10px radius, 24px padding
- Max-width: 500px (small), 700px (medium), 900px (large)
- Close button: top-right, ghost style

### Sidebar Navigation
- Background: var(--bg-secondary)
- Active item: accent-dim background, accent text, left accent border
- Inactive item: text-secondary, hover overlay on hover
- Icon + label layout, 12px gap
- Collapsible to icon-only mode

### Status Badges
- Online/Active: green + green-dim background
- Offline/Inactive: text-muted + bg-secondary
- Warning: yellow + yellow-dim background
- Error: red + red-dim background
- Pill shape (20px radius), 6px 12px padding, 11px font

### Charts (Recharts)
- Line/Area: accent color (#00bfff)
- Grid: var(--border) at 20% opacity
- Tooltip: bg-card, 1px border, 6px radius
- Legend: text-secondary, 12px
- Fill gradients: accent color fading to transparent

### Empty States
- Centered in container
- Icon: 48px, text-muted color
- Title: 16px, text-primary
- Description: 14px, text-secondary
- CTA button: primary style
- Never show just "0" or "No data" — always helpful with next action

## Layout Rules
- Dashboard uses CSS Grid: sidebar + main content
- Main content max-width: none (full-width within padding)
- Page padding: 24px on desktop, 16px on mobile
- Card grids: auto-fill, min 280px per card
- Responsive breakpoint: 768px (sidebar collapses)
- Stat cards: 4-column grid on desktop, 2 on tablet, 1 on mobile
- Always dark theme by default — match it for any new components
- Consistent 16px gap between all grid items

## Animation
- Transitions: 0.15s ease for hover, 0.2s ease for expand/collapse
- No heavy animations — keep it snappy
- Loading states: subtle pulse animation on skeleton elements
- Page transitions: none (instant mount)

## Accessibility
- All interactive elements have visible focus states (accent glow outline)
- Minimum contrast ratio: 4.5:1 for body text, 3:1 for large text
- All images need alt text
- Form inputs need associated labels
- Color is never the only indicator of state (always pair with text/icon)

## Do NOT
- Use random colors not in the palette
- Use different border radius values than 6px/10px/20px/50%
- Add box shadows in dark mode (only in light mode)
- Use fonts other than Inter
- Create inconsistent button styles
- Use bright white (#fff) as text in dark mode — use #f0f0f5
- Add gratuitous animations or transitions over 0.3s
