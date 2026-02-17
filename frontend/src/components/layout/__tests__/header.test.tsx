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

vi.mock("@/lib/theme-context", () => ({
  useTheme: vi.fn().mockReturnValue({ resolved: "light", setTheme: vi.fn() }),
}))

const mockClearApiKey = vi.fn()
const mockGetApiKey = vi.fn()

vi.mock("@/lib/api", () => ({
  clearApiKey: () => mockClearApiKey(),
  getApiKey: () => mockGetApiKey(),
}))

const mockLogout = vi.fn().mockResolvedValue(undefined)

vi.mock("@/lib/auth-context", () => ({
  useAuth: () => ({ user: null, logout: mockLogout }),
}))

describe("Header", () => {
  const onTeamChange = vi.fn()
  const onDateRangeChange = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    mockUseTeams.mockReturnValue({ data: undefined })
    // Default: API key auth (admin role, team filter visible)
    mockGetApiKey.mockReturnValue("test-key")
  })

  const renderHeader = (props?: { teamId?: string | null }) =>
    render(
      <MemoryRouter>
        <Header
          teamId={props?.teamId ?? null}
          onTeamChange={onTeamChange}
          dateRange={null}
          onDateRangeChange={onDateRangeChange}
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

  it("renders avatar button for user menu", () => {
    renderHeader()

    const avatarButton = screen.getByLabelText("User menu")
    expect(avatarButton).toBeInTheDocument()
  })

  it("opens dropdown with sign out and theme toggle on avatar click", () => {
    renderHeader()

    const avatarButton = screen.getByLabelText("User menu")
    fireEvent.click(avatarButton)

    expect(screen.getByText("Sign out")).toBeInTheDocument()
    expect(screen.getByText("Dark mode")).toBeInTheDocument()
  })

  it("calls clearApiKey and reload when clicking sign out", () => {
    const reloadMock = vi.fn()
    Object.defineProperty(window, "location", { value: { reload: reloadMock }, writable: true })

    renderHeader()

    const avatarButton = screen.getByLabelText("User menu")
    fireEvent.click(avatarButton)

    const signOutButton = screen.getByText("Sign out")
    fireEvent.click(signOutButton)

    expect(mockClearApiKey).toHaveBeenCalled()
    expect(reloadMock).toHaveBeenCalled()
  })

  it("closes dropdown on outside click", () => {
    renderHeader()

    const avatarButton = screen.getByLabelText("User menu")
    fireEvent.click(avatarButton)
    expect(screen.getByText("Sign out")).toBeInTheDocument()

    fireEvent.mouseDown(document.body)
    expect(screen.queryByText("Sign out")).not.toBeInTheDocument()
  })
})
