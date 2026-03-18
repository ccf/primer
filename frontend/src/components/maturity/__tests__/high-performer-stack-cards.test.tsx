import { render, screen } from "@testing-library/react"

import { HighPerformerStackCards } from "@/components/maturity/high-performer-stack-cards"

describe("HighPerformerStackCards", () => {
  it("renders an empty state", () => {
    render(<HighPerformerStackCards stacks={[]} />)

    expect(screen.getByText("No explicit high-performer stacks detected yet.")).toBeInTheDocument()
  })

  it("renders stack evidence", () => {
    render(
      <HighPerformerStackCards
        stacks={[
          {
            stack_id: "stack-1",
            label: "github + review-pr",
            customizations: [
              {
                identifier: "github",
                customization_type: "mcp",
                provenance: "user_local",
                invocation_count: 3,
              },
              {
                identifier: "review-pr",
                customization_type: "skill",
                provenance: "repo_defined",
                invocation_count: 1,
              },
            ],
            engineer_count: 1,
            session_count: 2,
            avg_effectiveness_score: 88.2,
            avg_leverage_score: 91.4,
            top_projects: ["primer"],
            top_engineers: ["Alice"],
          },
        ]}
      />,
    )

    expect(screen.getByText("github + review-pr")).toBeInTheDocument()
    expect(screen.getByText("Used by 1 engineer across 2 sessions.")).toBeInTheDocument()
    expect(screen.getByText("88.2")).toBeInTheDocument()
    expect(screen.getByText("91.4")).toBeInTheDocument()
    expect(screen.getByText("User Local")).toBeInTheDocument()
    expect(screen.getByText("Alice")).toBeInTheDocument()
  })
})
