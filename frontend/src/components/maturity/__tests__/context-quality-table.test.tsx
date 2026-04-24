import { render, screen } from "@testing-library/react"

import { ContextQualityTable } from "@/components/maturity/context-quality-table"

describe("ContextQualityTable", () => {
  it("renders an empty state", () => {
    render(<ContextQualityTable rows={[]} />)

    expect(screen.getByText("No context quality signals available yet.")).toBeInTheDocument()
  })

  it("renders context quality rows", () => {
    render(
      <ContextQualityTable
        rows={[
          {
            repository: "acme/api",
            session_count: 12,
            context_quality_score: 82.8,
            guide_coverage_score: 80,
            guide_freshness_score: 100,
            token_efficiency_score: 91.4,
            sensor_coverage_score: 70,
            cache_hit_rate: 0.42,
            avg_input_tokens: 18_500,
            context_usage_coverage_pct: 50,
            tool_coverage_pct: 100,
            model_coverage_pct: 75,
            facet_coverage_pct: 55,
            has_claude_md: true,
            has_agents_md: false,
            readiness_checked_at: "2026-04-20T00:00:00Z",
            top_gaps: ["Add AGENTS.md", "Complete outcome facets"],
          },
        ]}
      />,
    )

    expect(screen.getByText("acme/api")).toBeInTheDocument()
    expect(screen.getByText("12 sessions")).toBeInTheDocument()
    expect(screen.getByText("82.8")).toBeInTheDocument()
    expect(screen.getByText("100 fresh")).toBeInTheDocument()
    expect(screen.getByText("42% cache, 18.5K avg input")).toBeInTheDocument()
    expect(screen.getByText("50% context / 75% models")).toBeInTheDocument()
    expect(screen.getByText("Add AGENTS.md")).toBeInTheDocument()
    expect(screen.getByText("Complete outcome facets")).toBeInTheDocument()
  })
})
