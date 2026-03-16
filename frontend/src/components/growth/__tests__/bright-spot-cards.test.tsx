import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"

import { BrightSpotCards } from "@/components/growth/bright-spot-cards"

describe("BrightSpotCards", () => {
  it("renders an empty state", () => {
    render(
      <MemoryRouter>
        <BrightSpotCards spots={[]} />
      </MemoryRouter>,
    )

    expect(screen.getByText("No bright spots identified yet.")).toBeInTheDocument()
  })

  it("renders exemplar session links and metrics", () => {
    render(
      <MemoryRouter>
        <BrightSpotCards
          spots={[
            {
              bright_spot_id: "abc123",
              title: "Bright spot: debugging on primer",
              summary: "Three engineers converged on a strong pattern.",
              cluster_type: "session_type",
              cluster_label: "debugging on primer",
              session_count: 4,
              engineer_count: 3,
              success_rate: 1,
              avg_duration: 240,
              exemplar_session_id: "sess-1",
              exemplar_engineer_id: "eng-1",
              exemplar_engineer_name: "Alice Example",
              exemplar_duration_seconds: 180,
              exemplar_tools: ["Read", "Edit", "Bash"],
            },
          ]}
        />
      </MemoryRouter>,
    )

    expect(screen.getByText("Bright spot: debugging on primer")).toBeInTheDocument()
    expect(screen.getByText("Alice Example")).toBeInTheDocument()
    expect(screen.getByText("View session")).toHaveAttribute("href", "/sessions/sess-1")
    expect(screen.getByText("Read")).toBeInTheDocument()
    expect(screen.getByText("100%")).toBeInTheDocument()
  })
})
