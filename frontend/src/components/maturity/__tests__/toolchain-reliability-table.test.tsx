import { render, screen } from "@testing-library/react"

import { ToolchainReliabilityTable } from "@/components/maturity/toolchain-reliability-table"

describe("ToolchainReliabilityTable", () => {
  it("renders an empty state", () => {
    render(<ToolchainReliabilityTable rows={[]} />)

    expect(screen.getByText("No toolchain reliability signals available yet.")).toBeInTheDocument()
  })

  it("renders reliability rows", () => {
    render(
      <ToolchainReliabilityTable
        rows={[
          {
            identifier: "github",
            surface_type: "mcp",
            provenance: "user_local",
            source_classification: "marketplace",
            session_count: 4,
            engineer_count: 2,
            friction_session_count: 2,
            friction_session_rate: 0.5,
            failure_session_count: 1,
            failure_session_rate: 0.25,
            recovery_rate: 0.5,
            success_rate: 0.75,
            abandonment_rate: 0.25,
            avg_recovery_steps: 2.5,
            top_friction_types: ["tool_error", "timeout"],
          },
        ]}
      />,
    )

    expect(screen.getByText("github")).toBeInTheDocument()
    expect(screen.getByText("Mcp")).toBeInTheDocument()
    expect(screen.getByText("Marketplace")).toBeInTheDocument()
    expect(screen.getAllByText("50%")).toHaveLength(2)
    expect(screen.getByText("25%")).toBeInTheDocument()
    expect(screen.getByText("25% abandoned")).toBeInTheDocument()
    expect(screen.getByText("2.5 steps")).toBeInTheDocument()
    expect(screen.getByText("Tool Error")).toBeInTheDocument()
    expect(screen.getByText("Timeout")).toBeInTheDocument()
  })
})
