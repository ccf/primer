# Primer Brand Guide

## Mark

The Primer mark is an isometric cube with three translucent faces at varying opacities, thin solid edges, and vertex connection nodes. It represents a structure to be seen through and decoded — a direct metaphor for what Primer does: making complex AI usage patterns transparent and understandable.

The cube is constructed on an isometric grid with faces at 15%, 35%, and 55% opacity, giving it depth and dimensionality while remaining a single-color asset. The vertex dots at each corner suggest connection points in a network of insights.

The mark works at sizes from 16px (favicon) to 512px+ (marketing).

## Logo Variants

| File | Use |
|------|-----|
| `logo-mark.svg` | Standalone mark (indigo on light) |
| `logo-mark-light.svg` | Standalone mark (white on dark) |
| `logo-wordmark.svg` | Mark + wordmark (light backgrounds) |
| `logo-wordmark-light.svg` | Mark + wordmark (dark backgrounds) |

## Wordmark

The wordmark uses **Space Grotesk** at weight 600 (semibold), all lowercase, with tight letter-spacing (-2px at 36px). The lowercase treatment and tight tracking give it a modern, approachable feel — the text is the logo, not text next to an icon.

**Font**: [Space Grotesk](https://fonts.google.com/specimen/Space+Grotesk) (OFL license)
**Weight**: 600 (SemiBold)
**Case**: lowercase
**Tracking**: -2px at display size

Fallback stack: `'Space Grotesk', system-ui, sans-serif`

## Color System

### Brand Color

**Primer Indigo** `#6366F1` — the single signature color.

### Four-Tier Ramp

| Token | Hex | Use |
|-------|-----|-----|
| `primer-brand` | `#6366F1` | Logo, primary accents, CTAs |
| `primer-foreground` | `#4338CA` | Accessible text on white (WCAG AA) |
| `primer-surface` | `#EEF2FF` | Light tint backgrounds, cards |
| `primer-border` | `#C7D2FE` | Borders, dividers, subtle accents |

### Extended Palette

| Name | Hex | Use |
|------|-----|-----|
| `primer-dark` | `#0F0B2A` | Dark text, dark-mode backgrounds |
| `primer-50` | `#EEF2FF` | Lightest surface |
| `primer-100` | `#E0E7FF` | Hover surfaces |
| `primer-200` | `#C7D2FE` | Borders |
| `primer-400` | `#818CF8` | Secondary accents, charts |
| `primer-500` | `#6366F1` | Brand primary |
| `primer-600` | `#4F46E5` | Hover states on primary |
| `primer-700` | `#4338CA` | Foreground text |
| `primer-900` | `#312E81` | Deep accents |

### Semantic Colors (UI Only)

These are separate from brand colors and should never be substituted.

| State | Hex |
|-------|-----|
| Success | `#16A34A` |
| Warning | `#D97706` |
| Critical | `#DC2626` |
| Info | `#2563EB` |

## Typography

**Brand / Display**: Space Grotesk 600, tight tracking
**UI / Body**: `system-ui, -apple-system, 'Segoe UI', sans-serif`, weight 400-600
**Code**: `ui-monospace, 'SF Mono', Menlo, monospace`

## Illustration Principles

1. **Abstract over literal** — represent concepts geometrically, not with illustrations of people or screens
2. **Isometric spatial language** — use the cube's isometric grid as the basis for all supporting artwork
3. **Translucency as metaphor** — varying opacity conveys layers of data being decoded, seen through, understood
4. **Connection nodes** — vertex dots from the mark can extend into illustrations as data points in a network
5. **Dark-background hero sections** — dark (`#0F0B2A`) with brand-colored geometric elements
6. **Gradient washes for atmosphere only** — gradients appear in marketing contexts, never in UI elements or icons
7. **Single accent color per composition** — use opacity variations of `#6366F1` for depth rather than multiple colors
