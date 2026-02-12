import { render, screen } from "@testing-library/react"
import { ToolRankingChart } from "@/components/dashboard/tool-ranking-chart"
import type { ToolRanking } from "@/types/api"

const sampleData: ToolRanking[] = [
  { tool_name: "Read", total_calls: 100, session_count: 50 },
]

describe("ToolRankingChart", () => {
  it("returns null for empty array", () => {
    const { container } = render(<ToolRankingChart data={[]} />)

    expect(container.firstChild).toBeNull()
  })

  it("renders 'Top Tools' when data is provided", () => {
    render(<ToolRankingChart data={sampleData} />)

    expect(screen.getByText("Top Tools")).toBeInTheDocument()
  })
})
