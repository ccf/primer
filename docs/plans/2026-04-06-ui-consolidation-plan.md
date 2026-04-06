# UI Consolidation Plan

> Goal: Reduce visual density, eliminate overlapping surfaces, and create a clear information
> hierarchy that leads users from insight to action in every view.

## Principles

1. **One question per view.** The default view answers one decision question. Detail is one click
   deeper, not visible by default.
2. **Narrative over metrics.** Lead with a sentence, not a grid of numbers. Numbers support the
   sentence.
3. **Progressive disclosure.** Show the 3 most important things first. Everything else collapses,
   expands, or links to a dedicated page.
4. **Consistent scoping.** Every page is either org-level, team-level, project-level, or
   engineer-level. Never mix scopes on the same surface without explicit labels.

## Current State

19 pages, ~294 frontend files, ~20K lines of components. The densest pages:

| Page | Sections | Problem |
|------|----------|---------|
| Growth | 25+ components across 4 tabs | Skills tab alone has 10 sub-components |
| Maturity | 30+ components across 6 tabs | Agents tab has 9 sub-components |
| Quality | 12+ flat sections, no tabs | Wall of cards/charts |
| Project Workspace | 12+ flat sections | Everything visible at once |
| Dashboard | 7 sections | Too much for a landing page |
| Profile / Engineer Profile | Nearly identical 5-tab layouts | Two pages doing the same job |

## Phase 1: Structural Simplification (High Impact, Low Risk)

### 1.1 Merge Profile and Engineer Profile

**Current:** `/profile` (logged-in user) and `/engineers/:id` (any engineer) are nearly identical
5-tab layouts with the same components. Two code paths, same UX.

**Change:** Unify into a single `/engineers/:id` page. `/profile` becomes a redirect to
`/engineers/{currentUserId}`. The page accepts an optional `engineerId` param; if missing, defaults
to the authenticated user. The "My Profile" sidebar entry links to the unified page.

**Files to modify:**
- `pages/profile.tsx` → redirect wrapper only
- `pages/engineer-profile.tsx` → becomes the single implementation
- `components/layout/sidebar.tsx` → update Profile link
- `App.tsx` → update routing

**Risk:** Low. Both pages already use the same underlying components and API hooks.

### 1.2 Add tabs to Quality page

**Current:** 12+ flat sections in a single scroll. Users must scroll past PR comparison charts to
reach review findings, past findings to reach post-merge outcomes.

**Change:** Organize into 3 tabs:
- **Overview** — QualityOverviewCards + ClaudePRComparison + QualityByTypeChart
- **Findings** — FindingsOverviewSection + FindingsTable
- **Outcomes** — PostMergeOutcomesSection + CodeVolumeChart + EngineerQualityTable + QualityAttributionTable

The first tab answers "how's our code quality?" The other tabs are drill-downs.

**Files to modify:**
- `pages/quality.tsx` → restructure into PageTabs

### 1.3 Add tabs to Project Workspace

**Current:** 12+ flat sections. Readiness, agent mix, overview, enablement, repos, friction,
workflows, cost, quality, PRs — all visible at once.

**Change:** Organize into 4 tabs:
- **Overview** — ProjectScorecard + ProjectAgentMixCard + OverviewCard + ProjectEnablementCard
- **Workflows** — ProjectWorkflowSection + FrictionCard
- **Quality** — QualityViewCard + LinkedPRTable + QualityAttributionTable
- **Cost** — CostViewCard + ModelBreakdownTable

Overview answers "is this project healthy?" Other tabs are drill-downs.

**Files to modify:**
- `pages/project-workspace.tsx` → restructure into PageTabs

### 1.4 Reduce Growth Skills tab density

**Current:** Skills tab shows 10 sub-components in one scroll: SkillInventorySummary,
CoverageSummary, TeamSkillGaps, SkillUniverseChart, LearningPathCards, ReuseOpportunityCards,
PromptOpportunityCards, ReusableAssetTable, PromptReuseTable, EngineerSkillTable.

**Change:** Split into 2 sub-sections with collapsible detail:
- **Skill Coverage** (default open) — SkillInventorySummary + CoverageSummary + TeamSkillGaps +
  SkillUniverseChart
- **Learning & Reuse** (default collapsed) — LearningPathCards + ReuseOpportunityCards +
  PromptOpportunityCards + ReusableAssetTable + PromptReuseTable + EngineerSkillTable

Or promote to a 5th tab: "Learning" alongside the existing Onboarding/Patterns/Skills/Playbooks.

**Files to modify:**
- `pages/growth.tsx` → restructure Skills tab

### 1.5 Reduce Maturity Agents tab density

