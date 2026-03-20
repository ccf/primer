import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter } from "react-router-dom"

vi.mock("@/lib/api", () => ({
  getApiKey: vi.fn(),
}))

vi.mock("@/lib/auth-context", () => ({
  useAuth: vi.fn(),
}))

vi.mock("@/hooks/use-api-queries", () => ({
  useEngineerProfile: vi.fn(),
  useEngineers: vi.fn(),
  useOnboardingAcceleration: vi.fn(),
  usePatternSharing: vi.fn(),
  useSkillInventory: vi.fn(),
  useLearningPaths: vi.fn(),
}))

vi.mock("@/components/growth/cohort-comparison", () => ({
  CohortComparison: () => <div>cohorts</div>,
}))
vi.mock("@/components/growth/new-hire-table", () => ({
  NewHireTable: () => <div>new hires</div>,
}))
vi.mock("@/components/growth/velocity-chart", () => ({
  VelocityChart: () => <div>velocity</div>,
}))
vi.mock("@/components/growth/onboarding-recommendations", () => ({
  OnboardingRecommendations: () => <div>recommendations</div>,
}))
vi.mock("@/components/growth/pattern-summary", () => ({
  PatternSummary: () => <div>pattern summary</div>,
}))
vi.mock("@/components/growth/bright-spot-cards", () => ({
  BrightSpotCards: () => <div>bright spots</div>,
}))
vi.mock("@/components/growth/exemplar-session-library", () => ({
  ExemplarSessionLibrary: () => <div>exemplar session library</div>,
}))
vi.mock("@/components/growth/shared-pattern-card", () => ({
  SharedPatternCards: () => <div>shared patterns</div>,
}))
vi.mock("@/components/insights/skill-inventory-summary", () => ({
  SkillInventorySummary: () => <div>skill inventory</div>,
}))
vi.mock("@/components/growth/coverage-summary", () => ({
  CoverageSummary: () => <div>coverage</div>,
}))
vi.mock("@/components/insights/team-skill-gaps", () => ({
  TeamSkillGaps: () => <div>team skill gaps</div>,
}))
vi.mock("@/components/growth/skill-universe-chart", () => ({
  SkillUniverseChart: () => <div>skill universe</div>,
}))
vi.mock("@/components/growth/learning-path-cards", () => ({
  LearningPathCards: () => <div>learning paths</div>,
}))
vi.mock("@/components/growth/reuse-opportunity-cards", () => ({
  ReuseOpportunityCards: () => <div>reuse opportunities</div>,
}))
vi.mock("@/components/growth/reusable-asset-table", () => ({
  ReusableAssetTable: () => <div>reusable assets</div>,
}))
vi.mock("@/components/insights/engineer-skill-table", () => ({
  EngineerSkillTable: () => <div>engineer skill table</div>,
}))

import { getApiKey } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import {
  useEngineerProfile,
  useEngineers,
  useLearningPaths,
  useOnboardingAcceleration,
  usePatternSharing,
  useSkillInventory,
} from "@/hooks/use-api-queries"
import { GrowthPage } from "../growth"

const mockGetApiKey = vi.mocked(getApiKey)
const mockUseAuth = vi.mocked(useAuth)
const mockUseEngineerProfile = vi.mocked(useEngineerProfile)
const mockUseEngineers = vi.mocked(useEngineers)
const mockUseOnboardingAcceleration = vi.mocked(useOnboardingAcceleration)
const mockUsePatternSharing = vi.mocked(usePatternSharing)
const mockUseSkillInventory = vi.mocked(useSkillInventory)
const mockUseLearningPaths = vi.mocked(useLearningPaths)

