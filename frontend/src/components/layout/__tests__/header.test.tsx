import { render, screen, fireEvent } from "@testing-library/react"
import { vi, describe, it, expect, beforeEach } from "vitest"
import { MemoryRouter } from "react-router-dom"
import { Header } from "../header"

const mockUseTeams = vi.fn()

vi.mock("@/hooks/use-api-queries", () => ({
  useTeams: () => mockUseTeams(),
  useAlerts: vi.fn().mockReturnValue({ data: [], isLoading: false }),
}))

vi.mock("@/hooks/use-api-mutations", () => ({
  useAcknowledgeAlert: vi.fn().mockReturnValue({ mutate: vi.fn() }),
  useDismissAlert: vi.fn().mockReturnValue({ mutate: vi.fn() }),
}))

vi.mock("../alert-bell", () => ({
  AlertBell: () => null,
}))

const mockGetApiKey = vi.fn()

vi.mock("@/lib/api", () => ({
  clearApiKey: vi.fn(),
  getApiKey: () => mockGetApiKey(),
}))

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ user: null, logout: vi.fn() }),
}))

describe("Header", () => {
  const onTeamChange = vi.fn()
  const onDateRangeChange = vi.fn()
  const onToggleSidebar = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseTeams.mockReturnValue({ data: undefined })
    // Default: API key auth (admin role, team filter visible)
    mockGetApiKey.mockReturnValue("test-key")
  })

  const renderHeader = (props?: { teamId?: string | null; sidebarCollapsed?: boolean }) =>
    render(
      <MemoryRouter>
        <Header
          teamId={props?.teamId ?? null}
          onTeamChange={onTeamChange}
          dateRange={null}
          onDateRangeChange={onDateRangeChange}
          sidebarCollapsed={props?.sidebarCollapsed ?? false}
          onToggleSidebar={onToggleSidebar}
        />
      </MemoryRouter>,
    )

  it("renders the 'All teams' default option", () => {
    renderHeader()

    const select = screen.getByRole("combobox")
    expect(select).toBeInTheDocument()

    const allTeamsOption = screen.getByRole("option", { name: "All teams" })
    expect(allTeamsOption).toBeInTheDocument()
    expect((allTeamsOption as HTMLOptionElement).value).toBe("")
  })

  it("renders team options when useTeams returns data", () => {
    mockUseTeams.mockReturnValue({
      data: [{ id: "t1", name: "Platform", created_at: "2025-01-01T00:00:00" }],
    })

    renderHeader()

    const options = screen.getAllByRole("option")
    expect(options).toHaveLength(2)
    expect(screen.getByRole("option", { name: "Platform" })).toBeInTheDocument()
    expect((screen.getByRole("option", { name: "Platform" }) as HTMLOptionElement).value).toBe("t1")
  })

  it("calls onTeamChange with team id when selecting a team", () => {
    mockUseTeams.mockReturnValue({
      data: [{ id: "t1", name: "Platform", created_at: "2025-01-01T00:00:00" }],
    })

    renderHeader()

    const select = screen.getByRole("combobox")
    fireEvent.change(select, { target: { value: "t1" } })

    expect(onTeamChange).toHaveBeenCalledWith("t1")
  })

  it("calls onTeamChange with null when selecting 'All teams'", () => {
    mockUseTeams.mockReturnValue({
      data: [{ id: "t1", name: "Platform", created_at: "2025-01-01T00:00:00" }],
    })

    renderHeader({ teamId: "t1" })

    const select = screen.getByRole("combobox")
    fireEvent.change(select, { target: { value: "" } })

    expect(onTeamChange).toHaveBeenCalledWith(null)
  })

  it("shows sidebar toggle button when sidebar is collapsed", () => {
    renderHeader({ sidebarCollapsed: true })

    const toggleButton = screen.getByTitle("Expand sidebar")
    expect(toggleButton).toBeInTheDocument()

    fireEvent.click(toggleButton)
    expect(onToggleSidebar).toHaveBeenCalled()
  })

  it("hides sidebar toggle button when sidebar is expanded", () => {
    renderHeader({ sidebarCollapsed: false })

    expect(screen.queryByTitle("Expand sidebar")).not.toBeInTheDocument()
  })
})