**Current:** Agents & Skills tab shows 9 sub-components: AgentSkillTable, AgentTeamModeTable,
DelegationPatternTable, CustomizationBreakdownTable, CustomizationStateFunnelTable,
ToolchainReliabilityTable, TeamCustomizationLandscapeTable, CustomizationOutcomeTable,
HighPerformerStackCards.

**Change:** Split into sub-sections with clear headings:
- **Agent Patterns** — AgentSkillTable + AgentTeamModeTable + DelegationPatternTable
- **Customization Intelligence** — CustomizationBreakdownTable + CustomizationStateFunnelTable +
  CustomizationOutcomeTable + HighPerformerStackCards
- **Reliability & Landscape** — ToolchainReliabilityTable + TeamCustomizationLandscapeTable

Or split into separate tabs: rename "Agents & Skills" to just "Agents", add "Customizations" tab,
add "Reliability" tab. This would take Maturity from 6 tabs to 8, but each tab would be focused.

**Alternative:** Keep 6 tabs but add collapsible sections within Agents tab.

**Files to modify:**
- `pages/maturity.tsx` → restructure Agents tab

## Phase 2: Dashboard Simplification

### 2.1 Streamline the Dashboard

**Current:** KPI strip (5 cards) + Activity section (daily chart + outcome chart + heatmap) +
Attention section + Deep-dive cards + Recommendations.

**Change:**
- **KPI strip** — keep, but reduce to 4 (drop Health Score, it's a computed composite that's hard
  to action)
- **Activity** — keep daily chart + outcome chart side-by-side. Move heatmap to a collapsible
  "Show activity heatmap" toggle (it's interesting but not actionable)
- **Attention** — keep, this is the highest-value section
- **Deep-dive cards** — reduce to 2 most actionable cards based on data (e.g., "Top friction type"
  and "Cost trend"). Link to dedicated pages for detail
- **Recommendations** — keep but limit to top 3 (currently shows all)

Net effect: 7 sections → 5, with heatmap and extra recommendations behind interactions.

**Files to modify:**
- `pages/dashboard.tsx` — restructure sections
- `components/dashboard/deep-dive-cards.tsx` — limit to 2
- `components/dashboard/recommendations-panel.tsx` — limit to 3 with "Show all" link

## Phase 3: Visual Hierarchy and Polish

### 3.1 Consistent section headers with context

Every page section should follow:
```
## Section Title
One-line summary sentence ("Backend team's friction rate increased 15% this week")
[content: chart, table, or cards]
[optional: "View details →" link to deeper page]
```

This is a systematic pass through all pages to add summary sentences above data visualizations.

### 3.2 Empty-state improvements

When a page section has no data (no PRs, no friction, no customizations), show a helpful
empty state that explains what would appear and how to get it. The activation hub already does this
at the platform level; extend it to individual page sections.

### 3.3 Consistent card sizing and spacing

Audit all card grids for consistent sizing. Currently some pages use `grid-cols-2`, others
`grid-cols-3`, others `grid-cols-4`. Standardize:
- KPI strips: `grid-cols-5` on desktop, `grid-cols-2` on mobile
- Summary cards: `grid-cols-3` on desktop
- Detail tables: full-width
- Charts: full-width or `grid-cols-2` for side-by-side comparisons

## Implementation Order

| Step | Change | Impact | Effort |
|------|--------|--------|--------|
| 1 | Merge Profile/Engineer Profile | Removes duplicate page | Small |
| 2 | Add tabs to Quality page | Reduces wall-of-cards | Small |
| 3 | Add tabs to Project Workspace | Reduces wall-of-cards | Small |
| 4 | Reduce Growth Skills tab density | Reduces most overloaded tab | Small |
| 5 | Reduce Maturity Agents tab density | Reduces second-most overloaded tab | Small |
| 6 | Streamline Dashboard | Simplifies landing page | Medium |
| 7 | Summary sentences pass | Adds narrative context | Medium |
| 8 | Empty-state improvements | Improves demo experience | Medium |
| 9 | Consistent card sizing | Visual polish | Small |

Steps 1-5 are structural changes that can ship independently. Steps 6-9 are polish that builds on
the structure.

## What This Does NOT Change

- Page routing structure (no URL changes except Profile redirect)
- API endpoints or data model
- Component implementations (just reorganization)
- Feature coverage (nothing removed, only reorganized)

## Success Criteria

- Every page's default view fits on one screen without scrolling (on 1080p)
- No page has more than 6 visible sections before interaction
- Users can find "what needs attention" within 5 seconds of landing on any page
- Demo visitors can navigate the full product story in under 3 minutes
