# Marketing & Documentation Website Plan

## Context
Primer needs a public-facing website for marketing, documentation, and community. The existing MkDocs site handles reference docs but can't do marketing landing pages. The React dashboard is an authenticated SPA.

## Framework: Astro

**Why Astro:**
- Zero JS by default, Islands architecture for interactive components
- First-class MDX support for blog and docs
- Content collections with type-safe frontmatter
- Tailwind v4 native support (matches dashboard)
- Static site generation — ideal for GitHub Pages/Cloudflare

**Why not Next.js:** Unnecessary runtime complexity for a static marketing site.
**Why not extending MkDocs:** Poor for custom marketing layouts, hero sections, interactive demos.

## Project Location

```
insights/
  brand/                  # Shared brand assets (exists)
  docs/                   # MkDocs reference docs (exists)
  frontend/               # React dashboard SPA (exists)
  website/                # NEW: Astro marketing site
    src/
      assets/             # Images, illustrations
      components/         # Astro + React island components
      content/            # MDX content collections (blog, docs)
      layouts/            # Page layouts
      pages/              # Route pages
      styles/             # CSS with shared design tokens
    public/               # Static assets (logos, OG images)
    astro.config.mjs
    package.json
```

## Design Direction

Target aesthetic: **Linear.app, Vercel.com, Resend.com** — clean, minimal, developer-focused. NOT AgentsView's flashy style.

**Do:**
- Generous whitespace (80-120px section padding)
- Brand indigo `#6366F1` as sole accent color with opacity variations
- Dark hero sections with `#0F0B2A` background
- Isometric geometric elements extending the cube motif
- Space Grotesk 600 for headings, system fonts for body

**Don't:**
- Gradients on UI elements
- Multiple accent colors
- Illustrations of people or screens
- Excessive animation or parallax

## Design Token Sharing

Extract shared tokens from `brand/BRAND.md` into `brand/tokens.css`:
```css
--color-primary: oklch(0.585 0.233 264);   /* #6366F1 */
--primer-dark: #0F0B2A;
--primer-50 through --primer-900
```
Both `frontend/` and `website/` import this file.

## Site Structure

### Landing Page (`/`)
1. **Nav** — Logo, Features, Docs, Blog, GitHub, "Get Started" CTA, theme toggle
2. **Hero** — Dark bg, "See how your team uses AI coding tools", terminal animation, two CTAs
3. **Feature grid** — 6 cards: Dashboard, Cost Analysis, Friction Detection, MCP Sidecar, GitHub Integration, AI Maturity
4. **Architecture diagram** — Interactive isometric version of README diagram
5. **Dashboard preview** — Real screenshots with indigo tint
6. **Installation CTA** — Terminal code block with quickstart
7. **Footer** — Links, GitHub, MIT license

### Documentation Hub (`/docs/`)
Phase 1: Card grid linking to existing MkDocs pages
Phase 2: Migrate MkDocs content to Astro MDX

### Comparison Page (`/compare`)
Feature comparison table: Primer vs AgentsView vs DIY. Key differentiators: open source, self-hosted, privacy-first, MCP sidecar.

### Pricing Page (`/pricing`)
Two tiers: Community (free, self-hosted, all features) and Hosted (future, managed).

### Blog (`/blog`)
Astro content collections with MDX. Initial posts:
1. "Introducing Primer" — launch announcement
2. "Understanding your team's Claude Code usage"
3. "Setting up Primer in 5 minutes"

## Content Strategy

**Value proposition:** "See how your team uses AI coding tools"

**Messaging pillars:**
1. **Visibility** — Know what's happening across your AI usage
2. **Efficiency** — Find friction, track costs, accelerate adoption
3. **Privacy** — Self-hosted, data stays on your infrastructure
4. **Integration** — Works with Claude Code, GitHub, MCP

**Differentiators:** Open source (MIT), self-hosted, MCP sidecar (unique), multi-agent support, AI maturity scoring.

## Technical Details

### Hero Terminal Animation (React Island)
```
$ curl -fsSL https://primer.dev/install.sh | sh
  Installing Primer...
  Dashboard: http://localhost:8000
  Sessions will be tracked automatically.
```
Typing animation, `#0F0B2A` background, `#6366F1` prompt.

### Dark Mode
Same pattern as dashboard: localStorage `primer-theme`, `.dark` class, `prefers-color-scheme` detection. Shared key means preference carries across dashboard and website.

### Component Library
Astro components (zero JS) mirroring dashboard patterns:
- `Button.astro` — same variant/size system as `button.tsx`
- `Card.astro` — same rounded-2xl, border pattern
- React islands only for: terminal animation, interactive diagram, theme toggle

## Deployment

### Phase 1: GitHub Pages
GitHub Actions on push to `main` (paths: `website/**`, `brand/**`):
```yaml
- run: cd website && npm ci && npm run build
- uses: actions/deploy-pages@v4
```

### Phase 2: Custom Domain
`primer.dev` → GitHub Pages / Cloudflare Pages. Add canonical URLs and OG meta tags.

## Implementation Sequence

| Phase | Task |
|---|---|
| 1 | Scaffold Astro project, Tailwind v4, brand tokens |
| 2 | Base layout (nav, footer, dark mode, responsive) |
| 3 | Landing page (hero, features, architecture, CTA) |
| 4 | Hero terminal animation (React island) |
| 5 | Docs hub page (links to MkDocs) |
| 6 | Comparison page |
| 7 | Pricing page |
| 8 | Blog setup + 3 initial posts |
| 9 | SEO (meta tags, OG images, sitemap) |
| 10 | GitHub Actions deployment |
| 11 | Migrate MkDocs to Astro MDX (Phase 2) |

## Challenges
1. **Token sharing** — Dashboard uses OKLCH, BRAND.md uses hex. Author in hex, convert in both consumers.
2. **MkDocs coexistence** — Marketing site and MkDocs both generate static output; need merge or redirect strategy.
3. **Screenshots** — Need real dashboard captures; consider Playwright automation.
4. **SEO** — New domain starts with zero authority; link from README and existing docs.
