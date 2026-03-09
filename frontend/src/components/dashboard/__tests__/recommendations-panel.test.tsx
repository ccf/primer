import { vi } from "vitest"
import { render, screen } from "@testing-library/react"
import { RecommendationsPanel } from "@/components/dashboard/recommendations-panel"
import type { Recommendation } from "@/types/api"

vi.mock("@/hooks/use-api-queries", () => ({
  useEngineers: vi.fn().mockReturnValue({ data: [], isLoading: false }),
}))

vi.mock("@/hooks/use-api-mutations", () => ({
  useCreateIntervention: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
}))

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
    render(<RecommendationsPanel data={sampleRecs} teamId={null} />)

    expect(screen.getByText("Recommendations")).toBeInTheDocument()
  })

  it("shows empty state when data is empty", () => {
    render(<RecommendationsPanel data={[]} teamId={null} />)

    expect(
      screen.getByText("No recommendations — everything looks good!"),
    ).toBeInTheDocument()
  })

  it("renders recommendation cards when data is provided", () => {
    render(<RecommendationsPanel data={sampleRecs} teamId={null} />)

    expect(screen.getByText("Too many errors")).toBeInTheDocument()
    expect(screen.getByText("Slow sessions")).toBeInTheDocument()
  })
})
