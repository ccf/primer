# Primer Frontend

React dashboard for the Primer analytics platform.

## Tech Stack

- **React 18** with TypeScript
- **Vite** for build tooling
- **Tailwind CSS v4** with CSS custom properties for theming
- **React Router** for client-side routing
- **TanStack Query** for data fetching and caching
- **Recharts** for charts and visualizations
- **Lucide React** for icons
- **date-fns** for date formatting

## Development

```bash
npm install        # Install dependencies
npm run dev        # Start dev server (port 5173)
npm run build      # Production build
npm run preview    # Preview production build
npm run lint       # ESLint check
npx tsc -b --noEmit  # Type check
```

## Component Architecture

```
src/
  components/
    layout/         # AppShell, Header, Sidebar, DateRangePicker
    dashboard/      # StatCard, charts (Activity, Cost, Model, Tool, Outcome, SessionType)
    sessions/       # SessionTable, SessionDetailPanel, SessionFilters
    analytics/      # FrictionList
    shared/         # LoadingSkeleton, EmptyState, Badge, Button, Card
    ui/             # Primitive UI components (Button, Badge, Card)
  hooks/
    use-api-queries.ts     # TanStack Query hooks for all API endpoints
    use-keyboard-navigation.ts  # Arrow key navigation for tables
  lib/
    api.ts           # Fetch wrapper with auth headers
    auth-context.tsx  # OAuth/API key authentication provider
    theme-context.tsx # Dark mode ThemeProvider (light/dark/system)
    utils.ts         # Formatters (tokens, duration, cost, numbers)
  pages/
    overview.tsx      # Main dashboard with KPIs, charts, cost analysis
    sessions.tsx      # Session list with filters and keyboard nav
    session-detail.tsx # Session detail with copy-to-clipboard
    engineers.tsx     # Engineer list
    login.tsx         # Login page (OAuth + API key)
  types/
    api.ts            # TypeScript interfaces matching backend schemas
    auth.ts           # Auth user type
```

## Theming

The app supports light and dark mode via CSS custom properties defined in `index.css`. The `.dark` class on `<html>` activates dark theme variables. Theme preference is stored in `localStorage` under `primer-theme`.

The `ThemeProvider` in `lib/theme-context.tsx` manages the theme state and provides a `useTheme()` hook with `{ theme, resolved, setTheme }`.

## Key Patterns

- **Date Range Filtering** — All analytics hooks accept optional `startDate`/`endDate` params. The `DateRangePicker` in the header provides preset ranges (7d, 30d, 90d, 1y).
- **Cost Estimation** — The backend estimates costs using published Anthropic model pricing. The frontend displays cost cards, daily cost trends, and per-model cost breakdowns.
- **Keyboard Navigation** — The `useKeyboardNavigation` hook enables Arrow/Enter/Escape navigation on the sessions table.
