import { fireEvent, render, screen } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"
import { AdminAlertsTab } from "../admin-alerts-tab"

const mockUseAlertConfigs = vi.fn()
const mockUseResolvedAlertPolicy = vi.fn()
const mockUseTeams = vi.fn()
const mockCreate = vi.fn()
const mockUpdate = vi.fn()
const mockDelete = vi.fn()

vi.mock("@/hooks/use-api-queries", () => ({
  useAlertConfigs: () => mockUseAlertConfigs(),
  useResolvedAlertPolicy: () => mockUseResolvedAlertPolicy(),
  useTeams: () => mockUseTeams(),
}))

vi.mock("@/hooks/use-api-mutations", () => ({
  useCreateAlertConfig: () => ({ mutate: mockCreate, isPending: false }),
  useUpdateAlertConfig: () => ({ mutate: mockUpdate }),
  useDeleteAlertConfig: () => ({ mutate: mockDelete }),
}))

describe("AdminAlertsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockUseTeams.mockReturnValue({
      data: [
        { id: "team-1", name: "Platform" },
      ],
    })
    mockUseAlertConfigs.mockReturnValue({
      data: [
        {
          id: "cfg-1",
          team_id: null,
          alert_type: "friction_spike",
          threshold: 2,
          enabled: true,
        },
      ],
      isLoading: false,
    })
    mockUseResolvedAlertPolicy.mockReturnValue({
      data: {
        notifications_enabled: true,
        webhook_configured: true,
        policies: [
          {
            alert_type: "friction_spike",
            label: "Friction Spike",
            description: "Alert when today's friction count exceeds the recent baseline.",
            detector_window: "today vs trailing 7-day daily average",
            unit_label: "x baseline",
            effective_threshold: 2,
            effective_enabled: true,
            source: "default",
            default_threshold: 2,
            global_override_threshold: null,
            global_override_enabled: null,
            team_override_threshold: null,
            team_override_enabled: null,
          },
        ],
      },
    })
  })

  it("renders effective policy details", () => {
    render(<AdminAlertsTab />)

    expect(screen.getByText("Effective Policy")).toBeInTheDocument()
    expect(screen.getByText("Slack enabled")).toBeInTheDocument()
    expect(screen.getByText("Webhook configured")).toBeInTheDocument()
    expect(screen.getAllByText("Friction Spike").length).toBeGreaterThan(0)
    expect(screen.getByText("today vs trailing 7-day daily average")).toBeInTheDocument()
    expect(screen.getByText("Default 2 x baseline")).toBeInTheDocument()
  })

  it("creates an override", () => {
    render(<AdminAlertsTab />)

    fireEvent.change(screen.getByPlaceholderText("e.g. 2.0"), { target: { value: "4" } })
    fireEvent.click(screen.getByRole("button", { name: "Add" }))

    expect(mockCreate).toHaveBeenCalledWith({
      team_id: null,
      alert_type: "friction_spike",
      threshold: 4,
    })
  })
})