describe("GrowthPage", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.stubGlobal("localStorage", {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    })
    mockGetApiKey.mockReturnValue(null)
    mockUseAuth.mockReturnValue({
      user: {
        engineer_id: "eng-1",
        name: "Alice Example",
        email: "alice@example.com",
        role: "engineer",
        team_id: null,
        avatar_url: null,
        github_username: null,
        display_name: "Alice Example",
      },
    } as ReturnType<typeof useAuth>)
    mockUseOnboardingAcceleration.mockReturnValue({
      data: null,
      isLoading: false,
    } as unknown as ReturnType<typeof useOnboardingAcceleration>)
    mockUsePatternSharing.mockReturnValue({
      data: null,
      isLoading: false,
    } as unknown as ReturnType<typeof usePatternSharing>)
    mockUseSkillInventory.mockReturnValue({
      data: null,
      isLoading: false,
    } as unknown as ReturnType<typeof useSkillInventory>)
    mockUseLearningPaths.mockReturnValue({
      data: null,
      isLoading: false,
    } as unknown as ReturnType<typeof useLearningPaths>)
    mockUseEngineers.mockReturnValue({
      data: [],
      isLoading: false,
    } as unknown as ReturnType<typeof useEngineers>)
  })

  function renderPage() {
    return render(
      <MemoryRouter initialEntries={["/growth"]}>
        <GrowthPage teamId={null} dateRange={null} />
      </MemoryRouter>,
    )
  }

  it("shows personal workflow playbooks from the growth page", () => {
    mockUseEngineerProfile.mockReturnValue({
      data: {
        display_name: "Alice Example",
        name: "Alice Example",
        workflow_playbooks: [
          {
            playbook_id: "org:documentation::edit+execute+delegate",
            title: "documentation: edit -> execute -> delegate",
            summary: "Peers repeatedly use this pattern.",
            scope: "org",
            adoption_state: "not_used",
            session_type: "documentation",
            steps: ["edit", "execute", "delegate"],
            recommended_tools: ["Edit", "Bash"],
            caution_friction_types: ["tool_error"],
            example_projects: ["primer"],
            supporting_session_count: 4,
            supporting_peer_count: 3,
            success_rate: 1,
            friction_free_rate: 0.75,
            avg_duration_seconds: 247,
            engineer_usage_count: 0,
          },
        ],
      },
      isLoading: false,
    } as unknown as ReturnType<typeof useEngineerProfile>)

    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "Playbooks" }))

    expect(screen.getByText("Workflow Playbooks")).toBeInTheDocument()
    expect(
      screen.getByText("documentation: edit -> execute -> delegate"),
    ).toBeInTheDocument()
  })

  it("shows exemplar library content on the patterns tab", () => {
    mockUsePatternSharing.mockReturnValue({
      data: {
        patterns: [],
        bright_spots: [],
        exemplar_sessions: [],
        total_clusters_found: 0,
        sessions_analyzed: 0,
      },
      isLoading: false,
    } as unknown as ReturnType<typeof usePatternSharing>)
    mockUseEngineerProfile.mockReturnValue({
      data: null,
      isLoading: false,
    } as unknown as ReturnType<typeof useEngineerProfile>)

    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "Patterns" }))

    expect(screen.getByText("Exemplar Session Library")).toBeInTheDocument()
    expect(screen.getByText("exemplar session library")).toBeInTheDocument()
  })

  it("shows learning paths on the skills tab", () => {
    mockUseSkillInventory.mockReturnValue({
      data: {
        engineer_profiles: [],
        team_skill_gaps: [],
        reusable_assets: [],
        underused_reusable_assets: [],
        total_engineers: 1,
        total_session_types: 1,
        total_tools_used: 1,
      },
      isLoading: false,
    } as unknown as ReturnType<typeof useSkillInventory>)
    mockUseLearningPaths.mockReturnValue({
      data: {
        engineer_paths: [
          {
            engineer_id: "eng-1",
            name: "Alice Example",
            total_sessions: 4,
            recommendations: [],
            coverage_score: 0.5,
            complexity_trend: "flat",
          },
        ],
        team_skill_universe: {},
        sessions_analyzed: 4,
      },
      isLoading: false,
    } as unknown as ReturnType<typeof useLearningPaths>)
    mockUseEngineerProfile.mockReturnValue({
      data: null,
      isLoading: false,
    } as unknown as ReturnType<typeof useEngineerProfile>)

    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "Skills" }))

    expect(screen.getByText("Learning Paths")).toBeInTheDocument()
    expect(screen.getByText("learning paths")).toBeInTheDocument()
    expect(screen.getByText("reuse opportunities")).toBeInTheDocument()
    expect(screen.getByText("reusable assets")).toBeInTheDocument()
  })

  it("shows an engineer chooser for API-key admins without a selected context", () => {
    mockGetApiKey.mockReturnValue("test-key")
    mockUseAuth.mockReturnValue({ user: null } as ReturnType<typeof useAuth>)
    mockUseEngineerProfile.mockReturnValue({
      data: undefined,
      isLoading: false,
    } as ReturnType<typeof useEngineerProfile>)
    mockUseEngineers.mockReturnValue({
      data: [
        {
          id: "eng-1",
          name: "Alice Example",
          email: "alice@example.com",
          team_id: null,
          role: "engineer",
          avatar_url: null,
          github_username: null,
          display_name: "Alice Example",
          is_active: true,
          created_at: "2026-03-01T00:00:00Z",
        },
      ],
      isLoading: false,
    } as unknown as ReturnType<typeof useEngineers>)

    renderPage()
    fireEvent.click(screen.getByRole("button", { name: "Playbooks" }))

    expect(screen.getByText("Choose an engineer for playbooks")).toBeInTheDocument()
    expect(screen.getByText("Alice Example")).toBeInTheDocument()
  })
})
