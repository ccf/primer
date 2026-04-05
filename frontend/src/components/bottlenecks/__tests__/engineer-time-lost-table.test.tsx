import { render, screen } from "@testing-library/react"

import { EngineerTimeLostTable } from "@/components/bottlenecks/engineer-time-lost-table"

describe("EngineerTimeLostTable", () => {
  it("renders engineer time-lost rows", () => {
    render(
      <EngineerTimeLostTable
        data={[
          {
            engineer_id: "eng-1",
            engineer_name: "Alice",
            total_sessions: 8,
            sessions_with_friction: 3,
            total_friction_count: 7,
            estimated_minutes_lost: 96,
            avg_minutes_lost_per_friction_session: 32,
            top_friction_types: ["permission_denied", "timeout"],
          },
        ]}
      />,
    )

    expect(screen.getByText("Time Lost by Engineer")).toBeInTheDocument()
    expect(screen.getByText("Alice")).toBeInTheDocument()
    expect(screen.getByText("1.6h")).toBeInTheDocument()
    expect(screen.getByText("32m/session")).toBeInTheDocument()
    expect(screen.getByText("permission_denied")).toBeInTheDocument()
  })
})
