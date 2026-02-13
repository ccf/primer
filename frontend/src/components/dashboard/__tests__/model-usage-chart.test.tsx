import { render, screen } from "@testing-library/react"
import { ModelUsageChart } from "@/components/dashboard/model-usage-chart"
import type { ModelRanking } from "@/types/api"

const sampleData: ModelRanking[] = [
  {
    model_name: "claude-sonnet-4-5-20250929",
    total_input_tokens: 1000,
    total_output_tokens: 500,
    session_count: 10,
  },
]

describe("ModelUsageChart", () => {
  it("returns null for empty array", () => {
    const { container } = render(<ModelUsageChart data={[]} />)

    expect(container.firstChild).toBeNull()
  })

  it("renders 'Model Usage (tokens)' when data is provided", () => {
    render(<ModelUsageChart data={sampleData} />)

    expect(screen.getByText("Model Usage (tokens)")).toBeInTheDocument()
  })
})
