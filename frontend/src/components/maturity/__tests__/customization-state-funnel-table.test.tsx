import { render, screen } from "@testing-library/react"

import { CustomizationStateFunnelTable } from "@/components/maturity/customization-state-funnel-table"

describe("CustomizationStateFunnelTable", () => {
  it("renders an empty state", () => {
    render(<CustomizationStateFunnelTable rows={[]} />)

    expect(screen.getByText("No customization state coverage available yet.")).toBeInTheDocument()
  })

  it("renders state funnel rows", () => {
    render(
      <CustomizationStateFunnelTable
        rows={[
          {
            identifier: "github",
            customization_type: "mcp",
            provenance: "user_local",
            source_classification: "marketplace",
            available_session_count: 4,
            enabled_session_count: 3,
            invoked_session_count: 2,
            available_engineer_count: 3,
            enabled_engineer_count: 2,
            invoked_engineer_count: 1,
            activation_rate: 0.667,
            usage_rate: 0.333,
            available_not_enabled_engineer_count: 1,
            enabled_not_invoked_engineer_count: 1,
          },
        ]}
      />,
    )

    expect(screen.getByText("github")).toBeInTheDocument()
    expect(screen.getByText("Mcp")).toBeInTheDocument()
    expect(screen.getByText("Marketplace")).toBeInTheDocument()
    expect(screen.getByText("67%")).toBeInTheDocument()
    expect(screen.getByText("33%")).toBeInTheDocument()
    expect(screen.getByText("1 available not enabled")).toBeInTheDocument()
    expect(screen.getByText("1 enabled not invoked")).toBeInTheDocument()
  })
})
