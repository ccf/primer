import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { MemoryRouter, Route, Routes } from "react-router-dom"

vi.mock("@/lib/api", () => ({
  getApiKey: vi.fn(),
}))

vi.mock("@/lib/auth-context", () => ({
  useAuth: vi.fn(),
}))

vi.mock("@/hooks/use-api-queries", () => ({
  useEngineerProfile: vi.fn(),
  useEngineers: vi.fn(),
}))

vi.mock("@/components/ui/page-tabs", () => ({
  PageTabs: () => <div>tabs</div>,
}))

vi.mock("@/components/shared/profile-sidebar", () => ({
  ProfileSidebar: ({ profile }: { profile: { name: string } }) => <div>{profile.name}</div>,
}))

vi.mock("@/components/profile/profile-overview-tab", () => ({
  ProfileOverviewTab: () => <div>overview tab</div>,
}))

vi.mock("@/components/profile/profile-sessions-tab", () => ({
  ProfileSessionsTab: () => <div>sessions tab</div>,
}))

vi.mock("@/components/profile/profile-insights-tab", () => ({
  ProfileInsightsTab: () => <div>insights tab</div>,
}))

vi.mock("@/components/profile/profile-growth-tab", () => ({
  ProfileGrowthTab: () => <div>growth tab</div>,
}))

import { getApiKey } from "@/lib/api"
import { useAuth } from "@/lib/auth-context"
import { useEngineerProfile, useEngineers } from "@/hooks/use-api-queries"
import { ProfilePage } from "../profile"

const mockGetApiKey = vi.mocked(getApiKey)
const mockUseAuth = vi.mocked(useAuth)
const mockUseEngineerProfile = vi.mocked(useEngineerProfile)
const mockUseEngineers = vi.mocked(useEngineers)

const engineerList = [
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
  {
    id: "eng-2",
    name: "Bob Example",
    email: "bob@example.com",
    team_id: null,
    role: "engineer",
    avatar_url: null,
    github_username: null,
    display_name: "Bob Example",
    is_active: true,
    created_at: "2026-03-01T00:00:00Z",
  },
]

const engineerProfile = {
  engineer_id: "eng-1",
  name: "Alice Example",
  email: "alice@example.com",
  display_name: "Alice Example",
  team_id: null,
  team_name: null,
  avatar_url: null,
  github_username: null,
  created_at: "2026-03-01T00:00:00Z",
  overview: {
    total_sessions: 3,
    total_engineers: 1,
    total_messages: 12,
    total_tool_calls: 4,
    total_input_tokens: 100,
    total_output_tokens: 50,
    estimated_cost: 1.2,
    avg_session_duration: 120,
    avg_messages_per_session: 4,
    outcome_counts: {},
    session_type_counts: {},
    success_rate: 0.5,
    previous_period: null,
    end_reason_counts: {},
    cache_hit_rate: null,
    avg_health_score: null,
    agent_type_counts: {},
  },
  weekly_trajectory: [],
  friction: [],
  config_suggestions: [],
  strengths: {
    engineer_profiles: [],
    team_skill_gaps: [],
    total_engineers: 0,
    total_session_types: 0,
    total_tools_used: 0,
  },
  learning_paths: [],
  quality: {},
  leverage_score: null,
  effectiveness: null,
  projects: [],
  tool_rankings: [],
  workflow_playbooks: [],
}

describe("ProfilePage", () => {
  let storage: Record<string, string>

  beforeEach(() => {
    vi.clearAllMocks()
    storage = {}
    vi.stubGlobal("localStorage", {
      getItem: vi.fn((key: string) => storage[key] ?? null),
      setItem: vi.fn((key: string, value: string) => {
        storage[key] = value
      }),
      removeItem: vi.fn((key: string) => {
        delete storage[key]
      }),
    })
    mockGetApiKey.mockReturnValue("test-key")
    mockUseAuth.mockReturnValue({ user: null } as ReturnType<typeof useAuth>)
    mockUseEngineers.mockReturnValue({
      data: engineerList,
      isLoading: false,
    } as unknown as ReturnType<typeof useEngineers>)
    mockUseEngineerProfile.mockImplementation(
      (engineerId: string) =>
        ({
          data: engineerId === "eng-1" ? engineerProfile : undefined,
          isLoading: false,
        }) as ReturnType<typeof useEngineerProfile>,
    )
  })

  function renderPage(initialEntry = "/profile") {
    return render(
      <MemoryRouter initialEntries={[initialEntry]}>
        <Routes>
          <Route path="/profile" element={<ProfilePage teamId={null} dateRange={null} />} />
        </Routes>
      </MemoryRouter>,
    )
  }

  it("shows an engineer chooser for API-key admins without profile context", () => {
    renderPage()

    expect(screen.getByText("Choose a profile")).toBeInTheDocument()
    expect(screen.getByText("Alice Example")).toBeInTheDocument()
    expect(screen.getByText("Bob Example")).toBeInTheDocument()
  })

  it("lets API-key admins pick and remember an engineer profile", () => {
    renderPage()

    fireEvent.click(screen.getByText("Alice Example"))

    expect(screen.getByText("Viewing engineer profile context")).toBeInTheDocument()
    expect(screen.getAllByText("Alice Example").length).toBeGreaterThan(0)
    expect(screen.getByText("overview tab")).toBeInTheDocument()
    expect(storage.primer_profile_engineer_id).toBe("eng-1")
  })
})
