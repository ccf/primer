import { render, screen } from "@testing-library/react"
import { RecommendationsPanel } from "@/components/dashboard/recommendations-panel"
import type { Recommendation } from "@/types/api"

const sampleRecs: Recommendation[] = [
  {
    category: "friction",
    title: "Too many errors",
    description: "Reduce tool errors",
    severity: "warning",
    evidence: {},
  },
  {
    category: "performance",
    title: "Slow sessions",
    description: "Optimize long-running sessions",
    severity: "critical",
    evidence: {},
  },
]

describe("RecommendationsPanel", () => {
  it("renders 'Recommendations' title", () => {
    render(<RecommendationsPanel data={sampleRecs} />)

    expect(screen.getByText("Recommendations")).toBeInTheDocument()
  })

  it("shows empty state when data is empty", () => {
    render(<RecommendationsPanel data={[]} />)

    expect(
      screen.getByText("No recommendations — everything looks good!"),
    ).toBeInTheDocument()
  })

  it("renders recommendation cards when data is provided", () => {
    render(<RecommendationsPanel data={sampleRecs} />)

    expect(screen.getByText("Too many errors")).toBeInTheDocument()
    expect(screen.getByText("Slow sessions")).toBeInTheDocument()
  })
})
