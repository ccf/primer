import { render, screen } from "@testing-library/react"

import { ProfileSidebar } from "@/components/shared/profile-sidebar"

describe("ProfileSidebar", () => {
  it("renders leverage and effectiveness stats when available", () => {
    render(
      <ProfileSidebar
        profile={{
          display_name: "Charles",
          name: "Charles C. Figueiredo",
          email: "ccf@example.com",
          avatar_url: null,
          github_username: "ccf",
          team_name: "Platform",
          leverage_score: 72.3,
          effectiveness: { score: 81.4 },
          projects: ["insights"],
          overview: {
            total_sessions: 12,
            success_rate: 0.75,
            estimated_cost: 10.25,
            avg_session_duration: 1800,
          },
        }}
      />,
    )

    expect(screen.getByText("Leverage")).toBeInTheDocument()
    expect(screen.getByText("72.3")).toBeInTheDocument()
    expect(screen.getByText("Effectiveness")).toBeInTheDocument()
    expect(screen.getByText("81.4")).toBeInTheDocument()
    expect(screen.getByText("Platform")).toBeInTheDocument()
  })
})
