import { render, screen } from "@testing-library/react"
import { RecommendationCard } from "@/components/dashboard/recommendation-card"
import type { Recommendation } from "@/types/api"

const sampleRec: Recommendation = {
  category: "friction",
  title: "Too many errors",
  description: "Reduce tool errors",
  severity: "warning",
  evidence: {},
}

describe("RecommendationCard", () => {
  it("renders title and description", () => {
    render(<RecommendationCard rec={sampleRec} />)

    expect(screen.getByText("Too many errors")).toBeInTheDocument()
    expect(screen.getByText("Reduce tool errors")).toBeInTheDocument()
  })

  it("renders severity badge", () => {
    render(<RecommendationCard rec={sampleRec} />)

    expect(screen.getByText("warning")).toBeInTheDocument()
  })

  it("renders category badge", () => {
    render(<RecommendationCard rec={sampleRec} />)

    expect(screen.getByText("friction")).toBeInTheDocument()
  })

  it("uses 'secondary' variant for unknown severity", () => {
    const unknownRec: Recommendation = {
      ...sampleRec,
      severity: "unknown-level",
    }

    render(<RecommendationCard rec={unknownRec} />)

    const badge = screen.getByText("unknown-level")
    expect(badge).toBeInTheDocument()
    expect(badge.className).toContain("bg-secondary")
  })
})
