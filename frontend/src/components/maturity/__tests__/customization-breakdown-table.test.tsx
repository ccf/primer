import { render, screen } from "@testing-library/react"

import { CustomizationBreakdownTable } from "@/components/maturity/customization-breakdown-table"

describe("CustomizationBreakdownTable", () => {
  it("renders an empty state", () => {
    render(<CustomizationBreakdownTable data={[]} />)

    expect(screen.getByText("No explicit MCPs, skills, or subagents detected yet.")).toBeInTheDocument()
  })

  it("renders explicit customization rows", () => {
    render(
      <CustomizationBreakdownTable
        data={[
          {
            identifier: "github",
            customization_type: "mcp",
            provenance: "user_local",
            source_classification: "marketplace",
            total_invocations: 4,
            session_count: 2,
            engineer_count: 1,
            project_count: 1,
            top_projects: ["primer"],
            top_engineers: ["Alice"],
          },
        ]}
      />,
    )

    expect(screen.getByText("github")).toBeInTheDocument()
    expect(screen.getByText("Mcp")).toBeInTheDocument()
    expect(screen.getByText("User Local")).toBeInTheDocument()
    expect(screen.getByText("Marketplace")).toBeInTheDocument()
    expect(screen.getByText("4")).toBeInTheDocument()
  })
})
