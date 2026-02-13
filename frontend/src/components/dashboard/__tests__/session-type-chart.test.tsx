import { render, screen } from "@testing-library/react"
import { SessionTypeChart } from "@/components/dashboard/session-type-chart"

describe("SessionTypeChart", () => {
  it("returns null for empty data", () => {
    const { container } = render(<SessionTypeChart data={{}} />)

    expect(container.firstChild).toBeNull()
  })

  it("renders 'Session Types' title when data is provided", () => {
    render(<SessionTypeChart data={{ coding: 15, debugging: 8 }} />)

    expect(screen.getByText("Session Types")).toBeInTheDocument()
  })
})
