import { render, screen } from "@testing-library/react"
import { OutcomeChart } from "@/components/dashboard/outcome-chart"

describe("OutcomeChart", () => {
  it("returns null for empty data", () => {
    const { container } = render(<OutcomeChart data={{}} />)

    expect(container.firstChild).toBeNull()
  })

  it("renders 'Outcomes' title when data is provided", () => {
    render(<OutcomeChart data={{ success: 10, failure: 3 }} />)

    expect(screen.getByText("Outcomes")).toBeInTheDocument()
  })
})
