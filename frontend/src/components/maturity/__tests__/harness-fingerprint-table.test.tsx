import { render, screen } from "@testing-library/react"

import { HarnessFingerprintTable } from "@/components/maturity/harness-fingerprint-table"

describe("HarnessFingerprintTable", () => {
  it("renders an empty state", () => {
    render(<HarnessFingerprintTable rows={[]} />)

    expect(
      screen.getByText("No harness configuration fingerprints available yet."),
    ).toBeInTheDocument()
  })

  it("renders harness fingerprint rows", () => {
    render(
      <HarnessFingerprintTable
        rows={[
          {
            fingerprint_id: "abc123def4567890",
            label: "cursor / manual / 4.0 tools",
            agent_type: "cursor",
            permission_mode: "manual",
            session_count: 8,
            engineer_count: 3,
            success_rate: 0.75,
            avg_leverage_score: 82.4,
            compound_reliability_rate: 0.904,
            tool_count: 4,
            customization_count: 2,
            context_signal_count: 9,
            top_tools: ["Read", "Task:explore"],
            top_customizations: ["github"],
            signals: ["agent:cursor", "permission:manual", "context"],
          },
        ]}
      />,
    )

    expect(screen.getByText("cursor / manual / 4.0 tools")).toBeInTheDocument()
    expect(screen.getByText("abc123def4567890")).toBeInTheDocument()
    expect(screen.getByText("Cursor")).toBeInTheDocument()
    expect(screen.getByText("Manual")).toBeInTheDocument()
    expect(screen.getByText("8")).toBeInTheDocument()
    expect(screen.getByText("3 engineers")).toBeInTheDocument()
    expect(screen.getByText("75%")).toBeInTheDocument()
    expect(screen.getByText("90% 10-step")).toBeInTheDocument()
    expect(screen.getByText("82.4")).toBeInTheDocument()
    expect(screen.getByText("4 tools")).toBeInTheDocument()
    expect(screen.getByText("2 custom, 9 context")).toBeInTheDocument()
    expect(screen.getByText("Task:Explore")).toBeInTheDocument()
    expect(screen.getByText("github")).toBeInTheDocument()
    expect(screen.getByText("Agent:Cursor")).toBeInTheDocument()
  })
})
