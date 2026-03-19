import { render, screen } from "@testing-library/react"

import { TeamCustomizationLandscapeTable } from "@/components/maturity/team-customization-landscape-table"

describe("TeamCustomizationLandscapeTable", () => {
  it("renders an empty state", () => {
    render(<TeamCustomizationLandscapeTable data={[]} />)

    expect(screen.getByText("No cross-team customization landscape available yet.")).toBeInTheDocument()
  })

  it("renders team customization rows", () => {
    render(
      <TeamCustomizationLandscapeTable
        data={[
          {
            team_id: "team-1",
            team_name: "Platform",
            engineer_count: 3,
            engineers_using_explicit_customizations: 2,
            explicit_customization_count: 4,
            adoption_rate: 0.667,
            avg_effectiveness_score: 88.2,
            top_customizations: ["github", "review-pr"],
            unique_customizations: ["github"],
          },
        ]}
      />,
    )

    expect(screen.getByText("Platform")).toBeInTheDocument()
    expect(screen.getByText("67%")).toBeInTheDocument()
    expect(screen.getAllByText("github").length).toBeGreaterThan(0)
    expect(screen.getByText("review-pr")).toBeInTheDocument()
  })
})
