import { render, screen } from "@testing-library/react"

import { TeamSkillGaps } from "@/components/insights/team-skill-gaps"

describe("TeamSkillGaps", () => {
  it("renders the empty state", () => {
    render(<TeamSkillGaps data={[]} />)

    expect(
      screen.getByText("No significant skill gaps detected. All skills have good team coverage."),
    ).toBeInTheDocument()
  })

  it("renders enriched gap context", () => {
    render(
      <TeamSkillGaps
        data={[
          {
            skill: "primer: review-pr",
            coverage_pct: 33.3,
            total_engineers: 3,
            engineers_with_skill: 1,
            gap_type: "project_context",
            workflow_archetype: "debugging",
            tool_category: null,
            project_context: "primer",
            recommended_asset_type: "skill",
            recommended_identifier: "review-pr",
            evidence_summary:
              "review-pr performs well in primer, but only 1/3 engineers use it there.",
          },
        ]}
      />,
    )

    expect(screen.getByText("primer: review-pr")).toBeInTheDocument()
    expect(screen.getByText("Project Context")).toBeInTheDocument()
    expect(screen.getByText("Debugging")).toBeInTheDocument()
    expect(screen.getByText("primer")).toBeInTheDocument()
    expect(screen.getByText("Skill: review-pr")).toBeInTheDocument()
    expect(
      screen.getByText("review-pr performs well in primer, but only 1/3 engineers use it there."),
    ).toBeInTheDocument()
  })
})
